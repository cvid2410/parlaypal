<template>
  <div class="ask">
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
.ask { max-width: 460px; margin: 0 auto; padding: 16px 12px 30px; color: #eef3f2; font-family: 'Archivo', sans-serif; }
.chat { display: flex; flex-direction: column; gap: 11px; }
.msg { max-width: 86%; padding: 11px 13px; border-radius: 14px; font-size: 13.5px; line-height: 1.5; align-self: flex-start; background: #13191b; border: 1px solid #222d30; border-bottom-left-radius: 4px; }
.msg b { color: #1fd65f; }
.soon { text-align: center; margin: 22px 0 14px; padding: 20px; background: linear-gradient(135deg, #13261b, #13191b); border: 1px solid #0e3f23; border-radius: 14px; }
.soon .ic { font-size: 26px; }
.soon .t { font-size: 15px; font-weight: 800; margin: 8px 0 6px; }
.soon p { font-size: 12.5px; color: #8a9a9c; line-height: 1.5; }
.soon a { color: #1fd65f; }
.chips { display: flex; gap: 7px; flex-wrap: wrap; opacity: .5; }
.chip { background: #13191b; border: 1px solid #222d30; color: #8a9a9c; font-size: 12px; font-weight: 600; padding: 8px 13px; border-radius: 20px; }
</style>
