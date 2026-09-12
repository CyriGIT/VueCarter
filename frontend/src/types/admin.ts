export type AdminResourceKey =
  | 'legal-statuses'
  | 'phase-types'
  | 'styles'
  | 'programs'
  | 'formations'
  | 'professional-structures'
  | 'venues'
  | 'platforms'

export interface AdminItem {
  id: number
  estActif: boolean
  libelle?: string
  nom?: string
  parentId?: number | null
  organisme?: string | null
  type?: string
  email?: string | null
  pays?: string
  adresse?: string | null
  ville?: string
  npa?: string | null
  jauge?: number
  estFestival?: boolean
}

export type ExpertRole = 'expert_jury' | 'gestionnaire_case' | 'accompagnant'
export type ExpertStatus = 'pending' | 'active' | 'inactive'

export interface ExpertAdmin {
  id: number
  prenom: string
  nom: string
  email: string
  role: ExpertRole
  dateNaissance: string
  genre: string
  npa: string
  ville: string
  telephone?: string | null
  statut: ExpertStatus
}

export interface ExpertForm {
  prenom: string
  nom: string
  email: string
  role: ExpertRole
  dateNaissance: string
  genre: 'Homme' | 'Femme' | 'Autre'
  npa: string
  ville: string
  telephone?: string | null
  estActif?: boolean
}