<script setup lang="ts">
import { ref } from "vue";
import { useIntelStore } from "../stores/intel";
import IntelMap from "../components/IntelMap.vue";

const store = useIntelStore();
const file = ref<File | null>(null);
const message = ref("");
const imageId = ref<number | null>(null);
const running = ref(false);
const pollTimer = ref<number | null>(null);

const onFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  file.value = target.files?.[0] || null;
};

const runUploadDetection = async () => {
  if (!file.value) return;
  running.value = true;
  const res = await store.uploadAndDetect(file.value);
  imageId.value = res.image_id;
  await store.loadUploadedTileUrl(res.image_id);
  message.value = `Image ${res.image_id} queued. Task: ${res.task_id}`;
  if (pollTimer.value) window.clearInterval(pollTimer.value);
  pollTimer.value = window.setInterval(async () => {
    await store.pollTask();
    const s = String(store.taskResult?.status || "").toLowerCase();
    message.value = `Job ${s || "pending"} | ${store.taskResult?.message || "processing"}`;
    if (s === "success" || s === "failure" || s === "cancelled") {
      if (pollTimer.value) window.clearInterval(pollTimer.value);
      running.value = false;
      await store.loadDetections();
    }
  }, 2000);
};
</script>

<template>
  <main class="p-4">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h2 class="mb-2 text-cyan-300">Uploaded GeoTIFF Detection (Official Workflow)</h2>
      <p class="mb-2 text-xs text-slate-300">Use high-resolution uploaded GeoTIFF for reliable aircraft detection results.</p>
      <input type="file" accept=".tif,.tiff,.png,.jpg,.jpeg" @change="onFileChange" />
      <button class="ml-2 rounded bg-emerald-700 px-3 py-2 text-sm" @click="runUploadDetection">Upload + Detect</button>
      <p class="mt-2 text-xs text-cyan-200">{{ message }}</p>
      <div v-if="store.latestUpload" class="mt-2 rounded bg-slate-950 p-2 text-xs text-cyan-100">
        <p>File: {{ store.latestUpload.filename }}</p>
        <p>CRS: {{ store.latestUpload.crs || "none" }}</p>
        <p>Georeferenced: {{ store.latestUpload.georeferenced ? "yes" : "no" }}</p>
        <p>Resolution(m): {{ store.latestUpload.resolution_m || "n/a" }}</p>
      </div>
      <div class="mt-2 h-2 w-full rounded bg-slate-800">
        <div class="h-2 rounded bg-cyan-500" :style="{ width: `${Math.round((store.taskResult?.progress || 0) * 100)}%` }"></div>
      </div>
      <div class="mt-3">
        <p class="text-xs text-slate-300">Uploaded GeoTIFF tile overlay</p>
        <p class="text-xs text-cyan-300 break-all">{{ store.uploadedTileUrl }}</p>
      </div>
      <IntelMap :detections="store.detections" :raster-tiles-url="store.uploadedTileUrl" />
      <div class="mt-3 max-h-48 overflow-auto rounded bg-slate-950 p-2 text-xs text-cyan-100">
        <table class="w-full text-left">
          <thead>
            <tr>
              <th>ID</th><th>Class</th><th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in store.detections.slice(0, 200)" :key="d.id">
              <td>{{ d.id }}</td><td>{{ d.class_name }}</td><td>{{ Number(d.confidence).toFixed(3) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>
