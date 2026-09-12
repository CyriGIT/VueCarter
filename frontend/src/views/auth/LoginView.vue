<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiClient from '@/services/api'

const router = useRouter()
const route = useRoute()

// Mode actif : Connexion ou Enregistrement Artiste
const isRegisterMode = ref(false)

// Rôle sélectionné pour la connexion
const selectedRole = ref<'artist' | 'expert'>('artist')

// Champs d'authentification
const email = ref('')
const password = ref('')
const rememberMe = ref(true)

// Champs d'enregistrement (Réservé exclusivement aux Artistes)
const nom = ref('')
const prenom = ref('')
const commune = ref('')
const genre = ref<'Homme' | 'Femme' | 'Autre'>('Homme')
const dateNaissance = ref('')

// Retours d'état
const errorMessage = ref(route.query.reason === 'session_expired'
  ? 'Votre session a expiré. Veuillez vous reconnecter.'
  : '')
const successMessage = ref('')
const isLoading = ref(false)

const handleSubmit = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  isLoading.value = true

  try {
    if (isRegisterMode.value) {
      if (!email.value || !password.value || !nom.value || !prenom.value || !commune.value || !dateNaissance.value) {
        throw new Error('Veuillez remplir tous les champs obligatoires du profil.')
      }

      try {
        const payload = {
          email: email.value,
          password: password.value,
          nom: nom.value,
          prenom: prenom.value,
          commune: commune.value,
          genre: genre.value,
          date_naissance: dateNaissance.value
        }
        
        const response = await apiClient.post('/auth/register', payload)
        if (response.data?.access_token) {
          localStorage.setItem('auth_token', response.data.access_token)
          localStorage.setItem('user_role', 'artiste')
        } else {
          throw new Error('Réponse d’inscription invalide.')
        }
      } catch (apiErr: any) {
        errorMessage.value = apiErr.response?.data?.detail || apiErr.message || 'Inscription impossible.'
        return
      }

      successMessage.value = 'Compte créé. Vous pouvez maintenant créer votre projet.'
      await router.push('/artist/dashboard')

    } else {
      // Connexion (Artiste ou Expert)
      if (!email.value || !password.value) {
        throw new Error('Veuillez renseigner vos identifiants.')
      }

      try {
        const response = await apiClient.post('/auth/login', {
          email: email.value,
          password: password.value
        })
        if (response.data?.access_token) {
          localStorage.setItem('auth_token', response.data.access_token)
          localStorage.setItem('user_role', response.data.role)
        } else {
          throw new Error('Réponse d’authentification invalide.')
        }
        const role = response.data.role
        router.push(role === 'admin' ? '/admin/dashboard'
          : ['expert_jury', 'gestionnaire_case', 'accompagnant'].includes(role) ? '/expert/dashboard'
          : '/artist/dashboard')
      } catch (apiErr: any) {
        errorMessage.value = apiErr.response?.data?.detail || apiErr.message || 'Connexion impossible.'
        return
      }
    }
  } catch (err: any) {
    errorMessage.value = err.message || 'Une erreur est survenue.'
  } finally {
    isLoading.value = false
  }
}

const toggleMode = () => {
  isRegisterMode.value = !isRegisterMode.value
  errorMessage.value = ''
  successMessage.value = ''
  // En mode inscription, le rôle est systématiquement verrouillé sur artiste
  if (isRegisterMode.value) {
    selectedRole.value = 'artist'
  }
}
</script>

