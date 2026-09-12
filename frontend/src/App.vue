<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projectStore'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()
const isMobileMenuOpen = ref(false)

type AdminViewMode = 'admin' | 'expert' | 'accompagnant' | 'artiste'

const ADMIN_VIEW_MODE_KEY = 'admin_view_mode'
const storedAdminViewMode = localStorage.getItem(ADMIN_VIEW_MODE_KEY)
const adminViewMode = ref<AdminViewMode>(
  ['admin', 'expert', 'accompagnant', 'artiste'].includes(storedAdminViewMode ?? '')
    ? storedAdminViewMode as AdminViewMode
    : 'admin'
)

const isAuthPage = computed(() => route.path === '/login' || route.path === '/')
const userRole = ref(localStorage.getItem('user_role') || '')
const isAdmin = computed(() => userRole.value === 'admin')
const activeViewMode = computed(() => {
  if (isAdmin.value) return adminViewMode.value
  if (userRole.value === 'artiste') return 'artiste'
  if (userRole.value === 'accompagnant') return 'accompagnant'
  return 'expert'
})
const isAdminView = computed(() => isAdmin.value && activeViewMode.value === 'admin')
const isArtistView = computed(() => activeViewMode.value === 'artiste')
const isExpertView = computed(() => activeViewMode.value === 'expert')
const isAccompanyingView = computed(() => activeViewMode.value === 'accompagnant')
const canAccessExpertMode = computed(() => ['gestionnaire_case', 'expert_jury', 'accompagnant', 'admin'].includes(userRole.value))
const canAccessCohortViews = computed(() => ['gestionnaire_case', 'expert_jury', 'admin'].includes(userRole.value))
const canAccessAnalytics = computed(() => ['gestionnaire_case', 'expert_jury', 'accompagnant', 'admin'].includes(userRole.value))
const canAccessGrantDeadlines = computed(() => ['artiste', 'gestionnaire_case', 'admin'].includes(userRole.value))
const canManageEvaluationCriteria = computed(() => ['gestionnaire_case', 'admin'].includes(userRole.value))
const currentProject = computed(() => store.currentProject)
const profileName = computed(() => store.accountIdentity?.displayName ?? 'Utilisateur')
const profileInitials = computed(() => profileName.value.split(' ').map(name => name[0]).join('').slice(0, 2))
const profileContext = computed(() => {
  if (isAdmin.value) {
    return {
      admin: 'Vue administration',
      expert: 'Vue expert',
      accompagnant: 'Vue accompagnant',
      artiste: 'Vue artiste'
    }[adminViewMode.value]
  }
  if (userRole.value === 'gestionnaire_case') return 'Gestionnaire Case'
  if (userRole.value === 'expert_jury') return 'Jury Embrayage'
  if (userRole.value === 'accompagnant') return 'Accompagnant'
  return currentProject.value?.nom || 'Projet musical'
})

const handleAdminViewChange = () => {
  localStorage.setItem(ADMIN_VIEW_MODE_KEY, adminViewMode.value)
  isMobileMenuOpen.value = false

  const destinations: Record<AdminViewMode, string> = {
    admin: '/admin/dashboard',
    expert: '/expert/dashboard',
    accompagnant: '/expert/dashboard',
    artiste: '/artist/dashboard'
  }
  router.push(destinations[adminViewMode.value])
}

const loadAuthenticatedProfile = () => {
  userRole.value = localStorage.getItem('user_role') || ''
  if (!isAuthPage.value && localStorage.getItem('auth_token')) {
    store.fetchAccountIdentity()
    store.fetchProjects()
  }
}

