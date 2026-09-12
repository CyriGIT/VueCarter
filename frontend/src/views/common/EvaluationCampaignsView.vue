<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useEvaluationCampaignStore } from '@/stores/evaluationCampaignStore'
import { useProjectStore } from '@/stores/projectStore'
import type { EvaluationCampaignWrite } from '@/types/project'

const store = useEvaluationCampaignStore()
const projectStore = useProjectStore()
const feedback = ref('')
const isCreating = ref(false)
const form = reactive<EvaluationCampaignWrite>({
  nom: '', statut: 'brouillon', dateDebut: null, dateFin: null
})
const selected = computed(() => store.selectedCampaign)
const isReadOnly = computed(() => !isCreating.value && selected.value?.statut === 'cloturee')

function loadForm() {
  const campaign = selected.value
  if (!campaign) return
  Object.assign(form, {
    nom: campaign.nom,
    statut: campaign.statut,
    dateDebut: campaign.dateDebut,
    dateFin: campaign.dateFin
  })
  isCreating.value = false
  feedback.value = ''
}

function newCampaign() {
  Object.assign(form, { nom: '', statut: 'brouillon', dateDebut: null, dateFin: null })
  isCreating.value = true
  feedback.value = ''
}

async function saveCampaign() {
  const saved = await store.saveCampaign({ ...form }, isCreating.value ? undefined : selected.value?.id)
  if (!saved) return
  isCreating.value = false
  loadForm()
  feedback.value = 'Campagne enregistrée.'
}

async function selectCampaign(event: Event) {
  store.selectedCampaignId = Number((event.target as HTMLSelectElement).value)
  loadForm()
}

async function toggleProject(projectId: number, event: Event) {
  if (!selected.value) return
  const assigned = (event.target as HTMLInputElement).checked
  if (await store.setProjectAssignment(selected.value.id, projectId, assigned)) {
    feedback.value = 'Affectation projet mise à jour.'
  }
}

async function toggleJuror(jurorId: number, event: Event) {
  if (!selected.value) return
  const assigned = (event.target as HTMLInputElement).checked
  if (await store.setJurorAssignment(selected.value.id, jurorId, assigned)) {
    feedback.value = 'Affectation jury mise à jour.'
  }
}

watch(() => store.selectedCampaignId, loadForm)
onMounted(async () => {
  await Promise.all([store.fetchCampaigns(), store.fetchEligibleJurors(), projectStore.fetchProjects()])
  loadForm()
})
</script>

<template>
  <div class="min-h-full bg-[#0e0f12] text-gray-100">
    <header class="border-b border-[#282c37] bg-[#15171c] px-4 py-5 sm:px-8">
      <div class="mx-auto flex max-w-375 flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p class="text-xs font-bold uppercase text-[#00ff88]">Configuration Embrayage</p>
          <h1 class="mt-1 text-2xl font-black sm:text-3xl">Campagnes et affectations</h1>
          <p class="mt-1 text-sm text-gray-400">Les projets, jurés et critères sont figés explicitement par campagne.</p>
        </div>
        <button class="bg-[#00ff88] px-4 py-2 text-sm font-black text-black" @click="newCampaign">Nouvelle campagne</button>
      </div>
    </header>

    <main class="mx-auto max-w-375 space-y-6 px-4 py-6 sm:px-8">
      <p v-if="store.errorMessage" class="border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{{ store.errorMessage }}</p>
      <p v-if="feedback" class="border border-[#00ff88]/30 bg-[#00ff88]/10 px-4 py-3 text-sm text-[#00ff88]">{{ feedback }}</p>

      <section class="border border-[#282c37] bg-[#181a20] p-5">
        <div class="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end">
          <label class="flex-1"><span>Campagne</span><select :value="store.selectedCampaignId ?? ''" class="field" @change="selectCampaign"><option v-for="campaign in store.campaigns" :key="campaign.id" :value="campaign.id">{{ campaign.nom }} · {{ campaign.statut }}</option></select></label>
          <span v-if="selected" class="pb-2 text-xs text-gray-400">{{ selected.projectIds.length }} projets · {{ selected.jurorIds.length }} jurés</span>
        </div>
        <form class="grid gap-4 md:grid-cols-4" @submit.prevent="saveCampaign">
          <label class="md:col-span-2"><span>Nom</span><input v-model="form.nom" required maxlength="150" :disabled="isReadOnly" class="field disabled:opacity-50" /></label>
          <label><span>État</span><select v-model="form.statut" :disabled="isReadOnly" class="field disabled:opacity-50"><option value="brouillon">Brouillon</option><option value="ouverte">Ouverte</option><option value="cloturee">Clôturée</option></select></label>
          <div class="flex items-end"><button :disabled="store.isLoading || isReadOnly" class="w-full bg-[#00ff88] px-4 py-2.5 text-sm font-black text-black disabled:opacity-50">{{ isReadOnly ? 'Campagne clôturée' : 'Enregistrer' }}</button></div>
          <label><span>Début</span><input v-model="form.dateDebut" type="date" :disabled="isReadOnly" class="field disabled:opacity-50" /></label>
          <label><span>Fin</span><input v-model="form.dateFin" type="date" :disabled="isReadOnly" class="field disabled:opacity-50" /></label>
        </form>
      </section>

      <div v-if="selected && !isCreating" class="grid gap-6 lg:grid-cols-2">
        <section class="border border-[#282c37] bg-[#181a20] p-5">
          <h2 class="mb-1 text-base font-black">Projets candidats</h2>
          <p class="mb-4 text-xs text-gray-500">Un projet non affecté n’apparaît pas dans le cockpit de cette campagne.</p>
          <div class="divide-y divide-[#282c37]">
            <label v-for="project in projectStore.projects" :key="project.id" class="flex items-center justify-between gap-3 py-3">
              <span><strong class="block text-sm">{{ project.nom }}</strong><small class="text-gray-500">{{ project.genreMusical }}</small></span>
              <input type="checkbox" :checked="selected.projectIds.includes(project.id)" :disabled="store.isLoading || isReadOnly" class="h-5 w-5 accent-[#00ff88]" @change="toggleProject(project.id, $event)" />
            </label>
          </div>
        </section>

        <section class="border border-[#282c37] bg-[#181a20] p-5">
          <h2 class="mb-1 text-base font-black">Jurés affectés</h2>
          <p class="mb-4 text-xs text-gray-500">Chaque juré affecté peut saisir une seule note globale entière par projet.</p>
          <div class="divide-y divide-[#282c37]">
            <label v-for="juror in store.eligibleJurors" :key="juror.id" class="flex items-center justify-between gap-3 py-3">
              <span><strong class="block text-sm">{{ juror.prenom }} {{ juror.nom }}</strong><small class="text-gray-500">{{ juror.email }}</small></span>
              <input type="checkbox" :checked="selected.jurorIds.includes(juror.id)" :disabled="store.isLoading || isReadOnly" class="h-5 w-5 accent-[#00ff88]" @change="toggleJuror(juror.id, $event)" />
            </label>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.field { width: 100%; border: 1px solid #343845; background: #101216; padding: .6rem .75rem; color: #f3f4f6; outline: none; }
.field:focus { border-color: #00ff88; }
label > span { display: block; margin-bottom: .35rem; font-size: .75rem; font-weight: 700; color: #9ca3af; }
</style>