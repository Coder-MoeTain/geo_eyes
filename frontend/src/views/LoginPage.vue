<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useIntelStore } from "../stores/intel";

const store = useIntelStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref<string>("");
const loading = ref(false);

const submit = async () => {
  error.value = "";
  loading.value = true;
  try {
    await store.login(username.value, password.value);
    router.push("/dashboard");
  } catch (e: any) {
    error.value = String(e?.message || "Login failed");
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <main class="relative z-10 mx-auto flex min-h-screen max-w-6xl items-center justify-center px-6 py-10">
    <div class="grid w-full max-w-4xl grid-cols-1 gap-6 lg:grid-cols-2">
      <section class="glass-panel rounded-3xl p-8">
        <div class="mono-kicker">AUTHORIZED PERSONNEL ONLY</div>
        <h1 class="mt-2 text-3xl font-bold text-cyan-200">Secure Access Gateway</h1>
        <p class="mt-3 text-sm leading-relaxed text-slate-200/70">
          Authenticate to access the GeoEye operational console. All actions are audited. Unapproved access attempts are monitored.
        </p>
        <div class="mt-6 rounded-2xl border border-cyan-900/30 bg-slate-950/30 p-4 font-mono text-[11px] text-emerald-200/70">
          <div>LINK: ENCRYPTED</div>
          <div>SESSION: CONTROLLED</div>
          <div>MODE: GEOINT / AIRCRAFT</div>
        </div>
      </section>

      <section class="glass-panel rounded-3xl p-8">
        <div class="mono-kicker">CREDENTIALS</div>
        <h2 class="mt-2 text-xl font-semibold text-slate-100/90">Operator Login</h2>

        <div class="mt-6 space-y-4">
          <input
            v-model="username"
            class="w-full rounded-xl border border-cyan-900/30 bg-slate-950/40 p-3 text-slate-100 placeholder:text-slate-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-600/40"
            placeholder="Username"
            autocomplete="username"
          />
          <input
            v-model="password"
            type="password"
            class="w-full rounded-xl border border-cyan-900/30 bg-slate-950/40 p-3 text-slate-100 placeholder:text-slate-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-600/40"
            placeholder="Password"
            autocomplete="current-password"
            @keyup.enter="submit"
          />

          <button
            class="w-full rounded-xl border border-cyan-700/40 bg-cyan-500/15 px-4 py-3 font-semibold text-cyan-100 hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="loading || !username || !password"
            @click="submit"
          >
            {{ loading ? "Authorizing..." : "Authenticate" }}
          </button>

          <p v-if="error" class="rounded-xl border border-rose-900/40 bg-rose-950/30 p-3 text-sm text-rose-200">
            {{ error }}
          </p>
        </div>
      </section>
    </div>
  </main>
</template>
