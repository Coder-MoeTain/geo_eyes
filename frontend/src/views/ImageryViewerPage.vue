<script setup lang="ts">
import { ref } from "vue";
import { useIntelStore } from "../stores/intel";
import IntelMap from "../components/IntelMap.vue";
import { apiClient as api } from "../services/api";

const lat = ref(23.7);
const lon = ref(90.4);
const provider = ref("sentinel-2");
const cloudMax = ref(20);
const startDate = ref("");
const endDate = ref("");
const scene = ref<any>(null);
const aoiGeojson = ref<any>(null);
const aoiName = ref("AOI-1");
const savedAois = ref<any[]>([]);
const store = useIntelStore();

const loadScene = async () => {
  const { data } = await api.get("/api/v1/satellite-image", {
    params: {
      latitude: lat.value,
      longitude: lon.value,
      provider: provider.value,
      cloud_max: cloudMax.value,
      start_date: startDate.value || undefined,
      end_date: endDate.value || undefined,
      aoi_geojson: aoiGeojson.value || undefined,
    },
    headers: store.authHeaders(),
  });
  scene.value = data;
};
const updateAoi = (geo: any) => {
  aoiGeojson.value = geo;
  if (geo) localStorage.setItem("geoeye:lastAOI", JSON.stringify(geo));
};

const saveAoi = async () => {
  if (!aoiGeojson.value) return;
  await api.post("/api/v1/aoi", { name: aoiName.value, geojson: aoiGeojson.value }, { headers: store.authHeaders() });
  await loadAois();
};

const loadAois = async () => {
  const { data } = await api.get("/api/v1/aoi", { headers: store.authHeaders() });
  savedAois.value = data.items || [];
};

const applySavedAoi = (raw: any) => {
  aoiGeojson.value = raw?.geojson || null;
};

const loadLocalAoi = () => {
  const raw = localStorage.getItem("geoeye:lastAOI");
  if (raw) {
    try {
      aoiGeojson.value = JSON.parse(raw);
    } catch {
      // ignore
    }
  }
};

loadAois();
loadLocalAoi();
</script>

<template>
  <main class="p-4">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h2 class="mb-2 text-cyan-300">Satellite Imagery Viewer</h2>
      <div class="mb-3 flex gap-2">
        <input v-model.number="lat" type="number" class="rounded bg-slate-800 p-2 text-sm" placeholder="Latitude" />
        <input v-model.number="lon" type="number" class="rounded bg-slate-800 p-2 text-sm" placeholder="Longitude" />
        <select v-model="provider" class="rounded bg-slate-800 p-2 text-sm">
          <option value="sentinel-2">Sentinel-2</option>
          <option value="landsat">Landsat</option>
          <option value="all">All</option>
        </select>
      </div>
      <div class="mb-3 flex gap-2">
        <input v-model="startDate" type="date" class="rounded bg-slate-800 p-2 text-sm" />
        <input v-model="endDate" type="date" class="rounded bg-slate-800 p-2 text-sm" />
        <input v-model.number="cloudMax" type="number" min="0" max="100" class="w-28 rounded bg-slate-800 p-2 text-sm" placeholder="Cloud%" />
        <button class="rounded bg-cyan-600 px-3 py-2 text-sm font-semibold hover:bg-cyan-500" @click="loadScene">
          Load Scene
        </button>
      </div>
      <IntelMap :detections="[]" :enable-aoi-draw="true" @update:aoi="updateAoi" />
      <div class="mt-2 rounded bg-slate-800/60 p-2 text-xs">
        <div class="mb-2 flex gap-2">
          <input v-model="aoiName" class="rounded bg-slate-900 p-1" placeholder="AOI name" />
          <button class="rounded bg-cyan-700 px-2 py-1" @click="saveAoi">Save AOI</button>
          <button class="rounded bg-slate-700 px-2 py-1" @click="loadAois">Refresh AOIs</button>
        </div>
        <div class="max-h-24 overflow-auto">
          <button
            v-for="a in savedAois"
            :key="a.id"
            class="mr-1 mt-1 rounded bg-slate-900 px-2 py-1"
            @click="applySavedAoi(a)"
          >
            {{ a.name || `AOI-${a.id}` }}
          </button>
        </div>
      </div>
      <p class="mt-2 text-xs text-cyan-400">AOI: {{ aoiGeojson }}</p>
      <pre class="overflow-auto rounded bg-slate-950 p-3 text-xs text-cyan-100">{{ scene }}</pre>
    </section>
  </main>
</template>
