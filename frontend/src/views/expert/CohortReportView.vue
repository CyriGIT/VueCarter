<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useProjectStore } from '@/stores/projectStore'

const store = useProjectStore()

onMounted(() => {
  store.fetchProjects()
})

const projects = computed(() => store.projects)
const selectedProjects = computed(() => projects.value.filter(project => project.statutSelection === 'selectionne'))
const averageReadiness = computed(() => {
  if (projects.value.length === 0) return 0
  return Math.round(projects.value.reduce((total, project) => total + project.readinessScore, 0) / projects.value.length)
})
</script>

<template>
  <main class="w-full px-4 sm:px-6 lg:px-10 py-6 space-y-6 text-gray-100">
    <header class="border-b border-[#282c37] pb-5">
      <h1 class="text-2xl sm:text-3xl font-black text-white">Rapport de cohorte</h1>
    </header>

    <div v-if="store.isLoading" class="text-sm text-gray-400">Chargement des données...</div>
    <div v-else-if="store.errorMessage" class="text-sm text-rose-400">{{ store.errorMessage }}</div>

    <section class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="bg-[#181a20] border border-[#282c37] rounded-xl p-5">
        <span class="text-xs text-gray-400 block">Projets</span>
        <strong class="text-2xl text-white">{{ projects.length }}</strong>
      </div>
      <div class="bg-[#181a20] border border-[#282c37] rounded-xl p-5">
        <span class="text-xs text-gray-400 block">Sélectionnés</span>
        <strong class="text-2xl text-[#00ff88]">{{ selectedProjects.length }}</strong>
      </div>
      <div class="bg-[#181a20] border border-[#282c37] rounded-xl p-5">
        <span class="text-xs text-gray-400 block">Readiness moyenne</span>
        <strong class="text-2xl text-white">{{ averageReadiness }}%</strong>
      </div>
    </section>

    <section class="bg-[#181a20] border border-[#282c37] rounded-xl overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead class="bg-[#121418] text-xs uppercase text-gray-400">
          <tr>
            <th class="px-4 py-3">Projet</th>
            <th class="px-4 py-3">Commune</th>
            <th class="px-4 py-3">Genre</th>
            <th class="px-4 py-3">Readiness</th>
            <th class="px-4 py-3">Statut</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[#282c37]">
          <tr v-for="project in projects" :key="project.id">
            <td class="px-4 py-3 font-bold text-white">{{ project.nom }}</td>
            <td class="px-4 py-3 text-gray-300">{{ project.commune || 'N/A' }}</td>
            <td class="px-4 py-3 text-gray-300">{{ project.genreMusical || 'N/A' }}</td>
            <td class="px-4 py-3 text-[#00ff88]">{{ project.readinessScore }}%</td>
            <td class="px-4 py-3 text-gray-300">{{ project.statutSelection || 'En attente' }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>
