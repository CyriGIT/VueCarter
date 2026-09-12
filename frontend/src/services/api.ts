// Client HTTP partagé du frontend.
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  response => response,
  error => {
    const isAuthenticationRequest = error.config?.url?.startsWith('/auth/')

    if (error.response?.status === 401 && !isAuthenticationRequest) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_role')

      if (window.location.pathname !== '/login') {
        window.location.assign('/login?reason=session_expired')
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient