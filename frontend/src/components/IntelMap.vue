<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import L from "leaflet";
import "leaflet.markercluster";

const props = defineProps<{
  detections: any[];
  heatmap?: any;
  airports?: any[];
  rasterTilesUrl?: string;
  enableAoiDraw?: boolean;
  enableCompare?: boolean;
  compareLeftTilesUrl?: string;
  compareRightTilesUrl?: string;
}>();
const emit = defineEmits<{ "update:aoi": [any | null] }>();
const mapEl = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;
let layerGroup: L.LayerGroup | null = null;
let clusterLayer: any = null;
let heatLayer: L.LayerGroup | null = null;
let airportLayer: L.LayerGroup | null = null;
let rasterLayer: L.TileLayer | null = null;
let compareLeftLayer: L.TileLayer | null = null;
let compareRightLayer: L.TileLayer | null = null;
let measureLayer: L.LayerGroup | null = null;
const rasterOpacity = ref(0.7);
const showDetections = ref(true);
const showHeatmap = ref(true);
const showAirports = ref(true);
const isFullscreen = ref(false);
const mapLoading = ref(false);
const comparePct = ref(50);
const draggingCompare = ref(false);
const cursorLat = ref<number | null>(null);
const cursorLon = ref<number | null>(null);
const measurementMode = ref(false);
const measuredDistanceM = ref<number | null>(null);
let aoiLayer: L.LayerGroup | null = null;
let aoiPoints: L.LatLng[] = [];
let measurePoints: L.LatLng[] = [];

onMounted(() => {
  if (!mapEl.value) return;
  map = L.map(mapEl.value).setView([23.7, 90.4], 8);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);
  layerGroup = L.layerGroup().addTo(map);
  clusterLayer = (L as any).markerClusterGroup ? (L as any).markerClusterGroup() : null;
  if (clusterLayer) map.addLayer(clusterLayer);
  heatLayer = L.layerGroup().addTo(map);
  airportLayer = L.layerGroup().addTo(map);
  aoiLayer = L.layerGroup().addTo(map);
  measureLayer = L.layerGroup().addTo(map);
  map.doubleClickZoom.disable();
  map.on("mousemove", (e) => {
    cursorLat.value = e.latlng.lat;
    cursorLon.value = e.latlng.lng;
  });
  map.on("click", (e) => {
    if (measurementMode.value && measureLayer) {
      measurePoints.push(e.latlng);
      drawMeasurement();
      return;
    }
    if (!props.enableAoiDraw || !aoiLayer) return;
    aoiPoints.push(e.latlng);
    redrawAoi();
  });
});

const haversineM = (a: L.LatLng, b: L.LatLng) => {
  const R = 6371000;
  const toRad = (v: number) => (v * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lng - a.lng);
  const x =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
};

const drawMeasurement = () => {
  if (!measureLayer) return;
  measureLayer.clearLayers();
  if (measurePoints.length === 0) return;
  measurePoints.forEach((p) => L.circleMarker(p, { radius: 4, color: "#f43f5e" }).addTo(measureLayer!));
  if (measurePoints.length >= 2) {
    L.polyline(measurePoints, { color: "#f43f5e" }).addTo(measureLayer!);
    const last = measurePoints[measurePoints.length - 1];
    const prev = measurePoints[measurePoints.length - 2];
    measuredDistanceM.value = haversineM(prev, last);
    L.marker(last, { opacity: 0.001 })
      .bindTooltip(`${measuredDistanceM.value.toFixed(1)} m`, { permanent: true, direction: "top" })
      .addTo(measureLayer!);
  }
};

const clearMeasurement = () => {
  measurePoints = [];
  measuredDistanceM.value = null;
  measureLayer?.clearLayers();
};

const redrawAoi = () => {
  if (!aoiLayer) return;
  aoiLayer.clearLayers();
  if (aoiPoints.length === 0) return;
  aoiPoints.forEach((p) => L.circleMarker(p, { radius: 4, color: "#facc15" }).addTo(aoiLayer!));
  if (aoiPoints.length >= 2) L.polyline(aoiPoints, { color: "#facc15", dashArray: "4 4" }).addTo(aoiLayer!);
  if (aoiPoints.length >= 3) L.polygon(aoiPoints, { color: "#eab308", fillOpacity: 0.08 }).addTo(aoiLayer!);
};

const clearAoi = () => {
  aoiPoints = [];
  redrawAoi();
  emit("update:aoi", null);
};

const finishAoi = () => {
  if (aoiPoints.length < 3) return;
  const coords = aoiPoints.map((p) => [p.lng, p.lat]);
  coords.push([aoiPoints[0].lng, aoiPoints[0].lat]);
  emit("update:aoi", { type: "Polygon", coordinates: [coords] });
};

