<script setup lang="ts">
import { onMounted, ref } from 'vue'
import apiClient from '@/services/api'

interface AnalyticsProject {
  id: number
  nom: string
}

interface MetabaseEmbedResponse {
  url: string
  projects: AnalyticsProject[]
}

const embedUrl = ref('')
const isLoading = ref(true)
const errorMessage = ref('')
const projects = ref<AnalyticsProject[]>([])
const selectedProjectId = ref<number | ''>('')

const loadDashboard = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const response = await apiClient.get<MetabaseEmbedResponse>('/analytics/metabase/embed', {
      params: selectedProjectId.value === '' ? undefined : { project_id: selectedProjectId.value }
    })
    embedUrl.value = response.data.url
    projects.value = response.data.projects
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
      <div class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-end">
        <label v-if="projects.length" class="flex min-w-56 flex-col gap-1 text-xs font-bold text-gray-400">
          Projet
          <select
            v-model="selectedProjectId"
            :disabled="isLoading"
            class="h-9 border border-[#282c37] bg-[#121418] px-3 text-sm text-gray-100 outline-none focus:border-[#00ff88] disabled:opacity-50"
            @change="loadDashboard"
          >
            <option value="">Tous les projets accompagnés</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.nom }}
            </option>
          </select>
        </label>
        <button
          type="button"
          :disabled="isLoading"
          @click="loadDashboard"
          class="h-9 px-3 text-xs font-bold text-gray-200 border border-[#282c37] rounded-lg hover:border-[#7c3aed] disabled:opacity-50"
        >
          Actualiser
        </button>
      </div>
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