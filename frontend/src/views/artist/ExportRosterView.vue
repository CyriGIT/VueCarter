<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projectStore'
import { resolveProjectVideo } from '@/utils/projectVideo'

const router = useRouter()
const route = useRoute()
const store = useProjectStore()
const isLoading = ref(true)
const requestedProjectId = computed(() => {
  const rawId = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  return /^\d+$/.test(rawId || '') ? Number(rawId) : null
})
const selectedProject = computed(() => (
  requestedProjectId.value === null
    ? undefined
    : store.projects.find(project => project.id === requestedProjectId.value)
))

const projectRoster = computed(() => {
  const project = selectedProject.value
  if (!project) return undefined
  const bookingMember = project.members[0]
  const featuredVideo = resolveProjectVideo(project.assets)

  return {
    id: project.id,
    nom: project.nom,
    genre: project.genreMusical,
    langueChant: project.langueChant,
    localite: project.commune || 'Suisse',
    statutJuridique: project.statutJuridique,
    suisaInscrit: project.suisaInscrit,
    pitchAccroche: project.pitchAccroche || project.bioCourte,
    bioComplete: project.bioComplete || project.bioCourte,
    highlights: project.highlights || [],
    featuredVideo,
    topTracks: project.tracks.map(track => ({
      id: track.id,
      titre: track.titre,
      duree: track.duree,
      streams: track.streamsCount || 'N/A',
      isrc: track.isrc
    })),
    tourDates: project.concerts.map(concert => ({
      date: concert.date,
      salle: concert.lieu,
      ville: concert.ville,
      type: concert.type
    })),
    bookingContact: {
      nom: bookingMember ? `${bookingMember.prenom} ${bookingMember.nom}` : 'Non renseigné',
      email: bookingMember?.email || '',
      tel: bookingMember?.telephone || ''
    },
    platforms: {
      spotify: store.connectors.spotify.profileUrl || ''
    }
  }
})

onMounted(async () => {
  if (requestedProjectId.value === null) {
    isLoading.value = false
    return
  }
  store.setSelectedProject(requestedProjectId.value)
  await store.fetchProjects()
  if (selectedProject.value) await store.fetchConnectors(selectedProject.value.id)
  isLoading.value = false
})

// Impression / Génération PDF
const triggerPrint = () => {
  window.print()
}
</script>