watch(
  () => props.detections,
  (items) => {
    if (!layerGroup || !map) return;
    layerGroup.clearLayers();
    if (clusterLayer) clusterLayer.clearLayers();
    if (!showDetections.value) return;
    const asPoint = (geom: any): [number, number] | null => {
      if (!geom) return null;
      if (geom.type === "Point" && geom.coordinates) return [geom.coordinates[1], geom.coordinates[0]];
      if (geom.type === "Polygon" && geom.coordinates?.[0]?.length) {
        const ring = geom.coordinates[0];
        let sx = 0;
        let sy = 0;
        ring.forEach((c: number[]) => {
          sx += c[0];
          sy += c[1];
        });
        return [sy / ring.length, sx / ring.length];
      }
      return null;
    };
    if (items.length > 120 || clusterLayer) {
      const buckets = new Map<string, any[]>();
      items.forEach((d) => {
        const p = asPoint(d.geometry_geojson);
        if (!p) return;
        const key = `${Math.round(p[0] * 20) / 20}_${Math.round(p[1] * 20) / 20}`;
        const arr = buckets.get(key) || [];
        arr.push({ p, d });
        buckets.set(key, arr);
      });
      buckets.forEach((arr) => {
        const lat = arr.reduce((s, x) => s + x.p[0], 0) / arr.length;
        const lon = arr.reduce((s, x) => s + x.p[1], 0) / arr.length;
        const marker = L.circleMarker([lat, lon], { radius: Math.min(18, 6 + arr.length / 5), color: "#06b6d4" })
          .bindPopup(`Cluster: ${arr.length} detections`)
        if (clusterLayer) clusterLayer.addLayer(marker);
        else marker.addTo(layerGroup!);
      });
      return;
    }
    items.forEach((d) => {
      const geom = d.geometry_geojson;
      if (geom?.type === "Polygon") {
        const latlngs = geom.coordinates[0].map((c: number[]) => [c[1], c[0]]);
        const poly = L.polygon(latlngs as any, { color: "#22d3ee", weight: 2 }).bindPopup(
          `${d.class_name} (${d.confidence})`,
        ).bindTooltip(`${d.class_name} ${Number(d.confidence).toFixed(2)}`);
        poly.on("mouseover", () => poly.setStyle({ weight: 3, color: "#67e8f9" }));
        poly.on("mouseout", () => poly.setStyle({ weight: 2, color: "#22d3ee" }));
        poly.addTo(layerGroup!);
      } else if (geom?.type === "Point") {
        L.circleMarker([geom.coordinates[1], geom.coordinates[0]], { color: "#38bdf8" }).bindPopup(
          `${d.class_name} (${d.confidence})`,
        ).addTo(layerGroup!);
      }
    });
  },
  { deep: true },
);

watch(
  () => props.heatmap,
  (heatmap) => {
    if (!heatLayer) return;
    heatLayer.clearLayers();
    if (!showHeatmap.value) return;
    const features = heatmap?.features || [];
    features.forEach((f: any) => {
      const c = f.geometry?.coordinates;
      if (!c) return;
      const weight = Number(f.properties?.weight || 0.5);
      L.circleMarker([c[1], c[0]], {
        radius: 6 + weight * 8,
        color: "#f97316",
        fillOpacity: 0.2 + Math.min(0.7, weight),
      }).addTo(heatLayer!);
    });
  },
  { deep: true },
);

watch(
  () => props.airports,
  (airports) => {
    if (!airportLayer) return;
    airportLayer.clearLayers();
    if (!showAirports.value) return;
    (airports || []).forEach((a: any) => {
      const c = a.geometry?.coordinates;
      if (!c) return;
      L.circleMarker([c[1], c[0]], { radius: 4, color: "#22c55e" })
        .bindPopup(`${a.icao_code || "-"} ${a.name}`)
        .addTo(airportLayer!);
    });
  },
  { deep: true },
);

watch(showDetections, () => {
  if (!layerGroup) return;
  layerGroup.clearLayers();
  if (clusterLayer) clusterLayer.clearLayers();
});
watch(showHeatmap, () => {
  if (!heatLayer) return;
  heatLayer.clearLayers();
});
watch(showAirports, () => {
  if (!airportLayer) return;
  airportLayer.clearLayers();
});

watch(
  () => props.rasterTilesUrl,
  (url) => {
    if (!map) return;
    if (rasterLayer) {
      map.removeLayer(rasterLayer);
      rasterLayer = null;
    }
    if (url) {
      mapLoading.value = true;
      rasterLayer = L.tileLayer(url, { opacity: 0.7, maxZoom: 22 });
      rasterLayer.on("load", () => {
        mapLoading.value = false;
      });
      rasterLayer.on("tileerror", () => {
        mapLoading.value = false;
      });
      rasterLayer.addTo(map);
    }
  },
);

const applyCompareClip = () => {
  const container = (compareRightLayer as any)?.getContainer?.();
  if (container) container.style.clipPath = `inset(0 0 0 ${comparePct.value}%)`;
};

