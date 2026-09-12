<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useAdminStore } from '@/stores/adminStore'
import type { AdminItem, AdminResourceKey, ExpertAdmin, ExpertForm } from '@/types/admin'

const store = useAdminStore()
const section = ref<'accounts' | 'project' | 'styles' | 'distribution'>('accounts')
const resource = ref<AdminResourceKey>('legal-statuses')
const search = ref('')
const stateFilter = ref<'all' | 'active' | 'inactive'>('all')
const itemDialog = ref(false)
const expertDialog = ref(false)
const editingItem = ref<AdminItem | null>(null)
const editingExpert = ref<ExpertAdmin | null>(null)
const feedback = ref('')
const invitationUrl = ref('')
const itemForm = reactive<Record<string, any>>({})
const expertForm = reactive<ExpertForm & { estActif: boolean }>({
    prenom: '', nom: '', email: '', role: 'expert_jury', dateNaissance: '', genre: 'Autre',
    npa: '', ville: '', telephone: '', estActif: true
})

const sections = [
    { id: 'accounts' as const, label: 'Comptes' }, { id: 'project' as const, label: 'Projet' },
    { id: 'styles' as const, label: 'Styles' }, { id: 'distribution' as const, label: 'Diffusion' }
]
const meta: Record<AdminResourceKey, { label: string; singular: string; section: string }> = {
    'legal-statuses': { label: 'Statuts juridiques', singular: 'statut juridique', section: 'project' },
    'phase-types': { label: 'Phases', singular: 'phase', section: 'project' },
    styles: { label: 'Styles musicaux', singular: 'style', section: 'styles' },
    programs: { label: 'Programmes', singular: 'programme', section: 'project' },
    formations: { label: 'Formations', singular: 'formation', section: 'project' },
    'professional-structures': { label: 'Structures', singular: 'structure', section: 'project' },
    venues: { label: 'Salles et festivals', singular: 'salle', section: 'distribution' },
    platforms: { label: 'Plateformes', singular: 'plateforme', section: 'distribution' }
}
const sectionResources = computed(() => Object.entries(meta)
    .filter(([, value]) => value.section === section.value)
    .map(([key, value]) => ({ key: key as AdminResourceKey, ...value })))
const filteredItems = computed(() => store.resources[resource.value].filter(item => {
    const text = [item.libelle, item.nom, item.organisme, item.type, item.ville, item.pays].filter(Boolean).join(' ').toLowerCase()
    return text.includes(search.value.toLowerCase()) && (stateFilter.value === 'all' || item.estActif === (stateFilter.value === 'active'))
}))
const filteredExperts = computed(() => store.experts.filter(expert => {
    const matches = `${expert.prenom} ${expert.nom} ${expert.email} ${expert.role}`.toLowerCase().includes(search.value.toLowerCase())
    return matches && (stateFilter.value === 'all' || (stateFilter.value === 'active' ? expert.statut === 'active' : expert.statut !== 'active'))
}))
const expertRoleLabel = (role: ExpertAdmin['role']) => ({
    expert_jury: 'Expert jury',
    gestionnaire_case: 'Gestionnaire Case',
    accompagnant: 'Accompagnant'
})[role]

