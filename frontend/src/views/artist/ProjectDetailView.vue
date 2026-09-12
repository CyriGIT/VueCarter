<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projectStore'
import type {
  AssetMetadata,
  AssetWrite,
  JsonValue,
  MusicalProject,
  Mx3Band,
  Mx3Gig,
  ProjectAsset,
  SpotifyCatalog
} from '@/types/project'

const router = useRouter()
const route = useRoute()
const store = useProjectStore()

const project = computed<MusicalProject>(() => store.currentProject!)
const members = computed(() => store.currentProject?.members ?? [])
const tracks = computed(() => store.currentProject?.tracks ?? [])
const assets = computed(() => store.currentProject?.assets ?? [])
const concerts = computed(() => store.currentProject?.concerts ?? [])
const originalityUpdateTrackId = ref<number | null>(null)
const originalityUpdateError = ref<string | null>(null)
const formationDrafts = ref<Array<{ formationId: number; dateSuivi: string }>>([])
const programDrafts = ref<Array<{ programmeId: number; anneeParticipation: number; estLaureat: boolean }>>([])
const isSavingAccompaniment = ref(false)
const accompanimentFeedback = ref<{ type: 'success' | 'error'; message: string } | null>(null)
const newFormation = reactive({ formationId: '', dateSuivi: '' })
const newProgram = reactive({
  programmeId: '',
  anneeParticipation: new Date().getFullYear(),
  estLaureat: false
})

const formationLabel = (formationId: number) => {
  const reference = store.formationReferences.find(item => item.id === formationId)
  const existing = project.value.formationsSuivies.find(item => item.formationId === formationId)
  const item = reference || existing
  return item ? `${item.nom}${item.organisme ? ` · ${item.organisme}` : ''}` : `Formation #${formationId}`
}

const programLabel = (programmeId: number) => {
  const reference = store.programReferences.find(item => item.id === programmeId)
  const existing = project.value.programmesPrecedents.find(item => item.programmeId === programmeId)
  const item = reference || existing
  return item ? `${item.nom}${item.organisme ? ` · ${item.organisme}` : ''}` : `Programme #${programmeId}`
}

const formatAccompanimentDate = (value: string) => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  return match ? `${match[3]}.${match[2]}.${match[1]}` : value
}

function resetAccompanimentDrafts() {
  formationDrafts.value = project.value.formationsSuivies.map(item => ({
    formationId: item.formationId,
    dateSuivi: item.dateSuivi
  }))
  programDrafts.value = project.value.programmesPrecedents.map(item => ({
    programmeId: item.programmeId,
    anneeParticipation: item.anneeParticipation,
    estLaureat: item.estLaureat
  }))
}

function addFormationDraft() {
  const formationId = Number(newFormation.formationId)
  if (!formationId || !newFormation.dateSuivi) return
  if (formationDrafts.value.some(item => item.formationId === formationId && item.dateSuivi === newFormation.dateSuivi)) {
    accompanimentFeedback.value = { type: 'error', message: 'Cette formation est déjà renseignée à cette date.' }
    return
  }
  formationDrafts.value.push({ formationId, dateSuivi: newFormation.dateSuivi })
  newFormation.formationId = ''
  newFormation.dateSuivi = ''
  accompanimentFeedback.value = null
}

function addProgramDraft() {
  const programmeId = Number(newProgram.programmeId)
  const anneeParticipation = Number(newProgram.anneeParticipation)
  if (!programmeId || anneeParticipation < 1900 || anneeParticipation > 2100) return
  if (programDrafts.value.some(item => item.programmeId === programmeId && item.anneeParticipation === anneeParticipation)) {
    accompanimentFeedback.value = { type: 'error', message: 'Ce programme est déjà renseigné pour cette année.' }
    return
  }
  programDrafts.value.push({ programmeId, anneeParticipation, estLaureat: newProgram.estLaureat })
  newProgram.programmeId = ''
  newProgram.anneeParticipation = new Date().getFullYear()
  newProgram.estLaureat = false
  accompanimentFeedback.value = null
}

async function saveAccompaniment() {
  isSavingAccompaniment.value = true
  accompanimentFeedback.value = null
  const success = await store.updateProjectAccompaniment(
    project.value.id,
    formationDrafts.value,
    programDrafts.value
  )
  isSavingAccompaniment.value = false
  if (success) resetAccompanimentDrafts()
  accompanimentFeedback.value = success
    ? { type: 'success', message: 'Formations et programmes enregistrés.' }
    : { type: 'error', message: store.errorMessage || 'L’enregistrement a échoué.' }
}
const personalPageSites = ['Instagram', 'linktr.ee', 'lift.bio', 'hyperfollow.com', 'beacons.ai'] as const
const customPersonalPageSite = '__other__'
const isEnteringCustomPersonalPageSite = ref(false)
const personalPageSiteChoice = computed({
  get: () => isEnteringCustomPersonalPageSite.value
    ? customPersonalPageSite
    : personalPageSites.includes(project.value.personalPageSiteName as typeof personalPageSites[number])
    ? project.value.personalPageSiteName!
    : project.value.personalPageSiteName ? customPersonalPageSite : '',
  set: (choice: string) => {
    isEnteringCustomPersonalPageSite.value = choice === customPersonalPageSite
    project.value.personalPageSiteName = choice === customPersonalPageSite ? '' : choice || null
    if (!choice) project.value.personalPageUrl = null
  }
})

const customAssetTypeValue = '__custom__'
const showAssetForm = ref(false)
const editingAssetId = ref<number | null>(null)
const isSavingAsset = ref(false)
const assetFormError = ref<string | null>(null)
const metadataMode = ref<'pairs' | 'json'>('pairs')
const metadataPairs = ref<Array<{ key: string; value: string }>>([])
const metadataJson = ref('{}')
const selectedAssetFile = ref<File | null>(null)
const assetPendingDeletion = ref<ProjectAsset | null>(null)
const isDeletingAsset = ref(false)
const deleteAssetError = ref<string | null>(null)
const assetForm = reactive({
  titre: '',
  date: '',
  typeSelection: '',
  typeLibelle: '',
  url: '',
  featuredRoster: false,
  isJourneyEvent: false,
  eventSource: ''
})

const isAssetFormValid = computed(() => Boolean(
  assetForm.titre.trim()
  && assetForm.typeSelection
  && (assetForm.typeSelection !== customAssetTypeValue || assetForm.typeLibelle.trim())
  && (!assetForm.isJourneyEvent || assetForm.date)
))

function resetAssetForm() {
  editingAssetId.value = null
  assetForm.titre = ''
  assetForm.date = ''
  assetForm.typeSelection = ''
  assetForm.typeLibelle = ''
  assetForm.url = ''
  assetForm.featuredRoster = false
  assetForm.isJourneyEvent = false
  assetForm.eventSource = ''
  metadataMode.value = 'pairs'
  metadataPairs.value = []
  metadataJson.value = '{}'
  selectedAssetFile.value = null
  assetFormError.value = null
}

function openCreateAssetForm() {
  resetAssetForm()
  showAssetForm.value = true
}

function openEditAssetForm(asset: ProjectAsset) {
  resetAssetForm()
  editingAssetId.value = asset.id
  assetForm.titre = asset.titre
  assetForm.date = asset.date ?? ''
  assetForm.typeSelection = String(asset.typeId)
  assetForm.url = asset.url
  assetForm.featuredRoster = asset.featuredRoster
  assetForm.isJourneyEvent = asset.isJourneyEvent
  assetForm.eventSource = asset.eventSource ?? ''
  metadataJson.value = JSON.stringify(asset.metadata, null, 2)
  metadataPairs.value = Object.entries(asset.metadata).map(([key, value]) => ({
    key,
    value: typeof value === 'string' ? value : JSON.stringify(value)
  }))
  showAssetForm.value = true
}

function closeAssetForm() {
  showAssetForm.value = false
  resetAssetForm()
}

function addMetadataPair() {
  metadataPairs.value.push({ key: '', value: '' })
}

function selectAssetFile(event: Event) {
  const input = event.target as HTMLInputElement
  selectedAssetFile.value = input.files?.[0] ?? null
  if (selectedAssetFile.value) assetForm.url = ''
}

function clearAssetFile() {
  selectedAssetFile.value = null
}

function formatFileSize(size: number): string {
  return size < 1024 * 1024
    ? `${Math.ceil(size / 1024)} Ko`
    : `${(size / (1024 * 1024)).toFixed(1)} Mo`
}

function removeMetadataPair(index: number) {
  metadataPairs.value.splice(index, 1)
}

function parseMetadataValue(value: string): JsonValue {
  const trimmed = value.trim()
  if (!trimmed) return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return value
  }
}

function metadataFromPairs(): AssetMetadata | null {
  const metadata: AssetMetadata = {}
  for (const pair of metadataPairs.value) {
    const key = pair.key.trim()
    if (!key) {
      assetFormError.value = 'Chaque métadonnée doit avoir une clé.'
      return null
    }
    if (Object.prototype.hasOwnProperty.call(metadata, key)) {
      assetFormError.value = `La clé « ${key} » est utilisée plusieurs fois.`
      return null
    }
    metadata[key] = parseMetadataValue(pair.value)
  }
  return metadata
}

function metadataFromJson(): AssetMetadata | null {
  try {
    const parsed: unknown = JSON.parse(metadataJson.value)
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') {
      assetFormError.value = 'Les métadonnées JSON doivent former un objet.'
      return null
    }
    return parsed as AssetMetadata
  } catch {
    assetFormError.value = 'Le JSON des métadonnées est invalide.'
    return null
  }
}

function switchMetadataMode(mode: 'pairs' | 'json') {
  assetFormError.value = null
  if (mode === metadataMode.value) return
  if (mode === 'json') {
    const metadata = metadataFromPairs()
    if (!metadata) return
    metadataJson.value = JSON.stringify(metadata, null, 2)
  } else {
    const metadata = metadataFromJson()
    if (!metadata) return
    metadataPairs.value = Object.entries(metadata).map(([key, value]) => ({
      key,
      value: typeof value === 'string' ? value : JSON.stringify(value)
    }))
  }
  metadataMode.value = mode
}

async function submitAsset() {
  if (!isAssetFormValid.value || isSavingAsset.value) return
  assetFormError.value = null
  const metadata = metadataMode.value === 'pairs' ? metadataFromPairs() : metadataFromJson()
  if (!metadata) return

  const payload: AssetWrite = {
    titre: assetForm.titre.trim(),
    date: assetForm.date || null,
    ...(assetForm.typeSelection === customAssetTypeValue
      ? { typeLibelle: assetForm.typeLibelle.trim() }
      : { typeId: Number(assetForm.typeSelection) }),
    url: assetForm.url.trim(),
    metadata,
    featuredRoster: assetForm.featuredRoster,
    isJourneyEvent: assetForm.isJourneyEvent,
    eventSource: assetForm.isJourneyEvent ? assetForm.eventSource.trim() || null : null
  }

  isSavingAsset.value = true
  const success = editingAssetId.value === null
    ? await store.addAsset(project.value.id, payload, selectedAssetFile.value)
    : await store.updateAsset(project.value.id, editingAssetId.value, payload, selectedAssetFile.value)
  isSavingAsset.value = false
  if (success) {
    saveFeedback.value = {
      type: 'success',
      message: editingAssetId.value === null ? 'Asset créé avec succès.' : 'Asset modifié avec succès.'
    }
    closeAssetForm()
    setTimeout(() => { saveFeedback.value = null }, 4000)
  } else {
    assetFormError.value = store.errorMessage || 'Erreur lors de l’enregistrement de l’asset.'
  }
}

