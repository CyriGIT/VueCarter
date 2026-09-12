<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useGrantDeadlineStore } from '@/stores/grantDeadlineStore'
import { useProjectStore } from '@/stores/projectStore'
import type { GrantDeadline } from '@/types/grantDeadline'

const store = useGrantDeadlineStore()
const projectStore = useProjectStore()
const userRole = localStorage.getItem('user_role') || ''
const canManage = ['admin', 'gestionnaire_case'].includes(userRole)
const isArtist = userRole === 'artiste'
const today = new Date().toISOString().slice(0, 10)
const editingId = ref<number | null>(null)
const feedback = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const form = reactive({ bailleur: '', dateProchaineSoumission: '', urlFormulaire: '' })
const applicationForm = reactive({ projectId: 0, dateDepot: today })

const selectedProject = computed(() => (
  projectStore.projects.find(project => project.id === applicationForm.projectId)
))
const selectedApplications = computed(() => selectedProject.value?.grantApplications || [])
const applicationFor = (deadlineId: number) => (
  selectedApplications.value.find(application => application.deadlineId === deadlineId)
)

const upcomingCount = computed(() => store.deadlines.filter(item => (
  item.estActif && item.dateProchaineSoumission >= today
)).length)

const formatDate = (value: string) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  return match ? `${match[3]}.${match[2]}.${match[1]}` : value
}

const deadlineState = (deadline: GrantDeadline) => {
  if (!deadline.estActif) return { label: 'Archivée', classes: 'text-gray-400 border-gray-600 bg-gray-500/10' }
  if (deadline.dateProchaineSoumission < today) return { label: 'Expirée', classes: 'text-rose-300 border-rose-500/40 bg-rose-500/10' }
  return { label: 'À venir', classes: 'text-[#00ff88] border-[#00ff88]/40 bg-[#00ff88]/10' }
}

function resetForm() {
  editingId.value = null
  form.bailleur = ''
  form.dateProchaineSoumission = ''
  form.urlFormulaire = ''
  feedback.value = null
}

function editDeadline(deadline: GrantDeadline) {
  editingId.value = deadline.id
  form.bailleur = deadline.bailleur
  form.dateProchaineSoumission = deadline.dateProchaineSoumission
  form.urlFormulaire = deadline.urlFormulaire
  feedback.value = null
}

async function submitDeadline() {
  feedback.value = null
  const payload = {
    bailleur: form.bailleur.trim(),
    dateProchaineSoumission: form.dateProchaineSoumission,
    urlFormulaire: form.urlFormulaire.trim()
  }
  const saved = editingId.value === null
    ? await store.createDeadline(payload)
    : await store.updateDeadline(editingId.value, { ...payload, estActif: true })
  if (!saved) {
    feedback.value = { type: 'error', text: store.errorMessage || 'L’enregistrement a échoué.' }
    return
  }
  await store.fetchDeadlines(true)
  resetForm()
  feedback.value = { type: 'success', text: 'Échéance enregistrée.' }
}

async function setActive(deadline: GrantDeadline, estActif: boolean) {
  feedback.value = null
  const saved = await store.updateDeadline(deadline.id, {
    bailleur: deadline.bailleur,
    dateProchaineSoumission: deadline.dateProchaineSoumission,
    urlFormulaire: deadline.urlFormulaire,
    estActif
  })
  if (saved) {
    await store.fetchDeadlines(true)
    feedback.value = { type: 'success', text: estActif ? 'Échéance réactivée.' : 'Échéance archivée.' }
  } else {
    feedback.value = { type: 'error', text: store.errorMessage || 'La modification a échoué.' }
  }
}

async function declareApplication(deadlineId: number) {
  feedback.value = null
  if (!applicationForm.projectId) return
  const saved = await projectStore.declareGrantApplication(applicationForm.projectId, {
    deadlineId,
    dateDepot: applicationForm.dateDepot
  })
  feedback.value = saved
    ? { type: 'success', text: 'Demande déclarée.' }
    : { type: 'error', text: projectStore.errorMessage || 'La déclaration a échoué.' }
}

