import type { GrantApplication } from '@/types/grantDeadline'

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
export type AssetMetadata = { [key: string]: JsonValue }

export interface Member {
  id: number
  nom: string
  prenom: string
  genre: 'Homme' | 'Femme' | 'Autre'
  dateNaissance: string
  role: string
  email: string
  telephone: string
  hasAccount: boolean
}

export interface Track {
  id: number
  titre: string
  duree: string
  dateCreation: string
  isrc: string
  hasAudio: boolean
  estOriginal: boolean
  streamsCount?: string
}

export interface ProjectAsset {
  id: number
  titre: string
  date: string | null
  typeId: number
  type: string
  metadata: AssetMetadata
  url: string
  featuredRoster: boolean
  isJourneyEvent: boolean
  eventId: number | null
  eventSource: string | null
}

export interface AssetType {
  id: number
  libelle: string
  description: string | null
}

export interface AssetWrite {
  titre: string
  date: string | null
  typeId?: number
  typeLibelle?: string
  url: string
  metadata: AssetMetadata
  featuredRoster: boolean
  isJourneyEvent: boolean
  eventSource?: string | null
}

export interface AssetMutationResponse {
  asset: ProjectAsset
  highlight: Highlight | null
}

export interface AssetDeleteResponse {
  assetId: number
  eventId: number | null
}

export interface Venue {
  id: number
  nom: string
  adresse?: string
  ville: string
  npa?: string
  pays: string
  jauge: number
  estFestival: boolean
}

export interface VenueCreate {
  nom: string
  adresse?: string
  ville: string
  npa?: string
  pays: string
  jauge: number
  estFestival: boolean
}

export interface ConcertCreate {
  date: string
  type: 'Local (NE)' | 'Hors-Canton' | 'Export'
  typeEvenement: 'Concert' | 'Résidence' | 'Showcase'
  cachetBrut?: number
  venueId?: number
  newVenue?: VenueCreate
}

export interface Concert {
  id: number
  annee: number
  date: string
  venueId?: number
  lieu: string
  ville: string
  pays: string
  jauge: number
  type: 'Local (NE)' | 'Hors-Canton' | 'Export'
  typeEvenement?: 'Concert' | 'Résidence' | 'Showcase'
  cachetBrut?: number | null
}

export interface Highlight {
  id: number
  type: string
  titre: string
  date: string
  source: string | null
  url: string | null
}

export interface AudienceMetric {
  platform: string
  type: string
  value: number
  date: string
}

export type EvaluationScores = Record<string, number>
export type EvaluationCriterionType = 'objectif' | 'subjectif'
export type EvaluationMode = 'automatique' | 'manuel'

export interface EvaluationCriterionWrite {
  nom: string
  type: EvaluationCriterionType
  noteMaximale: number
  poids: number
  ordre: number
  modeEvaluation: EvaluationMode
  regleObjective: string | null
}

export interface EvaluationCriterion extends EvaluationCriterionWrite {
  id: number
  code: string
  estActif: boolean
  estUtilise: boolean
}

export interface CampaignJuror {
  id: number
  prenom: string
  nom: string
  email: string
}

export type EvaluationCampaignStatus = 'brouillon' | 'ouverte' | 'cloturee'

export interface EvaluationCampaignWrite {
  nom: string
  statut: EvaluationCampaignStatus
  dateDebut: string | null
  dateFin: string | null
}

export interface EvaluationCampaign extends EvaluationCampaignWrite {
  id: number
  dateCreation: string
  projectIds: number[]
  jurorIds: number[]
}

export interface JuryNote {
  expertId: number
  expertNom: string
  note: number | null
  estNotePersonnelle: boolean
}

export interface CampaignEvaluation {
  campaignId: number
  projectId: number
  bilanId: number | null
  scores: EvaluationScores
  remarques: string
  statut: 'en_attente' | 'selectionne' | 'refuse'
  decisionEmailSentAt: string | null
  gridScore: number | null
  gridCoverageCount: number
  gridCriteriaCount: number
  juryAverage: number | null
  globalScore: number | null
  juryCoverageCount: number
  juryCount: number
  juryNotes: JuryNote[]
}

export interface ObjectiveRule {
  code: string
  libelle: string
}