<template>
  <div v-if="isLoading" class="w-full min-h-screen bg-[#0e0f12] px-6 py-10 text-sm text-gray-400">
    Chargement de la fiche roster...
  </div>
  <div v-else-if="!projectRoster" class="w-full min-h-screen bg-[#0e0f12] px-6 py-10 text-gray-300 space-y-4">
    <p>Cette fiche roster est introuvable ou vous n’y avez pas accès.</p>
    <button type="button" @click="router.back()" class="px-3 py-1.5 rounded-lg border border-[#282c37] text-xs font-bold text-gray-300 hover:text-white">
      ← Retour
    </button>
  </div>
  <div v-else class="w-full min-h-screen bg-[#0e0f12] text-gray-100 py-6 px-4 sm:px-8 lg:px-16 print:bg-white print:text-black print:p-0">
    
    <!-- Barre d'outils (Non imprimée) -->
    <div class="max-w-6xl mx-auto flex items-center justify-between border-b border-[#282c37] pb-4 mb-8 print:hidden">
      <button 
        @click="router.back()" 
        class="text-xs font-bold text-gray-400 hover:text-white px-3 py-1.5 rounded-lg bg-[#181a20] border border-[#282c37] cursor-pointer"
      >
        ← Retour
      </button>

      <div class="flex items-center gap-3">
        <span class="text-xs text-gray-400">Aperçu fiche vitrine (Roster Press-Kit)</span>
        <button 
          @click="triggerPrint" 
          class="px-4 py-2 bg-[#00ff88] hover:bg-[#00e57a] text-black font-black text-xs rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 shadow-lg shadow-[#00ff88]/20"
        >
          <span>📄</span> Imprimer / Exporter en PDF
        </button>
      </div>
    </div>

    <!-- Conteneur du roster exporté -->
    <div class="max-w-6xl mx-auto space-y-10 print:space-y-6">
      
      <!-- 1. Hero Header : Nom, Genre & Accroche -->
      <section class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center border-b border-[#282c37] pb-8 print:border-gray-300">
        <div class="lg:col-span-8 space-y-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs uppercase font-extrabold px-2.5 py-1 rounded bg-[#7c3aed]/20 text-[#7c3aed] border border-[#7c3aed]/30 print:bg-gray-100 print:text-black">
              {{ projectRoster.genre }}
            </span>
            <span class="text-xs px-2.5 py-1 rounded bg-[#181a20] text-gray-400 border border-[#282c37] print:border-gray-300">
              📍 {{ projectRoster.localite }}
            </span>
            <span class="text-xs px-2.5 py-1 rounded bg-[#181a20] text-[#00ff88] border border-[#00ff88]/30 font-semibold print:text-black">
              {{ projectRoster.suisaInscrit ? 'SUISA ✓' : '' }} · {{ projectRoster.statutJuridique }}
            </span>
          </div>

          <h1 class="text-4xl sm:text-6xl font-black tracking-tight text-white print:text-black">
            {{ projectRoster.nom }}
          </h1>

          <p class="text-base sm:text-lg text-gray-300 font-medium leading-relaxed italic print:text-gray-800">
            "{{ projectRoster.pitchAccroche }}"
          </p>
        </div>

        <!-- Liens rapides / Booking Contact Box -->
        <div class="lg:col-span-4 bg-[#181a20] border border-[#282c37] rounded-2xl p-5 space-y-3 print:border-gray-300 print:bg-gray-50">
          <span class="text-[10px] uppercase font-bold text-gray-400 block tracking-widest">Booking & Management</span>
          <div>
            <strong class="text-sm text-white block print:text-black">{{ projectRoster.bookingContact.nom }}</strong>
            <span class="text-xs text-[#00ff88] block font-mono print:text-black">{{ projectRoster.bookingContact.email }}</span>
            <span class="text-xs text-gray-400 block font-mono">{{ projectRoster.bookingContact.tel }}</span>
          </div>

          <!-- Puces Plateformes d'Écoute -->
          <div class="flex flex-wrap gap-2 pt-2 border-t border-[#282c37] print:hidden">
            <a v-if="projectRoster.platforms.spotify" :href="projectRoster.platforms.spotify" target="_blank" class="text-[11px] px-2.5 py-1 rounded bg-[#121418] border border-[#282c37] hover:border-[#00ff88] text-gray-300 transition-colors">
              🟢 Spotify
            </a>
          </div>
        </div>
      </section>

      <!-- 2. Bloc Multimédia : Vidéo Phare & Biographie Détaillée -->
      <section class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        <!-- Intégration Vidéo Clip / Live -->
        <div class="lg:col-span-7 space-y-3">
          <div class="w-full aspect-video rounded-2xl overflow-hidden border border-[#282c37] bg-[#121418] shadow-2xl relative group">
            <iframe 
              v-if="projectRoster.featuredVideo?.kind === 'youtube'"
              :src="projectRoster.featuredVideo.url"
              class="w-full h-full" 
              :title="projectRoster.featuredVideo.title"
              frameborder="0" 
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
              allowfullscreen
            ></iframe>
            <video
              v-else-if="projectRoster.featuredVideo?.kind === 'file'"
              :src="projectRoster.featuredVideo.url"
              :aria-label="projectRoster.featuredVideo.title"
              class="w-full h-full object-contain"
              controls
              preload="metadata"
            ></video>
            <div v-else class="w-full h-full flex items-center justify-center px-6 text-center text-sm text-gray-400">
              Aucune vidéo lisible n’est configurée pour ce projet.
            </div>
          </div>
          <div class="flex justify-between text-xs text-gray-400">
            <span>{{ projectRoster.featuredVideo?.title || projectRoster.nom }}</span>
            <span class="text-[11px]">{{ projectRoster.featuredVideo?.credits || '' }}</span>
          </div>
        </div>

        <!-- Biographie Complète & Identité -->
        <div class="lg:col-span-5 space-y-4">
          <h2 class="text-lg font-bold text-white uppercase tracking-wider print:text-black">
            Présentation du projet
          </h2>
          <p class="text-sm text-gray-300 leading-relaxed text-justify print:text-black">
            {{ projectRoster.bioComplete }}
          </p>
        </div>
      </section>

      <!-- 3. Grille 3 Blocs : Éléments Marquants, Top Tracks & Dates Live -->
      <section class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t border-[#282c37] print:border-gray-300">
        
        <!-- Bloc A : Faits Marquants & Reconnaissance par les Pairs -->
        <div class="bg-[#181a20] border border-[#282c37] rounded-xl p-5 space-y-3 print:border-gray-300 print:bg-transparent">
          <h3 class="text-xs uppercase font-extrabold tracking-wider text-[#00ff88] print:text-black">
            ★ Faits Marquants & Médias
          </h3>
          <div class="space-y-2.5">
            <div v-for="h in projectRoster.highlights" :key="h.id" class="text-xs space-y-0.5 border-b border-[#282c37]/60 pb-2">
              <span class="text-[10px] text-gray-500 font-mono block">{{ h.date }} · {{ h.type }}</span>
              <a
                v-if="h.url"
                :href="h.url"
                target="_blank"
                rel="noopener noreferrer"
                class="font-bold text-gray-200 hover:text-[#00ff88] block print:text-black"
              >{{ h.titre }}</a>
              <strong v-else class="text-gray-200 block print:text-black">{{ h.titre }}</strong>
              <span v-if="h.source" class="text-[10px] text-gray-500 block">{{ h.source }}</span>
            </div>
          </div>
        </div>

        <!-- Bloc B : Top Tracks en Écoute -->
        <div class="bg-[#181a20] border border-[#282c37] rounded-xl p-5 space-y-3 print:border-gray-300 print:bg-transparent">
          <h3 class="text-xs uppercase font-extrabold tracking-wider text-[#7c3aed] print:text-black">
            🎵 Morceaux Principaux
          </h3>
          <div class="space-y-2.5">
            <div v-for="t in projectRoster.topTracks" :key="t.id" class="flex items-center justify-between p-2 rounded bg-[#121418] border border-[#282c37] text-xs print:bg-transparent print:border-gray-200">
              <div>
                <strong class="text-white block print:text-black">{{ t.titre }}</strong>
                <span class="text-[10px] text-gray-400 font-mono">{{ t.duree }} · ISRC: {{ t.isrc }}</span>
              </div>
              <span class="text-[11px] font-bold text-[#00ff88] font-mono print:text-black">{{ t.streams }}</span>
            </div>
          </div>
        </div>

        <!-- Bloc C : Prochaines Dates Live -->
        <div class="bg-[#181a20] border border-[#282c37] rounded-xl p-5 space-y-3 print:border-gray-300 print:bg-transparent">
          <h3 class="text-xs uppercase font-extrabold tracking-wider text-gray-300 print:text-black">
            🗓️ Tournée & Dates Clés
          </h3>
          <div class="space-y-2.5">
            <div v-for="d in projectRoster.tourDates" :key="d.date" class="text-xs flex justify-between items-center border-b border-[#282c37]/60 pb-2">
              <div>
                <strong class="text-white block print:text-black">{{ d.salle }} ({{ d.ville }})</strong>
                <span class="text-[10px] text-gray-500">{{ d.type }}</span>
              </div>
              <span class="text-xs font-mono font-bold text-gray-300 print:text-black">{{ d.date }}</span>
            </div>
          </div>
        </div>

      </section>

      <!-- Footer / Mention du Programme Embrayage (Case à Chocs) -->
      <footer class="pt-6 border-t border-[#282c37] flex flex-col sm:flex-row items-center justify-between text-xs text-gray-500 gap-2 print:border-gray-300 print:text-gray-600">
        <span>Fiche générée via <strong>Vue Carter</strong> · Plateforme de centralisation et valorisation de parcours</span>
        <span>Dispositif d'accompagnement : <strong>Case à Chocs / Ville de Neuchâtel</strong></span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
@media print {
  body {
    background: white !important;
    color: black !important;
  }
}
</style>