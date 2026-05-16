<template>
  <div class="affiliate-ctas">
    <h3 class="section-title">Place Your Bets</h3>

    <div v-if="loading" class="books-list">
      <div v-for="i in 3" :key="i" class="book-skeleton" />
    </div>

    <div v-else class="books-list">
      <div v-for="book in books" :key="book.key" class="book-card">
        <div class="book-info">
          <span class="book-name">{{ book.name }}</span>
          <span class="book-promo">{{ book.promo }}</span>
        </div>
        <a
          :href="book.url || '#'"
          target="_blank"
          rel="noopener noreferrer sponsored"
          class="book-btn"
        >
          Bet Now
        </a>
      </div>
    </div>

    <p class="disclaimer">21+ only. Gambling problem? Call 1-800-GAMBLER.</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Book {
  key: string
  name: string
  promo: string
  url: string
}

const books = ref<Book[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/config')
    if (!res.ok) throw new Error('Failed to fetch config')
    const data = await res.json()
    books.value = data.books
  } catch {
    books.value = [
      { key: 'draftkings', name: 'DraftKings', promo: 'Bet $5, Get $200 in Bonus Bets', url: '#' },
      { key: 'fanduel', name: 'FanDuel', promo: 'Bet $5, Get $200 in Bonus Bets', url: '#' },
      { key: 'betmgm', name: 'BetMGM', promo: 'First Bet Offer Up to $1,500', url: '#' },
    ]
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.affiliate-ctas {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
}

.section-title {
  font-size: 0.9rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: var(--text);
}

.books-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.book-skeleton {
  height: 52px;
  background: var(--dark);
  border-radius: 6px;
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.book-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  background: var(--dark);
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
}

.book-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.book-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text);
}

.book-promo {
  font-size: 0.75rem;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-btn {
  flex-shrink: 0;
  background: var(--green);
  color: #000;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 6px;
  transition: opacity 0.15s;
}

.book-btn:hover { opacity: 0.85; }

.disclaimer {
  font-size: 0.7rem;
  color: var(--muted);
  text-align: center;
}
</style>