const onCompareDragStart = () => {
  draggingCompare.value = true;
};

const onCompareDragMove = (e: MouseEvent) => {
  if (!draggingCompare.value || !mapEl.value) return;
  const rect = mapEl.value.getBoundingClientRect();
  const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
  comparePct.value = (x / rect.width) * 100;
};

const onCompareDragEnd = () => {
  draggingCompare.value = false;
};

watch(
  () => [props.enableCompare, props.compareLeftTilesUrl, props.compareRightTilesUrl] as const,
  ([enabled, left, right]) => {
    if (!map) return;
    if (compareLeftLayer) {
      map.removeLayer(compareLeftLayer);
      compareLeftLayer = null;
    }
    if (compareRightLayer) {
      map.removeLayer(compareRightLayer);
      compareRightLayer = null;
    }
    if (enabled && left && right) {
      compareLeftLayer = L.tileLayer(left, { opacity: rasterOpacity.value, maxZoom: 22 }).addTo(map);
      compareRightLayer = L.tileLayer(right, { opacity: rasterOpacity.value, maxZoom: 22 }).addTo(map);
      compareRightLayer.on("load", applyCompareClip);
      applyCompareClip();
    }
  },
);

watch(comparePct, applyCompareClip);

watch(rasterOpacity, (v) => {
  if (rasterLayer) rasterLayer.setOpacity(v);
  if (compareLeftLayer) compareLeftLayer.setOpacity(v);
  if (compareRightLayer) compareRightLayer.setOpacity(v);
});

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value;
  setTimeout(() => map?.invalidateSize(), 100);
};

const toggleMeasurement = () => {
  measurementMode.value = !measurementMode.value;
  if (!measurementMode.value) clearMeasurement();
};
</script>

<template>
  <div class="relative" :class="{ 'fixed inset-0 z-[1000] bg-slate-950 p-2': isFullscreen }">
    <div ref="mapEl" class="h-[420px] w-full rounded" :class="{ 'h-[96vh]': isFullscreen }" @mousemove="onCompareDragMove" @mouseup="onCompareDragEnd" @mouseleave="onCompareDragEnd"></div>
    <div class="absolute left-2 top-2 z-[500] rounded bg-slate-900/90 p-2 text-xs text-cyan-100">
      <div class="mb-1 flex items-center gap-2">
        <span>Raster opacity</span>
        <input v-model.number="rasterOpacity" type="range" min="0" max="1" step="0.05" />
      </div>
      <div class="mb-1 flex gap-2">
        <button class="rounded bg-slate-800 px-2 py-1" @click="showDetections = !showDetections">Detections</button>
        <button class="rounded bg-slate-800 px-2 py-1" @click="showHeatmap = !showHeatmap">Heatmap</button>
        <button class="rounded bg-slate-800 px-2 py-1" @click="showAirports = !showAirports">Airports</button>
      </div>
      <div class="mb-1 flex gap-2">
        <button class="rounded bg-slate-800 px-2 py-1" @click="toggleMeasurement">
          {{ measurementMode ? "Stop Measure" : "Measure" }}
        </button>
        <button class="rounded bg-slate-800 px-2 py-1" @click="clearMeasurement">Clear Measure</button>
      </div>
      <div v-if="enableCompare" class="mb-1">
        <label class="mb-1 block">Compare slider</label>
        <input v-model.number="comparePct" type="range" min="0" max="100" step="1" class="w-full" />
      </div>
      <button class="rounded bg-slate-800 px-2 py-1" @click="toggleFullscreen">{{ isFullscreen ? "Exit Fullscreen" : "Fullscreen" }}</button>
    </div>
    <div v-if="mapLoading" class="absolute bottom-2 left-2 z-[500] rounded bg-slate-900/90 px-2 py-1 text-xs text-cyan-200">
      Loading imagery tiles...
    </div>
    <div class="absolute bottom-2 right-2 z-[500] rounded bg-slate-900/90 px-2 py-1 text-xs text-cyan-100">
      {{ cursorLat?.toFixed(5) || "--" }}, {{ cursorLon?.toFixed(5) || "--" }}
    </div>
    <div v-if="enableAoiDraw" class="absolute right-2 top-2 z-[500] flex gap-2">
      <button class="rounded bg-slate-900/90 px-2 py-1 text-xs text-yellow-200" @click="finishAoi">Finish AOI</button>
      <button class="rounded bg-slate-900/90 px-2 py-1 text-xs text-rose-200" @click="clearAoi">Clear AOI</button>
    </div>
    <div
      v-if="enableCompare"
      class="absolute bottom-0 top-0 z-[550] w-1 cursor-col-resize bg-cyan-300/70"
      :style="{ left: `${comparePct}%` }"
      @mousedown.prevent="onCompareDragStart"
    ></div>
  </div>
</template>
