<template>
  <div class="preview">
    <div class="live"><span class="dot" /> signals the moment a line goes soft</div>
    <div class="stack">
      <div v-for="(s, i) in samples" :key="i" class="minicard" :class="s.kind">
        <div class="row">
          <span class="badge">{{ s.badge }}</span>
          <span class="lg">{{ s.lg }}</span>
          <span class="ago">{{ s.ago }}</span>
        </div>
        <div class="body">
          <div class="info">
            <div class="pick">{{ s.pick }}</div>
            <div class="fx">{{ s.fx }}</div>
          </div>
          <div class="metric">
            <div class="v">{{ s.metric }}</div>
            <div class="k">{{ s.label }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Static, illustrative sample signals for the login pitch - one of each type so new users
// see the range. EV lives on soft leagues; arbs/middles are mechanical and span every
// league (incl. the big ones), matching how the product works. Shared by the desktop pitch
// panel and the mobile block under the form.
const samples = [
  { kind: 'ev', badge: 'Value bet', pick: 'Pumas −0.5', fx: 'Pumas vs Necaxa', lg: 'Liga MX · Mexico', metric: '+4.8%', label: 'your edge', ago: '2m' },
  { kind: 'arb', badge: 'Arbitrage', pick: 'Win either way', fx: 'Inter vs Milan', lg: 'Serie A · Italy', metric: '+2.1%', label: 'locked profit', ago: '5m' },
  { kind: 'middle', badge: 'Middle', pick: 'Over 2.5 / Under 3.5', fx: 'Palmeiras vs Grêmio', lg: 'Série A · Brazil', metric: '+6.0%', label: 'middle upside', ago: '8m' },
]
</script>

<style scoped>
.live { display: flex; align-items: center; gap: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--txt-3); margin-bottom: 12px; }
.live .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); animation: lp 1.8s infinite; }
@keyframes lp { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }
.stack { display: flex; flex-direction: column; gap: 10px; }

/* mirrors the Signals cards: accent spine + badge keyed to kind */
.minicard { position: relative; border: 1px solid var(--hair); border-radius: 14px; padding: 14px 16px 14px 18px; background: var(--bg); overflow: hidden; }
.minicard::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent, var(--hair-2)); }
.minicard.ev { --accent: var(--green); }
.minicard.arb { --accent: var(--hair-2); }
.minicard.middle { --accent: #5cb3ff; }
.minicard .row { display: flex; align-items: center; gap: 9px; margin-bottom: 11px; }
.minicard .badge { font-size: 9.5px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 100px; }
.minicard.ev .badge { background: var(--green-dim); color: var(--green); }
.minicard.arb .badge { background: var(--surface-2); color: var(--txt); border: 1px solid var(--hair-2); }
.minicard.middle .badge { background: #0c2536; color: #5cb3ff; }
.minicard .lg { font-size: 11px; color: var(--txt-3); }
.minicard .ago { margin-left: auto; font-family: 'Spline Sans Mono', monospace; font-size: 11px; color: var(--txt-3); }
.minicard .body { display: flex; align-items: center; gap: 12px; }
.minicard .info { flex: 1; min-width: 0; }
.minicard .pick { font-size: 17px; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; }
.minicard .fx { font-size: 11.5px; color: var(--txt-3); margin-top: 4px; }
.minicard .metric { text-align: right; flex-shrink: 0; }
.minicard .metric .v { font-family: 'Spline Sans Mono', monospace; font-size: 18px; font-weight: 600; color: var(--green); line-height: 1; }
.minicard .metric .k { font-size: 9px; color: var(--txt-3); text-transform: uppercase; letter-spacing: .05em; margin-top: 5px; font-weight: 700; white-space: nowrap; }
</style>
