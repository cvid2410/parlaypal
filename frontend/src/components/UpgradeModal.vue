<template>
  <div v-if="ui.showUpgrade" class="modal" @click.self="ui.closeUpgrade()">
    <div class="sheet">
      <h3>Unlock the edge</h3>
      <p class="lead">Free shows you scores. <b>Pro</b> shows you where the money is — live, the moment a line goes soft.</p>
      <div class="vmath">Most Bettor members clear the $29 in their first week</div>

      <div class="plan" @click="choose('bettor')">
        <div class="pn">Bettor <span class="pr">$29<small>/mo</small></span></div>
        <div class="pd">All value bets live · every soft league · stake calculator · filter by your books</div>
      </div>
      <div class="plan feat" @click="choose('sharp')">
        <div class="feattag">Most popular</div>
        <div class="pn">Sharp <span class="pr">$79<small>/mo</small></span></div>
        <div class="pd">Everything + live in-play · corners &amp; cards models · instant push · custom alerts</div>
      </div>

      <p v-if="err" class="err">{{ err }}</p>
      <button class="cl" @click="ui.closeUpgrade()">Maybe later</button>
      <p class="devnote">{{ billing.stripe_enabled ? 'Secure checkout via Stripe · cancel anytime.' : 'Dev build: flips your tier instantly (no Stripe key set).' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useUiStore } from '../stores/ui'

const auth = useAuthStore()
const ui = useUiStore()
const billing = ref<{ stripe_enabled: boolean; allow_dev_upgrade: boolean }>({ stripe_enabled: false, allow_dev_upgrade: true })
const err = ref('')

async function loadBilling() {
  try {
    const res = await auth.authFetch('/billing/config')
    if (res.ok) billing.value = await res.json()
  } catch { /* keep dev defaults */ }
}

async function choose(tier: string) {
  err.value = ''
  if (billing.value.stripe_enabled) {
    const res = await auth.authFetch('/billing/checkout', { method: 'POST', body: JSON.stringify({ tier }) })
    if (res.ok) { window.location.href = (await res.json()).url; return }
    err.value = 'Checkout is unavailable right now.'
    return
  }
  await auth.upgrade(tier)
  ui.closeUpgrade()
}

onMounted(loadBilling)
</script>

<style scoped>
.modal { position: fixed; inset: 0; background: rgba(5, 8, 10, .86); backdrop-filter: blur(6px); display: flex; align-items: center; justify-content: center; padding: 18px; z-index: 60; }
.sheet { background: #0c1112; border: 1px solid #222d30; border-radius: 22px; padding: 28px 24px; width: 100%; max-width: 420px; box-shadow: 0 12px 50px rgba(0, 0, 0, .6); }
.sheet h3 { font-size: 24px; font-weight: 800; text-align: center; letter-spacing: -.02em; }
.lead { text-align: center; color: #8a9a9c; font-size: 13px; margin: 9px 0 16px; line-height: 1.55; }
.lead b { color: #1fd65f; }
.vmath { border: 1px solid #0e3f23; background: #0c1f14; border-radius: 12px; padding: 11px; font-size: 12.5px; color: #1fd65f; text-align: center; margin-bottom: 18px; font-weight: 600; }
.plan { border: 1px solid #222d30; border-radius: 15px; padding: 16px 18px; margin-bottom: 11px; cursor: pointer; transition: .18s; }
.plan:hover { border-color: #2f3c40; }
.plan.feat { border-color: #1fd65f; background: #0c1f14; }
.plan .pn { font-size: 16px; font-weight: 800; display: flex; justify-content: space-between; align-items: center; letter-spacing: -.01em; }
.plan .pn .pr { font-family: 'Spline Sans Mono', monospace; font-weight: 600; color: #1fd65f; }
.plan .pn .pr small { font-size: 11px; color: #5f6f71; }
.plan .pd { font-size: 12.5px; color: #8a9a9c; margin-top: 6px; line-height: 1.5; }
.plan .feattag { font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 5px; color: #1fd65f; }
.err { color: #ff5a52; font-size: 12.5px; text-align: center; margin-top: 10px; }
.cl { display: block; width: 100%; margin-top: 8px; background: none; border: none; color: #5f6f71; font-size: 13px; padding: 10px; cursor: pointer; font-weight: 500; }
.devnote { text-align: center; color: #5f6f71; font-size: 10.5px; margin-top: 2px; }
</style>

