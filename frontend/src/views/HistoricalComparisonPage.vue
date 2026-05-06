<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useIntelStore } from "../stores/intel";
import IntelMap from "../components/IntelMap.vue";
import { apiClient as api } from "../services/api";

const store = useIntelStore();
const beforeImageId = ref<number | null>(null);
const afterImageId = ref<number | null>(null);
const result = ref<any>(null);
const uploads = ref<any[]>([]);
const leftTiles = ref("");
const rightTiles = ref("");
const layer = ref("new_aircraft");

const compare = async () => {
  if (!beforeImageId.value || !afterImageId.value) return;
  const { data } = await api.post("/api/v1/change-detection", {}, {
    headers: store.authHeaders(),
    params: { before_image_id: beforeImageId.value, after_image_id: afterImageId.value, match_distance_m: 40 },
  });
  result.value = data;
};

const asDetectionFeatures = () => {
  const features = result.value?.[layer.value]?.features || [];
  return features.map((f: any, idx: number) => ({
    id: idx + 1,
    class_name: f.properties?.class_name || layer.value,
    confidence: Number(f.properties?.confidence || 0),
    geometry_geojson: f.geometry,
    timestamp: new Date().toISOString(),
  }));
};

const loadUploads = async () => {
  const { data } = await api.get("/api/v1/uploads", { headers: store.authHeaders() });
  uploads.value = data.items || [];
};

const loadTiles = async () => {
  if (!beforeImageId.value || !afterImageId.value) return;
  const a = await api.get(`/api/v1/uploaded-image/${beforeImageId.value}/tiles`, { headers: store.authHeaders() });
  const b = await api.get(`/api/v1/uploaded-image/${afterImageId.value}/tiles`, { headers: store.authHeaders() });
  leftTiles.value = a.data.tiles_url;
  rightTiles.value = b.data.tiles_url;
};

onMounted(loadUploads);
</script>

<template>
  <main class="p-4">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h2 class="mb-2 text-cyan-300">Historical Comparison</h2>
      <div class="mb-2 flex gap-2">
        <select v-model.number="beforeImageId" class="rounded bg-slate-800 p-2 text-sm">
          <option :value="null">Before image</option>
          <option v-for="u in uploads" :key="u.id" :value="u.id">{{ u.id }} - {{ u.filename }}</option>
        </select>
        <select v-model.number="afterImageId" class="rounded bg-slate-800 p-2 text-sm">
          <option :value="null">After image</option>
          <option v-for="u in uploads" :key="u.id" :value="u.id">{{ u.id }} - {{ u.filename }}</option>
        </select>
        <button class="rounded bg-slate-700 px-3 py-2 text-sm" @click="loadTiles">Load Split Tiles</button>
        <button class="rounded bg-cyan-700 px-3 py-2 text-sm" @click="compare">Compare</button>
      </div>
      <div class="mb-2 rounded bg-slate-800/60 p-2 text-xs">
        <label class="mr-2">Layer</label>
        <select v-model="layer" class="rounded bg-slate-900 p-1">
          <option value="new_aircraft">New (green)</option>
          <option value="removed_aircraft">Removed (red)</option>
          <option value="moved_aircraft">Moved (yellow)</option>
          <option value="unchanged_aircraft">Unchanged (blue)</option>
          <option value="uncertain">Uncertain</option>
        </select>
      </div>
      <IntelMap
        :detections="asDetectionFeatures()"
        :enable-compare="true"
        :compare-left-tiles-url="leftTiles || undefined"
        :compare-right-tiles-url="rightTiles || undefined"
      />
      <div class="mt-2 rounded bg-slate-950 p-2 text-xs text-cyan-100">
        <p>Summary: {{ result?.summary || {} }}</p>
      </div>
      <pre class="overflow-auto rounded bg-slate-950 p-3 text-xs text-cyan-100">{{ result }}</pre>
    </section>
  </main>
</template>