function metadataSummary(metadata: AssetMetadata): string {
  const entries = Object.entries(metadata).slice(0, 3)
  if (!entries.length) return 'Aucune métadonnée'
  return entries.map(([key, value]) => {
    const rendered = typeof value === 'string' ? value : JSON.stringify(value)
    return `${key}: ${rendered}`
  }).join(' · ')
}

function askDeleteAsset(asset: ProjectAsset) {
  assetPendingDeletion.value = asset
  deleteAssetError.value = null
}

function cancelDeleteAsset() {
  assetPendingDeletion.value = null
  deleteAssetError.value = null
}

async function confirmDeleteAsset() {
  if (!assetPendingDeletion.value || isDeletingAsset.value) return
  isDeletingAsset.value = true
  deleteAssetError.value = null
  const success = await store.removeAsset(project.value.id, assetPendingDeletion.value.id)
  isDeletingAsset.value = false
  if (success) {
    assetPendingDeletion.value = null
    saveFeedback.value = { type: 'success', message: 'Asset supprimé définitivement.' }
    setTimeout(() => { saveFeedback.value = null }, 4000)
  } else {
    deleteAssetError.value = store.errorMessage || 'Erreur lors de la suppression de l’asset.'
  }
}

// Vrai si l'ID demandé dans l'URL ne correspond à aucun projet accessible à l'utilisateur connecté
// (évite de basculer silencieusement sur un autre projet via le fallback de store.currentProject)
const requestedProjectId = computed(() => Number(route.params.id) || 1)
const projectAccessDenied = computed(() =>
  hasLoadedProject.value && !store.projects.some(p => p.id === requestedProjectId.value)
)

// Sélection en cascade (Niveau 1 : racine FCMA -> Niveau 2 : macro-genre -> Niveau 3 : sous-genre)
const selectedRootId = ref<number | null>(null)
const selectedBranchId = ref<number | null>(null)
const selectedLeafId = ref<number | null>(null)

const rootStyles = computed(() => store.styleTaxonomy.filter(s => s.idParent === null))
const branchStyles = computed(() =>
  selectedRootId.value === null ? [] : store.styleTaxonomy.filter(s => s.idParent === Number(selectedRootId.value))
)
const leafStyles = computed(() =>
  selectedBranchId.value === null ? [] : store.styleTaxonomy.filter(s => s.idParent === Number(selectedBranchId.value))
)

function onRootChange() {
  selectedBranchId.value = null
  selectedLeafId.value = null
}
function onBranchChange() {
  selectedLeafId.value = null
}

function addSelectedStyle() {
  if (!selectedLeafId.value) return
  const leaf = store.styleTaxonomy.find(s => s.id === Number(selectedLeafId.value))
  if (!leaf) return
  if (project.value.styles.some(s => s.id === leaf.id)) return
  project.value.styles.push({
    id: leaf.id,
    nom: leaf.nom,
    principal: project.value.styles.length === 0
  })
  selectedRootId.value = null
  selectedBranchId.value = null
  selectedLeafId.value = null
}

function removeStyle(styleId: number) {
  project.value.styles = project.value.styles.filter(s => s.id !== styleId)
  const hasPrincipal = project.value.styles.some(s => s.principal)
  if (!hasPrincipal && project.value.styles.length > 0) {
    project.value.styles[0]!.principal = true
  }
}

function setPrincipalStyle(styleId: number) {
  project.value.styles.forEach(s => { s.principal = s.id === styleId })
}

// Gestion des membres du projet : ajout, retrait, invitation à créer un compte de connexion
const showAddMemberForm = ref(false)
const isAddingMember = ref(false)
const addMemberError = ref<string | null>(null)
const newMemberForm = reactive({
  nom: '',
  prenom: '',
  dateNaissance: '',
  genre: 'Homme',
  npa: '',
  ville: '',
  email: '',
  telephone: '',
  role: ''
})
const memberPendingRemoval = ref<{ id: number; nom: string; prenom: string } | null>(null)
const isRemovingMember = ref(false)
const removeMemberError = ref<string | null>(null)
const invitationUrl = ref<string | null>(null)
const invitingMemberId = ref<number | null>(null)
const inviteError = ref<string | null>(null)

function toggleAddMemberForm() {
  addMemberError.value = null
  showAddMemberForm.value = !showAddMemberForm.value
}

async function addMember() {
  if (isAddingMember.value) return

  isAddingMember.value = true
  addMemberError.value = null
  const success = await store.addMember(project.value.id, { ...newMemberForm })
  isAddingMember.value = false
  if (success) {
    showAddMemberForm.value = false
    newMemberForm.nom = ''
    newMemberForm.prenom = ''
    newMemberForm.dateNaissance = ''
    newMemberForm.genre = 'Homme'
    newMemberForm.npa = ''
    newMemberForm.ville = ''
    newMemberForm.email = ''
    newMemberForm.telephone = ''
    newMemberForm.role = ''
  } else {
    addMemberError.value = store.errorMessage || 'Erreur lors de l’ajout du membre.'
  }
}

function askRemoveMember(member: { id: number; nom: string; prenom: string }) {
  memberPendingRemoval.value = member
  removeMemberError.value = null
}

function cancelRemoveMember() {
  memberPendingRemoval.value = null
  removeMemberError.value = null
}

async function confirmRemoveMember() {
  if (!memberPendingRemoval.value) return
  isRemovingMember.value = true
  removeMemberError.value = null
  const success = await store.removeMember(project.value.id, memberPendingRemoval.value.id)
  isRemovingMember.value = false
  if (success) {
    memberPendingRemoval.value = null
  } else {
    removeMemberError.value = store.errorMessage || 'Erreur lors du retrait du membre.'
  }
}

async function inviteMember(memberId: number) {
  invitingMemberId.value = memberId
  inviteError.value = null
  invitationUrl.value = null
  const url = await store.inviteMember(project.value.id, memberId)
  invitingMemberId.value = null
  if (url) {
    invitationUrl.value = url
  } else {
    inviteError.value = store.errorMessage || 'Erreur lors de la génération de l’invitation.'
  }
}

// Visuel officiel du projet (stocké comme Asset de type "Image")
const showImageForm = ref(false)
const imageUrlInput = ref('')
const isSavingImage = ref(false)
const isImportingSpotifyImage = ref(false)
const imageError = ref<string | null>(null)

function toggleImageForm() {
  imageUrlInput.value = project.value.avatarUrl || ''
  imageError.value = null
  showImageForm.value = !showImageForm.value
}

async function saveProjectImage() {
  if (!imageUrlInput.value.trim()) return
  isSavingImage.value = true
  imageError.value = null
  const success = await store.updateProjectImage(project.value.id, imageUrlInput.value.trim())
  isSavingImage.value = false
  if (success) {
    showImageForm.value = false
  } else {
    imageError.value = store.errorMessage || 'Erreur lors de la mise à jour de l’image.'
  }
}

async function importImageFromSpotify() {
  isImportingSpotifyImage.value = true
  imageError.value = null
  const connectorsLoaded = await store.fetchConnectors(project.value.id)
  if (!connectorsLoaded || !store.connectors.spotify.connected) {
    isImportingSpotifyImage.value = false
    imageError.value = connectorsLoaded
      ? 'Reliez d’abord le projet à un véritable artiste Spotify.'
      : store.errorMessage || 'Impossible de vérifier la liaison Spotify.'
    return
  }
  const success = await store.importSpotifyImage(project.value.id)
  isImportingSpotifyImage.value = false
  if (success) {
    showImageForm.value = false
  } else {
    imageError.value = store.errorMessage || 'Erreur lors de l’import de l’image Spotify.'
  }
}

// Import Spotify : connexion à l'artiste, chargement du catalogue (albums + tracklist) puis sélection avant enregistrement en base
const showSpotifyConnectForm = ref(false)
const spotifyArtistIdInput = ref('')
const isConnectingSpotify = ref(false)
const spotifyConnectError = ref<string | null>(null)

function openSpotifyConnectionFromImage() {
  showSpotifyConnectForm.value = true
  spotifyConnectError.value = null
  imageError.value = 'Renseignez l’ID ou l’URL du profil Spotify, puis connectez le projet.'
}

async function connectSpotifyAccount() {
  if (!spotifyArtistIdInput.value.trim()) return
  isConnectingSpotify.value = true
  spotifyConnectError.value = null
  const success = await store.connectSpotify(project.value.id, spotifyArtistIdInput.value.trim())
  isConnectingSpotify.value = false
  if (success) {
    showSpotifyConnectForm.value = false
    spotifyArtistIdInput.value = ''
  } else {
    spotifyConnectError.value = store.errorMessage || 'Erreur lors de la connexion Spotify.'
  }
}

const spotifyCatalog = ref<SpotifyCatalog | null>(null)
const isLoadingSpotifyCatalog = ref(false)
const spotifyCatalogError = ref<string | null>(null)
const selectedAlbumIds = ref<Set<string>>(new Set())
const selectedTrackIds = ref<Set<string>>(new Set())
const isImportingSpotify = ref(false)
const hasSpotifySelection = computed(() =>
  selectedAlbumIds.value.size > 0 || selectedTrackIds.value.size > 0
)

async function loadSpotifyCatalog() {
  isLoadingSpotifyCatalog.value = true
  spotifyCatalogError.value = null
  spotifyCatalog.value = await store.fetchSpotifyCatalog(project.value.id)
  isLoadingSpotifyCatalog.value = false
  if (!spotifyCatalog.value) {
    spotifyCatalogError.value = store.errorMessage || 'Impossible de charger le catalogue Spotify.'
  }
}

function toggleAlbumSelection(albumId: string) {
  const album = spotifyCatalog.value?.albums.find(a => a.id === albumId)
  if (!album) return
  const nextAlbumIds = new Set(selectedAlbumIds.value)
  const nextTrackIds = new Set(selectedTrackIds.value)
  if (nextAlbumIds.has(albumId)) {
    nextAlbumIds.delete(albumId)
    album.tracks.forEach(t => nextTrackIds.delete(t.id))
  } else {
    nextAlbumIds.add(albumId)
    album.tracks.forEach(t => nextTrackIds.add(t.id))
  }
  selectedAlbumIds.value = nextAlbumIds
  selectedTrackIds.value = nextTrackIds
}

function toggleTrackSelection(trackId: string) {
  const nextTrackIds = new Set(selectedTrackIds.value)
  if (nextTrackIds.has(trackId)) {
    nextTrackIds.delete(trackId)
  } else {
    nextTrackIds.add(trackId)
  }
  selectedTrackIds.value = nextTrackIds
}

