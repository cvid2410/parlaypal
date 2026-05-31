<template>
  <div class="legal">
    <header class="lhead">
      <RouterLink to="/" class="brand"><span class="mark" /><span class="wm">Parlay<span class="g">Pal</span></span></RouterLink>
      <RouterLink to="/" class="back">← Back to app</RouterLink>
    </header>
    <article class="doc">
      <h1>{{ title }}</h1>
      <p class="updated">Last updated: {{ updated }}</p>
      <slot />
    </article>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; updated: string }>()
</script>

<style scoped>
.legal { min-height: 100vh; }
.lhead { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid var(--hair); background: var(--panel); position: sticky; top: 0; backdrop-filter: blur(12px); }
.brand { display: flex; align-items: center; gap: 10px; }
.brand .mark { width: 10px; height: 10px; border-radius: 50%; background: var(--green); box-shadow: 0 0 10px var(--green); }
.brand .wm { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 19px; font-weight: 700; letter-spacing: -.02em; color: var(--txt); }
.brand .g { color: var(--green); }
.back { font-size: 13px; color: var(--txt-2); font-weight: 600; }
.back:hover { color: var(--txt); }
.doc { max-width: 760px; margin: 0 auto; padding: 44px 24px 80px; }
.doc h1 { font-family: 'Archivo Narrow', 'Archivo', sans-serif; font-size: 34px; font-weight: 700; letter-spacing: -.02em; }
.updated { color: var(--txt-3); font-size: 13px; margin: 8px 0 36px; }

:slotted(section) { margin-bottom: 28px; }
:slotted(h2) { font-size: 15px; font-weight: 700; margin-bottom: 9px; color: var(--txt); letter-spacing: -.01em; }
:slotted(p) { font-size: 14px; color: var(--txt-2); line-height: 1.7; margin-bottom: 10px; }
:slotted(ul) { padding-left: 20px; margin-bottom: 10px; }
:slotted(li) { font-size: 14px; color: var(--txt-2); line-height: 1.7; margin-bottom: 5px; }
:slotted(a) { color: var(--green); text-decoration: none; border-bottom: 1px solid var(--green-dim); }
:slotted(a:hover) { opacity: .85; }
:slotted(strong) { color: var(--txt); font-weight: 600; }
:slotted(.callout) { border: 1px solid var(--green-dim); background: #0c1f14; border-radius: 12px; padding: 14px 16px; font-size: 13.5px; color: var(--txt); line-height: 1.6; margin-bottom: 28px; }
</style>
