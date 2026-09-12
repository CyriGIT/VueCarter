import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#0e0f12',     // Fond global de l'application
          surface: '#181a20',  // Conteneurs et cartes principales
          hover: '#22252e',    // Couleur au survol
          border: '#282c37',   // Lignes de séparation et bordures
          accent: '#7c3aed',   // Violet néo (actions principales)
          green: '#00ff88',    // Vert électrique (KPIs, succès, syncs actives)
        }
      }
    },
  },
  plugins: [],
} satisfies Config