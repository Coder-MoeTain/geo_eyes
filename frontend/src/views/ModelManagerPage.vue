<script setup lang="ts">
import { onMounted } from "vue";
import { ref } from "vue";
import { useIntelStore } from "../stores/intel";

const store = useIntelStore();
const uploadMsg = ref("");
const uploadProgress = ref(0);
const file = ref<File | null>(null);
onMounted(async () => {
  await store.loadModels();
});

const onFile = (e: Event) => {
  const target = e.target as HTMLInputElement;
  file.value = target.files?.[0] || null;
};

const upload = async () => {
  if (!file.value) return;
  uploadProgress.value = 10;
  await store.uploadModel(file.value);
  uploadProgress.value = 100;
  uploadMsg.value = "Model uploaded and indexed.";
};
</script>

<template>
  <main class="p-4">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h2 class="mb-2 text-cyan-300">AI Model Manager</h2>
      <div class="mb-3 rounded bg-slate-950 p-2 text-xs">
        <input type="file" accept=".pt" @change="onFile" />
        <button class="ml-2 rounded bg-emerald-700 px-2 py-1" @click="upload">Upload .pt</button>
        <div class="mt-2 h-2 w-full rounded bg-slate-800">
          <div class="h-2 rounded bg-cyan-500" :style="{ width: `${uploadProgress}%` }"></div>
        </div>
        <p class="mt-1 text-cyan-200">{{ uploadMsg }}</p>
      </div>
      <table class="w-full text-left text-sm">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Version</th>
            <th>Checksum</th>
            <th>Active</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in store.models" :key="m.id">
            <td>{{ m.id }}</td>
            <td>{{ m.name }}</td>
            <td>{{ m.version }}</td>
            <td class="max-w-44 truncate text-xs">{{ m.checksum_sha256 || "-" }}</td>
            <td>{{ m.active ? "Yes" : "No" }}</td>
            <td>
              <button class="rounded bg-cyan-700 px-2 py-1 text-xs" @click="store.activateModel(m.id)">Set Active</button>
              <button class="ml-1 rounded bg-amber-700 px-2 py-1 text-xs" @click="store.disableModel(m.id)">Disable</button>
              <button class="ml-1 rounded bg-rose-700 px-2 py-1 text-xs" @click="store.deleteModel(m.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>
