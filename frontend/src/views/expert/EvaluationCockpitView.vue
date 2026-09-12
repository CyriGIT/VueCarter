<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProjectStore } from '@/stores/projectStore'
import { useEvaluationCriteriaStore } from '@/stores/evaluationCriteriaStore'
import { useEvaluationCampaignStore } from '@/stores/evaluationCampaignStore'
import { resolveProjectVideo } from '@/utils/projectVideo'
import type { AccompanyingExpert, AudienceMetric, EvaluationCriterion, EvaluationScores, ProjectFormation, ProjectProgramme } from '@/types/project'
import type { GrantApplication } from '@/types/grantDeadline'

type SelectionStatus = 'en_attente' | 'selectionne' | 'refuse'

interface ProjectCandidate {
  id: number
  nom: string
  genreMusical: string
  anneeCreation: number
  responsable: string
  localite: string
  ages: string
  femmesSurScene: number
  hommesSurScene: number
  autresSurScene: number
  langueChant: string
  bioCourte: string
  personalPageUrl: string | null
  personalPageSiteName: string | null
  objectifsCourtTerme: string | null
  objectifsMoyenTerme: string | null
  memberEmails: string[]
  decisionEmailSentAt: string | null
  accompanyingExpert: AccompanyingExpert | null
  grantApplications: GrantApplication[]
  // Indicateurs métiers du programme
  streamingTopTracks: { titre: string; views: string }[]
  audienceMetrics: AudienceMetric[]
  concerts: { local: number; horsCanton: number; export: number }
  residencesCount: number
  statutJuridique: string
  suisaInscrit: boolean
  hasMerch: boolean
  hasFicheTechnique: boolean
  hasDemandeSubvention: boolean
  hasLocal: boolean
  mixMasterContact: string
  formationsSuivies: ProjectFormation[]
  programmesPrecedents: ProjectProgramme[]
  promoAssetsUrl: string
  videoUrl: string
  scores: EvaluationScores
  remarques: string
  statutSelection: SelectionStatus
}

const selectedProjectId = ref<number>(1)
const searchQuery = ref('')
const saveMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const assignmentMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const decisionDrafts = ref<Record<number, SelectionStatus>>({})
const juryNote = ref<number | null>(null)
const store = useProjectStore()
const criteriaStore = useEvaluationCriteriaStore()
const campaignStore = useEvaluationCampaignStore()
const canManageEvaluations = computed(() => store.accountIdentity?.canManageEvaluations === true)
const canViewCohortReport = computed(() => store.accountIdentity?.role !== 'accompagnant')
const objectiveCriteria = computed(() => criteriaStore.criteria.filter(criterion => criterion.type === 'objectif'))
const subjectiveCriteria = computed(() => criteriaStore.criteria.filter(criterion => criterion.type === 'subjectif'))
const scoredObjectiveCount = computed(() => {
  const candidate = selectedProject.value
  if (!candidate) return 0
  return objectiveCriteria.value.filter(criterion => candidate.scores[criterion.code] !== undefined).length
})
const canEditCriterion = (criterion: EvaluationCriterion) => (
  criterion.modeEvaluation === 'manuel'
  && canManageEvaluations.value
  && campaignStore.selectedCampaign?.statut === 'ouverte'
)
const canSaveEvaluation = computed(() => canManageEvaluations.value && campaignStore.selectedCampaign?.statut === 'ouverte')
const canSaveJuryNote = computed(() => (
  store.accountIdentity?.role === 'expert_jury'
  && campaignStore.selectedCampaign?.statut === 'ouverte'
))

const audienceMetricLabels: Record<string, string> = {
  Followers: 'Followers',
  Abonnes: 'Abonnés',
  Ecoutes_Mensuelles: 'Écoutes mensuelles',
  Ecoutes_Cumulees: 'Écoutes cumulées',
  Vues_Profil: 'Vues du profil'
}

const formatMetricDate = (date: string): string => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date)
  return match ? `${match[3]}.${match[2]}.${match[1]}` : date
}

const ageAtYearEnd = (dateNaissance: string | undefined): number | null => {
  if (!dateNaissance) return null
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(dateNaissance)
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const parsedDate = new Date(Date.UTC(year, month - 1, day))
  if (
    parsedDate.getUTCFullYear() !== year ||
    parsedDate.getUTCMonth() !== month - 1 ||
    parsedDate.getUTCDate() !== day
  ) return null
  return new Date().getFullYear() - year
}

