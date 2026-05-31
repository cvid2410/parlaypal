<template>
  <div class="askwrap">
    <div class="chat">
      <div class="msg a">Hey 👋 I'm your soccer guy — soon you'll be able to ask me about any match, team, or table across every league we cover.</div>
      <div class="msg a">I'll answer from our own scores, fixtures and standings. I'll never give you a pick — that's what <b>Signals</b> is for.</div>
    </div>

    <div class="soon">
      <div class="ic">💬</div>
      <div class="t">Ask is coming soon</div>
      <p>A free conversational companion over our data. In the meantime, check live <RouterLink to="/scores">Scores</RouterLink> and the <RouterLink to="/leagues">Leagues</RouterLink> we cover.</p>
    </div>

    <div class="chips">
      <span class="chip">La Liga standings</span>
      <span class="chip">Any live scores?</span>
      <span class="chip">Motagua next game</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
onMounted(() => { if (!auth.isAuthed) router.push('/login') })
</script>

<style scoped>
.askwrap { max-width: 720px; color: var(--txt); }
.chat { display: flex; flex-direction: column; gap: 13px; }
.msg { max-width: 76%; padding: 13px 17px; font-size: 14px; line-height: 1.55; }
.msg.a { align-self: flex-start; background: var(--panel); border: 1px solid var(--hair); border-radius: 16px 16px 16px 5px; color: var(--txt-2); }
.msg.a b { color: var(--green); font-weight: 600; }
.soon { text-align: center; margin: 22px 0 16px; padding: 24px; background: linear-gradient(135deg, #0d2417, var(--panel)); border: 1px solid var(--green-dim); border-radius: 16px; }
.soon .ic { font-size: 26px; }
.soon .t { font-size: 16px; font-weight: 800; margin: 8px 0 6px; }
.soon p { font-size: 13px; color: var(--txt-2); line-height: 1.6; }
.soon a { color: var(--green); }
.chips { display: flex; gap: 9px; flex-wrap: wrap; opacity: .45; }
.chip { background: var(--panel); border: 1px solid var(--hair); color: var(--txt-2); font-size: 13px; font-weight: 500; padding: 9px 15px; border-radius: 100px; }
</style>
