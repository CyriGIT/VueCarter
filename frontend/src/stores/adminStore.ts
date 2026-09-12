import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import apiClient from '@/services/api'
import type { AdminItem, AdminResourceKey, ExpertAdmin, ExpertForm, ExpertRole } from '@/types/admin'

const resourceKeys: AdminResourceKey[] = [
  'legal-statuses', 'phase-types', 'styles', 'programs', 'formations',
  'professional-structures', 'venues', 'platforms'
]

function errorDetail(error: any, fallback: string) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(item => item.msg).filter(Boolean).join(' · ')
  return fallback
}

export const useAdminStore = defineStore('admin', () => {
  const resources = ref<Record<AdminResourceKey, AdminItem[]>>({
    'legal-statuses': [], 'phase-types': [], styles: [], programs: [], formations: [],
    'professional-structures': [], venues: [], platforms: []
  })
  const experts = ref<ExpertAdmin[]>([])
  const isLoading = ref(false)
  const isSaving = ref(false)
  const errorMessage = ref<string | null>(null)

  const activeTotal = computed(() => resourceKeys.reduce(
    (total, key) => total + resources.value[key].filter(item => item.estActif).length, 0
  ))

  async function fetchAll() {
    isLoading.value = true
    errorMessage.value = null
    try {
      const [expertResponse, resourceResponses] = await Promise.all([
        apiClient.get('/admin/experts'),
        Promise.all(resourceKeys.map(async key => ({
          key,
          response: await apiClient.get(`/admin/${key}`)
        })))
      ])
      experts.value = expertResponse.data
      resourceResponses.forEach(({ key, response }) => { resources.value[key] = response.data })
    } catch (error: any) {
      errorMessage.value = errorDetail(error, 'Impossible de charger les données d’administration.')
    } finally {
      isLoading.value = false
    }
  }

  async function createItem(key: AdminResourceKey, payload: Record<string, unknown>) {
    return save(async () => {
      const response = await apiClient.post(`/admin/${key}`, payload)
      resources.value[key].push(response.data)
      return response.data as AdminItem
    })
  }

  async function updateItem(key: AdminResourceKey, id: number, payload: Record<string, unknown>) {
    return save(async () => {
      const response = await apiClient.patch(`/admin/${key}/${id}`, payload)
      const index = resources.value[key].findIndex(item => item.id === id)
      if (index >= 0) resources.value[key][index] = response.data
      return response.data as AdminItem
    })
  }

  async function inviteExpert(payload: ExpertForm) {
    return save(async () => {
      const response = await apiClient.post('/admin/experts/invitations', payload)
      await fetchExperts()
      return response.data.invitationUrl as string
    })
  }

  async function renewInvitation(id: number, role: ExpertRole) {
    return save(async () => {
      const response = await apiClient.post(`/admin/experts/${id}/invitation`, { role })
      return response.data.invitationUrl as string
    })
  }

  async function updateExpert(id: number, payload: ExpertForm & { estActif: boolean }) {
    return save(async () => {
      const response = await apiClient.patch(`/admin/experts/${id}`, payload)
      const index = experts.value.findIndex(expert => expert.id === id)
      if (index >= 0) experts.value[index] = response.data
      return response.data as ExpertAdmin
    })
  }

  async function fetchExperts() {
    const response = await apiClient.get('/admin/experts')
    experts.value = response.data
  }

  async function save<T>(operation: () => Promise<T>): Promise<T | null> {
    isSaving.value = true
    errorMessage.value = null
    try {
      return await operation()
    } catch (error: any) {
      errorMessage.value = errorDetail(error, 'La modification n’a pas pu être enregistrée.')
      return null
    } finally {
      isSaving.value = false
    }
  }

  return {
    resources, experts, isLoading, isSaving, errorMessage, activeTotal,
    fetchAll, createItem, updateItem, inviteExpert, renewInvitation, updateExpert
  }
})