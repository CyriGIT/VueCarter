<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useEvaluationCriteriaStore } from '@/stores/evaluationCriteriaStore'
import type {
  EvaluationCriterion,
  EvaluationCriterionType,
  EvaluationCriterionWrite
} from '@/types/project'

const store = useEvaluationCriteriaStore()
const editing = ref<EvaluationCriterion | null>(null)
const typeFilter = ref<'all' | EvaluationCriterionType>('all')
const stateFilter = ref<'all' | 'active' | 'inactive'>('all')
const feedback = ref('')
const form = reactive<EvaluationCriterionWrite & { estActif: boolean }>({
  nom: '', type: 'subjectif', noteMaximale: 5, poids: 1, ordre: 10,
  modeEvaluation: 'manuel', regleObjective: null, estActif: true
})

const typeLabels: Record<EvaluationCriterionType, string> = {
  objectif: 'Objectif', subjectif: 'Subjectif'
}
const filteredCriteria = computed(() => store.criteria.filter(criterion => (
  (typeFilter.value === 'all' || criterion.type === typeFilter.value)
  && (stateFilter.value === 'all' || criterion.estActif === (stateFilter.value === 'active'))
)))
const structuralFieldsLocked = computed(() => editing.value?.estUtilise === true)
const availableRules = computed(() => store.objectiveRules.filter(rule => (
  rule.code === editing.value?.regleObjective
  || !store.criteria.some(criterion => criterion.regleObjective === rule.code)
)))

function resetForm() {
  editing.value = null
  Object.assign(form, {
    nom: '', type: 'subjectif', noteMaximale: 5, poids: 1,
    ordre: Math.max(0, ...store.criteria.map(criterion => criterion.ordre)) + 10,
    modeEvaluation: 'manuel', regleObjective: null, estActif: true
  })
  feedback.value = ''
}

function editCriterion(criterion: EvaluationCriterion) {
  editing.value = criterion
  Object.assign(form, criterion)
  feedback.value = ''
}

function normalizeConfiguration() {
  if (form.type !== 'objectif') {
    form.modeEvaluation = 'manuel'
    form.regleObjective = null
  }
  if (form.modeEvaluation === 'manuel') form.regleObjective = null
  if (form.modeEvaluation === 'automatique') {
    form.noteMaximale = 1
  }
}

function payload(): EvaluationCriterionWrite {
  return {
    nom: form.nom.trim(), type: form.type,
    noteMaximale: Number(form.noteMaximale), poids: Number(form.poids),
    ordre: Number(form.ordre), modeEvaluation: form.modeEvaluation,
    regleObjective: form.regleObjective || null
  }
}

async function saveCriterion() {
  const saved = editing.value
    ? await store.updateCriterion(editing.value.id, { ...payload(), estActif: form.estActif })
    : await store.createCriterion(payload())
  if (!saved) return
  feedback.value = editing.value ? 'Critère enregistré.' : 'Critère créé.'
  if (editing.value) {
    const updated = store.criteria.find(criterion => criterion.id === editing.value?.id)
    if (updated) editCriterion(updated)
    feedback.value = 'Critère enregistré.'
  } else {
    resetForm()
    feedback.value = 'Critère créé.'
  }
}

async function toggleCriterion(criterion: EvaluationCriterion) {
  const action = criterion.estActif ? 'désactiver' : 'réactiver'
  if (!confirm(`Confirmer ${action} « ${criterion.nom} » ?`)) return
  const { id, code, estUtilise, ...criterionPayload } = criterion
  const saved = await store.updateCriterion(id, {
    ...criterionPayload,
    estActif: !criterion.estActif
  })
  if (saved) {
    feedback.value = criterion.estActif ? 'Critère désactivé.' : 'Critère réactivé.'
    if (editing.value?.id === id) {
      const updated = store.criteria.find(item => item.id === id)
      if (updated) editCriterion(updated)
      feedback.value = criterion.estActif ? 'Critère désactivé.' : 'Critère réactivé.'
    }
  }
}

onMounted(async () => {
  await Promise.all([store.fetchCriteria(true), store.fetchConfigurationOptions()])
  resetForm()
})
</script>