onMounted(loadAuthenticatedProfile)
watch(() => route.path, loadAuthenticatedProfile)

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user_role')
  localStorage.removeItem(ADMIN_VIEW_MODE_KEY)
  store.resetAccountIdentity()
  userRole.value = ''
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen w-full flex flex-col bg-[#0e0f12] text-gray-100 font-sans antialiased">
    <!-- Header Principal Pleine Largeur -->
    <header class="w-full bg-[#181a20] border-b border-[#282c37] sticky top-0 z-50">
      <div class="w-full px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <!-- Logo & Titre Vue Carter -->
        <div class="flex items-center gap-6 lg:gap-10">
          <RouterLink to="/" class="flex items-center gap-3 text-white no-underline group">
            <div class="flex flex-col">
              <div class="flex items-center gap-2">
                <span class="font-extrabold tracking-wider text-base sm:text-lg text-white">VUE CARTER</span>
                <span class="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-[#282c37] text-[#00ff88]">
                  Case à Chocs
                </span>
              </div>
              <span class="text-[10px] tracking-widest uppercase text-gray-400 font-medium hidden sm:inline">
                Dispositif Embrayage · Musiques Actuelles
              </span>
            </div>
          </RouterLink>

          <!-- Navigation Desktop -->
          <nav v-if="!isAuthPage" class="hidden md:flex items-center gap-1 lg:gap-2">
            <RouterLink
              v-if="isAdminView"
              to="/admin/dashboard"
              class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
              active-class="!text-[#00ff88] !bg-[#00ff88]/10 border border-[#00ff88]/20"
            >Dashboard admin</RouterLink>
            <template v-if="isArtistView">
              <RouterLink
                to="/artist/dashboard"
                class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
                active-class="!text-[#00ff88] !bg-[#00ff88]/10 border border-[#00ff88]/20"
              >
                Dashboard & Profil
              </RouterLink>
              <RouterLink
                :to="currentProject ? `/artist/project/${currentProject.id}` : '/artist/dashboard'"
                class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
                active-class="!text-[#00ff88] !bg-[#00ff88]/10 border border-[#00ff88]/20"
              >
                Fiche Projet (Live & Assets)
              </RouterLink>
            </template>
            <template v-if="canAccessExpertMode && (isExpertView || isAccompanyingView)">
              <RouterLink
                to="/expert/dashboard"
                class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
                active-class="!text-[#7c3aed] !bg-[#7c3aed]/10 border border-[#7c3aed]/20"
              >
                Cockpit Évaluation
              </RouterLink>
              <RouterLink
                v-if="isExpertView && canAccessCohortViews"
                to="/expert/report"
                class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
                active-class="!text-[#7c3aed] !bg-[#7c3aed]/10 border border-[#7c3aed]/20"
              >
                Rapport de cohorte
              </RouterLink>
              <RouterLink
                v-if="canAccessAnalytics"
                to="/expert/analytics"
                class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
                active-class="!text-[#7c3aed] !bg-[#7c3aed]/10 border border-[#7c3aed]/20"
              >
                Analyses diachroniques
              </RouterLink>
            </template>
            <RouterLink
              v-if="!isAdmin && canManageEvaluationCriteria"
              to="/evaluation-campaigns"
              class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
              active-class="!text-[#00ff88] !bg-[#00ff88]/10 border border-[#00ff88]/20"
            >Campagnes</RouterLink>
            <RouterLink
              v-if="!isAdmin && canManageEvaluationCriteria"
              to="/evaluation-criteria"
              class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
              active-class="!text-[#00ff88] !bg-[#00ff88]/10 border border-[#00ff88]/20"
            >Critères de sélection</RouterLink>
            <RouterLink
              v-if="canAccessGrantDeadlines && (!isAdmin || isArtistView)"
              to="/grant-deadlines"
              class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-[#22252e] transition-colors"
              active-class="!text-[#00ff88] !bg-[#00ff88]/10 border border-[#00ff88]/20"
            >
              Aides & échéances
            </RouterLink>
          </nav>
        </div>

        <!-- Profil & Switch Vue (Desktop) -->
        <div class="hidden md:flex items-center gap-4">
          <template v-if="!isAuthPage">
            <label v-if="isAdmin" class="flex items-center gap-2">
              <span class="text-[10px] font-bold uppercase text-gray-500">Afficher</span>
              <select
                v-model="adminViewMode"
                class="h-9 min-w-44 rounded-md border border-[#343844] bg-[#121418] px-3 text-sm font-semibold text-gray-200 outline-none transition-colors hover:border-[#00ff88]/60 focus:border-[#00ff88]"
                aria-label="Choisir la vue administrateur"
                @change="handleAdminViewChange"
              >
                <option value="admin">Vue administration</option>
                <option value="expert">Vue expert</option>
                <option value="accompagnant">Vue accompagnant</option>
                <option value="artiste">Vue artiste</option>
              </select>
            </label>

            <div class="flex items-center gap-2.5 border-l border-[#282c37] pl-4">
              <div class="w-8 h-8 rounded-full bg-[#7c3aed] flex items-center justify-center font-bold text-xs text-white">
                {{ profileInitials }}
              </div>
              <div class="flex flex-col text-left">
                <span class="text-xs font-bold leading-tight">{{ profileName }}</span>
                <span class="text-[10px] text-gray-400 leading-tight">{{ profileContext }}</span>
              </div>
            </div>

            <button
              @click="handleLogout"
              class="text-xs px-2.5 py-1.5 text-gray-400 hover:text-rose-400 border border-[#282c37] hover:border-rose-500/40 rounded transition-colors"
            >
              Quitter
            </button>
          </template>
        </div>

        <!-- Bouton Burger Mobile -->
        <div class="flex md:hidden items-center gap-2">
          <button
            @click="isMobileMenuOpen = !isMobileMenuOpen"
            class="p-2 rounded-md text-gray-400 hover:text-white hover:bg-[#22252e] focus:outline-none"
          >
            <span class="text-xl">{{ isMobileMenuOpen ? '✕' : '☰' }}</span>
          </button>
        </div>
      </div>

      <!-- Menu Déroulant Mobile -->
      <div v-if="isMobileMenuOpen && !isAuthPage" class="md:hidden border-t border-[#282c37] bg-[#181a20] px-4 py-4 space-y-3">
        <label v-if="isAdmin" class="block border-b border-[#282c37] pb-4">
          <span class="mb-2 block text-[10px] font-bold uppercase text-gray-500">Choisir la vue</span>
          <select
            v-model="adminViewMode"
            class="h-11 w-full rounded-md border border-[#343844] bg-[#121418] px-3 text-sm font-semibold text-gray-200 outline-none focus:border-[#00ff88]"
            aria-label="Choisir la vue administrateur"
            @change="handleAdminViewChange"
          >
            <option value="admin">Vue administration</option>
            <option value="expert">Vue expert</option>
            <option value="accompagnant">Vue accompagnant</option>
            <option value="artiste">Vue artiste</option>
          </select>
        </label>
        <nav class="flex flex-col space-y-2">
          <RouterLink
            v-if="isAdminView"
            to="/admin/dashboard"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >Dashboard admin</RouterLink>
          <RouterLink
            v-if="isArtistView"
            to="/artist/dashboard"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >
            Dashboard Artiste
          </RouterLink>
          <RouterLink
            v-if="isArtistView && currentProject"
            :to="`/artist/project/${currentProject.id}`"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >
            Fiche Projet
          </RouterLink>
          <RouterLink
            v-if="canAccessExpertMode && (isExpertView || isAccompanyingView)"
            to="/expert/dashboard"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >
            Cockpit Expert
          </RouterLink>
          <RouterLink
            v-if="isExpertView && canAccessCohortViews"
            to="/expert/report"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >
            Rapport de cohorte
          </RouterLink>
          <RouterLink
            v-if="canAccessGrantDeadlines && (!isAdmin || isArtistView)"
            to="/grant-deadlines"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >
            Aides & échéances
          </RouterLink>
          <RouterLink
            v-if="!isAdmin && canManageEvaluationCriteria"
            to="/evaluation-campaigns"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >Campagnes</RouterLink>
          <RouterLink
            v-if="!isAdmin && canManageEvaluationCriteria"
            to="/evaluation-criteria"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >Critères de sélection</RouterLink>
          <RouterLink
            v-if="canAccessAnalytics && (isExpertView || isAccompanyingView)"
            to="/expert/analytics"
            @click="isMobileMenuOpen = false"
            class="px-3 py-2 rounded text-sm text-gray-200 hover:bg-[#22252e]"
          >
            Analyses diachroniques
          </RouterLink>
        </nav>
        <div class="pt-3 border-t border-[#282c37] flex items-center justify-between">
          <span class="text-xs text-gray-400">{{ profileName }}</span>
          <button @click="handleLogout" class="text-xs text-rose-400 font-semibold">Se déconnecter</button>
        </div>
      </div>
    </header>

    <!-- Zone Principale 100% Largeur -->
    <main class="w-full flex-1 min-h-0">
      <RouterView />
    </main>
  </div>
</template>