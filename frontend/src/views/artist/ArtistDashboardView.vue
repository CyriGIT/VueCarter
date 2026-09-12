<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useProjectStore } from '@/stores/projectStore'

const store = useProjectStore()

const artistProfile = computed(() => store.userProfile)
const projects = computed(() => store.projects)
const programmesPrecedents = computed(() => store.currentProject?.programmesPrecedents ?? [])

// Édition de la fiche personnelle de l'utilisateur connecté (table "Personne")
const isEditingProfile = ref(false)
const isSavingProfile = ref(false)
const profileFormError = ref<string | null>(null)
const profileForm = reactive({
  nom: '',
  prenom: '',
  dateNaissance: '',
  genre: 'Homme',
  adresse: '',
  npa: '',
  ville: '',
  canton: '',
  telephone: '',
  email: ''
})

function startEditProfile() {
  const profile = store.userProfile
  if (!profile) return
  profileFormError.value = null
  profileForm.nom = profile.nom
  profileForm.prenom = profile.prenom
  profileForm.dateNaissance = profile.dateNaissance
  profileForm.genre = profile.genre
  profileForm.adresse = profile.adresse || ''
  profileForm.npa = profile.npa || ''
  profileForm.ville = profile.ville || ''
  profileForm.canton = profile.canton || ''
  profileForm.telephone = profile.telephone
  profileForm.email = profile.email
  isEditingProfile.value = true
}

function cancelEditProfile() {
  isEditingProfile.value = false
  profileFormError.value = null
}

async function saveProfile() {
  isSavingProfile.value = true
  profileFormError.value = null
  const success = await store.updateUserProfile({ ...profileForm })
  isSavingProfile.value = false
  if (success) {
    isEditingProfile.value = false
  } else {
    profileFormError.value = store.errorMessage || 'Erreur lors de la mise à jour du profil.'
  }
}

onMounted(async () => {
  const userRole = localStorage.getItem('user_role')
  await Promise.all([
    store.fetchProjects(),
    ...(userRole === 'artiste' ? [store.fetchUserProfile()] : []),
    store.fetchLegalStatuses()
  ])
  if (store.projects.length === 0 && !store.errorMessage) {
    showNewProjectForm.value = true
  }
})

// Création d'un nouveau projet musical
const showNewProjectForm = ref(false)
const isCreatingProject = ref(false)
const newProjectError = ref<string | null>(null)
const newProjectForm = reactive({
  nom: '',
  dateCreation: '',
  langueChant: 'Français',
  statutJuridiqueId: 0,
  bioCourte: ''
})

function toggleNewProjectForm() {
  newProjectError.value = null
  showNewProjectForm.value = !showNewProjectForm.value
}

async function createProject() {
  isCreatingProject.value = true
  newProjectError.value = null
  const success = await store.createProject({
    ...newProjectForm,
    dateCreation: newProjectForm.dateCreation || undefined
  })
  isCreatingProject.value = false
  if (success) {
    showNewProjectForm.value = false
    newProjectForm.nom = ''
    newProjectForm.dateCreation = ''
    newProjectForm.langueChant = 'Français'
    newProjectForm.statutJuridiqueId = store.legalStatuses[0]?.id || 0
    newProjectForm.bioCourte = ''
  } else {
    newProjectError.value = store.errorMessage || 'Erreur lors de la création du projet.'
  }
}

// Suppression d'un projet musical, avec popup de confirmation
const projectPendingDeletion = ref<typeof store.projects[number] | null>(null)
const isDeletingProject = ref(false)
const deleteProjectError = ref<string | null>(null)

function askDeleteProject(project: typeof store.projects[number]) {
  projectPendingDeletion.value = project
  deleteProjectError.value = null
}

function cancelDeleteProject() {
  projectPendingDeletion.value = null
  deleteProjectError.value = null
}

