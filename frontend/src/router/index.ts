import { createRouter, createWebHistory } from 'vue-router'
import { jwtDecode } from 'jwt-decode'
import ProjectDetailView from '@/views/artist/ProjectDetailView.vue'
import ExportRosterView from '@/views/artist/ExportRosterView.vue'
import EvaluationCockpitView from '@/views/expert/EvaluationCockpitView.vue'

interface JwtPayload {
  sub: string
  role: 'artiste' | 'gestionnaire_case' | 'expert_jury' | 'accompagnant' | 'admin'
  exp: number
}

const routes = [
  {
    path: '/',
    name: 'home',
    redirect: () => {
      const token = localStorage.getItem('auth_token')
      if (token) {
        const decoded: JwtPayload = jwtDecode(token)
        return decoded.role === 'artiste' ? '/artist/dashboard' : decoded.role === 'admin' ? '/admin/dashboard' : '/expert/dashboard'
      }
      return '/login'
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue')
  },
  {
    path: '/invite',
    name: 'AcceptInvitation',
    component: () => import('@/views/auth/AcceptInvitationView.vue')
  },
  {
    path: '/artist/dashboard',
    name: 'ArtistDashboard',
    component: () => import('@/views/artist/ArtistDashboardView.vue'),
    meta: { requiresAuth: true, requiredRoles: ['artiste', 'admin'] }
  },
  {
    path: '/artist/project/:id',
    name: 'ProjectDetail',
    component:  () => import('@/views/artist/ProjectDetailView.vue'),
    meta: { requiresAuth: true, requiredRoles: ['artiste', 'admin'] }
  },
  {
    path: '/artist/project/:id/export',
    name: 'ExportRoster',
    component: () => import('@/views/artist/ExportRosterView.vue'),
    props: true,
    meta: { requiresAuth: true, requiredRoles: ['artiste', 'admin'] }
  },
  {
    path: '/projects/:id/roster',
    name: 'ProjectRoster',
    component: () => import('@/views/artist/ExportRosterView.vue'),
    props: true,
    meta: { requiresAuth: true, requiredRoles: ['artiste', 'gestionnaire_case', 'expert_jury', 'accompagnant', 'admin'] }
  },
  {
    path: '/expert/dashboard',
    name: 'ExpertDashboard',
    component: () => import('@/views/expert/EvaluationCockpitView.vue'),
    meta: { requiresAuth: true, requiredRoles: ['gestionnaire_case', 'expert_jury', 'accompagnant', 'admin'] }
  },
    {
    path: '/expert/report',
    name: 'ExpertReport',
    component: () => import('@/views/expert/CohortReportView.vue'),
    meta: { requiresAuth: true, requiredRoles: ['gestionnaire_case', 'expert_jury', 'admin'] }
  },
  {
    path: '/expert/analytics',
    name: 'ExpertAnalytics',
    component: () => import('@/views/expert/ExpertAnalyticsView.vue'),
    meta: { requiresAuth: true, requiredRoles: ['gestionnaire_case', 'expert_jury', 'accompagnant', 'admin'] }
  },
  {
    path: '/admin/dashboard',
    name: 'AdminDashboard',
    component: () => import('@/views/admin/AdminDashboardView.vue'),
    meta: { requiresAuth: true, requiredRole: 'admin' }
  },
  {
    path: '/grant-deadlines',
    name: 'GrantDeadlines',
    component: () => import('@/views/common/GrantDeadlinesView.vue'),
    meta: { requiresAuth: true, requiredRoles: ['artiste', 'gestionnaire_case', 'admin'] }
  },
  {
    path: '/evaluation-campaigns',
    name: 'EvaluationCampaigns',
    component: () => import('@/views/common/EvaluationCampaignsView.vue'),
    meta: { requiresAuth: true, requiredRoles: ['gestionnaire_case', 'admin'] }
  },
  {
    path: '/evaluation-criteria',
    name: 'EvaluationCriteria',
    component: () => import('@/views/common/EvaluationCriteriaView.vue'),
    meta: { requiresAuth: true, requiredRoles: ['gestionnaire_case', 'admin'] }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token')

  if (to.meta.requiresAuth) {
    if (!token) {
      return next({ name: 'Login' })
    }

    try {
      const decoded: JwtPayload = jwtDecode(token)
      const now = Date.now() / 1000

      // Vérification de l'expiration du token
      if (decoded.exp < now) {
        localStorage.removeItem('auth_token')
        return next({ name: 'Login' })
      }

      // Vérification du rôle requis pour la page
      const requiredRoles = to.meta.requiredRoles as string[] | undefined
      const hasRequiredRole = requiredRoles
        ? requiredRoles.includes(decoded.role)
        : !to.meta.requiredRole || decoded.role === to.meta.requiredRole

      if (!hasRequiredRole && decoded.role !== 'admin') {
        // Redirection vers son propre dashboard en cas de rôle non autorisé
        return next(decoded.role === 'artiste' ? '/artist/dashboard' : '/expert/dashboard')
      }

      next()
    } catch {
      localStorage.removeItem('auth_token')
      next({ name: 'Login' })
    }
  } else {
    next()
  }
})

export default router