async function importSpotifySelection() {
  if (!spotifyCatalog.value || !hasSpotifySelection.value || isImportingSpotify.value) return
  isImportingSpotify.value = true
  try {
    const albums = spotifyCatalog.value.albums
      .filter(a => selectedAlbumIds.value.has(a.id))
      .map(a => ({ spotifyId: a.id, titre: a.name, releaseDate: a.release_date }))
    const tracks = spotifyCatalog.value.albums
      .flatMap(a => a.tracks)
      .filter(t => selectedTrackIds.value.has(t.id))
      .map(t => ({
        spotifyId: t.id,
        titre: t.name,
        durationMs: t.duration_ms,
        releaseDate: t.release_date
      }))

    const success = await store.importSpotifySelection(project.value.id, tracks, albums)
    saveFeedback.value = success
      ? { type: 'success', message: 'Sélection Spotify importée avec succès.' }
      : { type: 'error', message: store.errorMessage || 'Erreur lors de l’import Spotify.' }
    if (success) {
      selectedAlbumIds.value = new Set()
      selectedTrackIds.value = new Set()
      spotifyCatalog.value = null
    }
  } catch {
    saveFeedback.value = { type: 'error', message: 'Erreur inattendue lors de l’import Spotify.' }
  } finally {
    isImportingSpotify.value = false
    setTimeout(() => { saveFeedback.value = null }, 4000)
  }
}

// MX3 / SRG SSR : recherche et liaison d'un groupe, puis consultation des concerts distants à la demande
const showMx3ConnectForm = ref(false)
const mx3Query = ref('')
const mx3Bands = ref<Mx3Band[]>([])
const selectedMx3BandId = ref<number | null>(null)
const isSearchingMx3 = ref(false)
const isConnectingMx3 = ref(false)
const mx3ConnectError = ref<string | null>(null)
const mx3Gigs = ref<Mx3Gig[] | null>(null)
const isLoadingMx3Gigs = ref(false)
const mx3GigsError = ref<string | null>(null)
const isSyncingMx3Metrics = ref(false)
const mx3MetricsFeedback = ref<{ type: 'success' | 'error'; message: string } | null>(null)

const mx3MetricLabels: Record<string, string> = {
  Ecoutes_Cumulees: 'Écoutes cumulées',
  Vues_Profil: 'Vues du profil',
  Playlists: 'Playlists',
  Singles_Publies: 'Singles publiés'
}

function toggleMx3ConnectForm() {
  showMx3ConnectForm.value = !showMx3ConnectForm.value
  mx3ConnectError.value = null
  if (showMx3ConnectForm.value && !mx3Query.value) {
    mx3Query.value = project.value.nom
  }
}

async function searchMx3Bands() {
  if (mx3Query.value.trim().length < 2 || isSearchingMx3.value) return
  isSearchingMx3.value = true
  mx3ConnectError.value = null
  selectedMx3BandId.value = null
  const bands = await store.searchMx3Bands(mx3Query.value.trim())
  isSearchingMx3.value = false
  if (bands) {
    mx3Bands.value = bands
  } else {
    mx3Bands.value = []
    mx3ConnectError.value = store.errorMessage || 'Erreur lors de la recherche MX3.'
  }
}

async function connectMx3Band() {
  if (selectedMx3BandId.value === null || isConnectingMx3.value) return
  isConnectingMx3.value = true
  mx3ConnectError.value = null
  const success = await store.connectMx3(project.value.id, selectedMx3BandId.value)
  isConnectingMx3.value = false
  if (success) {
    showMx3ConnectForm.value = false
    mx3Bands.value = []
    selectedMx3BandId.value = null
    mx3Gigs.value = null
  } else {
    mx3ConnectError.value = store.errorMessage || 'Erreur lors de la connexion à MX3.'
  }
}

async function loadMx3Gigs() {
  if (isLoadingMx3Gigs.value) return
  isLoadingMx3Gigs.value = true
  mx3GigsError.value = null
  const gigs = await store.fetchMx3Gigs(project.value.id)
  isLoadingMx3Gigs.value = false
  if (gigs) {
    mx3Gigs.value = gigs
  } else {
    mx3Gigs.value = null
    mx3GigsError.value = store.errorMessage || 'Erreur lors du chargement des concerts MX3.'
  }
}

async function syncMx3Metrics() {
  if (isSyncingMx3Metrics.value) return
  isSyncingMx3Metrics.value = true
  mx3MetricsFeedback.value = null
  const success = await store.triggerEtlSync('mx3')
  isSyncingMx3Metrics.value = false
  mx3MetricsFeedback.value = success
    ? { type: 'success', message: 'Métriques MX3 actualisées.' }
    : { type: 'error', message: store.errorMessage || 'Erreur lors de la synchronisation MX3.' }
}

function formatMx3Date(value: string): string {
  const compactDate = value.match(/^(\d{4})(\d{2})(\d{2})/)
  if (compactDate) return `${compactDate[3]}.${compactDate[2]}.${compactDate[1]}`
  const parsedDate = new Date(value)
  return Number.isNaN(parsedDate.getTime()) ? value || 'Date non renseignée' : parsedDate.toLocaleDateString('fr-CH')
}

// Ajout de concert
const showAddConcertForm = ref(false)
const projectForNewConcert = ref<MusicalProject | null>(null)
const isAddingConcert = ref(false)
const addConcertError = ref<string | null>(null)
const newVenueValue = '__new__'
const newConcertForm = reactive({
  date: '',
  venueSelection: '',
  type: 'Local (NE)' as 'Local (NE)' | 'Hors-Canton' | 'Export',
  typeEvenement: 'Concert' as 'Concert' | 'Résidence' | 'Showcase',
  cachetBrut: '' as number | ''
})
const newVenueForm = reactive({
  nom: '',
  adresse: '',
  ville: '',
  npa: '',
  pays: 'Suisse',
  jauge: 0,
  estFestival: false
})

const isCreatingVenue = computed(() => newConcertForm.venueSelection === newVenueValue)
const isConcertFormValid = computed(() => {
  if (!newConcertForm.date || !newConcertForm.venueSelection) return false
  if (!isCreatingVenue.value) return true
  return Boolean(
    newVenueForm.nom.trim()
    && newVenueForm.ville.trim()
    && newVenueForm.pays.trim()
    && newVenueForm.jauge >= 0
  )
})

function openAddConcertForm(project: MusicalProject) {
  projectForNewConcert.value = project
  newConcertForm.date = ''
  newConcertForm.venueSelection = ''
  newConcertForm.type = 'Local (NE)'
  newConcertForm.typeEvenement = 'Concert'
  newConcertForm.cachetBrut = ''
  newVenueForm.nom = ''
  newVenueForm.adresse = ''
  newVenueForm.ville = ''
  newVenueForm.npa = ''
  newVenueForm.pays = 'Suisse'
  newVenueForm.jauge = 0
  newVenueForm.estFestival = false
  addConcertError.value = null
  showAddConcertForm.value = true
}

function closeAddConcertForm() {
  showAddConcertForm.value = false
  projectForNewConcert.value = null
  addConcertError.value = null
}

async function submitConcert() {
  if (!projectForNewConcert.value || !isConcertFormValid.value || isAddingConcert.value) return
  isAddingConcert.value = true
  addConcertError.value = null

  const parts = newConcertForm.date.split('-') // YYYY-MM-DD
  const formattedDate = parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : newConcertForm.date

  const success = await store.addConcert(projectForNewConcert.value.id, {
    date: formattedDate,
    type: newConcertForm.type,
    typeEvenement: newConcertForm.typeEvenement,
    cachetBrut: newConcertForm.cachetBrut === '' ? undefined : Number(newConcertForm.cachetBrut),
    ...(isCreatingVenue.value
      ? {
          newVenue: {
            nom: newVenueForm.nom.trim(),
            adresse: newVenueForm.adresse.trim() || undefined,
            ville: newVenueForm.ville.trim(),
            npa: newVenueForm.npa.trim() || undefined,
            pays: newVenueForm.pays.trim(),
            jauge: Number(newVenueForm.jauge),
            estFestival: newVenueForm.estFestival
          }
        }
      : { venueId: Number(newConcertForm.venueSelection) })
  })

  isAddingConcert.value = false
  if (success !== false) {
    closeAddConcertForm()
  } else {
    addConcertError.value = store.errorMessage || "Erreur lors de l'ajout du concert."
  }
}


// Enregistrement des modifications du projet, avec popup de confirmation
const isSavingProject = ref(false)
const saveFeedback = ref<{ type: 'success' | 'error'; message: string } | null>(null)
// Evite d'afficher brièvement le projet mock par défaut du store le temps du chargement réel
const hasLoadedProject = ref(false)

async function saveProjectChanges() {
  isSavingProject.value = true
  const success = await store.updateProject(project.value.id, {
    nom: project.value.nom,
    dateCreation: project.value.dateCreation,
    statutJuridiqueId: project.value.statutJuridiqueId,
    statutJuridique: project.value.statutJuridique,
    suisaInscrit: project.value.suisaInscrit,
    hasLocal: project.value.hasLocal,
    hasFicheTechnique: project.value.hasFicheTechnique,
    hasMerch: project.value.hasMerch,
    personalPageUrl: project.value.personalPageUrl?.trim() || null,
    personalPageSiteName: project.value.personalPageSiteName?.trim() || null,
    objectifsCourtTerme: project.value.objectifsCourtTerme?.trim() || null,
    objectifsMoyenTerme: project.value.objectifsMoyenTerme?.trim() || null
  })
  let stylesSuccess = true
  if (project.value.styles.length > 0) {
    stylesSuccess = await store.updateProjectStyles(
      project.value.id,
      project.value.styles.map(s => ({ styleId: s.id, principal: s.principal }))
    )
  }
  isSavingProject.value = false
  saveFeedback.value = success && stylesSuccess
    ? { type: 'success', message: 'Modifications enregistrées avec succès.' }
    : { type: 'error', message: store.errorMessage || 'Erreur lors de l’enregistrement des modifications.' }
  setTimeout(() => { saveFeedback.value = null }, 4000)
}

onMounted(async () => {
  store.setSelectedProject(requestedProjectId.value)
  await store.fetchProjects()
  store.setSelectedProject(requestedProjectId.value)
  if (store.projects.some(item => item.id === requestedProjectId.value)) {
    await store.fetchConnectors(requestedProjectId.value)
  }
  store.fetchStyleTaxonomy()
  store.fetchLegalStatuses()
  await store.fetchAccompanimentReferences()
  store.fetchVenues()
  store.fetchAssetTypes()
  if (store.currentProject) resetAccompanimentDrafts()
  hasLoadedProject.value = true
})

// Actions
const deleteTrack = async (id: number) => {
  const success = await store.removeTrack(project.value.id, id)
  saveFeedback.value = success
    ? { type: 'success', message: 'Morceau supprimé définitivement.' }
    : { type: 'error', message: store.errorMessage || 'Erreur lors de la suppression du morceau.' }
  setTimeout(() => { saveFeedback.value = null }, 4000)
}
const setTrackOriginality = async (trackId: number, estOriginal: boolean) => {
  originalityUpdateTrackId.value = trackId
  originalityUpdateError.value = null
  const success = await store.updateTrackOriginality(project.value.id, trackId, estOriginal)
  if (!success) originalityUpdateError.value = store.errorMessage
  originalityUpdateTrackId.value = null
}
const deleteConcert = (id: number) => {
  store.removeConcert(project.value.id, id)
}
const exportRoster = () => {
  router.push(`/artist/project/${project.value.id}/export`)
}
</script>