async function withdrawApplication(deadlineId: number) {
  feedback.value = null
  if (!applicationForm.projectId) return
  const saved = await projectStore.withdrawGrantApplication(applicationForm.projectId, deadlineId)
  feedback.value = saved
    ? { type: 'success', text: 'Déclaration retirée.' }
    : { type: 'error', text: projectStore.errorMessage || 'Le retrait a échoué.' }
}

onMounted(async () => {
  await Promise.all([
    store.fetchDeadlines(canManage),
    isArtist ? projectStore.fetchProjects() : Promise.resolve()
  ])
  applicationForm.projectId = projectStore.projects[0]?.id || 0
})
</script>

<template>
  <div class="w-full min-h-full bg-[#0e0f12] px-4 sm:px-6 lg:px-10 py-7 text-gray-100">
    <div class="max-w-6xl mx-auto space-y-6">
      <header class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-[#282c37] pb-5">
        <div>
          <p class="text-xs font-bold uppercase text-[#00ff88]">Financement</p>
          <h1 class="mt-1 text-2xl font-black text-white">Aides et échéances</h1>
          <p class="mt-2 text-sm text-gray-400">Prochaines dates de dépôt auprès des bailleurs de fonds.</p>
        </div>
        <div class="text-left sm:text-right">
          <strong class="block text-2xl text-white">{{ upcomingCount }}</strong>
          <span class="text-xs text-gray-500">échéance(s) à venir</span>
        </div>
      </header>

      <section v-if="canManage" class="border-y border-[#282c37] py-5 space-y-4">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-sm font-bold text-white">{{ editingId === null ? 'Ajouter une échéance' : 'Modifier l’échéance' }}</h2>
          <button v-if="editingId !== null" type="button" @click="resetForm" class="text-xs text-gray-400 hover:text-white">Annuler</button>
        </div>
        <form @submit.prevent="submitDeadline" class="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_11rem_minmax(0,1.4fr)_auto] gap-3">
          <label class="space-y-1">
            <span class="block text-xs text-gray-400">Bailleur de fonds</span>
            <input v-model="form.bailleur" type="text" maxlength="150" required class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#7c3aed]" />
          </label>
          <label class="space-y-1">
            <span class="block text-xs text-gray-400">Prochaine date de dépôt</span>
            <input v-model="form.dateProchaineSoumission" type="date" :min="today" required class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#7c3aed]" />
          </label>
          <label class="space-y-1">
            <span class="block text-xs text-gray-400">Lien vers le formulaire</span>
            <input v-model="form.urlFormulaire" type="url" maxlength="2048" placeholder="https://..." required class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#7c3aed]" />
          </label>
          <button type="submit" :disabled="store.isSaving" class="self-end px-4 py-2 bg-[#7c3aed] hover:bg-[#6d28d9] rounded-lg text-sm font-bold text-white disabled:opacity-50">
            {{ store.isSaving ? 'Enregistrement...' : editingId === null ? 'Ajouter' : 'Enregistrer' }}
          </button>
        </form>
      </section>

      <section v-if="isArtist" class="border-y border-[#282c37] py-5 space-y-4">
        <div>
          <h2 class="text-sm font-bold text-white">Déclarer une demande effectuée</h2>
          <p class="mt-1 text-xs text-gray-400">Choisissez le projet concerné et la date à laquelle le dossier a été déposé.</p>
        </div>
        <div v-if="projectStore.projects.length" class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl">
          <label class="space-y-1">
            <span class="block text-xs text-gray-400">Projet</span>
            <select v-model="applicationForm.projectId" class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm">
              <option v-for="project in projectStore.projects" :key="project.id" :value="project.id">{{ project.nom }}</option>
            </select>
          </label>
          <label class="space-y-1">
            <span class="block text-xs text-gray-400">Date de dépôt</span>
            <input v-model="applicationForm.dateDepot" type="date" :max="today" class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm" />
          </label>
        </div>
        <p v-else class="text-sm text-gray-500">Créez d’abord un projet musical pour déclarer une demande.</p>

        <div v-if="selectedApplications.length" class="space-y-2 pt-2">
          <h3 class="text-xs font-bold uppercase text-gray-400">Mes demandes</h3>
          <div v-for="application in selectedApplications" :key="application.deadlineId" class="flex flex-wrap items-center justify-between gap-2 border-t border-[#282c37] pt-2 text-sm">
            <span><strong>{{ application.bailleur }}</strong> · déposée le {{ formatDate(application.dateDepot) }}</span>
            <button type="button" @click="withdrawApplication(application.deadlineId)" class="text-xs text-rose-300 hover:text-rose-200">Retirer la déclaration</button>
          </div>
        </div>
      </section>

      <p v-if="feedback" role="status" :class="feedback.type === 'success' ? 'text-[#00ff88]' : 'text-rose-400'" class="text-sm">
        {{ feedback.text }}
      </p>
      <p v-if="store.isLoading" class="text-sm text-gray-400">Chargement des échéances...</p>
      <p v-else-if="store.errorMessage && !feedback" class="text-sm text-rose-400">{{ store.errorMessage }}</p>

      <section v-else-if="store.deadlines.length" class="border-t border-[#282c37]">
        <article v-for="deadline in store.deadlines" :key="deadline.id" class="grid grid-cols-1 md:grid-cols-[11rem_minmax(0,1fr)_auto] gap-3 md:items-center py-5 border-b border-[#282c37]">
          <div>
            <time :datetime="deadline.dateProchaineSoumission" class="text-xl font-black text-white">{{ formatDate(deadline.dateProchaineSoumission) }}</time>
            <span :class="deadlineState(deadline).classes" class="block w-fit mt-1 px-2 py-0.5 rounded border text-[10px] font-bold uppercase">{{ deadlineState(deadline).label }}</span>
          </div>
          <div class="min-w-0">
            <h2 class="text-base font-bold text-gray-100">{{ deadline.bailleur }}</h2>
            <a :href="deadline.urlFormulaire" target="_blank" rel="noopener noreferrer" class="inline-block mt-1 text-sm text-[#00ff88] hover:underline">Ouvrir le formulaire ↗</a>
          </div>
          <div v-if="canManage" class="flex flex-wrap gap-2 md:justify-end">
            <button type="button" @click="editDeadline(deadline)" class="px-3 py-1.5 border border-[#3a3f4d] rounded text-xs text-gray-300 hover:text-white">Modifier</button>
            <button v-if="deadline.estActif" type="button" @click="setActive(deadline, false)" class="px-3 py-1.5 border border-rose-500/40 rounded text-xs text-rose-300">Archiver</button>
            <button v-else-if="deadline.dateProchaineSoumission >= today" type="button" @click="setActive(deadline, true)" class="px-3 py-1.5 border border-[#00ff88]/40 rounded text-xs text-[#00ff88]">Réactiver</button>
          </div>
          <div v-else-if="isArtist" class="flex md:justify-end">
            <span v-if="applicationFor(deadline.id)" class="px-3 py-1.5 border border-[#00ff88]/40 rounded text-xs font-bold text-[#00ff88]">Demande déclarée</span>
            <button v-else type="button" :disabled="!applicationForm.projectId || projectStore.isLoading" @click="declareApplication(deadline.id)" class="px-3 py-1.5 bg-[#7c3aed] rounded text-xs font-bold text-white disabled:opacity-40">J’ai déposé une demande</button>
          </div>
        </article>
      </section>

      <p v-else-if="!store.isLoading" class="py-10 border-y border-[#282c37] text-center text-sm text-gray-500">Aucune échéance de subvention disponible.</p>
    </div>
  </div>
</template>
