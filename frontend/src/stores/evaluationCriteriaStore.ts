import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/services/api'
import type {
  EvaluationCriterion,
  EvaluationCriterionWrite,
  ObjectiveRule
} from '@/types/project'

function apiErrorDetail(error: any, fallback: string): string {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  return fallback
}

export const useEvaluationCriteriaStore = defineStore('evaluationCriteria', () => {
  const criteria = ref<EvaluationCriterion[]>([])
  const objectiveRules = ref<ObjectiveRule[]>([])
  const isLoading = ref(false)
  const errorMessage = ref<string | null>(null)

  function sortCriteria() {
    criteria.value.sort((left, right) => left.ordre - right.ordre || left.id - right.id)
  }

  async function fetchCriteria(includeInactive = false): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.get('/evaluation/criteria', { params: { includeInactive } })
      criteria.value = response.data
      sortCriteria()
      return true
    } catch (error: any) {
      errorMessage.value = apiErrorDetail(error, 'La grille d’évaluation n’a pas pu être chargée.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function fetchConfigurationOptions(): Promise<boolean> {
    errorMessage.value = null
    try {
      const rulesResponse = await apiClient.get('/evaluation/criteria/objective-rules')
      objectiveRules.value = rulesResponse.data
      return true
    } catch (error: any) {
      errorMessage.value = apiErrorDetail(error, 'Les options de configuration n’ont pas pu être chargées.')
      return false
    }
  }

  async function createCriterion(payload: EvaluationCriterionWrite): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.post('/evaluation/criteria', payload)
      criteria.value.push(response.data)
      sortCriteria()
      return true
    } catch (error: any) {
      errorMessage.value = apiErrorDetail(error, 'Le critère n’a pas pu être créé.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function updateCriterion(
    id: number,
    payload: EvaluationCriterionWrite & { estActif: boolean }
  ): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.patch(`/evaluation/criteria/${id}`, payload)
      const index = criteria.value.findIndex(criterion => criterion.id === id)
      if (index >= 0) criteria.value[index] = response.data
      sortCriteria()
      return true
    } catch (error: any) {
      errorMessage.value = apiErrorDetail(error, 'Le critère n’a pas pu être modifié.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  return {
    criteria,
    objectiveRules,
    isLoading,
    errorMessage,
    fetchCriteria,
    fetchConfigurationOptions,
    createCriterion,
    updateCriterion
  }
})
