<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useIntelStore } from "../stores/intel";
import IntelMap from "../components/IntelMap.vue";

const router = useRouter();
const store = useIntelStore();
const lat = ref(23.7);
const lon = ref(90.4);
const provider = ref("sentinel-2");
const cloudMax = ref(20);
const startDate = ref("");
const endDate = ref("");

onMounted(async () => {
  await store.loadStats();
  await store.loadModels();
  await store.loadDetections();
  await store.loadHeatmap();
});

const detect = async () => {
  await store.triggerDetection({
    latitude: lat.value,
    longitude: lon.value,
    provider: provider.value,
    cloud_max: cloudMax.value,
    start_date: startDate.value || null,
    end_date: endDate.value || null,
  });
  router.push("/detections");
};
</script>

<template>
  <main class="grid grid-cols-1 gap-4 p-4 lg:grid-cols-3">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h3 class="mb-3 text-lg text-cyan-300">Target Acquisition</h3>
      <div class="space-y-3">
        <input v-model.number="lat" type="number" class="w-full rounded bg-slate-800 p-2" placeholder="Latitude" />
        <input v-model.number="lon" type="number" class="w-full rounded bg-slate-800 p-2" placeholder="Longitude" />
        <select v-model="provider" class="w-full rounded bg-slate-800 p-2">
          <option value="sentinel-2">Sentinel-2</option>
          <option value="landsat">Landsat</option>
          <option value="all">All (STAC)</option>
        </select>
        <div>
          <label class="text-xs text-slate-300">Cloud Cover Max: {{ cloudMax }}%</label>
          <input v-model.number="cloudMax" type="range" min="0" max="100" class="w-full" />
        </div>
        <input v-model="startDate" type="date" class="w-full rounded bg-slate-800 p-2" />
        <input v-model="endDate" type="date" class="w-full rounded bg-slate-800 p-2" />
        <button class="w-full rounded bg-emerald-600 p-2 font-semibold hover:bg-emerald-500" @click="detect">
          Run AI Detection
        </button>
      </div>
    </section>
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4 lg:col-span-2">
      <h3 class="mb-3 text-lg text-cyan-300">Activity Statistics</h3>
      <div class="mb-3 grid grid-cols-2 gap-2 text-xs">
        <div class="rounded bg-slate-950 p-2">
          <p class="text-slate-400">Total Detections</p>
          <p class="text-cyan-200">{{ store.detections.length }}</p>
        </div>
        <div class="rounded bg-slate-950 p-2">
          <p class="text-slate-400">Active Model</p>
          <p class="text-cyan-200">{{ (store.models.find((m: any) => m.active) || {}).name || "unknown" }}</p>
        </div>
      </div>
      <pre class="overflow-auto rounded bg-slate-950 p-3 text-xs text-cyan-100">{{ store.stats }}</pre>
      <div class="mt-3">
        <IntelMap :detections="store.detections" :heatmap="store.heatmap" />
      </div>
    </section>
  </main>
</template>
