export interface GrantDeadline {
  id: number
  bailleur: string
  dateProchaineSoumission: string
  urlFormulaire: string
  estActif: boolean
}

export interface GrantDeadlineWrite {
  bailleur: string
  dateProchaineSoumission: string
  urlFormulaire: string
}

export interface GrantApplication {
  deadlineId: number
  bailleur: string
  dateEcheance: string
  dateDepot: string
}

export interface GrantApplicationWrite {
  deadlineId: number
  dateDepot: string
}
