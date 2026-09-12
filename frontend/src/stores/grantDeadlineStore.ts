import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/services/api'
import type { GrantDeadline, GrantDeadlineWrite } from '@/types/grantDeadline'

function errorDetail(error: any, fallback: string): string {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(item => item.msg).filter(Boolean).join(' · ')
  return fallback
}

export const useGrantDeadlineStore = defineStore('grantDeadlines', () => {
  const deadlines = ref<GrantDeadline[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const errorMessage = ref<string | null>(null)

  async function fetchDeadlines(canManage: boolean): Promise<boolean> {
    isLoading.value = true
    errorMessage.value = null
    try {
      const response = await apiClient.get(canManage ? '/grant-deadlines/manage' : '/grant-deadlines')
      deadlines.value = response.data
      return true
    } catch (error: any) {
      errorMessage.value = errorDetail(error, 'Impossible de charger les échéances de subvention.')
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function createDeadline(payload: GrantDeadlineWrite): Promise<boolean> {
    return save(async () => {
      await apiClient.post('/grant-deadlines', payload)
    })
  }

  async function updateDeadline(id: number, payload: GrantDeadlineWrite & { estActif: boolean }): Promise<boolean> {
    return save(async () => {
      await apiClient.patch(`/grant-deadlines/${id}`, payload)
    })
  }

  async function save(operation: () => Promise<void>): Promise<boolean> {
    isSaving.value = true
    errorMessage.value = null
    try {
      await operation()
      return true
    } catch (error: any) {
      errorMessage.value = errorDetail(error, 'L’échéance n’a pas pu être enregistrée.')
      return false
    } finally {
      isSaving.value = false
    }
  }

  return {
    deadlines,
    isLoading,
    isSaving,
    errorMessage,
    fetchDeadlines,
    createDeadline,
    updateDeadline
  }
})