const candidates = computed<ProjectCandidate[]>(() => store.projects.length > 0
  ? store.projects
    .filter(project => campaignStore.selectedCampaign?.projectIds.includes(project.id))
    .map(project => {
      const members = project.members || []
      const ages = members.map(member => ageAtYearEnd(member.dateNaissance))
      const tracks = project.tracks || []
      const concerts = project.concerts || []
      const decisionDraft = decisionDrafts.value[project.id]
      const evaluation = campaignStore.evaluations.find(item => item.projectId === project.id)
      const scores: EvaluationScores = { ...(evaluation?.scores || {}) }
      return {
        id: project.id,
        nom: project.nom,
        genreMusical: project.genreMusical || 'Non renseigné',
        anneeCreation: Number(String(project.dateCreation).slice(0, 4)) || 0,
        responsable: members.map(member => `${member.prenom} ${member.nom}`).join(', ') || 'Non renseigné',
        localite: project.commune || 'Non renseignée',
        ages: ages.length > 0
          ? ages.map(age => age === null ? 'Non renseigné' : `${age} ans`).join(', ')
          : 'Non renseigné',
        femmesSurScene: members.filter(member => member.genre === 'Femme').length,
        hommesSurScene: members.filter(member => member.genre === 'Homme').length,
        autresSurScene: members.filter(member => member.genre === 'Autre').length,
        langueChant: project.langueChant,
        bioCourte: project.bioCourte,
        personalPageUrl: project.personalPageUrl || null,
        personalPageSiteName: project.personalPageSiteName || null,
        objectifsCourtTerme: project.objectifsCourtTerme || null,
        objectifsMoyenTerme: project.objectifsMoyenTerme || null,
        memberEmails: [...new Set(members.map(member => member.email?.trim()).filter(Boolean))] as string[],
        decisionEmailSentAt: decisionDraft && decisionDraft !== evaluation?.statut
          ? null
          : evaluation?.decisionEmailSentAt || null,
        accompanyingExpert: project.accompanyingExpert || null,
        grantApplications: project.grantApplications || [],
        streamingTopTracks: (project.tracks || []).slice(0, 3).map(track => ({ titre: track.titre, views: track.streamsCount || 'N/A' })),
        audienceMetrics: project.audienceMetrics || [],
        concerts: {
          local: concerts.filter(concert => concert.type === 'Local (NE)').length,
          horsCanton: concerts.filter(concert => concert.type === 'Hors-Canton').length,
          export: concerts.filter(concert => concert.type === 'Export').length
        },
        residencesCount: project.residencesCount || 0,
        statutJuridique: project.statutJuridique,
        suisaInscrit: project.suisaInscrit,
        hasMerch: project.hasMerch,
        hasFicheTechnique: project.hasFicheTechnique,
        hasDemandeSubvention: project.hasDemandeSubvention,
        hasLocal: project.hasLocal,
        mixMasterContact: project.mixMasterContact || 'N/A',
        formationsSuivies: project.formationsSuivies || [],
        programmesPrecedents: project.programmesPrecedents || [],
        promoAssetsUrl: project.assets[0]?.url || '',
        videoUrl: resolveProjectVideo(project.assets)?.url || '',
        scores,
        remarques: evaluation?.remarques || '',
        statutSelection: decisionDrafts.value[project.id] ?? evaluation?.statut ?? 'en_attente'
      }
    })
  : [])

const selectedProject = computed(() => {
  return candidates.value.find(c => c.id === selectedProjectId.value) || candidates.value[0]
})
const selectedEvaluation = computed(() => (
  campaignStore.evaluations.find(item => item.projectId === selectedProject.value?.id)
))
const decisionNeedsSave = computed(() => Boolean(
  selectedProject.value
  && selectedProject.value.statutSelection !== (selectedEvaluation.value?.statut ?? 'en_attente')
))

const selectCandidate = (projectId: number) => {
  selectedProjectId.value = projectId
  juryNote.value = campaignStore.evaluations
    .find(item => item.projectId === projectId)
    ?.juryNotes.find(note => note.estNotePersonnelle)?.note ?? null
}

const selectDecision = (status: SelectionStatus) => {
  if (!selectedProject.value) return
  decisionDrafts.value[selectedProject.value.id] = status
  saveMessage.value = null
}

onMounted(async () => {
  await Promise.all([
    store.fetchProjects(),
    store.fetchAccountIdentity(),
    criteriaStore.fetchCriteria(),
    campaignStore.fetchCampaigns()
  ])
  if (campaignStore.selectedCampaignId) await campaignStore.fetchEvaluations()
  if (canManageEvaluations.value) await store.fetchAccompanyingExperts()
  const firstProject = candidates.value[0]
  if (firstProject) selectCandidate(firstProject.id)
})

const changeCampaign = async (event: Event) => {
  await campaignStore.selectCampaign(Number((event.target as HTMLSelectElement).value))
  const firstProject = candidates.value[0]
  if (firstProject) selectCandidate(firstProject.id)
}

const changeAccompanyingExpert = async (event: Event) => {
  if (!selectedProject.value) return
  assignmentMessage.value = null
  const value = (event.target as HTMLSelectElement).value
  const saved = await store.assignAccompanyingExpert(
    selectedProject.value.id,
    value ? Number(value) : null
  )
  assignmentMessage.value = saved
    ? { type: 'success', text: value ? 'Accompagnant affecté.' : 'Accompagnant retiré.' }
    : { type: 'error', text: store.errorMessage || 'L’affectation a échoué.' }
}

