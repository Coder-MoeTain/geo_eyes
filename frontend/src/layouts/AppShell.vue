<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useIntelStore } from "../stores/intel";

const route = useRoute();
const router = useRouter();
const store = useIntelStore();

const username = computed(() => (store as any).username || "operator");

const nav = [
  { to: "/dashboard", label: "Dashboard", hint: "overview" },
  { to: "/detections", label: "Detections", hint: "signals" },
  { to: "/imagery", label: "Imagery", hint: "map" },
  { to: "/historical", label: "Historical", hint: "compare" },
  { to: "/airports", label: "Airports", hint: "targets" },
  { to: "/upload-detect", label: "Upload/Detect", hint: "ingest" },
  { to: "/alerts", label: "Alerts", hint: "watch" },
  { to: "/models", label: "Models", hint: "registry", admin: true },
  { to: "/training", label: "Training", hint: "gpu ops", admin: true },
  { to: "/admin", label: "Admin", hint: "audit", admin: true },
];

const visibleNav = computed(() => nav.filter((n) => !n.admin || store.role === "admin"));

const logout = async () => {
  // frontend keeps a token; backend also uses cookies. Clear local state and send user to login.
  store.token = "";
  store.role = "user";
  store.taskId = "";
  router.push("/login");
};
</script>

<template>
  <div class="relative z-10 flex min-h-screen">
    <aside class="glass-panel w-[280px] shrink-0 border-r border-cyan-900/40">
      <div class="p-5">
        <div class="mono-kicker">MILITARY INTELLIGENCE</div>
        <div class="mt-1 text-lg font-semibold text-cyan-200">GeoEye Ops Console</div>
        <div class="mt-1 text-xs text-slate-300/70">Secure GEOINT workstation</div>
      </div>

      <nav class="px-3 pb-4">
        <router-link
          v-for="item in visibleNav"
          :key="item.to"
          :to="item.to"
          class="nav-item mb-1 border border-transparent"
          :class="route.path === item.to ? 'nav-item-active' : ''"
        >
          <span class="w-20 font-mono text-[11px] uppercase tracking-widest text-emerald-200/60">{{ item.hint }}</span>
          <span class="font-semibold">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="mt-auto border-t border-cyan-900/30 p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="mono-kicker">SIGNED IN</div>
            <div class="text-sm font-semibold text-slate-100/90">{{ username }}</div>
            <div class="text-xs text-slate-300/60">role: {{ store.role }}</div>
          </div>
          <button class="btn-intel" @click="logout">Logout</button>
        </div>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="glass-surface border-b border-cyan-900/30 px-6 py-4">
        <div class="flex items-center justify-between gap-4">
          <div>
            <div class="mono-kicker">OPERATIONAL VIEW</div>
            <div class="text-base font-semibold text-slate-100/90">
              {{ (route.meta?.title as string) || "Intel Feed" }}
            </div>
          </div>
          <div class="hidden items-center gap-3 md:flex">
            <div class="rounded-full border border-cyan-700/30 bg-slate-950/30 px-3 py-2 font-mono text-[11px] tracking-widest text-cyan-200/80">
              STATUS: ACTIVE
            </div>
          </div>
        </div>
      </header>

      <main class="min-w-0 flex-1 p-6">
        <div class="glass-panel rounded-2xl p-5">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>