export interface AccompanimentReference {
  id: number
  nom: string
  organisme: string | null
  estActif: boolean
}

export interface ProjectFormation {
  formationId: number
  nom: string
  organisme: string | null
  dateSuivi: string
}

export interface ProjectProgramme {
  programmeId: number
  nom: string
  organisme: string | null
  anneeParticipation: number
  estLaureat: boolean
}

export interface AccompanyingExpert {
  id: number
  nom: string
  prenom: string
  email: string
  dateAffectation?: string | null
}

export interface MusicalProject {
  id: number
  nom: string
  dateCreation: string
  commune?: string
  genreMusical: string
  styles: ProjectStyle[]
  statutJuridiqueId: number
  statutJuridique: string
  langueChant: string
  bioCourte: string
  personalPageUrl?: string | null
  personalPageSiteName?: string | null
  objectifsCourtTerme?: string | null
  objectifsMoyenTerme?: string | null
  pitchAccroche?: string
  bioComplete?: string
  avatarUrl: string
  readinessScore: number
  // Métadonnées & Accompagnement Embrayage
  suisaInscrit: boolean
  hasLocal: boolean
  hasDemandeSubvention: boolean
  hasFicheTechnique: boolean
  hasMerch: boolean
  hasStudioContact?: boolean
  mixMasterContact: string
  formationsSuivies: ProjectFormation[]
  programmesPrecedents: ProjectProgramme[]
  grantApplications: GrantApplication[]
  accompanyingExpert?: AccompanyingExpert | null
  residencesCount: number
  instaFollowers: string
  audienceMetrics: AudienceMetric[]
  // Relations
  members: Member[]
  tracks: Track[]
  assets: ProjectAsset[]
  concerts: Concert[]
  highlights?: Highlight[]
  // Évaluation interne
  scores?: EvaluationScores
  remarquesEvaluation?: string
  statutSelection?: 'en_attente' | 'selectionne' | 'refuse'
  decisionEmailSentAt?: string | null
}

export interface UserProfile {
  id: number
  nom: string
  prenom: string
  email: string
  telephone: string
  genre: string
  dateNaissance: string
  avatarUrl: string
  // Fiche personnelle (table "Personne")
  adresse?: string
  npa?: string
  ville?: string
  canton?: string
  noIpi?: string
}

export interface AccountIdentity {
  id: number
  email: string
  displayName: string
  role: string
  personId: number | null
  canManageEvaluations: boolean
}

export interface ConnectorStatus {
  connected: boolean
  profileUrl?: string | null
  externalId?: string | null
  metrics: ConnectorMetric[]
  metricValue?: number | null
  metricType?: string | null
  lastSync?: string | null
}

export interface ConnectorMetric {
  type: string
  value: number
  date: string
}

export interface SyncConnectors {
  spotify: ConnectorStatus
  mx3: ConnectorStatus
}

export interface Mx3Band {
  id: number
  name: string
  city?: string | null
  profileUrl?: string | null
  imageUrl?: string | null
}

export interface Mx3Gig {
  name: string
  date: string
  bandName?: string | null
  stageName?: string | null
  location?: string | null
  locationUrl?: string | null
  ticketUrl?: string | null
}

// Taxonomie des styles musicaux (arbre à 3 niveaux : racine FCMA -> macro-genre -> sous-genre)
export interface StyleMusical {
  id: number
  nom: string
  idParent: number | null
}

// Style attribué à un projet (feuille de l'arbre StyleMusical), avec indicateur "principal"
export interface ProjectStyle {
  id: number
  nom: string
  principal: boolean
}

// Catalogue Spotify récupéré à la volée (non persisté), pour sélection avant import en base
export interface SpotifyCatalogTrack {
  id: string
  name: string
  track_number: number
  duration_ms: number
  release_date: string
}

export interface SpotifyCatalogAlbum {
  id: string
  name: string
  release_date: string
  album_type: string
  tracks: SpotifyCatalogTrack[]
}

export interface SpotifyCatalog {
  artist_id: string
  artist_name: string
  followers: number
  popularity: number
  genres: string[]
  albums: SpotifyCatalogAlbum[]
}

export interface LegalStatus {
  id: number
  libelle: string
  estActif: boolean
}