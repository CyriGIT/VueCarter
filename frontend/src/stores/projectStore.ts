import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api'
import type { 
  AccountIdentity,
  AccompanyingExpert,
  AccompanimentReference,
  MusicalProject, 
  UserProfile, 
  SyncConnectors, 
  Track, 
  AssetDeleteResponse,
  AssetMutationResponse,
  AssetType,
  AssetWrite,
  Concert, 
  ConcertCreate,
  Member, 
  EvaluationScores,
  StyleMusical,
  SpotifyCatalog,
  Mx3Band,
  Mx3Gig,
  Venue,
  LegalStatus
} from '@/types/project'
import type { GrantApplicationWrite } from '@/types/grantDeadline'

function apiErrorDetail(error: any, fallback: string): string {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map(item => typeof item?.msg === 'string' ? item.msg : String(item))
      .join(' · ')
  }
  return fallback
}

export const useProjectStore = defineStore('project', () => {
  // State
  const isLoading = ref<boolean>(false)
  const errorMessage = ref<string | null>(null)

  // Profil artiste (Données démographiques & administratives)
  const userProfile = ref<UserProfile | null>(null)
  const accountIdentity = ref<AccountIdentity | null>(null)

  function resetAccountIdentity() {
    accountIdentity.value = null
  }

  // État des connecteurs API
  const connectors = ref<SyncConnectors>({
    spotify: { connected: false, metrics: [] },
    mx3: { connected: false, metrics: [] }
  })

  const resetConnectors = () => {
    connectors.value = {
      spotify: { connected: false, metrics: [] },
      mx3: { connected: false, metrics: [] }
    }
  }

  // Taxonomie des styles musicaux (arbre à 3 niveaux), chargée depuis l'API
  const styleTaxonomy = ref<StyleMusical[]>([])
  const venues = ref<Venue[]>([])
  const legalStatuses = ref<LegalStatus[]>([])
  const assetTypes = ref<AssetType[]>([])
  const formationReferences = ref<AccompanimentReference[]>([])
  const programReferences = ref<AccompanimentReference[]>([])
  const accompanyingExperts = ref<AccompanyingExpert[]>([])

  // Liste des projets musicaux
  const projects = ref<MusicalProject[]>([])
  const concertCreates = ref<ConcertCreate[]>([])
  const evaluations = ref<EvaluationScores[]>([])
  const members = ref<Member[]>([])

  const selectedProjectId = ref<number | undefined>(undefined)

  // Computed
  const currentProject = computed<MusicalProject | undefined>(() => {
    return projects.value.find(p => p.id === selectedProjectId.value) || projects.value[0]
  })

  // Répartition statistique des dates de concert (Canton NE, Suisse, Export)
  const concertStats = computed(() => {
    if (!currentProject.value) return { local: 0, horsCanton: 0, export: 0 }
    const list = currentProject.value.concerts
    return {
      local: list.filter(c => c.type === 'Local (NE)').length,
      horsCanton: list.filter(c => c.type === 'Hors-Canton').length,
      export: list.filter(c => c.type === 'Export').length
    }
  })

  // Actions
  function setSelectedProject(id: number) {
    selectedProjectId.value = id
  }

  // Récupération de la taxonomie des styles musicaux (arbre à 3 niveaux)
  async function fetchStyleTaxonomy() {
    try {
      const response = await apiClient.get('/styles')
      styleTaxonomy.value = response.data
    } catch (err: any) {
      console.warn('Taxonomie des styles non chargée depuis l’API.', err.message)
    }
  }

  async function fetchLegalStatuses() {
    try {
      const response = await apiClient.get('/references/legal-statuses')
      legalStatuses.value = response.data
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors du chargement des statuts juridiques.')
    }
  }

  async function fetchAccompanimentReferences(): Promise<boolean> {
    errorMessage.value = null
    try {
      const [formationsResponse, programsResponse] = await Promise.all([
        apiClient.get('/references/formations'),
        apiClient.get('/references/programs')
      ])
      formationReferences.value = formationsResponse.data
      programReferences.value = programsResponse.data
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors du chargement des formations et programmes.')
      return false
    }
  }

  async function updateProjectAccompaniment(
    projectId: number,
    formationsSuivies: { formationId: number; dateSuivi: string }[],
    programmesPrecedents: { programmeId: number; anneeParticipation: number; estLaureat: boolean }[]
  ): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.put(`/projects/${projectId}/accompaniment`, {
        formationsSuivies,
        programmesPrecedents
      })
      const project = projects.value.find(item => item.id === projectId)
      if (project) {
        project.formationsSuivies = response.data.formationsSuivies
        project.programmesPrecedents = response.data.programmesPrecedents
      }
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Les formations et programmes n’ont pas pu être enregistrés.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function fetchVenues(): Promise<boolean> {
    errorMessage.value = null
    try {
      const response = await apiClient.get('/venues')
      venues.value = response.data
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors du chargement des salles.'
      return false
    }
  }

  async function fetchConnectors(projectId: number): Promise<boolean> {
    resetConnectors()
    errorMessage.value = null
    try {
      const response = await apiClient.get(`/etl/projects/${projectId}/connectors`)
      connectors.value = response.data
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors du chargement des connecteurs.'
      return false
    }
  }

  // Mise à jour des styles musicaux d'un projet (remplace l'association ProjetStyle)
  async function updateProjectStyles(
    projectId: number,
    styles: { styleId: number; principal: boolean }[]
  ): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.put(`/projects/${projectId}/styles`, { styles })
      const project = projects.value.find(p => p.id === projectId)
      if (project) project.styles = response.data
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la mise à jour des styles musicaux.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Création d'un nouveau projet musical, rattaché à l'utilisateur connecté
  async function createProject(data: {
    nom: string
    dateCreation?: string
    langueChant?: string
    statutJuridiqueId?: number
    statutJuridique?: string
    bioCourte?: string
  }): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.post('/projects', data)
      await fetchProjects()
      selectedProjectId.value = response.data.id
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la création du projet.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Suppression d'un projet musical (cascade côté backend sur toutes ses données liées)
  async function deleteProject(projectId: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      await apiClient.delete(`/projects/${projectId}`)
      projects.value = projects.value.filter(p => p.id !== projectId)
      if (selectedProjectId.value === projectId) {
        selectedProjectId.value = projects.value[0]?.id ?? 1
      }
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la suppression du projet.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Ajout d'un membre à un projet (réutilise une Personne existante par email, ou en crée une)
  async function addMember(projectId: number, data: {
    nom: string
    prenom: string
    dateNaissance: string
    genre: string
    npa: string
    ville: string
    email: string
    telephone?: string
    role: string
  }): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const project = projects.value.find(p => p.id === projectId)
      const alreadyExists = project?.members.some(m => m.email.toLowerCase() === data.email.toLowerCase())
      if (alreadyExists) {
        errorMessage.value = 'Cette personne est déjà membre du projet.'
        return false
      }

      const response = await apiClient.post(`/projects/${projectId}/members`, data)
      if (project) project.members.push(response.data)
      return true
    } catch (err: any) {
      if (err.response?.status === 409) {
        errorMessage.value = 'Cette personne est déjà membre du projet.'
      } else {
        errorMessage.value = err.response?.data?.detail || 'Erreur lors de l’ajout du membre.'
      }
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Retrait d'un membre du projet (départ logique, conserve l'historique)
  async function removeMember(projectId: number, personneId: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      await apiClient.delete(`/projects/${projectId}/members/${personneId}`)
      const project = projects.value.find(p => p.id === projectId)
      if (project) project.members = project.members.filter(m => m.id !== personneId)
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors du retrait du membre.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Génère un lien d'invitation pour qu'un membre crée son propre compte de connexion
  async function inviteMember(projectId: number, personneId: number): Promise<string | null> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.post(`/projects/${projectId}/members/${personneId}/invite`)
      return response.data.invitationUrl
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la génération de l’invitation.'
      return null
    } finally {
      isLoading.value = false
    }
  }

  // Mise à jour des métadonnées du projet (nom, date de création, statut juridique, SUISA, local, fiche technique, merch)
  async function updateProject(projectId: number, data: {
    nom: string
    dateCreation: string
    statutJuridiqueId: number
    statutJuridique: string
    suisaInscrit: boolean
    hasLocal: boolean
    hasFicheTechnique: boolean
    hasMerch: boolean
    personalPageUrl: string | null
    personalPageSiteName: string | null
    objectifsCourtTerme: string | null
    objectifsMoyenTerme: string | null
  }): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.put(`/projects/${projectId}`, data)
      const project = projects.value.find(p => p.id === projectId)
      if (project) Object.assign(project, response.data)
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la mise à jour du projet.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Remplace le visuel officiel du projet (URL manuelle)
  async function updateProjectImage(projectId: number, url: string): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.put(`/projects/${projectId}/image`, { url })
      const project = projects.value.find(p => p.id === projectId)
      if (project) project.avatarUrl = response.data.avatarUrl
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la mise à jour de l’image.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Importe la photo de profil de l'artiste Spotify lié comme visuel officiel du projet
  async function importSpotifyImage(projectId: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.post(`/etl/spotify/${projectId}/import-image`)
      const project = projects.value.find(p => p.id === projectId)
      if (project) project.avatarUrl = response.data.avatarUrl
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de l’import de l’image Spotify.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Récupération de la fiche personnelle de l'utilisateur connecté
  async function fetchAccountIdentity(): Promise<boolean> {
    resetAccountIdentity()
    try {
      const response = await apiClient.get('/me/account')
      accountIdentity.value = response.data
      return true
    } catch (err: any) {
      console.warn('Identité du compte non chargée depuis l’API.', err.message)
      return false
    }
  }

  async function fetchUserProfile() {
    try {
      const response = await apiClient.get('/me')
      userProfile.value = { ...userProfile.value, ...response.data }
    } catch (err: any) {
      console.warn('Profil utilisateur non chargé depuis l’API, conservation des données locales.', err.message)
    }
  }

  // Mise à jour de la fiche personnelle (nom, prénom, naissance, genre, adresse, npa, ville, canton, téléphone, email)
  async function updateUserProfile(data: {
    nom: string
    prenom: string
    dateNaissance: string
    genre: string
    adresse?: string
    npa: string
    ville: string
    canton?: string
    telephone?: string
    email: string
  }): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.put('/me', {
        nom_civil: data.nom,
        prenom: data.prenom,
        date_naissance: data.dateNaissance,
        genre: data.genre,
        adresse: data.adresse,
        npa: data.npa,
        ville: data.ville,
        canton: data.canton,
        telephone: data.telephone,
        email: data.email
      })
      userProfile.value = { ...userProfile.value, ...response.data }
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la mise à jour du profil.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Récupération de tous les projets depuis l'API
  async function fetchProjects() {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.get('/projects')
      if (response.data && Array.isArray(response.data)) {
        projects.value = response.data
        if (!projects.value.some(project => project.id === selectedProjectId.value)) {
          selectedProjectId.value = projects.value[0]?.id
        }
      }
    } catch (err: any) {
      projects.value = []
      selectedProjectId.value = undefined
      errorMessage.value = apiErrorDetail(err, 'Erreur lors du chargement des projets.')
    } finally {
      isLoading.value = false
    }
  }

  async function declareGrantApplication(projectId: number, payload: GrantApplicationWrite): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.post(`/grant-deadlines/projects/${projectId}/applications`, payload)
      const project = projects.value.find(item => item.id === projectId)
      if (project) {
        project.grantApplications = [
          ...(project.grantApplications || []).filter(item => item.deadlineId !== payload.deadlineId),
          response.data
        ]
        project.hasDemandeSubvention = true
      }
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'La demande de subvention n’a pas pu être déclarée.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function withdrawGrantApplication(projectId: number, deadlineId: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      await apiClient.delete(`/grant-deadlines/projects/${projectId}/applications/${deadlineId}`)
      const project = projects.value.find(item => item.id === projectId)
      if (project) {
        project.grantApplications = (project.grantApplications || []).filter(item => item.deadlineId !== deadlineId)
      }
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'La déclaration de demande n’a pas pu être retirée.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Morceaux (Tracks)
  async function addTrack(projectId: number, trackData: Omit<Track, 'id'>) {
    isLoading.value = true
    try {
      // Appel API Python
      const response = await apiClient.post(`/projects/${projectId}/tracks`, trackData)
      const newTrack = response.data
      const project = projects.value.find(p => p.id === projectId)
      if (project) project.tracks.push(newTrack)
    } catch {
      // Fallback local
      const project = projects.value.find(p => p.id === projectId)
      if (project) {
        const newId = project.tracks.length > 0 ? Math.max(...project.tracks.map(t => t.id)) + 1 : 1
        project.tracks.push({ id: newId, ...trackData })
      }
    } finally {
      isLoading.value = false
    }
  }

  async function updateTrackOriginality(projectId: number, trackId: number, estOriginal: boolean): Promise<boolean> {
    errorMessage.value = null
    try {
      const response = await apiClient.patch(`/projects/${projectId}/tracks/${trackId}/originality`, { estOriginal })
      const project = projects.value.find(p => p.id === projectId)
      const track = project?.tracks.find(item => item.id === trackId)
      if (track) track.estOriginal = response.data.estOriginal
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la mise à jour du morceau.'
      return false
    }
  }

  async function removeTrack(projectId: number, trackId: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      await apiClient.delete(`/projects/${projectId}/tracks/${trackId}`)
      const project = projects.value.find(p => p.id === projectId)
      if (project) {
        project.tracks = project.tracks.filter(t => t.id !== trackId)
      }
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors de la suppression du morceau.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Assets Multimédias
  async function fetchAssetTypes(): Promise<boolean> {
    errorMessage.value = null
    try {
      const response = await apiClient.get<AssetType[]>('/asset-types')
      assetTypes.value = response.data
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors du chargement des types d’assets.')
      return false
    }
  }

  function applyAssetMutation(projectId: number, response: AssetMutationResponse, previousEventId?: number | null) {
    const project = projects.value.find(p => p.id === projectId)
    if (!project) return
    const assetIndex = project.assets.findIndex(asset => asset.id === response.asset.id)
    if (assetIndex === -1) project.assets.push(response.asset)
    else project.assets[assetIndex] = response.asset

    const eventIdsToRemove = [previousEventId, response.asset.eventId]
      .filter((eventId): eventId is number => eventId !== null && eventId !== undefined)
    project.highlights = (project.highlights ?? []).filter(highlight => !eventIdsToRemove.includes(highlight.id))
    if (response.highlight) {
      project.highlights.push(response.highlight)
      project.highlights.sort((left, right) => right.date.localeCompare(left.date))
    }
  }

  async function addAsset(projectId: number, assetData: AssetWrite, file?: File | null): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = file
        ? await apiClient.post<AssetMutationResponse>(
            `/projects/${projectId}/assets/upload`,
            createAssetFormData(assetData, file)
          )
        : await apiClient.post<AssetMutationResponse>(`/projects/${projectId}/assets`, assetData)
      applyAssetMutation(projectId, response.data)
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors de la création de l’asset.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  function createAssetFormData(assetData: AssetWrite, file: File): FormData {
    const formData = new FormData()
    formData.append('payload', JSON.stringify(assetData))
    formData.append('file', file)
    return formData
  }

  async function updateAsset(projectId: number, assetId: number, assetData: AssetWrite, file?: File | null): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    const project = projects.value.find(p => p.id === projectId)
    const previousEventId = project?.assets.find(asset => asset.id === assetId)?.eventId
    try {
      const response = file
        ? await apiClient.patch<AssetMutationResponse>(
            `/projects/${projectId}/assets/${assetId}/upload`,
            createAssetFormData(assetData, file)
          )
        : await apiClient.patch<AssetMutationResponse>(`/projects/${projectId}/assets/${assetId}`, assetData)
      applyAssetMutation(projectId, response.data, previousEventId)
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors de la modification de l’asset.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function removeAsset(projectId: number, assetId: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.delete<AssetDeleteResponse>(`/projects/${projectId}/assets/${assetId}`)
      const project = projects.value.find(p => p.id === projectId)
      if (project) {
        project.assets = project.assets.filter(asset => asset.id !== response.data.assetId)
        if (response.data.eventId !== null) {
          project.highlights = (project.highlights ?? []).filter(highlight => highlight.id !== response.data.eventId)
        }
      }
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors de la suppression de l’asset.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Concerts & Tournées
  async function addConcert(projectId: number, concertData: ConcertCreate): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.post(`/projects/${projectId}/concerts`, concertData)
      const project = projects.value.find(p => p.id === projectId)
      if (project) project.concerts.push(response.data)
      if (concertData.newVenue) {
        venues.value.push({ id: response.data.venueId, ...concertData.newVenue })
        venues.value.sort((left, right) => left.nom.localeCompare(right.nom, 'fr'))
      }
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || "Erreur lors de l'ajout du concert."
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function removeConcert(projectId: number, concertId: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      await apiClient.delete(`/projects/${projectId}/concerts/${concertId}`)
      const project = projects.value.find(p => p.id === projectId)
      if (project) {
        project.concerts = project.concerts.filter(c => c.id !== concertId)
      }
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la suppression du concert.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Évaluation Embrayage (Réservé Expert / Case à Chocs)
  async function updateEvaluation(
    projectId: number,
    campaignId: number,
    scores: EvaluationScores, 
    remarques: string, 
    statut: 'en_attente' | 'selectionne' | 'refuse'
  ): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.put(`/projects/${projectId}/evaluation`, { campaignId, scores, remarques, statut })
      const project = projects.value.find(p => p.id === projectId)
      if (project) {
        project.scores = { ...response.data.scores }
        project.remarquesEvaluation = response.data.remarques
        project.statutSelection = response.data.statut
        project.decisionEmailSentAt = response.data.decisionEmailSentAt
      }
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors de l’enregistrement de l’évaluation.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function markDecisionEmailSent(projectId: number, campaignId: number): Promise<string | null> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.post(
        `/projects/${projectId}/evaluation/decision-email`,
        null,
        { params: { campaign_id: campaignId } }
      )
      const sentAt: string = response.data.decisionEmailSentAt
      const project = projects.value.find(item => item.id === projectId)
      if (project) project.decisionEmailSentAt = sentAt
      return sentAt
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Le suivi du mail n’a pas pu être enregistré.')
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAccompanyingExperts(): Promise<void> {
    errorMessage.value = null
    try {
      const response = await apiClient.get('/accompanying-experts')
      accompanyingExperts.value = response.data
    } catch (err: any) {
      accompanyingExperts.value = []
      errorMessage.value = apiErrorDetail(err, 'Erreur lors du chargement des accompagnants.')
    }
  }

  async function assignAccompanyingExpert(projectId: number, expertId: number | null): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.put(`/projects/${projectId}/accompanying-expert`, { expertId })
      const project = projects.value.find(item => item.id === projectId)
      if (project) project.accompanyingExpert = response.data
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'L’affectation de l’accompagnant a échoué.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Pipeline ETL Python (Synchronisation API externe)
  async function triggerEtlSync(platform: 'spotify' | 'mx3'): Promise<boolean> {
    if (selectedProjectId.value === undefined) return false
    isLoading.value = true
    errorMessage.value = null
    try {
      await apiClient.post(`/etl/sync/${platform}`, { projectId: selectedProjectId.value })
      await fetchConnectors(selectedProjectId.value)
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || `Erreur lors de la synchronisation ${platform.toUpperCase()}.`
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Lie un projet à un artiste Spotify (id ou URL) et met à jour l'état du connecteur
  async function connectSpotify(projectId: number, artistId: string): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      await apiClient.put(`/etl/spotify/${projectId}/connect`, { artistId })
      await fetchConnectors(projectId)
      return true
    } catch (err: any) {
      errorMessage.value = err.response?.data?.detail || 'Erreur lors de la connexion à Spotify.'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Récupère à la volée le catalogue Spotify (albums + morceaux) de l'artiste lié au projet
  async function fetchSpotifyCatalog(projectId: number): Promise<SpotifyCatalog | null> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.get(`/etl/spotify/${projectId}/catalog`)
      return response.data
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors du chargement du catalogue Spotify.')
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function searchMx3Bands(query: string): Promise<Mx3Band[] | null> {
    errorMessage.value = null
    try {
      const response = await apiClient.get('/etl/mx3/bands', { params: { query } })
      return response.data.bands
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors de la recherche MX3.')
      return null
    }
  }

  async function connectMx3(projectId: number, bandId: number): Promise<boolean> {
    errorMessage.value = null
    try {
      await apiClient.put(`/etl/mx3/${projectId}/connect`, { bandId })
      await fetchConnectors(projectId)
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors de la connexion à MX3.')
      return false
    }
  }

  async function fetchMx3Gigs(projectId: number): Promise<Mx3Gig[] | null> {
    errorMessage.value = null
    try {
      const response = await apiClient.get(`/etl/mx3/${projectId}/gigs`)
      return response.data.gigs
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors du chargement des concerts MX3.')
      return null
    }
  }

  // Importe en base les morceaux/albums Spotify sélectionnés par l'artiste
  async function importSpotifySelection(
    projectId: number,
    tracks: { spotifyId: string; titre: string; durationMs: number; releaseDate?: string }[],
    albums: { spotifyId: string; titre: string; releaseDate?: string }[]
  ): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      await apiClient.post(`/etl/spotify/${projectId}/import`, { tracks, albums })
      await fetchProjects()
      return true
    } catch (err: any) {
      errorMessage.value = apiErrorDetail(err, 'Erreur lors de l’import Spotify.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    isLoading,
    errorMessage,
    userProfile,
    accountIdentity,
    connectors,
    projects,
    selectedProjectId,
    styleTaxonomy,
    venues,
    legalStatuses,
    assetTypes,
    formationReferences,
    programReferences,
    accompanyingExperts,
    // Getters
    currentProject,
    concertStats,
    // Actions
    setSelectedProject,
    fetchProjects,
    declareGrantApplication,
    withdrawGrantApplication,
    fetchAccountIdentity,
    resetAccountIdentity,
    fetchUserProfile,
    updateUserProfile,
    updateProject,
    createProject,
    deleteProject,
    addMember,
    removeMember,
    inviteMember,
    updateProjectImage,
    importSpotifyImage,
    fetchStyleTaxonomy,
    fetchLegalStatuses,
    fetchAccompanimentReferences,
    fetchVenues,
    fetchConnectors,
    updateProjectStyles,
    updateProjectAccompaniment,
    addTrack,
    updateTrackOriginality,
    removeTrack,
    fetchAssetTypes,
    addAsset,
    updateAsset,
    removeAsset,
    addConcert,
    removeConcert,
    updateEvaluation,
    markDecisionEmailSent,
    fetchAccompanyingExperts,
    assignAccompanyingExpert,
    triggerEtlSync,
    connectSpotify,
    fetchSpotifyCatalog,
    searchMx3Bands,
    connectMx3,
    fetchMx3Gigs,
    importSpotifySelection
  }
})