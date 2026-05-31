import { defineStore } from 'pinia'
import { ref } from 'vue'

// App-level UI state — currently just the upgrade modal, shared by the sidebar
// Upgrade button and the locked signal cards.
export const useUiStore = defineStore('ui', () => {
  const showUpgrade = ref(false)
  const openUpgrade = () => { showUpgrade.value = true }
  const closeUpgrade = () => { showUpgrade.value = false }
  return { showUpgrade, openUpgrade, closeUpgrade }
})
