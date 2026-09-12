import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import apiClient from '@/services/api'
import type {
  CampaignEvaluation,
  CampaignJuror,
  EvaluationCampaign,
  EvaluationCampaignWrite
} from '@/types/project'

function apiErrorDetail(error: any, fallback: string): string {
  return typeof error.response?.data?.detail === 'string' ? error.response.data.detail : fallback
}

export const useEvaluationCampaignStore = defineStore('evaluationCampaign', () => {
  const campaigns = ref<EvaluationCampaign[]>([])
  const evaluations = ref<CampaignEvaluation[]>([])
  const eligibleJurors = ref<CampaignJuror[]>([])
  const selectedCampaignId = ref<number | null>(null)
  const isLoading = ref(false)
  const errorMessage = ref<string | null>(null)
  const selectedCampaign = computed(() => campaigns.value.find(item => item.id === selectedCampaignId.value) ?? null)

  async function fetchCampaigns(): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.get('/evaluation/campaigns')
      campaigns.value = response.data
      if (!campaigns.value.some(item => item.id === selectedCampaignId.value)) {
        selectedCampaignId.value = campaigns.value.find(item => item.statut === 'ouverte')?.id ?? campaigns.value[0]?.id ?? null
      }
      return true
    } catch (error: any) {
      campaigns.value = []
      selectedCampaignId.value = null
      errorMessage.value = apiErrorDetail(error, 'Les campagnes n’ont pas pu être chargées.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function fetchEvaluations(campaignId = selectedCampaignId.value): Promise<boolean> {
    if (!campaignId) return false
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.get(`/evaluation/campaigns/${campaignId}/evaluations`)
      evaluations.value = response.data
      return true
    } catch (error: any) {
      evaluations.value = []
      errorMessage.value = apiErrorDetail(error, 'Les évaluations de la campagne n’ont pas pu être chargées.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function selectCampaign(campaignId: number): Promise<void> {
    selectedCampaignId.value = campaignId
    await fetchEvaluations(campaignId)
  }

  async function fetchEligibleJurors(): Promise<boolean> {
    try {
      const response = await apiClient.get('/evaluation/campaigns/jurors')
      eligibleJurors.value = response.data
      return true
    } catch (error: any) {
      eligibleJurors.value = []
      errorMessage.value = apiErrorDetail(error, 'Les jurés n’ont pas pu être chargés.')
      return false
    }
  }

  async function saveCampaign(payload: EvaluationCampaignWrite, id?: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      if (id) await apiClient.patch(`/evaluation/campaigns/${id}`, payload)
      else await apiClient.post('/evaluation/campaigns', payload)
      await fetchCampaigns()
      return true
    } catch (error: any) {
      errorMessage.value = apiErrorDetail(error, 'La campagne n’a pas pu être enregistrée.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function setProjectAssignment(campaignId: number, projectId: number, assigned: boolean): Promise<boolean> {
    return setAssignment(`/evaluation/campaigns/${campaignId}/projects/${projectId}`, assigned)
  }

  async function setJurorAssignment(campaignId: number, jurorId: number, assigned: boolean): Promise<boolean> {
    return setAssignment(`/evaluation/campaigns/${campaignId}/jurors/${jurorId}`, assigned)
  }

  async function setAssignment(url: string, assigned: boolean): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      if (assigned) await apiClient.put(url)
      else await apiClient.delete(url)
      await fetchCampaigns()
      return true
    } catch (error: any) {
      errorMessage.value = apiErrorDetail(error, 'L’affectation n’a pas pu être modifiée.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function saveJuryNote(campaignId: number, projectId: number, note: number): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.put(
        `/evaluation/campaigns/${campaignId}/projects/${projectId}/jury-note`,
        { note }
      )
      const index = evaluations.value.findIndex(item => item.projectId === projectId)
      if (index >= 0) evaluations.value[index] = response.data
      else evaluations.value.push(response.data)
      return true
    } catch (error: any) {
      errorMessage.value = apiErrorDetail(error, 'La note jury n’a pas pu être enregistrée.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  return {
    campaigns, evaluations, eligibleJurors, selectedCampaignId, selectedCampaign,
    isLoading, errorMessage, fetchCampaigns, fetchEvaluations, selectCampaign,
    fetchEligibleJurors, saveCampaign, setProjectAssignment, setJurorAssignment, saveJuryNote
  }
})