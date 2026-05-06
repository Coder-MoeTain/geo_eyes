<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useIntelStore } from "../stores/intel";

const store = useIntelStore();
const audit = ref<any[]>([]);
const apiToken = ref("");
const error = ref("");

const loadAudit = async () => {
  error.value = "";
  try {
    const data = await store.loadAudit(100);
    audit.value = data.items || [];
  } catch (e: any) {
    error.value = e?.response?.data?.detail || "Failed to load audit logs";
  }
};

const rotateToken = async () => {
  error.value = "";
  try {
    apiToken.value = await store.rotateApiToken();
  } catch (e: any) {
    error.value = e?.response?.data?.detail || "Failed to rotate API token";
  }
};

onMounted(loadAudit);
</script>

<template>
  <main class="space-y-4 p-4">
    <section class="rounded-xl border border-cyan-900/50 bg-slate-900/60 p-4">
      <h2 class="mb-2 text-cyan-300">Admin Panel</h2>
      <div class="mb-3 flex gap-2">
        <button class="rounded bg-cyan-700 px-3 py-2 text-sm hover:bg-cyan-600" @click="loadAudit">Refresh Audit</button>
        <button class="rounded bg-emerald-700 px-3 py-2 text-sm hover:bg-emerald-600" @click="rotateToken">Rotate API Token</button>
      </div>
      <p v-if="apiToken" class="mb-2 rounded bg-slate-950 p-2 text-xs text-emerald-300">New API Token: {{ apiToken }}</p>
      <p v-if="error" class="mb-2 text-sm text-rose-300">{{ error }}</p>
      <pre class="h-[360px] overflow-auto rounded bg-slate-950 p-3 text-xs text-cyan-100">{{ audit }}</pre>
    </section>
  </main>
</template>