function chooseSection(value: typeof section.value) {
    section.value = value
    search.value = ''
    const first = Object.entries(meta).find(([, entry]) => entry.section === value)
    if (first) resource.value = first[0] as AdminResourceKey
}
function showItem(item?: AdminItem) {
    editingItem.value = item || null
    Object.keys(itemForm).forEach(key => delete itemForm[key])
    Object.assign(itemForm, item || { estActif: true })
    if (resource.value === 'professional-structures') { itemForm.type ||= 'Label'; itemForm.pays ||= 'Suisse' }
    if (resource.value === 'venues') { itemForm.pays ||= 'Suisse'; itemForm.jauge ??= 0; itemForm.estFestival ??= false }
    itemDialog.value = true
}
async function saveItem() {
    const result = editingItem.value
        ? await store.updateItem(resource.value, editingItem.value.id, { ...itemForm })
        : await store.createItem(resource.value, { ...itemForm })
    if (result) { itemDialog.value = false; feedback.value = 'Modification enregistrée.' }
}
async function toggleItem(item: AdminItem) {
    if (!confirm(`Confirmer ${item.estActif ? 'la désactivation' : 'la réactivation'} ?`)) return
    if (await store.updateItem(resource.value, item.id, { ...item, estActif: !item.estActif })) feedback.value = 'État mis à jour.'
}
function showExpert(expert?: ExpertAdmin) {
    editingExpert.value = expert || null
    Object.assign(expertForm, expert ? { ...expert, estActif: expert.statut === 'active' } : {
        prenom: '', nom: '', email: '', role: 'expert_jury', dateNaissance: '', genre: 'Autre',
        npa: '', ville: '', telephone: '', estActif: true
    })
    invitationUrl.value = ''
    expertDialog.value = true
}
async function saveExpert() {
    if (editingExpert.value) {
        if (await store.updateExpert(editingExpert.value.id, { ...expertForm })) { expertDialog.value = false; feedback.value = 'Compte enregistré.' }
    } else {
        const url = await store.inviteExpert({ ...expertForm })
        if (url) invitationUrl.value = new URL(url, location.origin).toString()
    }
}
async function copyInvitation(expert?: ExpertAdmin) {
    const url = expert ? await store.renewInvitation(expert.id, expert.role) : invitationUrl.value
    if (!url) return
    const absoluteUrl = new URL(url, location.origin).toString()
    await navigator.clipboard.writeText(absoluteUrl)
    feedback.value = 'Lien d’invitation copié.'
}
function title(item: AdminItem) { return item.libelle || item.nom || `Entrée ${item.id}` }
function detail(item: AdminItem) {
    if (resource.value === 'styles' && item.parentId) return `Parent: ${store.resources.styles.find(style => style.id === item.parentId)?.nom || item.parentId}`
    return [item.organisme, item.type, item.ville, item.pays].filter(Boolean).join(' · ')
}
onMounted(store.fetchAll)
</script>