<template>
  <div class="min-h-full bg-[#0e0f12] text-gray-100">
    <header class="border-b border-[#282c37] bg-[#15171c] px-4 py-5 sm:px-8">
      <div class="mx-auto max-w-375">
        <p class="text-xs font-bold uppercase text-[#00ff88]">Configuration Embrayage</p>
        <h1 class="mt-1 text-2xl font-black sm:text-3xl">Critères de sélection</h1>
        <p class="mt-1 text-sm text-gray-400">{{ store.criteria.filter(item => item.estActif).length }} critères actifs sur {{ store.criteria.length }}</p>
      </div>
    </header>

    <main class="mx-auto grid max-w-375 gap-6 px-4 py-6 sm:px-8 lg:grid-cols-[minmax(0,1fr)_24rem]">
      <section class="min-w-0">
        <div class="mb-4 flex flex-wrap gap-3">
          <select v-model="typeFilter" class="field w-44"><option value="all">Tous les types</option><option value="objectif">Objectifs</option><option value="subjectif">Subjectifs</option></select>
          <select v-model="stateFilter" class="field w-40"><option value="all">Tous les états</option><option value="active">Actifs</option><option value="inactive">Inactifs</option></select>
          <button type="button" class="bg-[#00ff88] px-4 py-2 text-sm font-black text-black" @click="resetForm">Ajouter un critère</button>
        </div>
        <p v-if="store.errorMessage" class="mb-4 border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{{ store.errorMessage }}</p>
        <p v-if="feedback" class="mb-4 border border-[#00ff88]/30 bg-[#00ff88]/10 px-4 py-3 text-sm text-[#00ff88]">{{ feedback }}</p>
        <div class="overflow-x-auto border border-[#282c37] bg-[#15171c]">
          <table class="w-full min-w-190 text-left text-sm">
            <thead class="border-b border-[#343845] bg-[#1d2027] text-xs uppercase text-gray-400"><tr><th class="px-4 py-3">Critère</th><th class="px-4 py-3">Type</th><th class="px-4 py-3">Barème</th><th class="px-4 py-3">Ordre</th><th class="px-4 py-3">État</th><th class="px-4 py-3 text-right">Actions</th></tr></thead>
            <tbody><tr v-for="criterion in filteredCriteria" :key="criterion.id" class="border-b border-[#282c37]">
              <td class="px-4 py-3"><strong class="block">{{ criterion.nom }}</strong><span class="text-xs text-gray-500">{{ criterion.modeEvaluation === 'automatique' ? 'Calcul automatique' : 'Saisie gestionnaire Case' }}</span></td>
              <td class="px-4 py-3">{{ typeLabels[criterion.type] }}</td><td class="px-4 py-3">/{{ criterion.noteMaximale }} · poids {{ criterion.poids }}</td><td class="px-4 py-3 font-mono">{{ criterion.ordre }}</td>
              <td class="px-4 py-3" :class="criterion.estActif ? 'text-[#00ff88]' : 'text-gray-500'">{{ criterion.estActif ? 'Actif' : 'Inactif' }}</td>
              <td class="px-4 py-3 text-right"><button type="button" class="mr-3 text-xs font-bold text-gray-300" @click="toggleCriterion(criterion)">{{ criterion.estActif ? 'Désactiver' : 'Réactiver' }}</button><button type="button" class="text-xs font-bold text-[#00ff88]" @click="editCriterion(criterion)">Modifier</button></td>
            </tr></tbody>
          </table>
          <p v-if="!filteredCriteria.length && !store.isLoading" class="py-10 text-center text-sm text-gray-500">Aucun critère.</p>
        </div>
      </section>

      <aside class="h-fit border border-[#282c37] bg-[#181a20] p-5 lg:sticky lg:top-22">
        <div class="mb-5 flex items-center justify-between"><h2 class="text-lg font-black">{{ editing ? 'Modifier le critère' : 'Nouveau critère' }}</h2><button v-if="editing" type="button" class="text-xs font-bold text-[#00ff88]" @click="resetForm">Nouveau</button></div>
        <form class="space-y-4" @submit.prevent="saveCriterion">
          <label><span>Libellé</span><input v-model="form.nom" required maxlength="150" class="field" /></label>
          <div class="grid grid-cols-2 gap-3"><label><span>Type</span><select v-model="form.type" :disabled="structuralFieldsLocked" class="field disabled:opacity-50" @change="normalizeConfiguration"><option value="objectif">Objectif</option><option value="subjectif">Subjectif</option></select></label><label v-if="form.type === 'objectif'"><span>Mode</span><select v-model="form.modeEvaluation" :disabled="structuralFieldsLocked" class="field disabled:opacity-50" @change="normalizeConfiguration"><option value="manuel">Manuel</option><option value="automatique">Automatique</option></select></label></div>
          <label v-if="form.type === 'objectif' && form.modeEvaluation === 'automatique'"><span>Règle automatique</span><select v-model="form.regleObjective" required :disabled="structuralFieldsLocked" class="field disabled:opacity-50"><option :value="null" disabled>Sélectionner une règle</option><option v-for="rule in availableRules" :key="rule.code" :value="rule.code">{{ rule.libelle }}</option></select></label>
          <div class="grid grid-cols-3 gap-3"><label><span>Barème</span><input v-model.number="form.noteMaximale" type="number" min="1" max="100" required :disabled="structuralFieldsLocked || form.modeEvaluation === 'automatique'" class="field disabled:opacity-50" /></label><label><span>Poids</span><input v-model.number="form.poids" type="number" min="1" max="100" required :disabled="structuralFieldsLocked" class="field disabled:opacity-50" /></label><label><span>Ordre</span><input v-model.number="form.ordre" type="number" min="0" required class="field" /></label></div>
          <p v-if="structuralFieldsLocked" class="border-l-2 border-amber-300 pl-3 text-xs text-amber-200">Ce critère est utilisé dans une campagne ou possède des notes. Seuls son libellé, son ordre et son état peuvent changer.</p>
          <label v-if="editing" class="flex items-center gap-2 text-sm"><input v-model="form.estActif" type="checkbox" /> Critère actif</label>
          <button :disabled="store.isLoading" class="w-full bg-[#00ff88] px-4 py-2 text-sm font-black text-black disabled:opacity-50">{{ store.isLoading ? 'Enregistrement...' : 'Enregistrer' }}</button>
        </form>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.field { border: 1px solid #343845; background: #101216; padding: .6rem .75rem; color: #f3f4f6; outline: none; }
.field:focus { border-color: #00ff88; }
label > span { display: block; margin-bottom: .35rem; font-size: .75rem; font-weight: 700; color: #9ca3af; }
label > .field { width: 100%; }
</style>
