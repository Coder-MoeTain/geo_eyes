<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useIntelStore } from "../stores/intel";

const store = useIntelStore();
const router = useRouter();
const username = ref("");
const password = ref("");

const submit = async () => {
  await store.login(username.value, password.value);
  router.push("/dashboard");
};
</script>

<template>
  <main class="mx-auto mt-16 max-w-md rounded-2xl border border-cyan-800/40 bg-slate-900/60 p-8 shadow-2xl">
    <h2 class="mb-6 text-2xl font-bold text-cyan-200">Secure Access</h2>
    <div class="space-y-4">
      <input v-model="username" class="w-full rounded bg-slate-800 p-3" placeholder="Username" />
      <input v-model="password" type="password" class="w-full rounded bg-slate-800 p-3" placeholder="Password" />
      <button class="w-full rounded bg-cyan-600 px-4 py-3 font-semibold hover:bg-cyan-500" @click="submit">
        Login
      </button>
    </div>
  </main>
</template>