const saveEvaluation = async () => {
  if (!selectedProject.value) return
  saveMessage.value = null
  const editableScores = Object.fromEntries(
    criteriaStore.criteria
      .filter(canEditCriterion)
      .filter(criterion => selectedProject.value!.scores[criterion.code] !== undefined)
      .map(criterion => [criterion.code, selectedProject.value!.scores[criterion.code]])
  ) as EvaluationScores
  const saved = await store.updateEvaluation(
    selectedProject.value.id,
    campaignStore.selectedCampaignId!,
    editableScores,
    selectedProject.value.remarques,
    selectedProject.value.statutSelection
  )
  saveMessage.value = saved
    ? { type: 'success', text: 'Évaluation enregistrée.' }
    : { type: 'error', text: store.errorMessage || 'L’évaluation n’a pas pu être enregistrée.' }
  if (saved) delete decisionDrafts.value[selectedProject.value.id]
  if (saved) await campaignStore.fetchEvaluations()
}

const saveJuryNote = async () => {
  if (!selectedProject.value || !campaignStore.selectedCampaignId || juryNote.value === null) return
  saveMessage.value = null
  const saved = await campaignStore.saveJuryNote(
    campaignStore.selectedCampaignId,
    selectedProject.value.id,
    juryNote.value
  )
  saveMessage.value = saved
    ? { type: 'success', text: 'Note jury enregistrée.' }
    : { type: 'error', text: campaignStore.errorMessage || 'La note n’a pas pu être enregistrée.' }
}

const prepareDecisionEmail = async () => {
  const candidate = selectedProject.value
  if (
    !candidate
    || candidate.statutSelection === 'en_attente'
    || decisionNeedsSave.value
    || candidate.memberEmails.length === 0
  ) return

  const subject = `Décision Embrayage - ${candidate.nom}`
  const decisionText = candidate.statutSelection === 'selectionne'
    ? 'Nous avons le plaisir de vous informer que votre projet a été retenu pour Embrayage.'
    : 'Nous vous informons que votre projet n’a pas été retenu pour Embrayage.'
  const body = `Bonjour,\n\n${decisionText}\n\nMeilleures salutations`
  window.location.href = `mailto:${candidate.memberEmails.join(',')}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`

  saveMessage.value = null
  const sentAt = await store.markDecisionEmailSent(candidate.id, campaignStore.selectedCampaignId!)
  if (!sentAt) {
    saveMessage.value = {
      type: 'error',
      text: store.errorMessage || 'Le suivi du mail n’a pas pu être enregistré.'
    }
  }
}

