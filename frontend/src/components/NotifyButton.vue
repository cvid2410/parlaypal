<template>
  <button
    class="notify-btn"
    :class="{ subscribed, unsupported }"
    :title="tooltip"
    :disabled="unsupported || loading"
    @click="toggle"
  >
    <span class="bell" v-html="subscribed ? '&#128276;' : '&#128277;'" />
    <span class="notify-label">{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const STORAGE_KEY = 'parlaypal:push-subscribed'

const subscribed = ref(false)
const loading = ref(false)
const unsupported = ref(false)

const label = computed(() => {
  if (unsupported.value) return 'Notifications unavailable'
  if (loading.value) return '...'
  return subscribed.value ? 'Notifications on' : 'Notify me'
})

const tooltip = computed(() => {
  if (unsupported.value) return 'Push notifications are not supported in this browser'
  return subscribed.value
    ? 'Click to turn off match reminders'
    : 'Get a push notification 30 minutes before every WC 2026 match'
})

onMounted(() => {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    unsupported.value = true
    return
  }
  subscribed.value = localStorage.getItem(STORAGE_KEY) === '1'
})

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)))
}

async function subscribe() {
  const permResult = await Notification.requestPermission()
  if (permResult !== 'granted') return

  const keyRes = await fetch('/api/push/vapid-public-key')
  if (!keyRes.ok) return
  const { public_key } = await keyRes.json()

  const reg = await navigator.serviceWorker.ready
  const pushSub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key),
  })

  const subJson = pushSub.toJSON()
  await fetch('/api/push/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      endpoint: subJson.endpoint,
      keys: subJson.keys,
    }),
  })

  subscribed.value = true
  localStorage.setItem(STORAGE_KEY, '1')
}

async function unsubscribe() {
  const reg = await navigator.serviceWorker.ready
  const pushSub = await reg.pushManager.getSubscription()
  if (pushSub) {
    await fetch('/api/push/unsubscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ endpoint: pushSub.endpoint }),
    })
    await pushSub.unsubscribe()
  }
  subscribed.value = false
  localStorage.removeItem(STORAGE_KEY)
}

async function toggle() {
  if (loading.value) return
  loading.value = true
  try {
    if (subscribed.value) await unsubscribe()
    else await subscribe()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.notify-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--muted);
  font-size: 0.8rem;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
  white-space: nowrap;
}

.notify-btn:hover:not(:disabled) {
  border-color: var(--green);
  color: var(--green);
}

.notify-btn.subscribed {
  border-color: var(--green);
  color: var(--green);
  background: rgba(0, 200, 83, 0.07);
}

.notify-btn.unsupported {
  opacity: 0.4;
  cursor: not-allowed;
}

.bell { font-style: normal; font-size: 0.9rem; }
</style>
