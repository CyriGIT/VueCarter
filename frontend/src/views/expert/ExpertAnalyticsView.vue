<script setup lang="ts">
import { onMounted, ref } from 'vue'
import apiClient from '@/services/api'

const embedUrl = ref('')
const isLoading = ref(true)
const errorMessage = ref('')

const loadDashboard = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const response = await apiClient.get<{ url: string }>('/analytics/metabase/embed')
    embedUrl.value = response.data.url
  } catch (error: any) {
    embedUrl.value = ''
    errorMessage.value = error.response?.data?.detail || 'Le tableau de bord analytique est indisponible.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <div class="min-h-full w-full px-4 py-6 sm:px-6 lg:px-10">
    <header class="mb-5 flex flex-col gap-3 border-b border-[#282c37] pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <span class="text-xs font-bold uppercase text-[#00ff88]">Pilotage des parcours</span>
        <h1 class="mt-1 text-2xl font-black text-white sm:text-3xl">Analyses diachroniques</h1>
        <p class="mt-1 text-sm text-gray-400">Concerts, audience, sorties, collaborations et structuration des projets.</p>
      </div>
      <button
        type="button"
        :disabled="isLoading"
        @click="loadDashboard"
        class="px-3 py-2 text-xs font-bold text-gray-200 border border-[#282c37] rounded-lg hover:border-[#7c3aed] disabled:opacity-50"
      >
        Actualiser
      </button>
    </header>

    <div v-if="isLoading" class="flex min-h-[65vh] items-center justify-center border border-[#282c37] bg-[#181a20] text-sm text-gray-400">
      Chargement du tableau de bord…
    </div>

    <div v-else-if="errorMessage" class="flex min-h-[40vh] flex-col items-center justify-center gap-4 border border-rose-500/30 bg-[#181a20] px-6 text-center">
      <p class="text-sm text-rose-400">{{ errorMessage }}</p>
      <button type="button" @click="loadDashboard" class="px-4 py-2 text-xs font-bold text-white bg-[#7c3aed] rounded-lg hover:bg-[#6d28d9]">
        Réessayer
      </button>
    </div>

    <iframe
      v-else
      :src="embedUrl"
      title="Tableau de bord Metabase des parcours artistiques"
      class="h-[calc(100vh-12rem)] min-h-170 w-full border-0 bg-[#181a20]"
      allowtransparency
    ></iframe>
  </div>
</template>