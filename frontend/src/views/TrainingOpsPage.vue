<script setup lang="ts">
import { ref } from "vue";
import { useIntelStore } from "../stores/intel";

const store = useIntelStore();
const datasetYaml = ref("data/datasets/aircraft/data.yaml");
const epochs = ref(20);
const imgSize = ref(1024);
const batchSize = ref(8);
const model = ref("yolov8m.pt");
const device = ref("cpu");
const statusText = ref("Idle");

const startTraining = async () => {
  const res = await store.trainModel({
    dataset_yaml: datasetYaml.value,
    epochs: epochs.value,
    img_size: imgSize.value,
    batch_size: batchSize.value,
    model: model.value,
    device: device.value,
  });
  statusText.value = `Training queued: ${res.task_id}`;
};

const poll = async () => {
  await store.pollTask();
  statusText.value = `Task ${store.taskResult?.status || "unknown"} ${store.taskResult?.message || ""}`.trim();
};
</script>

<template>
  <main class="grid grid-cols-1 gap-4 p-4 lg:grid-cols-3">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4 lg:col-span-2">
      <h2 class="mb-3 text-cyan-300">Training Operations</h2>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
        <input v-model="datasetYaml" class="rounded bg-slate-800 p-2 text-sm md:col-span-2" placeholder="dataset yaml path" />
        <input v-model.number="epochs" type="number" class="rounded bg-slate-800 p-2 text-sm" placeholder="epochs" />
        <input v-model.number="imgSize" type="number" class="rounded bg-slate-800 p-2 text-sm" placeholder="image size" />
        <input v-model.number="batchSize" type="number" class="rounded bg-slate-800 p-2 text-sm" placeholder="batch size" />
        <input v-model="model" class="rounded bg-slate-800 p-2 text-sm" placeholder="base model" />
        <select v-model="device" class="rounded bg-slate-800 p-2 text-sm">
          <option value="cpu">cpu</option>
          <option value="0">gpu:0</option>
        </select>
      </div>
      <div class="mt-3 flex gap-2">
        <button class="rounded bg-cyan-700 px-3 py-2 text-sm" @click="startTraining">Start Training Job</button>
        <button class="rounded bg-slate-700 px-3 py-2 text-sm" @click="poll">Poll Job</button>
      </div>
      <p class="mt-2 text-xs text-cyan-200">{{ statusText }}</p>
    </section>
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h3 class="mb-2 text-cyan-300">Runbook</h3>
      <ul class="space-y-1 text-xs text-slate-300">
        <li>Use verified YOLO datasets only.</li>
        <li>Prefer GPU for epochs &gt; 20.</li>
        <li>After completion, upload/activate best weights in Model Manager.</li>
      </ul>
    </section>
  </main>
</template>