<template>
    <div class="min-h-full bg-[#0e0f12] text-gray-100">
        <header class="border-b border-[#282c37] bg-[#15171c] px-4 py-5 sm:px-8">
            <div class="mx-auto flex max-w-375 flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div><p class="text-xs font-bold uppercase text-[#00ff88]">Administration</p><h1 class="mt-1 text-2xl font-black sm:text-3xl">Référentiels et accès</h1><p class="mt-1 text-sm text-gray-400">{{ store.activeTotal }} entrées actives · {{ store.experts.length }} accompagnants</p></div>
                <nav class="flex flex-wrap gap-2"><button v-for="tab in sections" :key="tab.id" class="border px-3 py-2 text-sm font-semibold" :class="section === tab.id ? 'border-[#00ff88] bg-[#00ff88]/10 text-[#00ff88]' : 'border-[#343845] text-gray-300'" @click="chooseSection(tab.id)">{{ tab.label }}</button></nav>
            </div>
        </header>
        <main class="mx-auto max-w-375 px-4 py-6 sm:px-8">
            <p v-if="store.errorMessage" class="mb-4 border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{{ store.errorMessage }}</p>
            <p v-if="feedback" class="mb-4 border border-[#00ff88]/30 bg-[#00ff88]/10 px-4 py-3 text-sm text-[#00ff88]">{{ feedback }}</p>
            <p v-if="store.isLoading" class="py-20 text-center text-gray-400">Chargement...</p>
            <template v-else>
                <div v-if="section !== 'accounts'" class="mb-5 flex gap-2 overflow-x-auto border-b border-[#282c37] pb-3"><button v-for="entry in sectionResources" :key="entry.key" class="whitespace-nowrap px-3 py-1.5 text-sm font-semibold" :class="resource === entry.key ? 'bg-white text-black' : 'text-gray-400'" @click="resource = entry.key">{{ entry.label }}</button></div>
                <div class="mb-4 flex flex-col gap-3 sm:flex-row"><input v-model="search" type="search" placeholder="Rechercher" class="field flex-1" /><select v-model="stateFilter" class="field sm:w-40"><option value="all">Tous les états</option><option value="active">Actifs</option><option value="inactive">Inactifs</option></select><button class="bg-[#00ff88] px-4 py-2 text-sm font-black text-black" @click="section === 'accounts' ? showExpert() : showItem()">{{ section === 'accounts' ? 'Inviter un accompagnant' : `Ajouter ${meta[resource].singular}` }}</button></div>
                <div class="overflow-x-auto border border-[#282c37] bg-[#15171c]"><table class="w-full min-w-170 text-left text-sm"><thead class="border-b border-[#343845] bg-[#1d2027] text-xs uppercase text-gray-400"><tr><th class="px-4 py-3">Nom</th><th class="px-4 py-3">Détail</th><th class="px-4 py-3">État</th><th class="px-4 py-3 text-right">Actions</th></tr></thead>
                    <tbody v-if="section === 'accounts'"><tr v-for="expert in filteredExperts" :key="expert.id" class="border-b border-[#282c37]"><td class="px-4 py-3"><strong class="block">{{ expert.prenom }} {{ expert.nom }}</strong><span class="text-xs text-gray-400">{{ expert.email }}</span></td><td class="px-4 py-3">{{ expertRoleLabel(expert.role) }}</td><td class="px-4 py-3"><span class="state">{{ expert.statut === 'pending' ? 'Invitation en attente' : expert.statut === 'active' ? 'Actif' : 'Inactif' }}</span></td><td class="px-4 py-3 text-right"><button v-if="expert.statut === 'pending'" class="mr-3 text-xs font-bold text-amber-300" @click="copyInvitation(expert)">Copier le lien</button><button class="text-xs font-bold text-[#00ff88]" @click="showExpert(expert)">Modifier</button></td></tr></tbody>
                    <tbody v-else><tr v-for="item in filteredItems" :key="item.id" class="border-b border-[#282c37]"><td class="px-4 py-3 font-bold">{{ title(item) }}</td><td class="px-4 py-3 text-gray-400">{{ detail(item) || '—' }}</td><td class="px-4 py-3"><span class="state">{{ item.estActif ? 'Actif' : 'Inactif' }}</span></td><td class="px-4 py-3 text-right"><button class="mr-3 text-xs font-bold text-gray-300" @click="toggleItem(item)">{{ item.estActif ? 'Désactiver' : 'Réactiver' }}</button><button class="text-xs font-bold text-[#00ff88]" @click="showItem(item)">Modifier</button></td></tr></tbody></table>
                    <p v-if="section === 'accounts' ? !filteredExperts.length : !filteredItems.length" class="py-10 text-center text-sm text-gray-500">Aucun résultat.</p>
                </div>
            </template>
        </main>

        <div v-if="itemDialog" class="dialog" @click.self="itemDialog = false"><form class="panel max-w-xl" @submit.prevent="saveItem"><header class="form-header"><h2>{{ editingItem ? 'Modifier' : 'Créer' }} {{ meta[resource].singular }}</h2><button type="button" @click="itemDialog = false">Fermer</button></header><div class="grid gap-4 sm:grid-cols-2">
            <label v-if="resource === 'legal-statuses'" class="sm:col-span-2"><span>Libellé</span><input v-model="itemForm.libelle" required class="field" /></label><label v-else class="sm:col-span-2"><span>Nom</span><input v-model="itemForm.nom" required class="field" /></label>
            <label v-if="resource === 'styles'"><span>Parent</span><select v-model="itemForm.parentId" class="field"><option :value="null">Racine</option><option v-for="style in store.resources.styles.filter(value => value.estActif && value.id !== editingItem?.id)" :key="style.id" :value="style.id">{{ style.nom }}</option></select></label>
            <label v-if="['programs','formations'].includes(resource)"><span>Organisme</span><input v-model="itemForm.organisme" class="field" /></label>
            <template v-if="resource === 'professional-structures'"><label><span>Type</span><select v-model="itemForm.type" class="field"><option>Label</option><option>Agence Booking</option><option>Management</option><option>Édition</option><option>Studio</option></select></label><label><span>Email</span><input v-model="itemForm.email" type="email" class="field" /></label><label><span>Pays</span><input v-model="itemForm.pays" required class="field" /></label></template>
            <template v-if="resource === 'venues'"><label><span>Ville</span><input v-model="itemForm.ville" required class="field" /></label><label><span>Pays</span><input v-model="itemForm.pays" required class="field" /></label><label><span>Adresse</span><input v-model="itemForm.adresse" class="field" /></label><label><span>NPA</span><input v-model="itemForm.npa" class="field" /></label><label><span>Jauge</span><input v-model.number="itemForm.jauge" type="number" min="0" class="field" /></label><label class="check"><input v-model="itemForm.estFestival" type="checkbox" /> Festival</label></template>
            <label v-if="resource === 'platforms'"><span>Type</span><input v-model="itemForm.type" required class="field" /></label>
        </div><footer class="actions"><button type="button" @click="itemDialog = false">Annuler</button><button :disabled="store.isSaving" class="primary">Enregistrer</button></footer></form></div>

        <div v-if="expertDialog" class="dialog" @click.self="expertDialog = false"><form class="panel max-w-2xl" @submit.prevent="saveExpert"><header class="form-header"><h2>{{ editingExpert ? 'Modifier le compte' : 'Inviter un accompagnant' }}</h2><button type="button" @click="expertDialog = false">Fermer</button></header><div class="grid gap-4 sm:grid-cols-2">
            <label><span>Prénom</span><input v-model="expertForm.prenom" required class="field" /></label><label><span>Nom</span><input v-model="expertForm.nom" required class="field" /></label><label class="sm:col-span-2"><span>Email</span><input v-model="expertForm.email" type="email" required class="field" /></label><label><span>Rôle</span><select v-model="expertForm.role" class="field"><option value="expert_jury">Expert jury</option><option value="gestionnaire_case">Gestionnaire Case</option><option value="accompagnant">Accompagnant</option></select></label><label><span>Date de naissance</span><input v-model="expertForm.dateNaissance" type="date" required class="field" /></label><label><span>Genre</span><select v-model="expertForm.genre" class="field"><option>Homme</option><option>Femme</option><option>Autre</option></select></label><label><span>NPA</span><input v-model="expertForm.npa" required class="field" /></label><label><span>Ville</span><input v-model="expertForm.ville" required class="field" /></label><label><span>Téléphone</span><input v-model="expertForm.telephone" class="field" /></label><label v-if="editingExpert?.statut !== 'pending'" class="check"><input v-model="expertForm.estActif" type="checkbox" /> Compte actif</label>
        </div><div v-if="invitationUrl" class="mt-5 border border-amber-500/40 bg-amber-500/10 p-3"><p class="mb-2 text-xs font-bold text-amber-300">Lien généré</p><div class="flex gap-2"><input :value="invitationUrl" readonly class="field min-w-0 flex-1" /><button type="button" class="primary" @click="copyInvitation()">Copier</button></div></div><footer class="actions"><button type="button" @click="expertDialog = false">Annuler</button><button :disabled="store.isSaving" class="primary">{{ editingExpert ? 'Enregistrer' : 'Générer le lien' }}</button></footer></form></div>
    </div>
</template>

<style scoped>
.field { width: 100%; border: 1px solid #343845; background: #101216; padding: .6rem .75rem; color: #f3f4f6; outline: none; }
.field:focus { border-color: #00ff88; }
label > span { display: block; margin-bottom: .35rem; font-size: .75rem; font-weight: 700; color: #9ca3af; }
.dialog { position: fixed; inset: 0; z-index: 60; display: flex; align-items: center; justify-content: center; background: rgb(0 0 0 / .72); padding: 1rem; }
.panel { max-height: 90vh; width: 100%; overflow-y: auto; border: 1px solid #343845; background: #181a20; padding: 1.25rem; }
.form-header, .actions { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.form-header { margin-bottom: 1.25rem; } .form-header h2 { font-size: 1.125rem; font-weight: 900; }
.actions { justify-content: flex-end; margin-top: 1.5rem; } .actions button { border: 1px solid #343845; padding: .55rem 1rem; font-size: .875rem; }
.actions .primary, .primary { border: 0; background: #00ff88; color: #050806; font-weight: 900; padding: .55rem 1rem; }
.check { display: flex; align-items: end; gap: .5rem; padding-bottom: .6rem; font-size: .875rem; }
.state { border: 1px solid #4b5563; padding: .25rem .5rem; font-size: .75rem; font-weight: 700; }
</style>