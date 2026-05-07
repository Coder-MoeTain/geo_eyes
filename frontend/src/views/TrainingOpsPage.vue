<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useIntelStore } from "../stores/intel";

const store = useIntelStore();
const datasetYaml = ref("coco128.yaml");
const epochs = ref(20);
const imgSize = ref(1024);
const batchSize = ref(8);
const model = ref("yolov8m.pt");
const trainingMethod = ref("yolov8-supervised");
const device = ref("0");
const statusText = ref("Idle");
const isPolling = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const progressPct = computed(() => Math.round((store.taskResult?.progress || 0) * 100));
const latestTrainedModel = computed(() => {
  const rows = (store.models || []).filter((m: any) => m?.metrics?.training_method);
  return rows.length ? rows[0] : null;
});

const startTraining = async () => {
  const res = await store.trainModel({
    training_method: trainingMethod.value,
    dataset_yaml: datasetYaml.value,
    epochs: epochs.value,
    img_size: imgSize.value,
    batch_size: batchSize.value,
    model: model.value,
    device: device.value,
  });
  statusText.value = `Training queued: ${res.task_id}`;
  startPolling();
};

const poll = async () => {
  await store.pollTask();
  statusText.value = `Task ${store.taskResult?.status || "unknown"} ${store.taskResult?.message || ""}`.trim();
  const status = String(store.taskResult?.status || "").toLowerCase();
  if (status === "success" || status === "failure" || status === "completed" || status === "failed") {
    stopPolling();
    await store.loadModels();
  }
};

const startPolling = () => {
  if (pollTimer) return;
  isPolling.value = true;
  pollTimer = setInterval(() => {
    void poll();
  }, 2500);
};

const stopPolling = () => {
  if (!pollTimer) return;
  clearInterval(pollTimer);
  pollTimer = null;
  isPolling.value = false;
};

onMounted(async () => {
  await store.loadTrainingOptions();
  await store.loadModels();
});

onBeforeUnmount(() => stopPolling());
</script>

<template>
  <main class="grid grid-cols-1 gap-4 lg:grid-cols-3">
    <section class="lg:col-span-2">
      <h2 class="mb-3 text-cyan-200">Training Operations</h2>
      <p class="mb-4 text-xs text-slate-200/70">
        Tip: choose <span class="font-mono text-emerald-200/70">COCO128</span> to auto-download a labeled dataset and validate your GPU training pipeline end-to-end.
      </p>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
        <select v-model="trainingMethod" class="rounded bg-slate-800 p-2 text-sm md:col-span-2">
          <option
            v-for="m in store.trainingOptions?.methods || [{ id: 'yolov8-supervised', name: 'YOLOv8 Supervised' }]"
            :key="m.id"
            :value="m.id"
          >
            {{ m.name }}
          </option>
        </select>

        <div class="md:col-span-2 grid grid-cols-1 gap-2">
          <select v-model="datasetYaml" class="rounded bg-slate-800 p-2 text-sm">
            <option
              v-for="d in store.trainingOptions?.datasets || [{ id: 'coco128.yaml', name: 'COCO128 (auto-download)' }]"
              :key="d.id"
              :value="d.id"
            >
              {{ d.name }}
            </option>
          </select>
          <input v-model="datasetYaml" class="rounded bg-slate-800 p-2 text-sm" placeholder="dataset yaml path (advanced override)" />
        </div>
        <input v-model.number="epochs" type="number" class="rounded bg-slate-800 p-2 text-sm" placeholder="epochs" />
        <input v-model.number="imgSize" type="number" class="rounded bg-slate-800 p-2 text-sm" placeholder="image size" />
        <input v-model.number="batchSize" type="number" class="rounded bg-slate-800 p-2 text-sm" placeholder="batch size" />
        <select v-model="model" class="rounded bg-slate-800 p-2 text-sm">
          <option
            v-for="m in store.trainingOptions?.base_models || [{ id: 'yolov8m.pt', family: 'YOLOv8', size: 'medium' }]"
            :key="m.id"
            :value="m.id"
          >
            {{ m.id }} ({{ m.size }})
          </option>
        </select>
        <select v-model="device" class="rounded bg-slate-800 p-2 text-sm">
          <option v-for="d in store.trainingOptions?.devices || [{ id: '0', label: 'GPU 0' }, { id: 'cpu', label: 'CPU' }]" :key="d.id" :value="d.id">
            {{ d.label }}
          </option>
        </select>
      </div>
      <div class="mt-3 flex gap-2">
        <button class="btn-intel" @click="startTraining">Start Training Job</button>
        <button class="btn-intel" @click="poll">Poll Job</button>
        <button class="btn-intel" @click="isPolling ? stopPolling() : startPolling()">
          {{ isPolling ? "Stop Auto Poll" : "Auto Poll" }}
        </button>
      </div>
      <div class="mt-3 h-2 rounded bg-slate-700">
        <div class="h-2 rounded bg-cyan-500" :style="{ width: `${progressPct}%` }"></div>
      </div>
      <p class="mt-2 text-xs text-cyan-200">{{ statusText }}</p>
      <p class="mt-1 text-xs text-slate-300">Progress: {{ progressPct }}%</p>
    </section>
    <section>
      <h3 class="mb-2 text-cyan-200">Runbook</h3>
      <ul class="space-y-1 text-xs text-slate-300">
        <li>Use verified YOLO datasets only.</li>
        <li>Prefer GPU for epochs &gt; 20.</li>
        <li>After completion, latest trained model is auto-registered and set active.</li>
      </ul>
      <div class="mt-4 rounded bg-slate-950 p-2 text-xs text-cyan-100">
        <div class="mb-1 text-cyan-300">Latest Trained Model</div>
        <div v-if="latestTrainedModel">
          <div>Name: {{ latestTrainedModel.name }}</div>
          <div>Base: {{ latestTrainedModel.metrics?.base_model || "n/a" }}</div>
          <div>Method: {{ latestTrainedModel.metrics?.training_method || "n/a" }}</div>
          <div>Device: {{ latestTrainedModel.metrics?.device || "n/a" }}</div>
        </div>
        <div v-else>No training model registered yet.</div>
      </div>
    </section>
  </main>
</template>