const filteredCandidates = computed(() => {
  return candidates.value.filter(c => 
    c.nom.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    c.genreMusical.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    c.localite.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const scoreSummary = (candidate: ProjectCandidate | undefined) => {
  const evaluation = campaignStore.evaluations.find(item => item.projectId === candidate?.id)
  return {
    score: evaluation?.globalScore?.toFixed(1) ?? '—',
    coverage: `${evaluation?.juryCoverageCount ?? 0}/${evaluation?.juryCount ?? 0}`,
    gridScore: evaluation?.gridScore?.toFixed(1) ?? '—',
    juryAverage: evaluation?.juryAverage?.toFixed(1) ?? '—'
  }
}
const totalScore = computed(() => scoreSummary(selectedProject.value))
</script>

<template>
  <div class="w-full px-4 sm:px-6 lg:px-10 py-6 space-y-6">
    <!-- En-tête Cockpit -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#282c37] pb-5">
      <div>
        <div class="flex items-center gap-2">
          <span class="px-2.5 py-0.5 rounded bg-[#7c3aed]/20 text-[#7c3aed] border border-[#7c3aed]/30 text-xs font-bold uppercase">
            {{ campaignStore.selectedCampaign?.nom || 'Aucune campagne' }}
          </span>
          <span class="text-xs text-gray-400">· {{ campaignStore.selectedCampaign?.statut || 'indisponible' }}</span>
        </div>
        <h1 class="text-2xl sm:text-3xl font-black text-white mt-1">
          Cockpit d'Évaluation des Candidatures
        </h1>
      </div>

      <div class="flex items-center gap-3">
        <select
          :value="campaignStore.selectedCampaignId ?? ''"
          @change="changeCampaign"
          class="bg-[#121418] border border-[#343845] px-3 py-2 text-xs text-gray-200"
        >
          <option v-for="campaign in campaignStore.campaigns" :key="campaign.id" :value="campaign.id">
            {{ campaign.nom }} · {{ campaign.statut }}
          </option>
        </select>
        <button v-if="canViewCohortReport" class="px-3.5 py-2 bg-[#22252e] hover:bg-[#282c37] border border-[#282c37] text-gray-200 text-xs font-bold rounded-lg transition-colors">
          📄 Exporter rapport de cohorte (Canton NE)
        </button>
        <button
          v-if="canManageEvaluations"
          class="px-4 py-2 bg-[#00ff88] hover:bg-[#00e57a] text-black text-xs font-black rounded-lg transition-colors"
        >
          Valider les lauréats Embrayage
        </button>
      </div>
    </div>

    <!-- Layout 2 Colonnes Pleine Largeur : Liste des Candidats (1/3) & Fiche d'Évaluation Active (2/3) -->
    <div class="w-full grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Colonne Gauche : Liste & Filtres des Candidatures (4 cols) -->
      <aside class="lg:col-span-4 space-y-4">
        <div class="bg-[#181a20] border border-[#282c37] rounded-xl p-4 space-y-3">
          <div class="flex justify-between items-center">
            <h2 class="text-sm font-bold text-white uppercase tracking-wider">Candidats Embrayage</h2>
            <span class="text-xs font-mono text-[#00ff88] bg-[#00ff88]/10 px-2 py-0.5 rounded">
              {{ filteredCandidates.length }} projets
            </span>
          </div>

          <input
            type="text"
            v-model="searchQuery"
            placeholder="Filtrer par nom, genre, commune..."
            class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]"
          />
        </div>

        <div class="space-y-2 max-h-[75vh] overflow-y-auto pr-1">
          <div
            v-for="cand in filteredCandidates"
            :key="cand.id"
            @click="selectCandidate(cand.id)"
            :class="[
              'p-4 rounded-xl border transition-all cursor-pointer flex flex-col gap-2',
              selectedProjectId === cand.id
                ? 'bg-[#1e222b] border-[#7c3aed] shadow-lg shadow-[#7c3aed]/10'
                : 'bg-[#181a20] border-[#282c37] hover:border-gray-600'
            ]"
          >
            <div class="flex items-start justify-between">
              <div>
                <h3 class="text-sm font-extrabold text-white">{{ cand.nom }}</h3>
                <span class="text-[11px] text-gray-400">{{ cand.genreMusical }}</span>
              </div>
              <span 
                :class="[
                  'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase',
                  cand.statutSelection === 'selectionne' ? 'bg-[#00ff88]/15 text-[#00ff88] border border-[#00ff88]/30' :
                  cand.statutSelection === 'refuse' ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30' :
                  'bg-[#282c37] text-gray-300'
                ]"
              >
                {{ cand.statutSelection === 'selectionne' ? 'Sélectionné' : cand.statutSelection === 'refuse' ? 'Refusé' : 'En attente' }}
              </span>
            </div>

            <div class="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-[#282c37]/60">
              <span>📍 {{ cand.localite }}</span>
              <span class="font-bold text-gray-200">
                Score : <strong class="text-[#00ff88]">
                  {{ scoreSummary(cand).score }}/20
                </strong>
              </span>
            </div>
          </div>
        </div>
      </aside>

      <!-- Colonne Droite : Fiche 360° du Projet & Formulaire d'Évaluation (8 cols) -->
      <main v-if="selectedProject" class="lg:col-span-8 space-y-6">
        
        <!-- Bloc 1 : Synthèse du Projet Sélectionné & KPIs -->
        <section class="bg-[#181a20] border border-[#282c37] rounded-xl p-6 space-y-5">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div class="flex items-center gap-2.5">
                <h2 class="text-2xl font-black text-white">{{ selectedProject.nom }}</h2>
                <span class="text-xs px-2.5 py-0.5 rounded bg-[#22252e] text-[#00ff88] border border-[#00ff88]/30 font-semibold">
                  {{ selectedProject.genreMusical }}
                </span>
                <span class="text-xs px-2 py-0.5 rounded bg-[#22252e] text-gray-300">
                  Création : {{ selectedProject.anneeCreation }}
                </span>
              </div>
              <p class="text-xs text-gray-400 mt-1">
                Responsable : <strong>{{ selectedProject.responsable }}</strong> · 📍 {{ selectedProject.localite }}
              </p>
            </div>

            <div class="flex items-center gap-3 shrink-0">
              <RouterLink
                :to="{ name: 'ProjectRoster', params: { id: selectedProject.id } }"
                class="px-3 py-2 rounded-lg border border-[#282c37] bg-[#121418] text-xs font-bold text-gray-300 hover:text-white hover:border-[#00ff88]/50"
              >
                Voir la fiche roster
              </RouterLink>
              <div class="bg-[#121418] border border-[#7c3aed]/40 px-4 py-2 rounded-xl text-center">
                <span class="text-[10px] uppercase font-bold text-gray-400 block tracking-wider">Score global provisoire</span>
                <span class="text-2xl font-black text-[#00ff88]">{{ totalScore.score }}<span class="text-xs text-gray-500 font-normal"> /20</span></span>
                <span class="block text-[10px] text-gray-500">Grille {{ totalScore.gridScore }}/20 · Jury {{ totalScore.juryAverage }}/20</span>
                <span class="block text-[10px] text-gray-500">{{ totalScore.coverage }} jurés ont noté</span>
              </div>
            </div>
          </div>

          <p class="text-sm text-gray-300 leading-relaxed bg-[#121418] p-3.5 rounded-lg border border-[#282c37]">
            {{ selectedProject.bioCourte }}
          </p>

          <div
            v-if="selectedProject.statutSelection === 'selectionne'"
            class="bg-[#121418] border border-[#00ff88]/30 rounded-lg p-3.5 space-y-2"
          >
            <label for="accompanying-expert" class="text-xs font-semibold text-gray-300 block">
              Expert accompagnant
            </label>
            <select
              v-if="canManageEvaluations"
              id="accompanying-expert"
              :value="selectedProject.accompanyingExpert?.id ?? ''"
              :disabled="store.isLoading"
              @change="changeAccompanyingExpert"
              class="w-full bg-[#181a20] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 disabled:opacity-50"
            >
              <option value="">Aucun accompagnant</option>
              <option v-for="expert in store.accompanyingExperts" :key="expert.id" :value="expert.id">
                {{ expert.prenom }} {{ expert.nom }} · {{ expert.email }}
              </option>
            </select>
            <p v-else class="text-sm text-white">
              <template v-if="selectedProject.accompanyingExpert">
                {{ selectedProject.accompanyingExpert.prenom }} {{ selectedProject.accompanyingExpert.nom }}
              </template>
              <span v-else class="text-gray-500">Non affecté</span>
            </p>
            <p
              v-if="assignmentMessage"
              role="status"
              :class="assignmentMessage.type === 'success' ? 'text-[#00ff88]' : 'text-rose-400'"
              class="text-xs"
            >
              {{ assignmentMessage.text }}
            </p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div class="bg-[#121418] p-3.5 rounded-lg border border-[#282c37]">
              <span class="block mb-1.5 font-semibold text-gray-400">Page du projet</span>
              <a
                v-if="selectedProject.personalPageUrl && selectedProject.personalPageSiteName"
                :href="selectedProject.personalPageUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="font-bold text-[#00ff88] hover:underline"
              >
                {{ selectedProject.personalPageSiteName }}
              </a>
              <span v-else class="text-gray-500">Non renseigné</span>
            </div>
            <div class="bg-[#121418] p-3.5 rounded-lg border border-[#282c37]">
              <span class="block mb-1.5 font-semibold text-gray-400">Objectifs à court terme (dans l’année)</span>
              <p class="whitespace-pre-wrap leading-relaxed text-gray-300">
                {{ selectedProject.objectifsCourtTerme || 'Non renseigné' }}
              </p>
            </div>
            <div class="bg-[#121418] p-3.5 rounded-lg border border-[#282c37]">
              <span class="block mb-1.5 font-semibold text-gray-400">Objectifs à moyen terme (dans 5 ans)</span>
              <p class="whitespace-pre-wrap leading-relaxed text-gray-300">
                {{ selectedProject.objectifsMoyenTerme || 'Non renseigné' }}
              </p>
            </div>
          </div>

          <div class="bg-[#121418] border border-[#282c37] rounded-lg p-3.5 space-y-2">
            <span class="block text-xs font-semibold text-gray-400">Demandes de subvention effectuées</span>
            <div v-if="selectedProject.grantApplications.length" class="divide-y divide-[#282c37]">
              <div v-for="application in selectedProject.grantApplications" :key="application.deadlineId" class="flex flex-wrap justify-between gap-2 py-2 text-xs">
                <strong class="text-gray-200">{{ application.bailleur }}</strong>
                <span class="text-gray-400">Déposée le {{ formatMetricDate(application.dateDepot) }} · échéance {{ formatMetricDate(application.dateEcheance) }}</span>
              </div>
            </div>
            <span v-else class="text-xs text-gray-500">Aucune demande déclarée.</span>
          </div>

          <!-- Métriques Démographiques & Cantonales -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 py-3 border-y border-[#282c37] text-xs">
            <div>
              <span class="text-gray-400 block">Sur scène (H / F / Autre)</span>
              <strong class="text-gray-200">
                {{ selectedProject.hommesSurScene }}H · {{ selectedProject.femmesSurScene }}F · {{ selectedProject.autresSurScene }}Autre
              </strong>
            </div>
            <div>
              <span class="text-gray-400 block">Âges déclarés</span>
              <strong class="text-gray-200">{{ selectedProject.ages }}</strong>
            </div>
            <div>
              <span class="text-gray-400 block">Langue chant</span>
              <strong class="text-gray-200">{{ selectedProject.langueChant }}</strong>
            </div>
            <div>
              <span class="text-gray-400 block">Statut Juridique</span>
              <strong class="text-gray-200">{{ selectedProject.statutJuridique }}</strong>
            </div>
          </div>

          <!-- Indicateurs de Vitalité & Réseau -->
          <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3 text-xs">
            <div class="bg-[#121418] p-2.5 rounded border border-[#282c37]">
              <span class="text-gray-400 block text-[11px]">Concerts (NE / CH / Export)</span>
              <strong class="text-sm text-white font-black">
                {{ selectedProject.concerts.local }} / {{ selectedProject.concerts.horsCanton }} / <span class="text-[#00ff88]">{{ selectedProject.concerts.export }}</span>
              </strong>
            </div>
            <div class="col-span-2 bg-[#121418] p-2.5 rounded border border-[#282c37]">
              <span class="text-gray-400 block text-[11px] mb-1.5">Audience</span>
              <div v-if="selectedProject.audienceMetrics.length" class="space-y-1">
                <div
                  v-for="metric in selectedProject.audienceMetrics"
                  :key="`${metric.platform}-${metric.type}`"
                  class="flex items-baseline justify-between gap-3"
                >
                  <span class="min-w-0 truncate text-[11px] text-gray-400">
                    {{ metric.platform }} · {{ audienceMetricLabels[metric.type] || metric.type }}
                  </span>
                  <strong class="shrink-0 text-sm text-white font-black">
                    {{ metric.value.toLocaleString('fr-CH') }}
                  </strong>
                </div>
                <span class="block pt-1 text-[10px] text-gray-500">
                  Relevé du {{ formatMetricDate(selectedProject.audienceMetrics[0]!.date) }}
                </span>
              </div>
              <strong v-else class="text-sm text-gray-500 font-semibold">Aucun relevé disponible</strong>
            </div>
            <div class="bg-[#121418] p-2.5 rounded border border-[#282c37]">
              <span class="text-gray-400 block text-[11px]">Résidences effectuées</span>
              <strong class="text-sm text-white font-black">{{ selectedProject.residencesCount }} session(s)</strong>
            </div>
            <div class="bg-[#121418] p-2.5 rounded border border-[#282c37]">
              <span class="text-gray-400 block text-[11px]">Inscription SUISA</span>
              <strong :class="selectedProject.suisaInscrit ? 'text-[#00ff88]' : 'text-gray-300'" class="text-sm font-black">
                {{ selectedProject.suisaInscrit ? 'Inscrit' : 'Non inscrit' }}
              </strong>
            </div>
            <div class="bg-[#121418] p-2.5 rounded border border-[#282c37]">
              <span class="text-gray-400 block text-[11px]">Merchandising</span>
              <strong :class="selectedProject.hasMerch ? 'text-[#00ff88]' : 'text-gray-300'" class="text-sm font-black">
                {{ selectedProject.hasMerch ? 'Disponible' : 'Non disponible' }}
              </strong>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 border-y border-[#282c37] py-4">
            <div class="space-y-2">
              <h3 class="text-xs uppercase font-bold text-gray-400">Formations suivies</h3>
              <div v-if="selectedProject.formationsSuivies.length" class="space-y-2">
                <div
                  v-for="formation in selectedProject.formationsSuivies"
                  :key="`${formation.formationId}-${formation.dateSuivi}`"
                  class="flex items-start justify-between gap-3 text-xs"
                >
                  <div class="min-w-0">
                    <strong class="block text-gray-200">{{ formation.nom }}</strong>
                    <span v-if="formation.organisme" class="text-gray-500">{{ formation.organisme }}</span>
                  </div>
                  <span class="shrink-0 text-gray-400">{{ formatMetricDate(formation.dateSuivi) }}</span>
                </div>
              </div>
              <p v-else class="text-xs text-gray-500">Aucune formation renseignée.</p>
            </div>

            <div class="space-y-2">
              <h3 class="text-xs uppercase font-bold text-gray-400">Programmes d’accompagnement</h3>
              <div v-if="selectedProject.programmesPrecedents.length" class="space-y-2">
                <div
                  v-for="program in selectedProject.programmesPrecedents"
                  :key="`${program.programmeId}-${program.anneeParticipation}`"
                  class="flex items-start justify-between gap-3 text-xs"
                >
                  <div class="min-w-0">
                    <strong class="block text-gray-200">{{ program.nom }}</strong>
                    <span v-if="program.organisme" class="text-gray-500">{{ program.organisme }}</span>
                  </div>
                  <span
                    :class="program.estLaureat ? 'text-[#00ff88]' : 'text-gray-400'"
                    class="shrink-0 font-semibold"
                  >
                    {{ program.anneeParticipation }} · {{ program.estLaureat ? 'Lauréat' : 'Participant' }}
                  </span>
                </div>
              </div>
              <p v-else class="text-xs text-gray-500">Aucun programme renseigné.</p>
            </div>
          </div>

          <!-- Tracks en Écoute directe (Top Streams) -->
          <div class="space-y-2">
            <span class="text-xs uppercase font-bold text-gray-400 tracking-wider">Top 3 Streaming Tracks</span>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div v-for="t in selectedProject.streamingTopTracks" :key="t.titre" class="bg-[#121418] border border-[#282c37] p-2 rounded flex justify-between items-center text-xs">
                <span class="truncate text-gray-200">🎵 {{ t.titre }}</span>
                <span class="text-[10px] text-[#00ff88] font-bold shrink-0">{{ t.views }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Bloc 2 : Grille d'Évaluation Officielle (Saisie Jury & Décision) -->
        <section class="bg-[#181a20] border border-[#282c37] rounded-xl p-6 space-y-6">
          <div class="flex items-center justify-between border-b border-[#282c37] pb-3">
            <h2 class="text-base font-extrabold text-white uppercase tracking-wider">
              Grille de Notation (Critères Embrayage)
            </h2>
            <span class="text-xs text-gray-400">Pondération dynamique</span>
          </div>

          <div v-if="objectiveCriteria.length" class="space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="text-xs font-bold uppercase tracking-wider text-gray-300">Critères objectifs</h3>
              <span class="text-xs font-black text-[#00ff88]">
                {{ scoredObjectiveCount }} / {{ objectiveCriteria.length }} renseignés
              </span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                v-for="criterion in objectiveCriteria"
                :key="criterion.id"
                class="flex items-center gap-3 bg-[#121418] border border-[#282c37] rounded p-3"
              >
                <input v-if="criterion.noteMaximale === 1" v-model="selectedProject.scores[criterion.code]" type="checkbox" :true-value="1" :false-value="0" :disabled="!canEditCriterion(criterion)" class="h-5 w-5 accent-[#00ff88] disabled:opacity-70" />
                <input v-else v-model.number="selectedProject.scores[criterion.code]" type="number" min="0" :max="criterion.noteMaximale" :disabled="!canEditCriterion(criterion)" class="w-20 bg-[#0e0f12] border border-[#343845] px-2 py-1 text-sm disabled:opacity-50" />
                <span class="min-w-0"><strong class="block text-xs text-gray-100">{{ criterion.nom }}</strong><small class="text-[10px] text-gray-500">{{ criterion.modeEvaluation === 'automatique' ? 'Calcul automatique' : 'Saisie manuelle' }}</small></span>
              </label>
            </div>
          </div>

          <div v-if="subjectiveCriteria.length" class="space-y-3 pt-4 border-t border-[#282c37]">
            <h3 class="text-xs font-bold uppercase tracking-wider text-gray-300">Critères subjectifs</h3>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div v-for="criterion in subjectiveCriteria" :key="criterion.id" class="space-y-1">
              <label class="text-xs text-gray-300 font-semibold block">{{ criterion.nom }} (/{{ criterion.noteMaximale }})</label>
              <input
                type="number"
                min="0"
                :max="criterion.noteMaximale"
                v-model.number="selectedProject.scores[criterion.code]"
                :disabled="!canEditCriterion(criterion)"
                class="w-full bg-[#121418] border border-[#282c37] rounded px-3 py-2 text-sm text-white focus:border-[#7c3aed] focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            </div>
          </div>

          <div class="space-y-3 pt-4 border-t border-[#282c37]">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-gray-300">Notes globales du jury</span>
              <strong class="text-xs text-[#00ff88]">{{ selectedEvaluation?.juryCoverageCount ?? 0 }} / {{ selectedEvaluation?.juryCount ?? 0 }} reçues</strong>
            </div>
            <div v-if="selectedEvaluation?.juryNotes.length" class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div v-for="note in selectedEvaluation.juryNotes" :key="note.expertId" class="border border-[#282c37] bg-[#121418] p-3">
                <span class="text-gray-400 block text-[11px]">{{ note.estNotePersonnelle ? 'Ma note' : note.expertNom }}</span>
                <strong class="mt-1 block text-lg text-white">{{ note.note ?? '—' }}<small class="text-gray-500"> /20</small></strong>
              </div>
            </div>
            <label v-if="store.accountIdentity?.role === 'expert_jury'" class="block max-w-xs">
              <span class="mb-1 block text-xs font-semibold text-gray-300">Ma note globale entière (/20)</span>
              <input
                v-model.number="juryNote"
                type="number"
                min="0"
                max="20"
                step="1"
                :disabled="!canSaveJuryNote"
                class="w-full bg-[#121418] border border-[#282c37] rounded px-3 py-2 text-white disabled:opacity-50"
              />
            </label>
            <p v-if="campaignStore.selectedCampaign?.statut === 'cloturee'" class="text-xs text-amber-300">Cette campagne est clôturée; les saisies sont verrouillées.</p>
          </div>

          <!-- Remarques & Décision -->
          <div v-if="canManageEvaluations" class="space-y-3 pt-4 border-t border-[#282c37]">
            <label class="text-xs text-gray-300 font-semibold block">Appréciation qualitative & Remarques confidentielles</label>
            <textarea
              v-model="selectedProject.remarques"
              :disabled="!canManageEvaluations"
              rows="3"
              class="w-full bg-[#121418] border border-[#282c37] rounded-lg p-3 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed] disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Inscrire ici les axes prioritaires d'accompagnement (résidence, admin, booking)..."
            ></textarea>
          </div>

          <div class="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
            <div v-if="canManageEvaluations" class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                @click="selectDecision('selectionne')"
                :class="[
                  'px-4 py-2 rounded-lg border text-xs font-bold transition-all outline-offset-2',
                  selectedProject.statutSelection === 'selectionne'
                    ? 'bg-[#00ff88] border-[#00ff88] text-black shadow-lg shadow-[#00ff88]/20 outline-2 outline-[#00ff88]'
                    : 'bg-[#121418] border-[#282c37] text-gray-300 outline-none hover:border-[#00ff88]'
                ]"
              >
                ✓ Retenir pour Embrayage
              </button>
              <button
                type="button"
                @click="selectDecision('refuse')"
                :class="[
                  'px-4 py-2 rounded-lg border text-xs font-bold transition-all outline-offset-2',
                  selectedProject.statutSelection === 'refuse'
                    ? 'bg-rose-500 border-rose-500 text-white outline-2 outline-rose-500'
                    : 'bg-[#121418] border-[#282c37] text-gray-300 outline-none hover:border-rose-500'
                ]"
              >
                ✕ Refuser
              </button>
              <button
                type="button"
                @click="selectDecision('en_attente')"
                :class="[
                  'px-4 py-2 rounded-lg border text-xs font-bold transition-all outline-offset-2',
                  selectedProject.statutSelection === 'en_attente'
                    ? 'bg-[#282c37] border-amber-300 text-amber-200 outline-2 outline-amber-300'
                    : 'bg-[#121418] border-[#282c37] text-gray-300 outline-none hover:border-amber-300'
                ]"
              >
                En attente
              </button>
            </div>

            <div v-if="canManageEvaluations" class="w-full sm:w-auto flex flex-col items-start sm:items-end gap-2">
              <span
                v-if="selectedProject.decisionEmailSentAt"
                class="inline-flex items-center gap-2 text-xs font-bold text-[#00ff88]"
              >
                <span class="w-2 h-2 rounded-full bg-[#00ff88]"></span>
                Mail envoyé
              </span>
              <template v-else>
                <span class="inline-flex items-center gap-2 text-xs font-bold text-amber-300">
                  <span class="w-2 h-2 rounded-full bg-amber-300"></span>
                  Mail non envoyé
                </span>
                <button
                  type="button"
                  @click="prepareDecisionEmail"
                  :disabled="store.isLoading || selectedProject.statutSelection === 'en_attente' || decisionNeedsSave || selectedProject.memberEmails.length === 0"
                  class="px-4 py-2 rounded-lg border border-[#00ff88]/50 bg-[#00ff88]/10 text-xs font-bold text-[#00ff88] hover:bg-[#00ff88]/20 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Ouvrir le client mail
                </button>
                <span v-if="decisionNeedsSave" class="text-[11px] text-gray-500">Enregistrez d’abord la décision.</span>
                <span v-else-if="selectedProject.memberEmails.length === 0" class="text-[11px] text-rose-400">Aucune adresse membre renseignée.</span>
              </template>
            </div>

            <div v-if="canSaveEvaluation" class="w-full sm:w-auto flex flex-col items-stretch sm:items-end gap-2">
              <button
                @click="saveEvaluation"
                :disabled="store.isLoading"
                class="w-full sm:w-auto px-5 py-2 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold rounded-lg transition-colors"
              >
                {{ store.isLoading ? 'Enregistrement…' : "Enregistrer l'évaluation" }}
              </button>
              <p
                v-if="saveMessage"
                role="status"
                :class="saveMessage.type === 'success' ? 'text-[#00ff88]' : 'text-rose-400'"
                class="text-xs"
              >
                {{ saveMessage.text }}
              </p>
            </div>
            <div v-if="store.accountIdentity?.role === 'expert_jury'" class="w-full sm:w-auto flex flex-col items-stretch sm:items-end gap-2">
              <button
                @click="saveJuryNote"
                :disabled="campaignStore.isLoading || !canSaveJuryNote || juryNote === null"
                class="w-full sm:w-auto px-5 py-2 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold rounded-lg transition-colors"
              >
                {{ campaignStore.isLoading ? 'Enregistrement…' : 'Enregistrer ma note' }}
              </button>
              <p v-if="saveMessage" role="status" :class="saveMessage.type === 'success' ? 'text-[#00ff88]' : 'text-rose-400'" class="text-xs">{{ saveMessage.text }}</p>
            </div>
          </div>
        </section>
      </main>
      <main v-else class="lg:col-span-8 bg-[#181a20] border border-[#282c37] rounded-xl p-6 text-sm text-gray-400">
        Aucun projet à évaluer.
      </main>
    </div>
  </div>
</template>