<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header class="border-b border-cyan-900/60 bg-slate-900/70 p-4 backdrop-blur">
      <h1 class="text-xl font-semibold text-cyan-300">GeoEye-AI Intelligence Portal</h1>
      <p class="text-xs text-cyan-500">Military-grade Geo Intelligence Dashboard</p>
      <nav class="mt-3 flex flex-wrap gap-2 text-xs">
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/dashboard">Dashboard</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/detections">Detections</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/imagery">Imagery</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/historical">Historical</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/airports">Airports</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/models">Models</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/upload-detect">Upload Detect</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/training">Training Ops</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/alerts">Alerts</router-link>
        <router-link class="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" to="/admin">Admin</router-link>
      </nav>
    </header>
    <router-view />
  </div>
</template>
