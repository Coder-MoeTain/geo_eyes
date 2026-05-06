<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useIntelStore } from "../stores/intel";
import IntelMap from "../components/IntelMap.vue";
import { apiClient as api } from "../services/api";

const store = useIntelStore();
const pollMessage = ref("Waiting for task...");
const lat = ref(23.7);
const lon = ref(90.4);
const compareEnabled = ref(false);
const compareLeft = ref("");
const compareRight = ref("");

onMounted(async () => {
  await store.loadDetections();
  await store.loadHeatmap();
  const interval = setInterval(async () => {
    await store.pollTask();
    pollMessage.value = `Task status: ${store.taskResult?.status || "N/A"}`;
    if (store.taskResult?.status === "SUCCESS" || store.taskResult?.status === "FAILURE") {
      await store.loadDetections();
      await store.loadHeatmap();
      clearInterval(interval);
    }
  }, 2000);
});

const loadAirports = async () => {
  await store.loadNearbyAirports(lat.value, lon.value, 75);
};

const exportGeojson = async () => {
  const data = await store.loadDetectionsGeojson(5000);
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/geo+json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "detections.geojson";
  a.click();
  URL.revokeObjectURL(a.href);
};

const exportCsv = () => {
  const header = ["id", "class_name", "confidence", "timestamp"];
  const lines = [header.join(",")].concat(
    store.detections.map((d: any) => [d.id, d.class_name, d.confidence, d.timestamp].join(",")),
  );
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "detections.csv";
  a.click();
  URL.revokeObjectURL(a.href);
};

const cancelJob = async () => {
  await store.cancelTask();
  pollMessage.value = "Task status: cancelled";
};

const review = async (id: number, qa_status: "accepted" | "rejected" | "uncertain") => {
  await api.patch(`/api/v1/detections/${id}/review`, { qa_status }, { headers: store.authHeaders() });
  await store.loadDetections();
};
</script>

<template>
  <main class="grid grid-cols-1 gap-4 p-4 lg:grid-cols-3">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4 lg:col-span-2">
      <h3 class="mb-2 text-cyan-300">Detection Output</h3>
      <p class="mb-3 text-sm text-cyan-500">{{ pollMessage }}</p>
      <div class="mb-2 h-2 w-full rounded bg-slate-800">
        <div class="h-2 rounded bg-cyan-500" :style="{ width: `${Math.round((store.taskResult?.progress || 0) * 100)}%` }"></div>
      </div>
      <p class="mb-2 text-xs text-slate-300">Detections: {{ store.detections.length }}</p>
      <div class="mb-2 flex gap-2">
        <button class="rounded bg-cyan-700 px-2 py-1 text-xs" @click="exportGeojson">Export GeoJSON</button>
        <button class="rounded bg-cyan-700 px-2 py-1 text-xs" @click="exportCsv">Export CSV</button>
        <button class="rounded bg-rose-700 px-2 py-1 text-xs" @click="cancelJob">Cancel Job</button>
      </div>
      <div class="h-[420px] overflow-auto rounded bg-slate-950 p-3 text-xs text-cyan-100">
        <table class="w-full text-left">
          <thead>
            <tr>
              <th>ID</th>
              <th>Class</th>
              <th>Confidence</th>
              <th>Timestamp</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in store.detections" :key="d.id">
              <td>{{ d.id }}</td>
              <td>{{ d.class_name }}</td>
              <td>{{ Number(d.confidence).toFixed(3) }}</td>
              <td>{{ d.timestamp }}</td>
              <td class="space-x-1">
                <button class="rounded bg-emerald-700 px-1 py-0.5 text-[10px]" @click="review(d.id, 'accepted')">Accept</button>
                <button class="rounded bg-rose-700 px-1 py-0.5 text-[10px]" @click="review(d.id, 'rejected')">Reject</button>
                <button class="rounded bg-amber-700 px-1 py-0.5 text-[10px]" @click="review(d.id, 'uncertain')">Uncertain</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h3 class="mb-2 text-cyan-300">Map Layer</h3>
      <div class="mb-2 flex gap-2">
        <input v-model.number="lat" type="number" class="w-1/2 rounded bg-slate-800 p-1 text-xs" placeholder="Lat" />
        <input v-model.number="lon" type="number" class="w-1/2 rounded bg-slate-800 p-1 text-xs" placeholder="Lon" />
        <button class="rounded bg-emerald-700 px-2 text-xs" @click="loadAirports">Airports</button>
      </div>
      <div class="mb-2 rounded bg-slate-800/60 p-2 text-xs">
        <label class="mr-2">
          <input v-model="compareEnabled" type="checkbox" />
          Split Compare
        </label>
        <input v-model="compareLeft" class="mt-1 w-full rounded bg-slate-900 p-1" placeholder="Left tiles URL (e.g. /titiler/cog/tiles/{z}/{x}/{y}.png?url=/data/uploads/a.tif)" />
        <input v-model="compareRight" class="mt-1 w-full rounded bg-slate-900 p-1" placeholder="Right tiles URL" />
      </div>
      <IntelMap
        :detections="store.detections"
        :heatmap="store.heatmap"
        :airports="store.airports"
        :enable-compare="compareEnabled"
        :compare-left-tiles-url="compareLeft || undefined"
        :compare-right-tiles-url="compareRight || undefined"
      />
    </section>
  </main>
</template>
