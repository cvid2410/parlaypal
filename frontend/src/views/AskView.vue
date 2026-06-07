<template>
  <div class="ask">
    <div class="inner">
      <div class="chat">
        <div class="msg a">{{ $t('ask.msg1') }}</div>
        <div class="msg a">{{ $t('ask.msg2_a') }}<b>{{ $t('nav.signals') }}</b>{{ $t('ask.msg2_b') }}</div>
      </div>

      <div class="soon">
        <div class="ic" aria-hidden="true">💬</div>
        <div class="t">{{ $t('ask.soon_title') }}</div>
        <p>{{ $t('ask.soon_a') }}<RouterLink to="/scores">{{ $t('nav.scores') }}</RouterLink>{{ $t('ask.soon_mid') }}<RouterLink to="/leagues">{{ $t('nav.leagues') }}</RouterLink>{{ $t('ask.soon_b') }}</p>
      </div>

      <div class="examples">
        <span class="lbl">{{ $t('ask.examples_label') }}</span>
        <div class="chips">
          <span class="chip">{{ $t('ask.ex1') }}</span>
          <span class="chip">{{ $t('ask.ex2') }}</span>
          <span class="chip">{{ $t('ask.ex3') }}</span>
        </div>
      </div>

      <!-- disabled preview of the composer, to make the page feel like the real thing -->
      <div class="composer" aria-hidden="true">
        <span class="ph">{{ $t('ask.placeholder') }}</span>
        <span class="send">→</span>
      </div>
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
.ask { color: var(--txt); }
.inner { width: 100%; max-width: 600px; }

.chat { display: flex; flex-direction: column; gap: 13px; }
.msg { max-width: 88%; padding: 13px 17px; font-size: 14px; line-height: 1.55; }
.msg.a { align-self: flex-start; background: var(--panel); border: 1px solid var(--hair); border-radius: 16px 16px 16px 5px; color: var(--txt-2); }
.msg.a b { color: var(--green); font-weight: 600; }

.soon { text-align: center; margin: 22px 0; padding: 28px 24px; background: linear-gradient(135deg, #0d2417, var(--panel)); border: 1px solid var(--green-dim); border-radius: 18px; }
.soon .ic { font-size: 28px; }
.soon .t { font-size: 17px; font-weight: 800; margin: 10px 0 7px; letter-spacing: -.01em; }
.soon p { font-size: 13px; color: var(--txt-2); line-height: 1.6; max-width: 420px; margin: 0 auto; }
.soon a { color: var(--green); font-weight: 600; }

.examples { margin-bottom: 22px; }
.examples .lbl { display: block; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--txt-3); margin-bottom: 11px; }
.chips { display: flex; gap: 9px; flex-wrap: wrap; }
.chip { background: var(--panel); border: 1px solid var(--hair); color: var(--txt-2); font-size: 13px; font-weight: 500; padding: 9px 15px; border-radius: 100px; }

.composer { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 14px 16px; border: 1px solid var(--hair); border-radius: 14px; background: var(--panel); opacity: .55; }
.composer .ph { font-size: 14px; color: var(--txt-3); }
.composer .send { width: 30px; height: 30px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; border-radius: 9px; background: var(--surface-2); color: var(--txt-3); font-size: 15px; }

@media (max-width: 600px) { .msg { max-width: 100%; } }
</style>