<template>
  <div class="min-h-[calc(100vh-64px)] w-full flex items-center justify-center px-4 sm:px-6 py-8 sm:py-12 bg-[#0e0f12]">
    <div class="w-full max-w-lg bg-[#181a20] border border-[#282c37] rounded-2xl p-6 sm:p-8 shadow-2xl transition-all">
      
      <!-- En-tête -->
      <div class="text-center mb-6">
        <span class="inline-block text-xs font-extrabold tracking-wider bg-[#7c3aed]/15 text-[#7c3aed] border border-[#7c3aed]/30 px-3 py-1 rounded-full mb-3">
          VUE CARTER
        </span>
        <h2 class="text-xl sm:text-2xl font-black text-white mb-1">
          {{ isRegisterMode ? 'Créer un compte artiste' : 'Accès à la plateforme' }}
        </h2>
        <p class="text-xs sm:text-sm text-gray-400">
          {{ isRegisterMode 
            ? 'Créez votre profil personnel avant de renseigner votre projet musical.'
            : 'Centralisation, valorisation et pilotage des parcours en musiques actuelles.' }}
        </p>
      </div>

      <!-- Onglets Mode : Connexion vs Inscription -->
      <div class="flex border-b border-[#282c37] mb-6">
        <button
          type="button"
          @click="isRegisterMode = false"
          :class="[
            'w-1/2 py-2 text-xs font-bold transition-all border-b-2 cursor-pointer text-center',
            !isRegisterMode
              ? 'border-[#00ff88] text-[#00ff88]'
              : 'border-transparent text-gray-400 hover:text-white'
          ]"
        >
          Connexion
        </button>
        <button
          type="button"
          @click="isRegisterMode = true; selectedRole = 'artist'"
          :class="[
            'w-1/2 py-2 text-xs font-bold transition-all border-b-2 cursor-pointer text-center',
            isRegisterMode
              ? 'border-[#7c3aed] text-[#7c3aed]'
              : 'border-transparent text-gray-400 hover:text-white'
          ]"
        >
          Créer un compte Artiste
        </button>
      </div>

      <!-- Sélecteur de rôle (Uniquement visible en mode Connexion) -->
      <div v-if="!isRegisterMode" class="grid grid-cols-2 gap-3 mb-6">
        <button
          type="button"
          @click="selectedRole = 'artist'"
          :class="[
            'flex items-center gap-2.5 p-3 rounded-xl border text-left transition-all cursor-pointer',
            selectedRole === 'artist'
              ? 'bg-[#7c3aed]/10 border-[#7c3aed] text-white'
              : 'bg-[#121418] border-[#282c37] text-gray-400 hover:border-gray-600'
          ]"
        >
          <span class="text-lg">🎤</span>
          <div class="flex flex-col">
            <strong class="text-xs font-bold text-white">Artiste</strong>
            <small class="text-[10px] text-gray-400">Projets & Roster</small>
          </div>
        </button>

        <button
          type="button"
          @click="selectedRole = 'expert'"
          :class="[
            'flex items-center gap-2.5 p-3 rounded-xl border text-left transition-all cursor-pointer',
            selectedRole === 'expert'
              ? 'bg-[#7c3aed]/10 border-[#7c3aed] text-white'
              : 'bg-[#121418] border-[#282c37] text-gray-400 hover:border-gray-600'
          ]"
        >
          <span class="text-lg">🎛️</span>
          <div class="flex flex-col">
            <strong class="text-xs font-bold text-white">Accompagnant</strong>
            <small class="text-[10px] text-gray-400">Case à Chocs & Jury</small>
          </div>
        </button>
      </div>

      <!-- Avertissement de sécurité si Inscription Artiste -->
      <div v-else class="mb-4 p-2.5 rounded-lg bg-[#7c3aed]/10 border border-[#7c3aed]/20 text-[11px] text-gray-300 flex items-center gap-2">
        <span>ℹ️</span>
        <span>L'accès accompagnant / jury est attribué sur invitation de la Case à Chocs.</span>
      </div>

      <!-- Messages Flash -->
      <div v-if="errorMessage" class="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
        ⚠️ {{ errorMessage }}
      </div>
      <div v-if="successMessage" class="mb-4 p-3 rounded-lg bg-[#00ff88]/10 border border-[#00ff88]/30 text-[#00ff88] text-xs">
        ✓ {{ successMessage }}
      </div>

      <!-- Formulaire -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        
        <!-- Champs personnels (Mode Inscription uniquement) -->
        <template v-if="isRegisterMode">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-semibold text-gray-300 mb-1" for="prenom">Prénom</label>
              <input
                type="text"
                id="prenom"
                v-model="prenom"
                placeholder="Prenom"
                required
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#7c3aed]"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-300 mb-1" for="nom">Nom</label>
              <input
                type="text"
                id="nom"
                v-model="nom"
                placeholder="Nom"
                required
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#7c3aed]"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div>
              <label class="block text-xs font-semibold text-gray-300 mb-1" for="commune">Commune (NE)</label>
              <input
                type="text"
                id="commune"
                v-model="commune"
                placeholder="Neuchâtel"
                required
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-[#7c3aed]"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-300 mb-1" for="genrePers">Genre</label>
              <select
                id="genrePers"
                v-model="genre"
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-2 py-2 text-xs text-white focus:outline-none focus:border-[#7c3aed]"
              >
                <option value="Homme">Homme</option>
                <option value="Femme">Femme</option>
                <option value="Autre">Autre</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-300 mb-1" for="dateNaissance">Date de naissance</label>
              <input
                type="date"
                id="dateNaissance"
                v-model="dateNaissance"
                required
                class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-[#7c3aed]"
              />
            </div>
          </div>
        </template>

        <!-- Identifiants Communs -->
        <div>
          <label class="block text-xs font-semibold text-gray-300 mb-1.5" for="email">Adresse e-mail</label>
          <input
            type="email"
            id="email"
            v-model="email"
            :placeholder="selectedRole === 'artist' ? 'artiste@example.com' : 'gestionnaire@example.com'"
            required
            class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-[#7c3aed] transition-colors"
          />
        </div>

        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="block text-xs font-semibold text-gray-300" for="password">Mot de passe</label>
            <a v-if="!isRegisterMode" href="#" class="text-[11px] text-gray-400 hover:text-[#00ff88]">Mot de passe oublié ?</a>
          </div>
          <input
            type="password"
            id="password"
            v-model="password"
            placeholder="••••••••••••"
            required
            class="w-full bg-[#121418] border border-[#282c37] rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-[#7c3aed] transition-colors"
          />
        </div>

        <div v-if="!isRegisterMode" class="flex items-center text-xs text-gray-400">
          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input type="checkbox" v-model="rememberMe" class="rounded bg-[#121418] border-[#282c37] text-[#7c3aed] focus:ring-0" />
            Rester connecté
          </label>
        </div>

        <!-- Bouton Submit -->
        <button
          type="submit"
          :disabled="isLoading"
          class="w-full py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-bold text-sm rounded-lg transition-all shadow-lg shadow-[#7c3aed]/20 disabled:opacity-50 cursor-pointer"
        >
          <span v-if="!isLoading">
            {{ isRegisterMode 
              ? 'Créer mon compte artiste →'
              : `Se connecter en tant qu'${selectedRole === 'artist' ? 'Artiste' : 'Accompagnant'} →` }}
          </span>
          <span v-else>Traitement en cours...</span>
        </button>
      </form>

      <!-- Footer -->
      <footer class="mt-6 pt-4 border-t border-[#282c37] text-center space-y-3">
        <p class="text-xs text-gray-400">
          {{ isRegisterMode ? 'Déjà enregistré ?' : 'Nouveau projet musical émergent ?' }}
          <button 
            type="button" 
            @click="toggleMode" 
            class="font-bold underline ml-1 cursor-pointer text-[#00ff88] hover:text-[#00ff88]/80"
          >
            {{ isRegisterMode ? 'Se connecter' : 'Créer un profil artiste' }}
          </button>
        </p>

        <div>
          <span class="text-[11px] text-gray-500 block">Dispositif d'accompagnement :</span>
          <strong class="text-xs text-gray-400">Programme Embrayage · Case à Chocs</strong>
        </div>
      </footer>
    </div>
  </div>
</template>