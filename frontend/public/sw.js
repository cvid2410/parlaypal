self.addEventListener('push', event => {
  if (!event.data) return
  const { title, body, icon } = event.data.json()
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: icon || '/favicon.ico',
      badge: '/favicon.ico',
      vibrate: [200, 100, 200],
    })
  )
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  event.waitUntil(clients.openWindow('/'))
})
