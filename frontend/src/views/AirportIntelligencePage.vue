<script setup lang="ts">
import { ref } from "vue";
import { apiClient as api } from "../services/api";
import { useIntelStore } from "../stores/intel";
import IntelMap from "../components/IntelMap.vue";

const store = useIntelStore();
const query = ref("");
const results = ref<any[]>([]);
const selected = ref<any>(null);
const activity = ref<any>(null);
const nearbyDetections = ref<any[]>([]);

const search = async () => {
  const { data } = await api.get("/api/v1/airports/search", {
    params: { q: query.value || "air" },
    headers: store.authHeaders(),
  });
  results.value = data.items || [];
};

const selectAirport = async (row: any) => {
  selected.value = row;
  const detail = await api.get(`/api/v1/airports/${row.id}`, { headers: store.authHeaders() });
  selected.value = detail.data;
  const act = await api.get(`/api/v1/airports/${row.id}/activity`, { headers: store.authHeaders() });
  activity.value = act.data;
  const det = await api.get(`/api/v1/airports/${row.id}/detections`, { headers: store.authHeaders() });
  nearbyDetections.value = (det.data.items || []).map((d: any) => ({
    ...d,
    geometry_geojson: d.geometry,
  }));
};
</script>

<template>
  <main class="grid grid-cols-1 gap-4 p-4 lg:grid-cols-3">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h2 class="mb-2 text-cyan-300">Airport Intelligence</h2>
      <div class="mb-2 flex gap-2">
        <input v-model="query" class="w-full rounded bg-slate-800 p-2 text-sm" placeholder="Search by ICAO / name" />
        <button class="rounded bg-cyan-700 px-2 py-1 text-xs" @click="search">Search</button>
      </div>
      <div class="max-h-72 overflow-auto text-xs">
        <button
          v-for="r in results"
          :key="r.id"
          class="mb-1 block w-full rounded bg-slate-950 px-2 py-1 text-left hover:bg-slate-800"
          @click="selectAirport(r)"
        >
          {{ r.ident || r.iata_code || r.name }} - {{ r.name }}
        </button>
      </div>
      <pre class="mt-2 overflow-auto rounded bg-slate-950 p-2 text-xs text-cyan-100">{{ activity }}</pre>
    </section>
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4 lg:col-span-2">
      <h3 class="mb-2 text-cyan-300">Airport Detection Footprint</h3>
      <IntelMap :detections="nearbyDetections" />
    </section>
  </main>
</template>