<template>
  <div class="w-full px-4 sm:px-6 lg:px-10 py-6 sm:py-8 space-y-8 bg-[#0e0f12] text-gray-100">

    <div v-if="!hasLoadedProject" class="text-sm text-gray-400">
      Chargement du projet...
    </div>

    <div v-else-if="projectAccessDenied" class="text-sm text-gray-300 space-y-3">
      <p>Ce projet est introuvable ou vous n'y avez pas accès.</p>
      <RouterLink to="/artist/dashboard" class="inline-block text-xs font-bold text-[#7c3aed] hover:underline">
        ← Retour au Dashboard
      </RouterLink>
    </div>

    <template v-else>
    <!-- Popup de confirmation d'enregistrement -->
    <div
      v-if="saveFeedback"
      class="fixed top-4 right-4 z-50 px-4 py-3 rounded-lg border text-sm font-semibold shadow-xl"
      :class="saveFeedback.type === 'success'
        ? 'bg-[#0f1c16] border-[#00ff88]/40 text-[#00ff88]'
        : 'bg-[#1c1315] border-rose-500/40 text-rose-400'"
    >
      {{ saveFeedback.message }}
    </div>

    <!-- En-tête de navigation rapide -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#282c37] pb-4">
      <div class="flex items-center gap-3">
        <RouterLink to="/artist/dashboard" class="text-xs font-bold text-gray-400 hover:text-white px-2.5 py-1.5 rounded bg-[#181a20] border border-[#282c37]">
          ← Retour au Dashboard
        </RouterLink>
        <span class="text-xs text-[#00ff88] font-mono bg-[#00ff88]/10 px-2 py-0.5 rounded border border-[#00ff88]/20">
          Projet actif : #00{{ project.id }}
        </span>
      </div>

      <div class="flex items-center gap-3">
        <button @click="exportRoster" class="px-4 py-2 bg-transparent hover:bg-white/5 border border-[#7c3aed] text-[#7c3aed] hover:text-white text-xs font-bold rounded-lg transition-colors cursor-pointer">
          Exporter Fiche Vitrine (Roster) ↗
        </button>
        <button
          @click="saveProjectChanges"
          :disabled="isSavingProject"
          class="px-4 py-2 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-xs font-bold rounded-lg transition-colors cursor-pointer shadow-lg shadow-[#7c3aed]/20 disabled:opacity-50"
        >
          {{ isSavingProject ? 'Enregistrement...' : 'Enregistrer les modifications' }}
        </button>
      </div>
    </div>

    <!-- 1. En-tête & Métadonnées du Projet (Top Card) -->
    <section class="w-full bg-[#181a20] border border-[#282c37] rounded-2xl p-5 sm:p-7 shadow-xl">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        <!-- Bloc Photo / Pochette du Projet -->
        <div class="lg:col-span-3 flex flex-col items-center gap-3">
          <div
            class="w-full aspect-square max-w-55 rounded-xl border-2 border-dashed border-[#282c37] hover:border-[#7c3aed] bg-[#121418] bg-cover bg-center flex flex-col items-center justify-center text-center p-4 transition-colors group cursor-pointer"
            :style="project.avatarUrl ? { backgroundImage: `url(${project.avatarUrl})`, borderStyle: 'solid' } : {}"
            @click="toggleImageForm"
          >
            <template v-if="!project.avatarUrl">
              <span class="text-3xl text-gray-500 group-hover:scale-110 transition-transform">📸</span>
              <span class="text-xs font-semibold text-gray-400 mt-2">Visuel officiel du projet</span>
              <span class="text-[10px] text-gray-600">JPG, PNG max 5Mo</span>
            </template>
          </div>
          <button
            @click="toggleImageForm"
            class="text-xs text-gray-400 hover:text-white px-3 py-1 bg-[#22252e] rounded border border-[#282c37] cursor-pointer"
          >
            Remplacer l'image
          </button>

          <div v-if="showImageForm" class="w-full space-y-2">
            <input
              v-model="imageUrlInput"
              placeholder="URL de l'image"
              class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]"
            />
            <button
              @click="saveProjectImage"
              :disabled="isSavingImage || !imageUrlInput.trim()"
              class="w-full text-[10px] font-bold uppercase px-2 py-1.5 rounded bg-[#7c3aed] hover:bg-[#6d28d9] text-white transition-colors disabled:opacity-40 cursor-pointer"
            >
              {{ isSavingImage ? 'Enregistrement...' : 'Enregistrer' }}
            </button>
            <button
              v-if="store.connectors.spotify.connected"
              @click="importImageFromSpotify"
              :disabled="isImportingSpotifyImage"
              class="w-full text-[10px] font-bold uppercase px-2 py-1.5 rounded bg-[#00ff88] hover:bg-[#00e57a] text-black transition-colors disabled:opacity-40 cursor-pointer"
            >
              {{ isImportingSpotifyImage ? 'Import...' : 'Importer depuis Spotify' }}
            </button>
            <button
              v-else
              type="button"
              @click="openSpotifyConnectionFromImage"
              class="w-full text-[10px] font-bold uppercase px-2 py-1.5 rounded border border-[#00ff88]/40 text-[#00ff88] hover:bg-[#00ff88]/10 transition-colors cursor-pointer"
            >
              Lier un artiste Spotify
            </button>
            <div v-if="imageError" class="text-[10px] text-red-400">{{ imageError }}</div>
          </div>
        </div>

        <!-- Formulaire Métadonnées Projet -->
        <div class="lg:col-span-9 space-y-4">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1" for="nomProjet">Nom du projet musical</label>
            <input
              id="nomProjet"
              type="text"
              v-model="project.nom"
              class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-4 py-2.5 text-base font-extrabold text-white focus:outline-none focus:border-[#7c3aed]"
            />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-gray-400 mb-1" for="dateCrea">Date de création</label>
              <input
                id="dateCrea"
                type="date"
                v-model="project.dateCreation"
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]"
              />
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-400 mb-1" for="statut">Statut juridique</label>
              <select
                id="statut"
                v-model="project.statutJuridiqueId"
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]"
              >
                <option v-if="!store.legalStatuses.some(status => status.id === project.statutJuridiqueId)" :value="project.statutJuridiqueId">
                  {{ project.statutJuridique }} (inactif)
                </option>
                <option v-for="status in store.legalStatuses" :key="status.id" :value="status.id">{{ status.libelle }}</option>
              </select>
            </div>
          </div>

          <!-- Styles musicaux : affichage par étiquettes, ajout via sélection en cascade sur 3 niveaux -->
          <div>
            <label class="block text-xs font-semibold text-gray-400 mb-2">Styles musicaux</label>
            <div class="flex flex-wrap gap-2 mb-3">
              <span
                v-for="s in project.styles"
                :key="s.id"
                class="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border cursor-pointer"
                :class="s.principal
                  ? 'bg-[#00ff88]/10 text-[#00ff88] border-[#00ff88]/30'
                  : 'bg-[#22252e] text-gray-300 border-[#282c37]'"
                @click="setPrincipalStyle(s.id)"
                :title="s.principal ? 'Style principal' : 'Cliquer pour définir comme principal'"
              >
                {{ s.nom }}
                <button type="button" @click.stop="removeStyle(s.id)" class="hover:text-rose-400">✕</button>
              </span>
              <span v-if="project.styles.length === 0" class="text-xs text-gray-500">Aucun style sélectionné</span>
            </div>
            <div class="flex flex-col sm:flex-row gap-2">
              <select
                v-model="selectedRootId"
                @change="onRootChange"
                class="flex-1 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]"
              >
                <option :value="null">Niveau 1 : racine</option>
                <option v-for="r in rootStyles" :key="r.id" :value="r.id">{{ r.nom }}</option>
              </select>
              <select
                v-model="selectedBranchId"
                @change="onBranchChange"
                :disabled="!selectedRootId"
                class="flex-1 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed] disabled:opacity-40"
              >
                <option :value="null">Niveau 2 : macro-genre</option>
                <option v-for="b in branchStyles" :key="b.id" :value="b.id">{{ b.nom }}</option>
              </select>
              <select
                v-model="selectedLeafId"
                :disabled="!selectedBranchId"
                class="flex-1 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed] disabled:opacity-40"
              >
                <option :value="null">Niveau 3 : sous-genre</option>
                <option v-for="l in leafStyles" :key="l.id" :value="l.id">{{ l.nom }}</option>
              </select>
              <button
                type="button"
                @click="addSelectedStyle"
                :disabled="!selectedLeafId"
                class="px-3 py-2 text-xs font-bold rounded-lg bg-[#7c3aed] hover:bg-[#6d28d9] text-white transition-colors disabled:opacity-40 cursor-pointer"
              >
                + Ajouter
              </button>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-[#282c37]/80">
            <div>
              <label class="block text-xs font-semibold text-gray-400 mb-1" for="personalPageSite">
                Réseau social ou page personnelle
              </label>
              <select
                id="personalPageSite"
                v-model="personalPageSiteChoice"
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]"
              >
                <option value="">Aucune page</option>
                <option v-for="site in personalPageSites" :key="site" :value="site">{{ site }}</option>
                <option :value="customPersonalPageSite">Autre</option>
              </select>
              <input
                v-if="personalPageSiteChoice === customPersonalPageSite"
                v-model="project.personalPageSiteName"
                type="text"
                maxlength="100"
                placeholder="Nom du site"
                class="w-full mt-2 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-400 mb-1" for="personalPageUrl">Lien vers la page</label>
              <input
                id="personalPageUrl"
                v-model="project.personalPageUrl"
                type="url"
                maxlength="2048"
                placeholder="https://..."
                :disabled="!personalPageSiteChoice"
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed] disabled:opacity-40"
              />
            </div>
          </div>
          <!-- Diagnostic de structuration & Autonomie -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <label class="flex items-center gap-2 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-300 cursor-pointer">
              <input type="checkbox" v-model="project.suisaInscrit" class="accent-[#00ff88]" />
              Inscrit SUISA
            </label>
            <label class="flex items-center gap-2 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-300 cursor-pointer">
              <input type="checkbox" v-model="project.hasLocal" class="accent-[#00ff88]" />
              Local de répétition
            </label>
            <label class="flex items-center gap-2 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-300 cursor-pointer">
              <input type="checkbox" v-model="project.hasFicheTechnique" class="accent-[#00ff88]" />
              Fiche technique
            </label>
            <label class="flex items-center gap-2 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-300 cursor-pointer">
              <input type="checkbox" v-model="project.hasMerch" class="accent-[#00ff88]" />
              Merch
            </label>
          </div>
          <!-- Section Tableau des Membres -->
          <div class="pt-4 border-t border-[#282c37]/80 space-y-3">
            <div class="flex justify-between items-center">
              <div class="flex items-center gap-2">
                <h3 class="text-sm font-extrabold uppercase tracking-wider text-white">Membres du projet</h3>
                <span class="text-xs text-gray-400">({{ members.length }} déclarés)</span>
              </div>
              <div class="flex items-center gap-2">
                <button class="px-2.5 py-1 text-xs bg-[#22252e] hover:bg-[#282c37] border border-[#282c37] rounded text-gray-300 cursor-pointer">
                  Voir tout
                </button>
                <button
                  @click="toggleAddMemberForm"
                  class="px-2.5 py-1 text-xs bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-bold rounded cursor-pointer"
                >
                  + Ajouter un membre
                </button>
              </div>
            </div>

            <!-- Formulaire d'ajout de membre -->
            <form
              v-if="showAddMemberForm"
              @submit.prevent="addMember"
              class="bg-[#121418] border border-[#282c37] rounded-lg p-3 space-y-2"
            >
              <div v-if="addMemberError" class="text-xs text-red-400">{{ addMemberError }}</div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <input v-model="newMemberForm.nom" placeholder="Nom" required class="bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
                <input v-model="newMemberForm.prenom" placeholder="Prénom" required class="bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
                <input v-model="newMemberForm.dateNaissance" type="date" required class="bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
                <select v-model="newMemberForm.genre" class="bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]">
                  <option value="Homme">Homme</option>
                  <option value="Femme">Femme</option>
                  <option value="Autre">Autre</option>
                </select>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <input v-model="newMemberForm.npa" placeholder="NPA" required class="bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
                <input v-model="newMemberForm.ville" placeholder="Ville" required class="bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
                <input v-model="newMemberForm.email" type="email" placeholder="Email" required class="bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
                <input v-model="newMemberForm.telephone" placeholder="Téléphone" class="bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
              </div>
              <input v-model="newMemberForm.role" placeholder="Rôle / Instrument" required class="w-full bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
              <div class="flex items-center justify-end gap-2">
                <button type="button" @click="showAddMemberForm = false" class="px-3 py-1.5 text-xs font-bold rounded-lg border border-[#282c37] text-gray-300 hover:bg-white/5 transition-colors">
                  Annuler
                </button>
                <button type="submit" :disabled="isAddingMember" class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#7c3aed] hover:bg-[#6d28d9] text-white transition-colors disabled:opacity-50">
                  {{ isAddingMember ? 'Ajout...' : 'Ajouter' }}
                </button>
              </div>
            </form>

            <div v-if="invitationUrl" class="bg-[#0f1c16] border border-[#00ff88]/40 rounded-lg p-3 text-xs text-[#00ff88] break-all">
              Lien d'invitation généré : {{ invitationUrl }}
            </div>
            <div v-if="inviteError" class="text-xs text-red-400">{{ inviteError }}</div>

            <!-- Table Responsive des Membres -->
            <div class="overflow-x-auto border border-[#282c37] rounded-lg">
              <table class="w-full text-left text-xs text-gray-300">
                <thead class="bg-[#121418] text-gray-400 uppercase font-semibold border-b border-[#282c37]">
                  <tr>
                    <th class="py-2.5 px-3">Nom</th>
                    <th class="py-2.5 px-3">Prénom</th>
                    <th class="py-2.5 px-3">Genre</th>
                    <th class="py-2.5 px-3">Date naissance</th>
                    <th class="py-2.5 px-3">Rôle / Instrument</th>
                    <th class="py-2.5 px-3">Email</th>
                    <th class="py-2.5 px-3">Téléphone</th>
                    <th class="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[#282c37]/60">
                  <tr v-for="m in members" :key="m.id" class="hover:bg-[#1e222b] transition-colors">
                    <td class="py-2.5 px-3 font-bold text-white">{{ m.nom }}</td>
                    <td class="py-2.5 px-3">{{ m.prenom }}</td>
                    <td class="py-2.5 px-3">{{ m.genre }}</td>
                    <td class="py-2.5 px-3 font-mono text-gray-400">{{ m.dateNaissance }}</td>
                    <td class="py-2.5 px-3 text-[#00ff88] font-medium">{{ m.role }}</td>
                    <td class="py-2.5 px-3 text-gray-400">{{ m.email }}</td>
                    <td class="py-2.5 px-3 font-mono text-gray-400">{{ m.telephone }}</td>
                    <td class="py-2.5 px-3 text-right space-x-1">
                      <button
                        v-if="!m.hasAccount"
                        @click="inviteMember(m.id)"
                        :disabled="invitingMemberId === m.id"
                        class="p-1 text-gray-400 hover:text-[#00ff88] cursor-pointer disabled:opacity-40"
                        title="Inviter à créer un compte"
                      >
                        ✉️
                      </button>
                      <button class="p-1 text-gray-400 hover:text-[#7c3aed] cursor-pointer" title="Modifier">✏️</button>
                      <button @click="askRemoveMember(m)" class="p-1 text-gray-400 hover:text-rose-400 cursor-pointer" title="Supprimer">🗑️</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6 pt-6 border-t border-[#282c37]">
          <div>
            <label class="block text-xs font-bold uppercase text-gray-400 mb-2" for="objectifsCourtTerme">
              Objectifs à court terme (dans l’année)
            </label>
            <textarea
              id="objectifsCourtTerme"
              v-model="project.objectifsCourtTerme"
              maxlength="5000"
              rows="5"
              placeholder="Bref descriptif des objectifs du projet à court terme"
              class="w-full resize-y bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]"
            ></textarea>
          </div>
          <div>
            <label class="block text-xs font-bold uppercase text-gray-400 mb-2" for="objectifsMoyenTerme">
              Objectifs à moyen terme (dans 5 ans)
            </label>
            <textarea
              id="objectifsMoyenTerme"
              v-model="project.objectifsMoyenTerme"
              maxlength="5000"
              rows="5"
              placeholder="Bref descriptif des objectifs du projet à moyen terme"
              class="w-full resize-y bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]"
            ></textarea>
          </div>
        </div>
    </section>

    <section class="w-full bg-[#181a20] border border-[#282c37] rounded-xl p-5 sm:p-6 space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#282c37] pb-4">
        <div>
          <h2 class="text-base font-extrabold text-white uppercase">Formations et accompagnements</h2>
          <p class="mt-1 text-xs text-gray-400">Historique des formations et programmes suivis par le projet.</p>
        </div>
        <button
          type="button"
          @click="saveAccompaniment"
          :disabled="isSavingAccompaniment"
          class="px-4 py-2 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-xs font-bold rounded-lg disabled:opacity-50"
        >
          {{ isSavingAccompaniment ? 'Enregistrement...' : 'Enregistrer le parcours' }}
        </button>
      </div>

      <p
        v-if="accompanimentFeedback"
        role="status"
        :class="accompanimentFeedback.type === 'success' ? 'text-[#00ff88]' : 'text-rose-400'"
        class="text-xs"
      >
        {{ accompanimentFeedback.message }}
      </p>

      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div class="space-y-3">
          <h3 class="text-sm font-bold text-white">Formations suivies</h3>
          <form @submit.prevent="addFormationDraft" class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_10rem_auto] gap-2">
            <select v-model="newFormation.formationId" required class="bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]">
              <option value="">Choisir une formation</option>
              <option v-for="item in store.formationReferences" :key="item.id" :value="item.id">
                {{ item.nom }}{{ item.organisme ? ` · ${item.organisme}` : '' }}
              </option>
            </select>
            <input v-model="newFormation.dateSuivi" type="date" required class="bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
            <button type="submit" class="px-3 py-2 bg-[#22252e] hover:bg-[#282c37] border border-[#3a3f4d] rounded-lg text-xs font-bold text-white">Ajouter</button>
          </form>
          <div v-if="formationDrafts.length" class="divide-y divide-[#282c37] border-y border-[#282c37]">
            <div v-for="(item, index) in formationDrafts" :key="`${item.formationId}-${item.dateSuivi}`" class="flex items-center justify-between gap-3 py-3 text-xs">
              <div class="min-w-0">
                <strong class="block truncate text-gray-200">{{ formationLabel(item.formationId) }}</strong>
                <span class="text-gray-500">Suivie le {{ formatAccompanimentDate(item.dateSuivi) }}</span>
              </div>
              <button type="button" @click="formationDrafts.splice(index, 1)" aria-label="Retirer la formation" title="Retirer" class="shrink-0 text-rose-400 hover:text-rose-300 text-lg">×</button>
            </div>
          </div>
          <p v-else class="text-xs text-gray-500">Aucune formation renseignée.</p>
        </div>

        <div class="space-y-3">
          <h3 class="text-sm font-bold text-white">Programmes d’accompagnement</h3>
          <form @submit.prevent="addProgramDraft" class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_7rem_auto] gap-2">
            <select v-model="newProgram.programmeId" required class="bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]">
              <option value="">Choisir un programme</option>
              <option v-for="item in store.programReferences" :key="item.id" :value="item.id">
                {{ item.nom }}{{ item.organisme ? ` · ${item.organisme}` : '' }}
              </option>
            </select>
            <input v-model.number="newProgram.anneeParticipation" type="number" min="1900" max="2100" required class="bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
            <button type="submit" class="px-3 py-2 bg-[#22252e] hover:bg-[#282c37] border border-[#3a3f4d] rounded-lg text-xs font-bold text-white">Ajouter</button>
          </form>
          <label class="inline-flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
            <input v-model="newProgram.estLaureat" type="checkbox" class="accent-[#00ff88]" />
            Projet lauréat de ce programme
          </label>
          <div v-if="programDrafts.length" class="divide-y divide-[#282c37] border-y border-[#282c37]">
            <div v-for="(item, index) in programDrafts" :key="`${item.programmeId}-${item.anneeParticipation}`" class="flex items-center justify-between gap-3 py-3 text-xs">
              <div class="min-w-0">
                <strong class="block truncate text-gray-200">{{ programLabel(item.programmeId) }}</strong>
                <span class="text-gray-500">{{ item.anneeParticipation }} · {{ item.estLaureat ? 'Lauréat' : 'Participant' }}</span>
              </div>
              <button type="button" @click="programDrafts.splice(index, 1)" aria-label="Retirer le programme" title="Retirer" class="shrink-0 text-rose-400 hover:text-rose-300 text-lg">×</button>
            </div>
          </div>
          <p v-else class="text-xs text-gray-500">Aucun programme renseigné.</p>
        </div>
      </div>
    </section>

    <!-- Popup de confirmation de retrait d'un membre -->
    <div
      v-if="memberPendingRemoval"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
    >
      <div class="w-full max-w-sm bg-[#181a20] border border-[#282c37] rounded-xl p-5 space-y-4">
        <h3 class="text-base font-bold text-white">Retirer ce membre ?</h3>
        <p class="text-sm text-gray-400">
          « {{ memberPendingRemoval.prenom }} {{ memberPendingRemoval.nom }} » sera retiré du projet (son historique est conservé).
        </p>
        <div v-if="removeMemberError" class="text-xs text-red-400">{{ removeMemberError }}</div>
        <div class="flex items-center justify-end gap-2">
          <button
            @click="cancelRemoveMember"
            class="px-3 py-1.5 text-xs font-bold rounded-lg border border-[#282c37] text-gray-300 hover:bg-white/5 transition-colors cursor-pointer"
          >
            Annuler
          </button>
          <button
            @click="confirmRemoveMember"
            :disabled="isRemovingMember"
            class="px-3 py-1.5 text-xs font-bold rounded-lg bg-rose-600 hover:bg-rose-700 text-white transition-colors disabled:opacity-50 cursor-pointer"
          >
            {{ isRemovingMember ? 'Retrait...' : 'Retirer' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Import Spotify : connexion à l'artiste, chargement du catalogue puis sélection des morceaux/albums à ajouter en base -->
    <section class="w-full bg-[#181a20] border border-[#282c37] rounded-2xl p-5 sm:p-7 space-y-4 shadow-xl">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 class="text-base sm:text-lg font-extrabold text-white">🎧 Import Spotify</h3>
          <p class="text-xs text-gray-400">Charge le catalogue de l'artiste lié et choisis ce qu'il faut ajouter comme morceaux/assets.</p>
        </div>
        <button
          @click="showSpotifyConnectForm = !showSpotifyConnectForm"
          class="text-[10px] uppercase font-bold text-[#7c3aed] underline shrink-0"
        >
          {{ store.connectors.spotify.connected ? 'Modifier la liaison Spotify' : 'Lier un artiste Spotify' }}
        </button>
      </div>

      <div v-if="!store.connectors.spotify.connected" class="text-[11px] text-gray-500">Non lié</div>
      <div v-else class="flex flex-wrap items-center gap-3 text-[11px] text-gray-400">
        <a
          v-if="store.connectors.spotify.profileUrl"
          :href="store.connectors.spotify.profileUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-[#00ff88] hover:underline"
        >
          Ouvrir le profil Spotify
        </a>
        <span v-if="store.connectors.spotify.metricValue !== null && store.connectors.spotify.metricValue !== undefined">
          {{ store.connectors.spotify.metricValue.toLocaleString() }} {{ store.connectors.spotify.metricType || 'followers' }}
        </span>
        <span v-if="store.connectors.spotify.lastSync">Dernière relève : {{ store.connectors.spotify.lastSync }}</span>
      </div>

      <form v-if="showSpotifyConnectForm" @submit.prevent="connectSpotifyAccount" class="flex flex-col sm:flex-row gap-2 max-w-md">
        <input
          v-model="spotifyArtistIdInput"
          placeholder="ID artiste Spotify"
          class="flex-1 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]"
        />
        <button
          type="submit"
          :disabled="isConnectingSpotify || !spotifyArtistIdInput.trim()"
          class="px-3 py-2 text-xs font-bold rounded-lg bg-[#00ff88] hover:bg-[#00e57a] text-black transition-colors disabled:opacity-40 cursor-pointer"
        >
          {{ isConnectingSpotify ? 'Connexion...' : 'Connecter' }}
        </button>
      </form>
      <div v-if="spotifyConnectError" class="text-xs text-red-400">{{ spotifyConnectError }}</div>

      <button
        @click="loadSpotifyCatalog"
        :disabled="isLoadingSpotifyCatalog"
        class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#00ff88] hover:bg-[#00e57a] text-black transition-colors disabled:opacity-50 cursor-pointer"
      >
        {{ isLoadingSpotifyCatalog ? 'Chargement...' : 'Charger le catalogue Spotify' }}
      </button>

      <div v-if="spotifyCatalogError" class="text-xs text-red-400">{{ spotifyCatalogError }}</div>

      <div v-if="spotifyCatalog" class="space-y-4">
        <p class="text-xs text-gray-400">
          Artiste : <span class="text-gray-200 font-semibold">{{ spotifyCatalog.artist_name }}</span>
          · {{ spotifyCatalog.followers.toLocaleString() }} followers
        </p>

        <div v-for="album in spotifyCatalog.albums" :key="album.id" class="border border-[#282c37] rounded-lg p-3 space-y-2">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              :checked="selectedAlbumIds.has(album.id)"
              @change="toggleAlbumSelection(album.id)"
              class="accent-[#00ff88]"
            />
            <span class="text-sm font-bold text-white">{{ album.name }}</span>
            <span class="text-[10px] text-gray-500">({{ album.release_date }} · {{ album.album_type }})</span>
          </label>
          <div class="pl-6 space-y-1">
            <label v-for="track in album.tracks" :key="track.id" class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                :checked="selectedTrackIds.has(track.id)"
                @change="toggleTrackSelection(track.id)"
                class="accent-[#00ff88]"
              />
              {{ track.track_number }}. {{ track.name }}
            </label>
          </div>
        </div>

        <button
          type="button"
          @click="importSpotifySelection"
          :disabled="isImportingSpotify || !hasSpotifySelection"
          class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#7c3aed] hover:bg-[#6d28d9] text-white transition-colors disabled:opacity-40 cursor-pointer"
        >
          {{ isImportingSpotify ? 'Import...' : 'Importer la sélection' }}
        </button>
      </div>
    </section>

    <!-- MX3 : liaison du groupe et récupération à la demande des concerts SRG SSR -->
    <section class="w-full bg-[#181a20] border border-[#282c37] rounded-2xl p-5 sm:p-7 space-y-4 shadow-xl">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 class="text-base sm:text-lg font-extrabold text-white">Concerts MX3</h3>
          <p class="text-xs text-gray-400">Lie le groupe MX3 du projet et consulte les prochaines dates publiées sur la plateforme.</p>
        </div>
        <button
          type="button"
          @click="toggleMx3ConnectForm"
          class="text-[10px] uppercase font-bold text-sky-400 underline shrink-0"
        >
          {{ store.connectors.mx3.connected ? 'Modifier la liaison MX3' : 'Lier un groupe MX3' }}
        </button>
      </div>

      <div v-if="!store.connectors.mx3.connected" class="text-[11px] text-gray-500">Non lié</div>
      <div v-else class="flex flex-wrap items-center gap-3 text-[11px] text-gray-400">
        <a
          v-if="store.connectors.mx3.profileUrl"
          :href="store.connectors.mx3.profileUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-sky-400 hover:underline"
        >
          Ouvrir le profil MX3
        </a>
        <span v-if="store.connectors.mx3.externalId">ID MX3 : {{ store.connectors.mx3.externalId }}</span>
        <span v-if="store.connectors.mx3.lastSync">Dernière relève : {{ store.connectors.mx3.lastSync }}</span>
      </div>

      <dl v-if="store.connectors.mx3.metrics.length" class="grid grid-cols-2 lg:grid-cols-4 gap-x-5 gap-y-3 border-y border-[#282c37] py-3">
        <div v-for="metric in store.connectors.mx3.metrics" :key="metric.type" class="min-w-0">
          <dt class="text-[10px] uppercase font-bold text-gray-500 truncate">
            {{ mx3MetricLabels[metric.type] || metric.type }}
          </dt>
          <dd class="text-lg font-mono font-bold text-white">{{ metric.value.toLocaleString('fr-CH') }}</dd>
        </div>
      </dl>

      <div v-if="showMx3ConnectForm" class="space-y-3">
        <form @submit.prevent="searchMx3Bands" class="flex flex-col sm:flex-row gap-2 max-w-xl">
          <input
            v-model="mx3Query"
            placeholder="Nom du groupe MX3"
            class="flex-1 bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-sky-400"
          />
          <button
            type="submit"
            :disabled="isSearchingMx3 || mx3Query.trim().length < 2"
            class="px-3 py-2 text-xs font-bold rounded-lg bg-sky-400 hover:bg-sky-300 text-black transition-colors disabled:opacity-40 cursor-pointer"
          >
            {{ isSearchingMx3 ? 'Recherche...' : 'Rechercher' }}
          </button>
        </form>

        <div v-if="mx3Bands.length" class="max-w-2xl border border-[#282c37] rounded-lg divide-y divide-[#282c37] overflow-hidden">
          <label
            v-for="band in mx3Bands"
            :key="band.id"
            class="flex items-center gap-3 p-3 bg-[#121418] hover:bg-[#151820] cursor-pointer"
          >
            <input v-model="selectedMx3BandId" type="radio" :value="band.id" class="accent-sky-400" />
            <img v-if="band.imageUrl" :src="band.imageUrl" :alt="band.name" class="w-10 h-10 object-cover rounded" />
            <span class="min-w-0 flex-1">
              <strong class="block text-sm text-white truncate">{{ band.name }}</strong>
              <span class="block text-[11px] text-gray-500">{{ band.city || 'Ville non renseignée' }} · ID {{ band.id }}</span>
            </span>
            <a
              v-if="band.profileUrl"
              :href="band.profileUrl"
              target="_blank"
              rel="noopener noreferrer"
              @click.stop
              class="text-[11px] text-sky-400 hover:underline"
            >Voir</a>
          </label>
        </div>
        <p v-else-if="!isSearchingMx3 && mx3Query && !mx3ConnectError" class="text-xs text-gray-500">
          Lance une recherche pour sélectionner le bon groupe.
        </p>

        <button
          v-if="mx3Bands.length"
          type="button"
          @click="connectMx3Band"
          :disabled="selectedMx3BandId === null || isConnectingMx3"
          class="px-3 py-1.5 text-xs font-bold rounded-lg bg-sky-400 hover:bg-sky-300 text-black transition-colors disabled:opacity-40 cursor-pointer"
        >
          {{ isConnectingMx3 ? 'Connexion...' : 'Lier le groupe sélectionné' }}
        </button>
      </div>
      <div v-if="mx3ConnectError" class="text-xs text-red-400">{{ mx3ConnectError }}</div>

      <div v-if="store.connectors.mx3.connected" class="flex flex-wrap gap-2">
        <button
          type="button"
          @click="syncMx3Metrics"
          :disabled="isSyncingMx3Metrics"
          class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#00ff88] hover:bg-[#00e57a] text-black transition-colors disabled:opacity-50 cursor-pointer"
        >
          {{ isSyncingMx3Metrics ? 'Actualisation...' : 'Actualiser les métriques MX3' }}
        </button>
        <button
          type="button"
          @click="loadMx3Gigs"
          :disabled="isLoadingMx3Gigs"
          class="px-3 py-1.5 text-xs font-bold rounded-lg bg-sky-400 hover:bg-sky-300 text-black transition-colors disabled:opacity-50 cursor-pointer"
        >
          {{ isLoadingMx3Gigs ? 'Chargement...' : 'Charger les concerts MX3' }}
        </button>
      </div>

      <p
        v-if="mx3MetricsFeedback"
        :class="mx3MetricsFeedback.type === 'success' ? 'text-[#00ff88]' : 'text-red-400'"
        class="text-xs"
      >
        {{ mx3MetricsFeedback.message }}
      </p>

      <div v-if="mx3GigsError" class="text-xs text-red-400">{{ mx3GigsError }}</div>
      <p v-if="mx3Gigs !== null && mx3Gigs.length === 0" class="text-xs text-gray-500">
        Aucun concert à venir n'est publié sur MX3.
      </p>
      <div v-if="mx3Gigs?.length" class="divide-y divide-[#282c37] border-y border-[#282c37]">
        <article v-for="(gig, index) in mx3Gigs" :key="`${gig.date}-${gig.name}-${index}`" class="py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
          <time class="text-xs font-mono font-bold text-sky-400 sm:w-24 shrink-0">{{ formatMx3Date(gig.date) }}</time>
          <div class="min-w-0 flex-1">
            <strong class="block text-sm text-white">{{ gig.name }}</strong>
            <span class="block text-xs text-gray-400">{{ gig.location || gig.stageName || 'Lieu non renseigné' }}</span>
          </div>
          <div class="flex gap-3 text-[11px]">
            <a v-if="gig.locationUrl" :href="gig.locationUrl" target="_blank" rel="noopener noreferrer" class="text-sky-400 hover:underline">Lieu</a>
            <a v-if="gig.ticketUrl" :href="gig.ticketUrl" target="_blank" rel="noopener noreferrer" class="text-[#00ff88] hover:underline">Billets</a>
          </div>
        </article>
      </div>
    </section>

    <!-- 2. Grille 2 Colonnes : Morceaux (Gauche) & Assets (Droite) -->
    <div class="w-full grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- Colonne Morceaux -->
      <section class="bg-[#181a20] border border-[#282c37] rounded-2xl p-5 sm:p-6 space-y-4">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <h3 class="text-base font-extrabold text-white">🎵 Morceaux (Tracks)</h3>
            <span class="text-xs text-[#00ff88] font-mono bg-[#00ff88]/10 px-2 py-0.5 rounded">
              {{ tracks.length }} titres
            </span>
          </div>
          <button class="text-xs text-gray-400 hover:text-white px-2.5 py-1 bg-[#22252e] rounded border border-[#282c37] cursor-pointer">
            Voir tout
          </button>
        </div>

        <!-- Grille de Cartes Morceaux -->
        <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          <div
            v-for="t in tracks"
            :key="t.id"
            class="bg-[#121418] border border-[#282c37] hover:border-[#7c3aed] rounded-xl p-3.5 flex flex-col justify-between transition-all group"
          >
            <div class="space-y-1.5">
              <strong class="text-xs font-bold text-white line-clamp-2 leading-tight block group-hover:text-[#00ff88]">
                {{ t.titre }}
              </strong>
              <div class="flex justify-between text-[11px] text-gray-400 font-mono">
                <span>{{ t.dateCreation }}</span>
                <span class="font-bold text-gray-200">{{ t.duree }}</span>
              </div>
              <span class="text-[10px] text-gray-500 block truncate font-mono">ISRC: {{ t.isrc }}</span>
              <div class="grid grid-cols-2 rounded-md border border-[#282c37] overflow-hidden" aria-label="Type de morceau">
                <button
                  type="button"
                  :disabled="originalityUpdateTrackId === t.id"
                  @click="setTrackOriginality(t.id, true)"
                  :class="t.estOriginal ? 'bg-[#00ff88] text-black' : 'bg-[#181a20] text-gray-400 hover:text-white'"
                  class="px-2 py-1 text-[10px] font-bold transition-colors disabled:opacity-50"
                >
                  Original
                </button>
                <button
                  type="button"
                  :disabled="originalityUpdateTrackId === t.id"
                  @click="setTrackOriginality(t.id, false)"
                  :class="!t.estOriginal ? 'bg-amber-400 text-black' : 'bg-[#181a20] text-gray-400 hover:text-white'"
                  class="px-2 py-1 text-[10px] font-bold border-l border-[#282c37] transition-colors disabled:opacity-50"
                >
                  Reprise
                </button>
              </div>
            </div>

            <div class="flex items-center justify-between pt-3 mt-3 border-t border-[#282c37] text-xs">
              <button class="text-gray-400 hover:text-white" title="Informations">ℹ️</button>
              <button class="text-gray-400 hover:text-[#7c3aed]" title="Modifier">✏️</button>
              <button class="text-gray-400 hover:text-[#00ff88]" title="Lier à un asset/concert">🔗</button>
              <button @click="deleteTrack(t.id)" class="text-gray-400 hover:text-rose-400" title="Supprimer">🗑️</button>
            </div>
          </div>

          <!-- Bouton / Carte d'Ajout (+) -->
          <div class="border-2 border-dashed border-[#282c37] hover:border-[#00ff88] rounded-xl p-4 flex flex-col items-center justify-center text-center cursor-pointer transition-all bg-[#121418]/50 hover:bg-[#121418] group min-h-35">
            <div class="w-10 h-10 rounded-full bg-[#22252e] group-hover:bg-[#00ff88] text-gray-400 group-hover:text-black flex items-center justify-center text-xl font-bold transition-all">
              +
            </div>
            <span class="text-xs font-semibold text-gray-400 group-hover:text-white mt-2">Nouveau morceau</span>
          </div>
        </div>
        <p v-if="originalityUpdateError" class="text-xs text-red-400">{{ originalityUpdateError }}</p>
      </section>

      <!-- Colonne Assets (Médias, Disques, Dossiers) -->
      <section class="bg-[#181a20] border border-[#282c37] rounded-2xl p-5 sm:p-6 space-y-4">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <h3 class="text-base font-extrabold text-white">📦 Assets & Supports de Production</h3>
            <span class="text-xs text-[#7c3aed] font-mono bg-[#7c3aed]/10 px-2 py-0.5 rounded">
              {{ assets.length }} fichiers
            </span>
          </div>
          <button class="text-xs text-gray-400 hover:text-white px-2.5 py-1 bg-[#22252e] rounded border border-[#282c37] cursor-pointer">
            Voir tout
          </button>
        </div>

        <form
          v-if="showAssetForm"
          @submit.prevent="submitAsset"
          class="space-y-4 border-y border-[#282c37] py-4"
        >
          <div class="flex items-center justify-between gap-3">
            <h4 class="text-sm font-bold text-white">
              {{ editingAssetId === null ? 'Nouvel asset' : 'Modifier l’asset' }}
            </h4>
            <button type="button" @click="closeAssetForm" class="text-gray-400 hover:text-white" title="Fermer">✕</button>
          </div>

          <p v-if="assetFormError" class="text-xs text-rose-400">{{ assetFormError }}</p>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label class="block sm:col-span-2">
              <span class="block text-xs text-gray-400 mb-1">Titre</span>
              <input v-model="assetForm.titre" required maxlength="255" class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
            </label>
            <label class="block">
              <span class="block text-xs text-gray-400 mb-1">Type</span>
              <select v-model="assetForm.typeSelection" required class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]">
                <option value="" disabled>Sélectionner</option>
                <option v-for="assetType in store.assetTypes" :key="assetType.id" :value="String(assetType.id)">
                  {{ assetType.libelle }}
                </option>
                <option :value="customAssetTypeValue">Autre</option>
              </select>
            </label>
            <label class="block">
              <span class="block text-xs text-gray-400 mb-1">Date</span>
              <input v-model="assetForm.date" type="date" :required="assetForm.isJourneyEvent" class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
            </label>
            <label v-if="assetForm.typeSelection === customAssetTypeValue" class="block sm:col-span-2">
              <span class="block text-xs text-gray-400 mb-1">Nouveau type</span>
              <input v-model="assetForm.typeLibelle" required maxlength="100" class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed]" />
            </label>
            <label class="block sm:col-span-2">
              <span class="block text-xs text-gray-400 mb-1">URL externe</span>
              <input v-model="assetForm.url" :disabled="selectedAssetFile !== null" type="url" maxlength="500" placeholder="https://" class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#7c3aed] disabled:opacity-40" />
            </label>
            <div class="sm:col-span-2 space-y-2">
              <span class="block text-xs text-gray-400">Ou téléverser un fichier (25 Mo maximum)</span>
              <label class="flex items-center justify-center min-h-20 border-2 border-dashed border-[#282c37] hover:border-[#7c3aed] rounded-lg cursor-pointer bg-[#121418]/60 px-3 text-center">
                <input type="file" class="sr-only" accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.mp3,.wav,.ogg,.mp4,.webm,.mov,.txt,.csv,.docx,.xlsx,.pptx" @change="selectAssetFile" />
                <span class="text-xs text-gray-400">Choisir un PDF, une image, un média ou un document</span>
              </label>
              <div v-if="selectedAssetFile" class="flex items-center justify-between gap-3 text-xs bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2">
                <span class="min-w-0 truncate text-gray-200">{{ selectedAssetFile.name }} · {{ formatFileSize(selectedAssetFile.size) }}</span>
                <button type="button" @click="clearAssetFile" class="text-rose-400 hover:text-rose-300 shrink-0">Retirer</button>
              </div>
              <p v-else-if="editingAssetId !== null && assetForm.url" class="text-[10px] text-gray-500">
                Aucun nouveau fichier sélectionné: le fichier ou lien actuel sera conservé.
              </p>
            </div>
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between gap-3">
              <span class="text-xs font-bold text-gray-300">Métadonnées</span>
              <div class="grid grid-cols-2 border border-[#282c37] rounded-lg overflow-hidden">
                <button type="button" @click="switchMetadataMode('pairs')" :class="metadataMode === 'pairs' ? 'bg-[#7c3aed] text-white' : 'bg-[#121418] text-gray-400'" class="px-2.5 py-1 text-[10px] font-bold">Champs</button>
                <button type="button" @click="switchMetadataMode('json')" :class="metadataMode === 'json' ? 'bg-[#7c3aed] text-white' : 'bg-[#121418] text-gray-400'" class="px-2.5 py-1 text-[10px] font-bold border-l border-[#282c37]">JSON</button>
              </div>
            </div>
            <template v-if="metadataMode === 'pairs'">
              <div v-for="(pair, index) in metadataPairs" :key="index" class="grid grid-cols-[1fr_1fr_auto] gap-2">
                <input v-model="pair.key" placeholder="Clé" class="min-w-0 bg-[#121418] border border-[#282c37] rounded-lg px-2 py-1.5 text-xs text-gray-200" />
                <input v-model="pair.value" placeholder="Valeur" class="min-w-0 bg-[#121418] border border-[#282c37] rounded-lg px-2 py-1.5 text-xs text-gray-200" />
                <button type="button" @click="removeMetadataPair(index)" class="w-8 text-rose-400 hover:bg-rose-500/10 rounded" title="Supprimer la métadonnée">✕</button>
              </div>
              <button type="button" @click="addMetadataPair" class="text-xs text-[#7c3aed] hover:text-white">+ Ajouter une métadonnée</button>
            </template>
            <textarea v-else v-model="metadataJson" rows="7" spellcheck="false" class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs font-mono text-gray-200 focus:outline-none focus:border-[#7c3aed]"></textarea>
          </div>

          <div class="space-y-2">
            <label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
              <input v-model="assetForm.featuredRoster" type="checkbox" class="accent-[#7c3aed]" />
              Mettre en avant dans le roster
            </label>
            <label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
              <input v-model="assetForm.isJourneyEvent" type="checkbox" class="accent-[#00ff88]" />
              Signaler comme événement de parcours
            </label>
            <label v-if="assetForm.isJourneyEvent" class="block pl-6">
              <span class="block text-xs text-gray-400 mb-1">Source média</span>
              <input v-model="assetForm.eventSource" maxlength="150" class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#00ff88]" />
            </label>
          </div>

          <div class="flex justify-end gap-2">
            <button type="button" @click="closeAssetForm" :disabled="isSavingAsset" class="px-3 py-1.5 text-xs font-bold rounded-lg border border-[#282c37] text-gray-300 hover:bg-white/5 disabled:opacity-40">Annuler</button>
            <button type="submit" :disabled="isSavingAsset || !isAssetFormValid" class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#7c3aed] hover:bg-[#6d28d9] text-white disabled:opacity-40">
              {{ isSavingAsset ? 'Enregistrement...' : 'Enregistrer' }}
            </button>
          </div>
        </form>

        <!-- Grille de Cartes Assets -->
        <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          <div
            v-for="a in assets"
            :key="a.id"
            class="bg-[#121418] border border-[#282c37] hover:border-[#7c3aed] rounded-xl p-3.5 flex flex-col justify-between transition-all group"
          >
            <div class="space-y-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-[#22252e] text-[#7c3aed] border border-[#282c37]">
                  {{ a.type }}
                </span>
                <span class="text-[10px] text-gray-500 font-mono">{{ a.date }}</span>
              </div>
              <strong class="text-xs font-bold text-white line-clamp-1 block group-hover:text-[#00ff88]">
                {{ a.titre }}
              </strong>
              <p class="text-[11px] text-gray-400 line-clamp-2 leading-tight">{{ metadataSummary(a.metadata) }}</p>
              <span v-if="a.isJourneyEvent" class="inline-block text-[9px] font-bold text-[#00ff88] border border-[#00ff88]/30 rounded px-1.5 py-0.5">
                Fait marquant
              </span>
            </div>

            <div class="flex items-center justify-between pt-3 mt-3 border-t border-[#282c37] text-xs">
              <a v-if="a.url" :href="a.url" target="_blank" rel="noopener noreferrer" class="text-gray-400 hover:text-white" title="Ouvrir le lien">↗</a>
              <span v-else class="w-3"></span>
              <button type="button" @click="openEditAssetForm(a)" class="text-gray-400 hover:text-[#7c3aed]" title="Modifier">✏️</button>
              <button type="button" @click="askDeleteAsset(a)" class="text-gray-400 hover:text-rose-400" title="Supprimer">🗑️</button>
            </div>
          </div>

          <!-- Bouton / Carte d'Ajout (+) -->
          <button type="button" @click="openCreateAssetForm" class="border-2 border-dashed border-[#282c37] hover:border-[#7c3aed] rounded-xl p-4 flex flex-col items-center justify-center text-center cursor-pointer transition-all bg-[#121418]/50 hover:bg-[#121418] group min-h-35">
            <div class="w-10 h-10 rounded-full bg-[#22252e] group-hover:bg-[#7c3aed] text-gray-400 group-hover:text-white flex items-center justify-center text-xl font-bold transition-all">
              +
            </div>
            <span class="text-xs font-semibold text-gray-400 group-hover:text-white mt-2">Ajouter un asset</span>
          </button>
        </div>
      </section>
    </div>

    <div v-if="assetPendingDeletion" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
      <div class="w-full max-w-md bg-[#181a20] border border-[#282c37] rounded-xl p-5 space-y-4">
        <h3 class="text-base font-bold text-white">Supprimer cet asset ?</h3>
        <p class="text-sm text-gray-400">
          « {{ assetPendingDeletion.titre }} » sera supprimé définitivement avec ses liens aux morceaux<span v-if="assetPendingDeletion.isJourneyEvent"> et son fait marquant associé</span>.
        </p>
        <p v-if="deleteAssetError" class="text-xs text-rose-400">{{ deleteAssetError }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" @click="cancelDeleteAsset" :disabled="isDeletingAsset" class="px-3 py-1.5 text-xs font-bold rounded-lg border border-[#282c37] text-gray-300 hover:bg-white/5 disabled:opacity-40">Annuler</button>
          <button type="button" @click="confirmDeleteAsset" :disabled="isDeletingAsset" class="px-3 py-1.5 text-xs font-bold rounded-lg bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-40">
            {{ isDeletingAsset ? 'Suppression...' : 'Supprimer définitivement' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 3. Frise Chronologique des Concerts (Live Timeline) -->
    <section class="w-full bg-[#181a20] border border-[#282c37] rounded-2xl p-5 sm:p-7 space-y-6 shadow-xl">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#282c37] pb-4">
        <div>
          <h3 class="text-base sm:text-lg font-extrabold text-white">🗓️ Frise Chronologique des Concerts & Tournées</h3>
          <p class="text-xs text-gray-400">Historique diachronique des représentations scéniques et jauges de diffusion.</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="openAddConcertForm(project as MusicalProject)"
            class="px-3 py-1.5 bg-[#00ff88] hover:bg-[#00e57a] text-black text-xs font-black rounded-lg transition-colors cursor-pointer"
            >
            + Ajouter une date de concert
          </button>
        </div>
      </div>

      <!-- Formulaire d'ajout de concert -->
      <form
        v-if="showAddConcertForm"
        @submit.prevent="submitConcert"
        class="bg-[#121418] border border-[#282c37] rounded-lg p-3 space-y-3"
      >
        <div v-if="addConcertError" class="text-xs text-red-400">{{ addConcertError }}</div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          <label class="block">
            <span class="block text-xs text-gray-400 mb-1">Date</span>
            <input
              v-model="newConcertForm.date"
              type="date"
              required
              class="w-full bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
            />
          </label>
          <label class="block sm:col-span-2">
            <span class="block text-xs text-gray-400 mb-1">Salle</span>
            <select
              v-model="newConcertForm.venueSelection"
              class="w-full bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
              required
            >
              <option value="" disabled>Sélectionner une salle</option>
              <option v-for="venue in store.venues" :key="venue.id" :value="String(venue.id)">
                {{ venue.nom }} — {{ venue.ville }}{{ venue.estFestival ? ' · Festival' : '' }}
              </option>
              <option :value="newVenueValue">+ Ajouter une salle</option>
            </select>
          </label>
          <label class="block">
            <span class="block text-xs text-gray-400 mb-1">Type d'événement</span>
            <select
              v-model="newConcertForm.typeEvenement"
              class="w-full bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
            >
              <option value="Concert">Concert</option>
              <option value="Résidence">Résidence</option>
              <option value="Showcase">Showcase</option>
            </select>
          </label>
        </div>

        <div
          v-if="isCreatingVenue"
          class="space-y-2 rounded-lg border border-[#00ff88]/25 bg-[#0e0f12] p-3"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h4 class="text-xs font-bold uppercase text-[#00ff88]">Nouvelle salle</h4>
            <label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
              <input v-model="newVenueForm.estFestival" type="checkbox" class="accent-[#00ff88]" />
              Festival
            </label>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
            <label class="block">
              <span class="block text-xs text-gray-400 mb-1">Nom</span>
              <input
                v-model.trim="newVenueForm.nom"
                type="text"
                required
                class="w-full bg-[#121418] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
              />
            </label>
            <label class="block sm:col-span-2">
              <span class="block text-xs text-gray-400 mb-1">Adresse</span>
              <input
                v-model.trim="newVenueForm.adresse"
                type="text"
                class="w-full bg-[#121418] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
              />
            </label>
            <label class="block">
              <span class="block text-xs text-gray-400 mb-1">NPA</span>
              <input
                v-model.trim="newVenueForm.npa"
                type="text"
                class="w-full bg-[#121418] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
              />
            </label>
            <label class="block">
              <span class="block text-xs text-gray-400 mb-1">Ville</span>
              <input
                v-model.trim="newVenueForm.ville"
                type="text"
                required
                class="w-full bg-[#121418] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
              />
            </label>
            <label class="block">
              <span class="block text-xs text-gray-400 mb-1">Pays</span>
              <input
                v-model.trim="newVenueForm.pays"
                type="text"
                required
                class="w-full bg-[#121418] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
              />
            </label>
            <label class="block">
              <span class="block text-xs text-gray-400 mb-1">Jauge</span>
              <input
                v-model.number="newVenueForm.jauge"
                type="number"
                min="0"
                step="1"
                required
                class="w-full bg-[#121418] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
              />
            </label>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <label class="block">
            <span class="block text-xs text-gray-400 mb-1">Cachet brut (CHF)</span>
            <input
              v-model.number="newConcertForm.cachetBrut"
              type="number"
              min="0"
              step="0.05"
              placeholder="Optionnel"
              class="w-full bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
            />
          </label>
          <label class="block">
            <span class="block text-xs text-gray-400 mb-1">Zone géographique</span>
            <select
              v-model="newConcertForm.type"
              class="w-full bg-[#0e0f12] border border-[#282c37] rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#00ff88]"
            >
              <option value="Local (NE)">Local (NE)</option>
              <option value="Hors-Canton">Hors-Canton</option>
              <option value="Export">Export</option>
            </select>
          </label>
        </div>

        <div class="flex items-center justify-end gap-2">
          <button
            type="button"
            @click="closeAddConcertForm"
            :disabled="isAddingConcert"
            class="px-3 py-1.5 text-xs font-bold rounded-lg border border-[#282c37] text-gray-300 hover:bg-white/5 transition-colors disabled:opacity-50 cursor-pointer"
          >
            Annuler
          </button>
          <button
            type="submit"
            :disabled="isAddingConcert || !isConcertFormValid"
            class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#00ff88] hover:bg-[#00e57a] text-black transition-colors disabled:opacity-40 cursor-pointer"
          >
            {{ isAddingConcert ? 'Ajout...' : 'Ajouter le concert' }}
          </button>
        </div>
      </form>

      <!-- Timeline Scrollable Horizontale Responsive -->
      <div class="overflow-x-auto pb-4 pt-2">
        <div class="min-w-212.5 relative">
          
          <!-- Ligne de temps principale (Horizontale) -->
          <div class="absolute top-1/2 left-0 w-full h-1 bg-[#282c37] -translate-y-1/2 z-0"></div>

          <!-- Jalons de Concerts -->
          <div class="grid grid-cols-5 gap-4 relative z-10">
            <div
              v-for="c in concerts"
              :key="c.id"
              class="bg-[#121418] border border-[#282c37] hover:border-[#00ff88] rounded-xl p-3.5 space-y-2 transition-all shadow-md group"
            >
              <!-- En-tête Date / Badge type -->
              <div class="flex justify-between items-center border-b border-[#282c37]/60 pb-2">
                <span class="text-xs font-mono font-bold text-[#00ff88]">{{ c.date }}</span>
                <span class="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-[#22252e] text-gray-300">
                  {{ c.type }}
                </span>
              </div>

              <!-- Lieu & Ville -->
              <div>
                <strong class="text-xs font-extrabold text-white block group-hover:text-[#00ff88]">{{ c.lieu }}</strong>
                <span class="text-[11px] text-gray-400 block">{{ c.ville }} ({{ c.pays }})</span>
                <span v-if="c.typeEvenement" class="text-[10px] font-semibold text-[#00ff88]">
                  {{ c.typeEvenement }}
                </span>
              </div>

              <!-- Jauge & cachet -->
              <div class="space-y-0.5 text-[10px] text-gray-500 font-mono">
                <div>Jauge : <span class="text-gray-300 font-bold">{{ c.jauge }} pers.</span></div>
                <div v-if="c.cachetBrut != null">
                  Cachet : <span class="text-gray-300 font-bold">{{ Number(c.cachetBrut).toLocaleString('fr-CH') }} CHF</span>
                </div>
              </div>

              <!-- Actions Concert -->
              <div class="flex items-center justify-between pt-2 border-t border-[#282c37] text-xs">
                <button class="text-gray-400 hover:text-white" title="Détails setlist">ℹ️</button>
                <button class="text-gray-400 hover:text-[#7c3aed]" title="Modifier">✏️</button>
                <button class="text-gray-400 hover:text-[#00ff88]" title="Lier feuille SUISA">🔗</button>
                <button @click="deleteConcert(c.id)" class="text-gray-400 hover:text-rose-400 cursor-pointer" title="Supprimer">🗑️</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
    </template>
  </div>
</template>