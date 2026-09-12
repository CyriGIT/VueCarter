<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiClient from '@/services/api'

const route = useRoute()
const router = useRouter()

const token = (route.query.token as string) || ''
const password = ref('')
const confirmPassword = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

async function acceptInvitation() {
  errorMessage.value = ''

  if (!token) {
    errorMessage.value = 'Lien d’invitation invalide.'
    return
  }
  if (password.value.length < 4) {
    errorMessage.value = 'Le mot de passe doit contenir au moins 4 caractères.'
    return
  }
  if (password.value !== confirmPassword.value) {
    errorMessage.value = 'Les mots de passe ne correspondent pas.'
    return
  }

  isSubmitting.value = true
  try {
    const response = await apiClient.post('/auth/accept-invitation', { token, password: password.value })
    localStorage.setItem('auth_token', response.data.access_token)
    localStorage.setItem('user_role', response.data.role)
    router.push(response.data.role === 'admin' ? '/admin/dashboard'
      : response.data.role === 'artiste' ? '/artist/dashboard'
      : '/expert/dashboard')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || 'Erreur lors de la création du compte.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-[#0e0f12] text-gray-100 px-4">
    <div class="w-full max-w-sm bg-[#181a20] border border-[#282c37] rounded-xl p-6 space-y-4">
      <div>
        <h1 class="text-lg font-extrabold text-white">Finaliser votre invitation</h1>
        <p class="text-sm text-gray-400 mt-1">Choisissez un mot de passe pour créer votre compte de connexion.</p>
      </div>

      <div v-if="!token" class="text-sm text-red-400">Lien d’invitation invalide ou incomplet.</div>

      <form v-else @submit.prevent="acceptInvitation" class="space-y-3">
        <div v-if="errorMessage" class="text-xs text-red-400">{{ errorMessage }}</div>
        <label class="block">
          <span class="text-xs text-gray-400">Mot de passe</span>
          <input v-model="password" type="password" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
        </label>
        <label class="block">
          <span class="text-xs text-gray-400">Confirmer le mot de passe</span>
          <input v-model="confirmPassword" type="password" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
        </label>
        <button
          type="submit"
          :disabled="isSubmitting"
          class="w-full py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-bold text-sm rounded-lg transition-all disabled:opacity-50 cursor-pointer"
        >
          {{ isSubmitting ? 'Création...' : 'Créer mon compte' }}
        </button>
      </form>
    </div>
  </div>
</template>