async function confirmDeleteProject() {
  if (!projectPendingDeletion.value) return
  isDeletingProject.value = true
  deleteProjectError.value = null
  const success = await store.deleteProject(projectPendingDeletion.value.id)
  isDeletingProject.value = false
  if (success) {
    projectPendingDeletion.value = null
  } else {
    deleteProjectError.value = store.errorMessage || 'Erreur lors de la suppression du projet.'
  }
}

const getConcertStats = (project: typeof store.projects[number]) => ({
  local: project.concerts?.filter(concert => concert.type === 'Local (NE)').length ?? 0,
  horsCanton: project.concerts?.filter(concert => concert.type === 'Hors-Canton').length ?? 0,
  export: project.concerts?.filter(concert => concert.type === 'Export').length ?? 0
})

const getTopTrackStreams = (project: typeof store.projects[number]) => {
  const topTrack = project.tracks?.find(track => track.streamsCount)
  return topTrack ? `${topTrack.streamsCount} (${topTrack.titre})` : 'N/A'
}

const calculateAge = (date: string) => {
  const diff = Date.now() - new Date(date).getTime()
  return Math.abs(new Date(diff).getUTCFullYear() - 1970)
}
</script>

<template>
  <div class="min-h-full w-full px-4 sm:px-6 lg:px-10 py-6 sm:py-8 space-y-6 sm:space-y-8">
    <div v-if="store.isLoading" class="text-sm text-gray-400">
      Chargement des données...
    </div>
    <div v-else-if="store.errorMessage" class="text-sm text-red-400">
      {{ store.errorMessage }}
    </div>

    <!-- Header Titre de Page -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
          Espace Artiste · <span class="text-[#00ff88]">Vue Carter</span>
        </h1>
        <p class="text-sm sm:text-base text-gray-400 mt-1">
          Gestion de profil, centralisation des tournées, synchronisation API et génération de fiches vitrines.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="toggleNewProjectForm"
          class="w-full sm:w-auto px-4 py-2 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-sm font-bold rounded-lg transition-all shadow-lg shadow-[#7c3aed]/20 cursor-pointer"
        >
          + Nouveau Projet Musical
        </button>
      </div>
    </div>

    <!-- Formulaire de création d'un nouveau projet musical -->
    <form
      v-if="showNewProjectForm"
      @submit.prevent="createProject"
      class="bg-[#181a20] border border-[#282c37] rounded-xl p-5 sm:p-6 space-y-3"
    >
      <h2 class="text-base font-bold text-white">Nouveau projet musical</h2>
      <div v-if="newProjectError" class="text-xs text-red-400">{{ newProjectError }}</div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label class="block">
          <span class="text-xs text-gray-400">Nom du projet</span>
          <input v-model="newProjectForm.nom" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
        </label>
        <label class="block">
          <span class="text-xs text-gray-400">Date de création</span>
          <input v-model="newProjectForm.dateCreation" type="date" class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
        </label>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label class="block">
          <span class="text-xs text-gray-400">Langue de chant</span>
          <input v-model="newProjectForm.langueChant" class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
        </label>
        <label class="block">
          <span class="text-xs text-gray-400">Statut juridique</span>
          <select v-model="newProjectForm.statutJuridiqueId" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]">
            <option :value="0" disabled>Sélectionner</option>
            <option v-for="status in store.legalStatuses" :key="status.id" :value="status.id">{{ status.libelle }}</option>
          </select>
        </label>
      </div>
      <label class="block">
        <span class="text-xs text-gray-400">Bio courte</span>
        <textarea v-model="newProjectForm.bioCourte" rows="2" class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]"></textarea>
      </label>
      <div class="flex items-center justify-end gap-2 pt-1">
        <button type="button" @click="showNewProjectForm = false" class="px-3 py-1.5 text-xs font-bold rounded-lg border border-[#282c37] text-gray-300 hover:bg-white/5 transition-colors">
          Annuler
        </button>
        <button type="submit" :disabled="isCreatingProject || !newProjectForm.nom.trim()" class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#7c3aed] hover:bg-[#6d28d9] text-white transition-colors disabled:opacity-50">
          {{ isCreatingProject ? 'Création...' : 'Créer le projet' }}
        </button>
      </div>
    </form>

    <!-- Grille Principale Responsive (1 col sur mobile, 3 cols sur Desktop) -->
    <div class="w-full grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Colonne 1 : Fiche Profil & Démographie (Statistiques cantonales) -->
      <section v-if="artistProfile" class="lg:col-span-1 bg-[#181a20] border border-[#282c37] rounded-xl p-5 sm:p-6 space-y-6">
        <div class="flex items-center gap-4">
          <div class="w-16 h-16 sm:w-20 sm:h-20 rounded-full border-2 border-[#7c3aed] p-1 bg-[#121418] shrink-0">
            <div class="w-full h-full rounded-full bg-linear-to-tr from-[#7c3aed] to-[#00ff88] flex items-center justify-center font-black text-xl text-black">
              {{ artistProfile.prenom[0] }}{{ artistProfile.nom[0] }}
            </div>
          </div>
          <div class="overflow-hidden flex-1">
            <h2 class="text-lg sm:text-xl font-bold truncate text-white">
              {{ artistProfile.prenom }} {{ artistProfile.nom }}
            </h2>
          </div>
          <button
            v-if="!isEditingProfile"
            @click="startEditProfile"
            class="shrink-0 text-[10px] uppercase font-bold px-2.5 py-1.5 rounded-lg border border-[#282c37] text-gray-300 hover:border-[#7c3aed] hover:text-[#7c3aed] transition-colors"
          >
            Modifier
          </button>
        </div>

        <!-- Formulaire d'édition de la fiche personnelle -->
        <form v-if="isEditingProfile" @submit.prevent="saveProfile" class="space-y-3 pt-4 border-t border-[#282c37] text-sm">
          <div v-if="profileFormError" class="text-xs text-red-400">{{ profileFormError }}</div>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-xs text-gray-400">Nom</span>
              <input v-model="profileForm.nom" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
            </label>
            <label class="block">
              <span class="text-xs text-gray-400">Prénom</span>
              <input v-model="profileForm.prenom" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
            </label>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-xs text-gray-400">Date de naissance</span>
              <input v-model="profileForm.dateNaissance" type="date" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
            </label>
            <label class="block">
              <span class="text-xs text-gray-400">Genre</span>
              <select v-model="profileForm.genre" class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]">
                <option value="Homme">Homme</option>
                <option value="Femme">Femme</option>
                <option value="Autre">Autre</option>
              </select>
            </label>
          </div>
          <label class="block">
            <span class="text-xs text-gray-400">Adresse</span>
            <input v-model="profileForm.adresse" class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
          </label>
          <div class="grid grid-cols-3 gap-3">
            <label class="block">
              <span class="text-xs text-gray-400">NPA</span>
              <input v-model="profileForm.npa" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
            </label>
            <label class="block col-span-2">
              <span class="text-xs text-gray-400">Ville</span>
              <input v-model="profileForm.ville" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
            </label>
          </div>
          <label class="block">
            <span class="text-xs text-gray-400">Canton</span>
            <input v-model="profileForm.canton" class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-xs text-gray-400">Téléphone</span>
              <input v-model="profileForm.telephone" class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
            </label>
            <label class="block">
              <span class="text-xs text-gray-400">Email</span>
              <input v-model="profileForm.email" type="email" required class="mt-1 w-full bg-[#121418] border border-[#282c37] rounded-lg px-2.5 py-1.5 text-gray-100 text-sm focus:outline-none focus:border-[#7c3aed]" />
            </label>
          </div>
          <div class="flex items-center justify-end gap-2 pt-1">
            <button type="button" @click="cancelEditProfile" class="px-3 py-1.5 text-xs font-bold rounded-lg border border-[#282c37] text-gray-300 hover:bg-white/5 transition-colors">
              Annuler
            </button>
            <button type="submit" :disabled="isSavingProfile" class="px-3 py-1.5 text-xs font-bold rounded-lg bg-[#7c3aed] hover:bg-[#6d28d9] text-white transition-colors disabled:opacity-50">
              {{ isSavingProfile ? 'Enregistrement...' : 'Enregistrer' }}
            </button>
          </div>
        </form>

        <!-- Fiche personnelle (données de contact) -->
        <div v-else class="space-y-3 pt-4 border-t border-[#282c37] text-sm">
          <div class="flex justify-between py-1 border-b border-[#282c37]/60">
            <span class="text-gray-400">Genre & Âge</span>
            <span class="font-semibold text-gray-200">{{ artistProfile.genre }} · {{ calculateAge(artistProfile.dateNaissance) }} ans</span>
          </div>
          <div class="flex justify-between items-start py-1 border-b border-[#282c37]/60">
            <span class="text-gray-400">Adresse</span>
            <span class="font-semibold text-gray-200 text-right">
              <span class="block">{{ artistProfile.adresse || '—' }}</span>
              <span class="block">{{ artistProfile.npa }} {{ artistProfile.ville }}</span>
            </span>
          </div>
          <div class="flex justify-between py-1 border-b border-[#282c37]/60">
            <span class="text-gray-400">Téléphone</span>
            <span class="font-semibold text-gray-200">{{ artistProfile.telephone }}</span>
          </div>
          <div class="flex justify-between py-1 border-b border-[#282c37]/60">
            <span class="text-gray-400">Email</span>
            <span class="font-semibold text-gray-200 truncate">{{ artistProfile.email }}</span>
          </div>
        </div>

        <!-- Formations & Parcours -->
        <div v-if="!isEditingProfile" class="space-y-2">
          <h3 class="text-xs uppercase tracking-wider text-gray-400 font-bold">Programmes & Formations</h3>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="program in programmesPrecedents" :key="`${program.programmeId}-${program.anneeParticipation}`" class="text-xs px-2 py-1 bg-[#22252e] border border-[#282c37] rounded text-gray-300">
              ★ {{ program.nom }} · {{ program.anneeParticipation }}
            </span>
          </div>
        </div>
      </section>

      <!-- Colonne 2 & 3 : Connecteurs API & Projets Actifs -->
      <div class="lg:col-span-2 space-y-6">

        <!-- Liste des Projets Musicaux (Cartes type Agence Roster) -->
        <section class="space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-lg sm:text-xl font-bold text-white">Projets Musicaux Actifs</h2>
            <span class="text-xs text-gray-400">{{ projects.length }} projet(s) en gestion</span>
          </div>

          <div v-if="projects.length === 0" class="border border-[#282c37] bg-[#181a20] rounded-xl p-6 text-center">
            <h3 class="text-base font-bold text-white">Créez votre premier projet musical</h3>
            <p class="mt-1 text-sm text-gray-400">Votre profil personnel est prêt. Le projet créé ici vous sera automatiquement rattaché.</p>
          </div>

          <div v-for="prj in projects" :key="prj.id" class="bg-[#181a20] border border-[#282c37] hover:border-[#7c3aed]/50 transition-all rounded-xl p-5 sm:p-6 space-y-5">
            <div class="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="text-xl font-extrabold text-white">{{ prj.nom }}</h3>
                  <span class="text-xs px-2 py-0.5 rounded bg-[#22252e] text-gray-300 font-medium border border-[#282c37]">
                    {{ prj.genreMusical }}
                  </span>
                  <span class="text-xs px-2 py-0.5 rounded bg-[#22252e] text-gray-400 font-medium">
                    Chant : {{ prj.langueChant }}
                  </span>
                </div>
                <p class="text-sm text-gray-300 mt-2 line-clamp-2 leading-relaxed">
                  {{ prj.bioCourte }}
                </p>
              </div>

              <!-- Jauge de complétion Fiche Roster -->
              <div class="w-full md:w-44 shrink-0 bg-[#121418] p-3 rounded-lg border border-[#282c37] text-left">
                <div class="flex justify-between text-xs mb-1">
                  <span class="text-gray-400">Presskit / Roster</span>
                  <span class="font-bold text-[#00ff88]">{{ prj.readinessScore }}%</span>
                </div>
                <div class="w-full bg-[#282c37] h-2 rounded-full overflow-hidden">
                  <div class="bg-linear-to-r from-[#7c3aed] to-[#00ff88] h-full" :style="{ width: prj.readinessScore + '%' }"></div>
                </div>
              </div>
            </div>

            <!-- Indicateurs Clés Métiers (Concerts, Résidences, Streams) -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 py-3 border-y border-[#282c37] text-center sm:text-left">
              <div>
                <span class="text-xs text-gray-400 block">Concerts (NE / CH / Export)</span>
                <span class="text-sm sm:text-base font-extrabold text-white">
                  {{ getConcertStats(prj).local }} / {{ getConcertStats(prj).horsCanton }} / <span class="text-[#00ff88]">{{ getConcertStats(prj).export }}</span>
                </span>
              </div>
              <div>
                <span class="text-xs text-gray-400 block">Résidences</span>
                <span class="text-sm sm:text-base font-extrabold text-white">{{ prj.residencesCount }} effectuées</span>
              </div>
              <div>
                <span class="text-xs text-gray-400 block">Top Track Stream</span>
                <span class="text-sm sm:text-base font-extrabold text-[#00ff88]">{{ getTopTrackStreams(prj) }}</span>
              </div>
              <div>
                <span class="text-xs text-gray-400 block">Followers Insta</span>
                <span class="text-sm sm:text-base font-extrabold text-white">{{ prj.instaFollowers }}</span>
              </div>
            </div>

            <!-- Actions Projets -->
            <div class="flex flex-col sm:flex-row items-center justify-end gap-3 pt-1">
              <RouterLink
                :to="`/artist/project/${prj.id}`"
                class="w-full sm:w-auto px-4 py-2 bg-[#22252e] hover:bg-[#282c37] border border-[#282c37] text-white text-xs font-bold rounded-lg text-center transition-colors"
              >
                Gérer morceaux, assets & timeline live →
              </RouterLink>
              <a
                href="#"
                class="w-full sm:w-auto px-4 py-2 bg-transparent hover:bg-white/5 border border-[#7c3aed] text-[#7c3aed] hover:text-white text-xs font-bold rounded-lg text-center transition-colors"
              >
                Exporter Fiche Vitrine (Roster) ↗
              </a>
              <button
                @click="askDeleteProject(prj)"
                class="w-full sm:w-auto px-4 py-2 bg-transparent hover:bg-rose-500/10 border border-rose-500/40 text-rose-400 hover:text-rose-300 text-xs font-bold rounded-lg text-center transition-colors cursor-pointer"
              >
                Supprimer le projet
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- Popup de confirmation de suppression -->
    <div
      v-if="projectPendingDeletion"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
    >
      <div class="w-full max-w-sm bg-[#181a20] border border-[#282c37] rounded-xl p-5 space-y-4">
        <h3 class="text-base font-bold text-white">Supprimer ce projet ?</h3>
        <p class="text-sm text-gray-400">
          Cette action supprimera définitivement « {{ projectPendingDeletion.nom }} » ainsi que tous ses morceaux, assets, concerts et données associées. Cette action est irréversible.
        </p>
        <div v-if="deleteProjectError" class="text-xs text-red-400">{{ deleteProjectError }}</div>
        <div class="flex items-center justify-end gap-2">
          <button
            @click="cancelDeleteProject"
            class="px-3 py-1.5 text-xs font-bold rounded-lg border border-[#282c37] text-gray-300 hover:bg-white/5 transition-colors cursor-pointer"
          >
            Annuler
          </button>
          <button
            @click="confirmDeleteProject"
            :disabled="isDeletingProject"
            class="px-3 py-1.5 text-xs font-bold rounded-lg bg-rose-600 hover:bg-rose-700 text-white transition-colors disabled:opacity-50 cursor-pointer"
          >
            {{ isDeletingProject ? 'Suppression...' : 'Supprimer définitivement' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>