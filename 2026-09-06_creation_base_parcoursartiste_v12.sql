-- ==============================================================================
-- Script de création de la base de données : Parcours d'Artiste (Case à Chocs)
-- Version : V12
-- Modèle : 3NF Hybride (Relationnel + JSONB)
-- SGBD Cible : PostgreSQL
-- ==============================================================================

-- ==============================================================================
-- 1. NOYAU IDENTITAIRE, DEMOGRAPHIQUE ET STYLISTIQUE
-- ==============================================================================

CREATE TABLE "CategorieArtiste" (
    id_categorie SERIAL PRIMARY KEY,
    libelle_categorie VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE "Personne" (
    id_personne SERIAL PRIMARY KEY,
    no_ipi VARCHAR(20), -- Numéro international pour les droits d'auteur
    nom_civil VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    date_naissance DATE NOT NULL,
    genre VARCHAR(15) NOT NULL,
    adresse VARCHAR(255),
    npa VARCHAR(20) NOT NULL,
    ville VARCHAR(100) NOT NULL,
    canton VARCHAR(50) DEFAULT 'Neuchâtel',
    telephone VARCHAR(20),
    email VARCHAR(150) UNIQUE,
    est_expert BOOLEAN DEFAULT FALSE
);

CREATE TABLE "StatutJuridique" (
    id_statut_juridique SERIAL PRIMARY KEY,
    libelle_statut VARCHAR(100) NOT NULL,
    est_actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX uq_statut_juridique_libelle_ci
    ON "StatutJuridique" (lower(trim(libelle_statut)));

CREATE TABLE "ProjetMusical" (
    id_projet SERIAL PRIMARY KEY,
    nom_projet VARCHAR(150) NOT NULL,
    bio_courte TEXT,
    est_groupe BOOLEAN NOT NULL DEFAULT FALSE,
    langue_chant VARCHAR(100),
    statut_juridique VARCHAR(100),
    for_juridique VARCHAR(100),
    date_creation DATE,
    page_personnelle_url VARCHAR(2048),
    page_personnelle_nom_site VARCHAR(100),
    objectifs_court_terme TEXT,
    objectifs_moyen_terme TEXT,
    
    -- Diagnostic de structuration & Autonomie (Formulaire Embrayage)
    est_inscrit_suisa BOOLEAN DEFAULT FALSE,
    possede_local_repetition BOOLEAN DEFAULT FALSE,
    possede_fiche_technique BOOLEAN DEFAULT FALSE,
    possede_merchandising BOOLEAN DEFAULT FALSE,
    a_contact_pro_studio BOOLEAN DEFAULT FALSE, -- Remplace le champ texte obsolète
    
    id_categorie_actuelle INT NOT NULL,
    id_statut_juridique INT NOT NULL,
    CONSTRAINT fk_projet_categorie FOREIGN KEY (id_categorie_actuelle) REFERENCES "CategorieArtiste"(id_categorie),
    CONSTRAINT fk_projet_statut_juridique
        FOREIGN KEY (id_statut_juridique)
        REFERENCES "StatutJuridique"(id_statut_juridique) ON DELETE RESTRICT,
    CONSTRAINT check_projet_page_personnelle_pair CHECK (
        (page_personnelle_url IS NULL) = (page_personnelle_nom_site IS NULL)
    ),
    CONSTRAINT check_projet_page_personnelle_url CHECK (
        page_personnelle_url IS NULL OR page_personnelle_url ~* '^https?://'
    ),
    CONSTRAINT check_projet_page_personnelle_nom CHECK (
        page_personnelle_nom_site IS NULL OR length(trim(page_personnelle_nom_site)) > 0
    ),
    CONSTRAINT check_projet_objectifs_court_terme CHECK (
        objectifs_court_terme IS NULL OR length(trim(objectifs_court_terme)) > 0
    ),
    CONSTRAINT check_projet_objectifs_moyen_terme CHECK (
        objectifs_moyen_terme IS NULL OR length(trim(objectifs_moyen_terme)) > 0
    )
);

CREATE TABLE "HistoriqueStatutJuridique" (
    id_historique_statut SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    statut_juridique VARCHAR(100) NOT NULL,
    id_statut_juridique INT NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE,
    CONSTRAINT fk_statut_juridique_projet
        FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_historique_statut_juridique
        FOREIGN KEY (id_statut_juridique)
        REFERENCES "StatutJuridique"(id_statut_juridique) ON DELETE RESTRICT,
    CONSTRAINT ck_statut_juridique_dates
        CHECK (date_fin IS NULL OR date_fin >= date_debut)
);

CREATE UNIQUE INDEX uq_statut_juridique_courant
    ON "HistoriqueStatutJuridique" (id_projet)
    WHERE date_fin IS NULL;

-- Table pour l'historisation des catégories d'artistes
CREATE TABLE "HistoriqueCategorie" (
    id_historique SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    id_categorie INT NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE, -- Reste NULL tant que c'est la catégorie actuelle
    CONSTRAINT fk_hist_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_hist_categorie FOREIGN KEY (id_categorie) REFERENCES "CategorieArtiste"(id_categorie)
);

CREATE TABLE "MembreProjet" (
    id_projet INT NOT NULL,
    id_personne INT NOT NULL,
    date_arrivee DATE NOT NULL,
    date_depart DATE,
    role_dans_groupe VARCHAR(100),
    PRIMARY KEY (id_projet, id_personne, date_arrivee),
    CONSTRAINT fk_membre_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_membre_personne FOREIGN KEY (id_personne) REFERENCES "Personne"(id_personne) ON DELETE CASCADE
);

CREATE TABLE "TypePhaseProjet" (
    id_type_phase SERIAL PRIMARY KEY,
    nom_phase VARCHAR(50) NOT NULL,
    est_actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX uq_type_phase_nom_ci
    ON "TypePhaseProjet" (lower(trim(nom_phase)));

CREATE TABLE "PhaseProjet" (
    id_phase SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    nom_phase VARCHAR(50),
    id_type_phase INT NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE,
    CONSTRAINT fk_phase_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_phase_type
        FOREIGN KEY (id_type_phase)
        REFERENCES "TypePhaseProjet"(id_type_phase) ON DELETE RESTRICT
);

CREATE TABLE "StyleMusical" (
    id_style SERIAL PRIMARY KEY,
    nom_style VARCHAR(100) NOT NULL,
    id_style_parent INT,
    est_actif BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_style_parent FOREIGN KEY (id_style_parent) REFERENCES "StyleMusical"(id_style) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_style_musical_nom_ci
    ON "StyleMusical" (lower(trim(nom_style)));

CREATE TABLE "ProjetStyle" (
    id_projet INT NOT NULL,
    id_style INT NOT NULL,
    est_style_principal BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id_projet, id_style),
    CONSTRAINT fk_projstyle_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_projstyle_style FOREIGN KEY (id_style) REFERENCES "StyleMusical"(id_style) ON DELETE CASCADE
);

-- ==============================================================================
-- 2. COMPTE UTILISATEUR DE L'APP
-- ==============================================================================

CREATE TABLE "RoleUtilisateur" (
    id_role SERIAL PRIMARY KEY,
    libelle_role VARCHAR(50) NOT NULL UNIQUE -- 'Admin', 'Gestionnaire_Case', 'Expert_Jury', 'Artiste'
);

CREATE TABLE "CompteUtilisateur" (
    id_utilisateur SERIAL PRIMARY KEY,
    email VARCHAR(150) NOT NULL UNIQUE,
    mot_de_passe_hash VARCHAR(255) NOT NULL,
	nom_affichage VARCHAR(150),
    id_role INT NOT NULL,
    id_personne INT, -- Optionnel : lié à une personne physique seulement si applicable
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    est_actif BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_compte_role FOREIGN KEY (id_role) REFERENCES "RoleUtilisateur"(id_role),
    CONSTRAINT fk_compte_personne FOREIGN KEY (id_personne) REFERENCES "Personne"(id_personne) ON DELETE SET NULL
);

CREATE TABLE "InvitationCompte" (
    id_personne INT PRIMARY KEY,
    role_invite VARCHAR(30) NOT NULL
        CHECK (role_invite IN ('expert_jury', 'gestionnaire_case', 'accompagnant')),
    date_invitation TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invitation_personne
        FOREIGN KEY (id_personne) REFERENCES "Personne"(id_personne) ON DELETE CASCADE
);

-- ==============================================================================
-- 3. ACCOMPAGNEMENT, FORMATION, ENTOURAGE ET FINANCEMENT
-- ==============================================================================

CREATE TABLE "ProgrammeAccompagnement" (
    id_programme SERIAL PRIMARY KEY,
    nom_programme VARCHAR(150) NOT NULL,
    organisme_organisateur VARCHAR(150),
    est_actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX uq_programme_nom_ci
    ON "ProgrammeAccompagnement" (lower(trim(nom_programme)));

CREATE TABLE "SuiviAccompagnement" (
    id_projet INT NOT NULL,
    id_programme INT NOT NULL,
    annee_participation SMALLINT NOT NULL,
    est_laureat BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (id_projet, id_programme, annee_participation),
    CONSTRAINT fk_suivi_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_suivi_prog FOREIGN KEY (id_programme) REFERENCES "ProgrammeAccompagnement"(id_programme)
);

CREATE TABLE "AffectationAccompagnement" (
    id_projet INT PRIMARY KEY,
    id_expert INT NOT NULL,
    date_affectation TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_affectation_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_affectation_expert FOREIGN KEY (id_expert) REFERENCES "Personne"(id_personne) ON DELETE RESTRICT
);

CREATE TABLE "Formation" (
    id_formation SERIAL PRIMARY KEY,
    nom_formation VARCHAR(150) NOT NULL,
    organisme_formateur VARCHAR(150),
    est_actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX uq_formation_nom_organisme_ci
    ON "Formation" (
        lower(trim(nom_formation)),
        lower(trim(COALESCE(organisme_formateur, '')))
    );

CREATE TABLE "ProjetFormation" (
    id_projet INT NOT NULL,
    id_formation INT NOT NULL,
    date_suivi DATE NOT NULL,
    PRIMARY KEY (id_projet, id_formation, date_suivi),
    CONSTRAINT fk_projform_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_projform_form FOREIGN KEY (id_formation) REFERENCES "Formation"(id_formation) ON DELETE CASCADE
);

-- NOUVEAU : Gestion des entreprises culturelles (Labels, Booking, Management)
CREATE TABLE "StructureProfessionnelle" (
    id_structure SERIAL PRIMARY KEY,
    nom_structure VARCHAR(150) NOT NULL,
    type_structure VARCHAR(50) NOT NULL CHECK (type_structure IN ('Label', 'Agence Booking', 'Management', 'Édition', 'Studio')),
    contact_email VARCHAR(150),
    pays VARCHAR(100) DEFAULT 'Suisse',
    est_actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX uq_structure_nom_type_ci
    ON "StructureProfessionnelle" (
        lower(trim(nom_structure)),
        lower(trim(type_structure))
    );

-- Table associative pour les liens entre le projet et une entreprise culturelle
CREATE TABLE "ProjetStructure" (
    id_projet INT NOT NULL,
    id_structure INT NOT NULL,
    date_debut DATE NOT NULL,
    date_fin DATE,
    PRIMARY KEY (id_projet, id_structure, date_debut),
    CONSTRAINT fk_projstruct_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_projstruct_struct FOREIGN KEY (id_structure) REFERENCES "StructureProfessionnelle"(id_structure) ON DELETE CASCADE
);

-- NOUVEAU : Gestion détaillée des subventions
CREATE TABLE "SoutienFinancier" (
    id_soutien SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    bailleur VARCHAR(150) NOT NULL, -- Ex: 'Ville de Neuchâtel', 'Loterie Romande', 'Pro Helvetia'
    montant_demande DECIMAL(10,2) NOT NULL,
    montant_octroye DECIMAL(10,2),
    annee SMALLINT NOT NULL,
    statut VARCHAR(50) DEFAULT 'En attente' CHECK (statut IN ('En attente', 'Octroyé', 'Refusé')),
    CONSTRAINT fk_soutien_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE
);

CREATE TABLE "EcheanceSubvention" (
    id_echeance SERIAL PRIMARY KEY,
    bailleur VARCHAR(150) NOT NULL,
    date_prochaine_soumission DATE NOT NULL,
    url_formulaire VARCHAR(2048) NOT NULL,
    est_actif BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT check_echeance_bailleur_non_vide CHECK (length(trim(bailleur)) > 0),
    CONSTRAINT check_echeance_url_http CHECK (url_formulaire ~* '^https?://')
);

CREATE UNIQUE INDEX uq_echeance_bailleur_date_ci
    ON "EcheanceSubvention" (lower(trim(bailleur)), date_prochaine_soumission);

CREATE TABLE "DeclarationDemandeSubvention" (
    id_projet INT NOT NULL,
    id_echeance INT NOT NULL,
    date_depot DATE NOT NULL,
    date_retrait DATE,
    PRIMARY KEY (id_projet, id_echeance),
    CONSTRAINT fk_declaration_subvention_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_declaration_subvention_echeance FOREIGN KEY (id_echeance) REFERENCES "EcheanceSubvention"(id_echeance) ON DELETE RESTRICT,
    CONSTRAINT check_declaration_retrait_apres_depot CHECK (date_retrait IS NULL OR date_retrait >= date_depot)
);

-- ==============================================================================
-- 4. ASSETS, OEUVRES, PRESSKIT ET COLLABORATIONS
-- ==============================================================================

-- Table de référence pour définir dynamiquement les types d'assets
CREATE TABLE "TypeAsset" (
    id_type SERIAL PRIMARY KEY,
    libelle VARCHAR(100) NOT NULL,  -- -- 'Disque/Release', 'Clip Video', 'PressKit PDF', 'Fiche Technique PDF', 'Arts plastiques', 'Pièce de théâtre'
    description TEXT
);

CREATE UNIQUE INDEX uq_type_asset_libelle_normalized
    ON "TypeAsset" (lower(trim(libelle)));

-- Table générique pour tous les assets du projet musical
CREATE TABLE "Asset" (
    id_asset SERIAL PRIMARY KEY,
    id_projet INT,
	id_personne INT,
    id_type INT NOT NULL,
    titre VARCHAR(255) NOT NULL,
    date_creation DATE,
    metadonnees JSONB NOT NULL DEFAULT '{}'::jsonb,
    chemin_stockage VARCHAR(500),
    est_featured_roster BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_asset_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_asset_personne FOREIGN KEY (id_personne) REFERENCES "Personne"(id_personne) ON DELETE CASCADE,
    -- Vérifie que l'asset est lié à une personne OU un projet
    CONSTRAINT check_asset_source CHECK (id_projet IS NOT NULL OR id_personne IS NOT NULL),
    CONSTRAINT check_asset_metadonnees_object CHECK (jsonb_typeof(metadonnees) = 'object'),
    CONSTRAINT fk_asset_type FOREIGN KEY (id_type) REFERENCES "TypeAsset"(id_type)
);

CREATE TABLE "Morceau" (
    id_morceau SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    titre_morceau VARCHAR(150) NOT NULL,
    duree TIME,
    annee_composition SMALLINT,
    date_sortie DATE,
	est_reprise BOOLEAN NOT NULL DEFAULT FALSE,
    code_isrc VARCHAR(12) UNIQUE,
    cle_suisa VARCHAR(20),
    est_top_track BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_morceau_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE
);

CREATE TABLE "EvenementParcours" (
    id_evenement SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    id_asset INT,
    type_evenement VARCHAR(100) NOT NULL,
    titre_evenement VARCHAR(255) NOT NULL,
    date_evenement DATE NOT NULL,
    media_source VARCHAR(150),
    url_preuve VARCHAR(2048),
    CONSTRAINT fk_evenement_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_evenement_asset FOREIGN KEY (id_asset) REFERENCES "Asset"(id_asset) ON DELETE CASCADE
);

CREATE UNIQUE INDEX uq_evenement_parcours_asset
    ON "EvenementParcours" (id_asset)
    WHERE id_asset IS NOT NULL;

-- Table pour gérer la complexité des collaborations (featurings, beatmakers)
CREATE TABLE "CollaborationMorceau" (
    id_collaboration SERIAL PRIMARY KEY,
    id_morceau INT NOT NULL,
    id_projet INT, -- -- Optionnel : si la collab est avec un groupe
    id_personne INT, -- -- Optionnel : si la collab est avec un artiste solo
    role_artistique VARCHAR(100) NOT NULL, -- Ex: 'Featuring', 'Mixage', 'Mastering', 'Beatmaker'
    date_collaboration DATE,
    CONSTRAINT fk_collab_morceau FOREIGN KEY (id_morceau) REFERENCES "Morceau"(id_morceau) ON DELETE CASCADE,
    CONSTRAINT fk_collab_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_collab_personne FOREIGN KEY (id_personne) REFERENCES "Personne"(id_personne) ON DELETE CASCADE,
    CONSTRAINT check_collab_source CHECK (id_projet IS NOT NULL OR id_personne IS NOT NULL)
);

-- Table pour lier des Personnes (compositeurs) à un Morceau

CREATE TABLE "CompositionMorceau" (
    id_composition SERIAL PRIMARY KEY,
    id_morceau INT NOT NULL,
    id_personne INT NOT NULL,
    role_composition VARCHAR(100) NOT NULL,
    pourcentage_droits DECIMAL(5,2),
    CONSTRAINT fk_comp_morceau FOREIGN KEY (id_morceau) REFERENCES "Morceau"(id_morceau) ON DELETE CASCADE,
    CONSTRAINT fk_comp_personne FOREIGN KEY (id_personne) REFERENCES "Personne"(id_personne) ON DELETE CASCADE
);

CREATE TABLE "ContenuAsset" (
    id_asset INT NOT NULL,
    id_morceau INT NOT NULL,
    ordre_apparition INT,
    PRIMARY KEY (id_asset, id_morceau),
    CONSTRAINT fk_contenu_asset FOREIGN KEY (id_asset) REFERENCES "Asset"(id_asset) ON DELETE CASCADE,
    CONSTRAINT fk_contenu_morceau FOREIGN KEY (id_morceau) REFERENCES "Morceau"(id_morceau) ON DELETE CASCADE
);

-- ==============================================================================
-- 5. LOGISTIQUE, DIFFUSION ET TRAJETS
-- ==============================================================================

CREATE TABLE "Venue" (
    id_venue SERIAL PRIMARY KEY,
    nom_venue VARCHAR(150) NOT NULL,
    adresse VARCHAR(255),
    ville VARCHAR(100) NOT NULL,
    npa VARCHAR(20),
    pays VARCHAR(100) NOT NULL,
    valeur_pairs INT NOT NULL DEFAULT 0,
    est_festival BOOLEAN DEFAULT FALSE,
    est_actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX uq_venue_nom_ville_pays_ci
    ON "Venue" (
        lower(trim(nom_venue)),
        lower(trim(ville)),
        lower(trim(pays))
    );

CREATE TABLE "Tournee" (
    id_tournee SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    nom_tournee VARCHAR(150) NOT NULL,
    date_debut_globale DATE NOT NULL,
    date_fin_globale DATE,
    CONSTRAINT fk_tournee_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE
);

CREATE TABLE "Concert" (
    id_concert SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    id_venue INT NOT NULL,
    id_tournee INT,
    date_heure TIMESTAMP NOT NULL,
    type_evenement VARCHAR(50) DEFAULT 'Concert' CHECK (type_evenement IN ('Concert', 'Résidence', 'Showcase')),
    zone_geographique VARCHAR(50) CHECK (zone_geographique IN ('Local/Neuchâtel', 'Hors Canton', 'International/Hors Suisse')),
    cachet_brut DECIMAL(10, 2),
    est_optionnel BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_concert_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_concert_venue FOREIGN KEY (id_venue) REFERENCES "Venue"(id_venue),
    CONSTRAINT fk_concert_tournee FOREIGN KEY (id_tournee) REFERENCES "Tournee"(id_tournee) ON DELETE SET NULL
);

CREATE TABLE "Setlist" (
    id_setlist SERIAL PRIMARY KEY,
    id_concert INT NOT NULL,
    id_morceau INT NOT NULL,
    ordre_passage INT NOT NULL,
    CONSTRAINT fk_setlist_concert FOREIGN KEY (id_concert) REFERENCES "Concert"(id_concert) ON DELETE CASCADE,
    CONSTRAINT fk_setlist_morceau FOREIGN KEY (id_morceau) REFERENCES "Morceau"(id_morceau) ON DELETE CASCADE
);

CREATE TABLE "TrajetLogistique" (
    id_trajet SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    id_concert INT,
    date_heure_depart TIMESTAMP NOT NULL,
    valeur_defrayement DECIMAL(10, 2),
    CONSTRAINT fk_trajet_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_trajet_concert FOREIGN KEY (id_concert) REFERENCES "Concert"(id_concert) ON DELETE SET NULL
);

-- ==============================================================================
-- 6. RESEAUX SOCIAUX, STREAMING ET METRIQUES
-- ==============================================================================

CREATE TABLE "Plateforme" (
    id_plateforme SERIAL PRIMARY KEY,
    nom_plateforme VARCHAR(100) NOT NULL,
    type_plateforme VARCHAR(50) NOT NULL,
    est_actif BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX uq_plateforme_nom_ci
    ON "Plateforme" (lower(trim(nom_plateforme)));

CREATE TABLE "PresenceWeb" (
    id_presence SERIAL PRIMARY KEY,
    id_projet INT NOT NULL,
    id_plateforme INT NOT NULL,
    url_profil VARCHAR(2048) NOT NULL,
    identifiant_api VARCHAR(255),
    CONSTRAINT fk_presence_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_presence_plateforme FOREIGN KEY (id_plateforme) REFERENCES "Plateforme"(id_plateforme) ON DELETE CASCADE,
    UNIQUE (id_projet, id_plateforme)
);

CREATE TABLE "ReleveMetrique" (
    id_releve SERIAL PRIMARY KEY,
    id_presence INT NOT NULL,
    date_releve DATE NOT NULL,
    type_indicateur VARCHAR(50) NOT NULL,
    valeur_compteur BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT fk_releve_presence FOREIGN KEY (id_presence) REFERENCES "PresenceWeb"(id_presence) ON DELETE CASCADE,
    UNIQUE (id_presence, date_releve, type_indicateur)
);

-- ==============================================================================
-- 7. EVALUATIONS ET DECISIONS JURY
-- ==============================================================================

CREATE TABLE "CampagneEvaluation" (
    id_campagne SERIAL PRIMARY KEY,
    nom_campagne VARCHAR(150) NOT NULL UNIQUE,
    statut VARCHAR(20) NOT NULL DEFAULT 'brouillon'
        CHECK (statut IN ('brouillon', 'ouverte', 'cloturee')),
    date_debut DATE,
    date_fin DATE,
    date_creation TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (date_fin IS NULL OR date_debut IS NULL OR date_fin >= date_debut)
);

CREATE TABLE "CampagneProjet" (
    id_campagne INT NOT NULL,
    id_projet INT NOT NULL,
    date_affectation TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_campagne, id_projet),
    CONSTRAINT fk_campagne_projet_campagne FOREIGN KEY (id_campagne) REFERENCES "CampagneEvaluation"(id_campagne) ON DELETE CASCADE,
    CONSTRAINT fk_campagne_projet_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE
);

CREATE TABLE "CampagneJure" (
    id_campagne INT NOT NULL,
    id_expert INT NOT NULL,
    date_affectation TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_campagne, id_expert),
    CONSTRAINT fk_campagne_jure_campagne FOREIGN KEY (id_campagne) REFERENCES "CampagneEvaluation"(id_campagne) ON DELETE CASCADE,
    CONSTRAINT fk_campagne_jure_expert FOREIGN KEY (id_expert) REFERENCES "Personne"(id_personne) ON DELETE RESTRICT
);

CREATE TABLE "BilanEvaluation" (
    id_bilan SERIAL PRIMARY KEY,
    id_campagne INT NOT NULL,
    id_projet INT NOT NULL,
    date_evaluation DATE NOT NULL,
    id_categorie_obtenue INT NOT NULL,
    remarques TEXT,
    statut_selection VARCHAR(20) NOT NULL DEFAULT 'en_attente'
        CHECK (statut_selection IN ('en_attente', 'selectionne', 'refuse')),
    decision_email_sent_at TIMESTAMPTZ,
    CONSTRAINT fk_bilan_campagne FOREIGN KEY (id_campagne) REFERENCES "CampagneEvaluation"(id_campagne) ON DELETE RESTRICT,
    CONSTRAINT fk_bilan_projet FOREIGN KEY (id_projet) REFERENCES "ProjetMusical"(id_projet) ON DELETE CASCADE,
    CONSTRAINT fk_bilan_categorie FOREIGN KEY (id_categorie_obtenue) REFERENCES "CategorieArtiste"(id_categorie),
    CONSTRAINT uq_bilan_campagne_projet UNIQUE (id_campagne, id_projet)
);

CREATE TABLE "CriteresEvaluation" (
    id_critere SERIAL PRIMARY KEY,
    nom_critere VARCHAR(150) NOT NULL,
    code_critere VARCHAR(50) NOT NULL UNIQUE,
    est_objectif BOOLEAN DEFAULT TRUE,
    poids INT DEFAULT 1,
    note_maximale SMALLINT NOT NULL DEFAULT 5 CHECK (note_maximale > 0),
    type_critere VARCHAR(20) NOT NULL DEFAULT 'subjectif'
        CHECK (type_critere IN ('objectif', 'subjectif')),
    est_actif BOOLEAN NOT NULL DEFAULT TRUE,
    ordre INT NOT NULL DEFAULT 0 CHECK (ordre >= 0),
    mode_evaluation VARCHAR(20) NOT NULL DEFAULT 'manuel'
        CHECK (mode_evaluation IN ('automatique', 'manuel')),
    regle_objective VARCHAR(50),
    CONSTRAINT ck_critere_configuration CHECK (
        (type_critere = 'objectif' AND mode_evaluation = 'automatique' AND regle_objective IS NOT NULL)
        OR (type_critere = 'objectif' AND mode_evaluation = 'manuel' AND regle_objective IS NULL)
        OR (type_critere = 'subjectif' AND mode_evaluation = 'manuel' AND regle_objective IS NULL)
    )
);

CREATE TABLE "CampagneCritere" (
    id_campagne INT NOT NULL,
    id_critere INT NOT NULL,
    poids INT NOT NULL CHECK (poids > 0),
    ordre INT NOT NULL CHECK (ordre >= 0),
    PRIMARY KEY (id_campagne, id_critere),
    CONSTRAINT fk_campagne_critere_campagne FOREIGN KEY (id_campagne) REFERENCES "CampagneEvaluation"(id_campagne) ON DELETE CASCADE,
    CONSTRAINT fk_campagne_critere_critere FOREIGN KEY (id_critere) REFERENCES "CriteresEvaluation"(id_critere) ON DELETE RESTRICT
);

CREATE TABLE "AppreciationExpert" (
    id_appreciation SERIAL PRIMARY KEY,
    id_bilan INT NOT NULL,
    id_expert INT NOT NULL,
    id_critere INT NOT NULL,
    note INT NOT NULL CHECK (note >= 0),
    commentaire TEXT,
    CONSTRAINT fk_bilan FOREIGN KEY (id_bilan) REFERENCES "BilanEvaluation"(id_bilan),
    CONSTRAINT fk_expert FOREIGN KEY (id_expert) REFERENCES "Personne"(id_personne),
    CONSTRAINT fk_critere FOREIGN KEY (id_critere) REFERENCES "CriteresEvaluation"(id_critere),
    CONSTRAINT uq_appreciation_bilan_critere UNIQUE (id_bilan, id_critere)
);

CREATE TABLE "NoteEvaluateur" (
    id_note SERIAL PRIMARY KEY,
    id_bilan INT NOT NULL,
    id_expert INT NOT NULL,
    note SMALLINT NOT NULL CHECK (note BETWEEN 0 AND 20),
    date_saisie TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_note_bilan FOREIGN KEY (id_bilan) REFERENCES "BilanEvaluation"(id_bilan) ON DELETE CASCADE,
    CONSTRAINT fk_note_expert FOREIGN KEY (id_expert) REFERENCES "Personne"(id_personne) ON DELETE RESTRICT,
    CONSTRAINT uq_note_bilan_expert UNIQUE (id_bilan, id_expert)
);

CREATE OR REPLACE FUNCTION validate_appreciation_note()
RETURNS TRIGGER AS $$
DECLARE
    maximum SMALLINT;
BEGIN
    SELECT note_maximale INTO maximum
    FROM "CriteresEvaluation"
    WHERE id_critere = NEW.id_critere;

    IF NEW.note > maximum THEN
        RAISE EXCEPTION 'La note % dépasse le maximum % du critère %',
            NEW.note, maximum, NEW.id_critere;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_appreciation_note
BEFORE INSERT OR UPDATE OF note, id_critere ON "AppreciationExpert"
FOR EACH ROW EXECUTE FUNCTION validate_appreciation_note();

-- ==============================================================================
-- 8. INSERTIONS INITIALES DE RÉFÉRENCE
-- ==============================================================================

INSERT INTO "StatutJuridique" (libelle_statut) VALUES
('Aucun'),
('Association'),
('Indépendant')
ON CONFLICT DO NOTHING;

INSERT INTO "TypePhaseProjet" (nom_phase) VALUES
('Idéation'),
('Création'),
('Diffusion')
ON CONFLICT DO NOTHING;

INSERT INTO "RoleUtilisateur" (id_role, libelle_role) VALUES 
(1, 'Admin'),
(2, 'Gestionnaire_Case'),
(3, 'Expert_Jury'),
(4, 'Artiste'),
(5, 'Accompagnant')
ON CONFLICT (id_role) DO NOTHING;

-- Catégories d'artistes
INSERT INTO "CategorieArtiste" (id_categorie, libelle_categorie) VALUES 
(1, 'Amateur'),
(2, 'Émergent'),
(3, 'Professionnel')
ON CONFLICT (id_categorie) DO NOTHING;

INSERT INTO "CriteresEvaluation" (
    id_critere, nom_critere, code_critere, est_objectif, poids, note_maximale,
    type_critere, est_actif, ordre, mode_evaluation, regle_objective
) VALUES
 (1, 'Respect des critères impératifs (historique)', 'respectCriteres', TRUE, 2, 5, 'objectif', FALSE, 5, 'manuel', NULL),
 (2, 'Potentiel artistique & professionnel', 'potentielArtistique', FALSE, 3, 8, 'subjectif', TRUE, 60, 'manuel', NULL),
 (3, 'Motivation et implication du groupe', 'motivation', FALSE, 2, 5, 'subjectif', TRUE, 70, 'manuel', NULL),
 (4, 'Qualité du dossier fourni', 'qualiteDossier', FALSE, 1, 2, 'subjectif', TRUE, 80, 'manuel', NULL),
(10, 'Projet neuchâtelois', 'objectifProjetNeuchatelois', TRUE, 1, 1, 'objectif', TRUE, 10, 'automatique', 'projet_neuchatelois'),
(11, 'Membres âgés de 18 à 25 ans', 'objectifMembres18A25', TRUE, 1, 1, 'objectif', TRUE, 20, 'automatique', 'membres_18_25'),
(12, 'Au moins un morceau original', 'objectifMorceauOriginal', TRUE, 1, 1, 'objectif', TRUE, 30, 'automatique', 'au_moins_un_morceau_original'),
(13, 'Concert déjà effectué', 'objectifConcertEffectue', TRUE, 1, 1, 'objectif', TRUE, 40, 'automatique', 'concert_effectue'),
(14, 'Au moins un morceau au répertoire', 'objectifRepertoire', TRUE, 1, 1, 'objectif', TRUE, 50, 'automatique', 'au_moins_un_morceau')
ON CONFLICT (code_critere) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('"CriteresEvaluation"', 'id_critere'),
    COALESCE((SELECT MAX(id_critere) FROM "CriteresEvaluation"), 1)
);

INSERT INTO "TypeAsset" (libelle, description) VALUES 
('Disque/Release', 'Album, EP ou Single'), 
('Clip Vidéo', 'Clip musical officiel'), 
('PressKit PDF', 'Dossier de presse promotionnel'), 
('Fiche Technique PDF', 'Rider technique et patch scène');

-- ==============================================================================
-- INSERTION LONGUE : TAXONOMIE ARBORESCENTE DES STYLES (3 NIVEAUX - ADMIN, GENRE PARENT, GENRE PRECIS)
-- ==============================================================================

-- ==============================================================================
-- NIVEAU 1 : RACINES INSTITUTIONNELLES FCMA (id_style_parent = NULL)
-- ==============================================================================
INSERT INTO "StyleMusical" (id_style, nom_style, id_style_parent) VALUES 
(1, 'Pop', NULL),
(2, 'Musiques improvisées', NULL),
(3, 'Pluridisciplinaire', NULL),
(4, 'Toutes musiques', NULL)
ON CONFLICT (id_style) DO NOTHING;

-- ==============================================================================
-- NIVEAU 2 : MACRO-GENRES (Rattachés aux racines FCMA)
-- ==============================================================================
INSERT INTO "StyleMusical" (id_style, nom_style, id_style_parent) VALUES 
(5, 'Ambient / New Age', 1),
(6, 'Electronica / Downtempo', 1),
(7, 'Hip-hop / R''n''B', 1),
(8, 'New Club', 1),
(9, 'UK Dance / Grime', 1),
(10, 'House / Techno', 1),
(11, 'Post Punk / New Wave', 1),
(12, 'Alternative Rock / Punk', 1),
(13, 'Rock', 1),
(14, 'Metal', 1),
(15, 'Avant Garde', 2),
(16, 'Caribbean', 1),
(17, 'Latin / Brazilian', 1),
(18, 'Jazz', 2),
(19, 'Soul / Rhythm & Blues', 1),
(20, 'Disco / Boogie', 1),
(21, 'African / Middle Eastern', 1),
(22, 'Asia', 1),
(23, 'Classical / Opera', 4),
(24, 'Other', 1)
ON CONFLICT (id_style) DO NOTHING;

-- Resynchronise la séquence SERIAL après ces insertions à id_style explicite,
-- sinon les INSERT auto-incrémentés du Niveau 3 retentent id_style=1, 2, 3...
SELECT setval(pg_get_serial_sequence('"StyleMusical"', 'id_style'), (SELECT MAX(id_style) FROM "StyleMusical"));

-- ==============================================================================
-- NIVEAU 3 : SOUS-GENRES ET MICRO-ESTHÉTIQUES
-- ==============================================================================
INSERT INTO "StyleMusical" (nom_style, id_style_parent) VALUES 
-- 1. Sous-genres de 'Ambient / New Age' (id_parent = 5)
('Ambient', 5), ('Fourth World', 5), ('Kosmische', 5), ('New Age', 5), ('Vaporwave', 5),

-- 2. Sous-genres de 'Electronica / Downtempo' (id_parent = 6)
('Beats', 6), ('Electronica', 6), ('Glitch', 6), ('Trip Hop', 6), ('Witch House', 6),

-- 3. Sous-genres de 'Hip-hop / R''n''B' (id_parent = 7)
('Chopped N Screwed', 7), ('Classic Hip Hop', 7), ('Cloud Rap', 7), ('Dirty South', 7),
('Drill', 7), ('Emo Rap', 7), ('Experimental Hip Hop', 7), ('G-Funk', 7),
('Gangsta Rap', 7), ('Hip Hop', 7), ('Memphis', 7), ('Motswako', 7),
('New Jack Swing', 7), ('RNB', 7), ('Rap', 7), ('Trap', 7),

-- 4. Sous-genres de 'New Club' (id_parent = 8)
('Afro House', 8), ('Afrobeats', 8), ('Amapiano', 8), ('Arrocha', 8),
('Baile Funk', 8), ('Ballroom', 8), ('Baltimore Club', 8), ('Bass', 8),
('Batida', 8), ('Brega', 8), ('Club', 8), ('Coupé-Décalé', 8),
('Deck', 8), ('EDM', 8), ('Electro Acholi', 8), ('Footwork', 8),
('Forró Piseiro', 8), ('Gengetone', 8), ('Gqom', 8), ('Hyperpop', 8),
('Jersey Club', 8), ('Kuduro', 8), ('Kwaito', 8), ('Mara', 8),
('Ndombolo', 8), ('Nightcore', 8), ('Raptor House', 8), ('Reggaeton', 8),
('Singeli', 8), ('Street Hop', 8), ('Vinahouse', 8), ('Wisisi', 8),

-- 5. Sous-genres de 'UK Dance / Grime' (id_parent = 9)
('Bassline', 9), ('Breakbeat Hardcore', 9), ('Breakcore', 9), ('Donk', 9),
('Drum & Bass', 9), ('Dubstep', 9), ('Garage', 9), ('Grime', 9),
('Jungle', 9), ('Speed Garage', 9), ('UK Funky', 9),

-- 6. Sous-genres de 'House / Techno' (id_parent = 10)
('Acid', 10), ('Ambient Techno', 10), ('Balearic House', 10), ('Breaks', 10),
('Broken Beat', 10), ('Chicago House', 10), ('Deep House', 10), ('Detroit House', 10),
('Detroit Techno', 10), ('Dub Techno', 10), ('Electro', 10), ('Euro House', 10),
('Gabber', 10), ('Ghetto House', 10), ('Ghettotech', 10), ('Happy Hardcore', 10),
('Hardstyle', 10), ('Hip-House', 10), ('House', 10), ('Leftfield House', 10),
('Leftfield Techno', 10), ('Makina', 10), ('Minimal', 10), ('Tech House', 10),
('Techno', 10), ('Trance', 10),

-- 7. Sous-genres de 'Post Punk / New Wave' (id_parent = 11)
('EBM', 11), ('Electroclash', 11), ('Goth Rock', 11), ('Industrial', 11),
('Minimal Synth', 11), ('New Beat', 11), ('New Wave', 11), ('No Wave', 11),
('Post Punk', 11), ('Synth Pop', 11),

-- 8. Sous-genres de 'Alternative Rock / Punk' (id_parent = 12)
('Art Rock', 12), ('Dream Pop', 12), ('Emo', 12), ('Garage Rock', 12),
('Grunge', 12), ('Hardcore Punk', 12), ('Indie Rock', 12), ('Math Rock', 12),
('Noise Rock', 12), ('Post Hardcore', 12), ('Post Rock', 12), ('Punk', 12),
('SHIBUYA-KEI', 12), ('Shoegaze', 12), ('Space Rock', 12),

-- 9. Sous-genres de 'Rock' (id_parent = 13)
('American Primitivism', 13), ('Classic Rock', 13), ('Country', 13),
('Folk', 13), ('Hard Rock', 13), ('Krautrock', 13), ('Power Pop', 13),
('Prog Rock', 13), ('Psychedelic Folk', 13), ('Psychedelic Rock', 13),
('Rock N Roll', 13), ('Rockabilly', 13), ('Soft Rock', 13), ('Surf', 13),
('Visual Kei', 13), ('Yacht Rock', 13),

-- 10. Sous-genres de 'Metal' (id_parent = 14)
('Black Metal', 14), ('Death Metal', 14), ('Doom', 14), ('Grindcore', 14),
('Heavy Metal', 14), ('Metalcore', 14), ('Nu Metal', 14), ('Sludge', 14),
('Thrash', 14),

-- 11. Sous-genres de 'Avant Garde' (id_parent = 15)
('Dark Ambient', 15), ('Drone', 15), ('Experimental', 15), ('Freak Folk', 15),
('Musique Concrete', 15), ('Noise', 15),

-- 12. Sous-genres de 'Caribbean' (id_parent = 16)
('Bashment', 16), ('Beguine', 16), ('Bouyon', 16), ('Bubbling', 16),
('Calypso', 16), ('Chutney', 16), ('Dancehall', 16), ('Dembow', 16),
('Dennery Segment', 16), ('Digi Dub', 16), ('Dub', 16), ('GWO KA', 16),
('La Plena', 16), ('Lovers Rock', 16), ('Mento', 16), ('Rabòday', 16),
('Reggae', 16), ('Rocksteady', 16), ('Shatta', 16), ('Ska', 16),
('Soca', 16), ('Steel Drum', 16), ('Twoubadou', 16), ('Zouk', 16),

-- 13. Sous-genres de 'Latin / Brazilian' (id_parent = 17)
('Bachata', 17), ('Batucada', 17), ('Bolero', 17), ('Bossa Nova', 17),
('Brasillica', 17), ('Carimbó', 17), ('Champeta', 17), ('Chicha', 17),
('Corrido', 17), ('Cumbia', 17), ('Flamenco', 17), ('Forró', 17),
('Freestyle', 17), ('GUARANÍ', 17), ('Gaita', 17), ('Guaracha', 17),
('Guarapo', 17), ('Huayños', 17), ('Joropo', 17), ('Kaseko', 17),
('Latin Jazz', 17), ('Latin Soul', 17), ('Mariachi', 17), ('Merengue', 17),
('Meringue', 17), ('Música Popular Brasileira', 17), ('Norteño', 17),
('Nueva Cancion', 17), ('Nueva Trova', 17), ('Nuevo Cancionero', 17),
('Pasillo', 17), ('Pasodoble', 17), ('Quechua', 17), ('Rancheras', 17),
('Rockola', 17), ('Salsa', 17), ('Samba', 17),
('South American Indigenous Music', 17), ('Tango', 17), ('Tonada', 17),
('Vallenato', 17), ('Zapateado', 17),

-- 14. Sous-genres de 'Jazz' (id_parent = 18)
('Afro Cuban Jazz', 18), ('Ambient Jazz', 18), ('Bebop', 18),
('Contemporary Jazz', 18), ('Free Jazz', 18), ('Hard Bop', 18),
('Jazz Fusion', 18), ('Jazz Rock', 18), ('Modal', 18), ('Post Bop', 18),
('Soul Jazz', 18), ('Spiritual Jazz', 18), ('Straight Jazz', 18),
('Sun Ra', 18), ('Swing', 18),

-- 15. Sous-genres de 'Soul / Rhythm & Blues' (id_parent = 19)
('Blues', 19), ('Doo Wop', 19), ('Funk', 19), ('Gospel', 19),
('P Funk', 19), ('Psychedelic Soul', 19), ('Rare Groove', 19),
('Rhythm & Blues', 19), ('Sacred Harp', 19), ('Slow Jams', 19),
('Soul', 19), ('Street Soul', 19), ('Sweet Soul', 19),

-- 16. Sous-genres de 'Disco / Boogie' (id_parent = 20)
('Boogie', 20), ('Bubblegum', 20), ('Classic Disco', 20),
('Cosmic Disco', 20), ('Italo', 20), ('Leftfield Disco', 20), ('Neo Disco', 20),

-- 17. Sous-genres de 'African / Middle Eastern' (id_parent = 21)
('Afro Disco', 21), ('Afrobeat', 21), ('Amazigh Music', 21),
('Anatolian Rock', 21), ('Arabian Bellydance', 21), ('Arabic Pop', 21),
('Arabic Traditional', 21), ('Arbantone', 21), ('Balani', 21),
('Benga', 21), ('Bikutsi', 21), ('Chaabi', 21), ('Chaoui', 21),
('Coladeira', 21), ('Dabke', 21), ('Dhaanto', 21), ('Eritrean Folk', 21),
('Eritrean Pop', 21), ('Ethiopian Jazz', 21), ('Ethiopian Pop', 21),
('Ethiopian Traditional', 21), ('Ethiopiques', 21), ('Fuji', 21),
('Funaná', 21), ('Ga', 21), ('Gnawa', 21), ('Griot', 21),
('Gumbe', 21), ('Gyil', 21), ('Halay', 21), ('Hawzi', 21),
('Highlife', 21), ('Iraqi Maqam', 21), ('Juju', 21), ('KHALEEJI', 21),
('Kabyle', 21), ('Kalenjin', 21), ('Kilalaky', 21), ('Kizomba', 21),
('Kora', 21), ('Lekompo', 21), ('Lewa', 21), ('MALAGASY FOLK', 21),
('Mahraganat', 21), ('Makossa', 21), ('Maloya', 21), ('Mande Music', 21),
('Mandinka', 21), ('Mapouka', 21), ('Maringa', 21), ('Mauritanian Traditional', 21),
('Mbalax', 21), ('Mezoued', 21), ('Mizmar', 21), ('Morna', 21),
('Muzika Mizrahit', 21), ('Persian Traditional', 21), ('Qaraami', 21),
('Rababa', 21), ('Raï', 21), ('Rumba', 21), ('Sahara Blues', 21),
('Sai', 21), ('Salegy', 21), ('Sega', 21), ('Semba', 21),
('Shangaan Electro', 21), ('Simpa', 21), ('Soukous', 21),
('South African Jazz', 21), ('Sudanese Folk', 21), ('Sudanese Pop', 21),
('Taarab', 21), ('Turkish Disco', 21), ('Wassalou', 21), ('Wassoulou', 21),
('Zamrock', 21), ('Ziglibithy', 21), ('Zouglou', 21), ('Zukra', 21),

-- 18. Sous-genres de 'Asia' (id_parent = 22)
('Luk Krung', 22), ('Afghan Traditional Music', 22), ('BAILA FOLK', 22),
('Balochi', 22), ('Bengali Pop', 22), ('Bhangra', 22), ('Bollywood', 22),
('Budots', 22), ('Burmese Folk', 22), ('C-Pop', 22), ('Canto Pop', 22),
('Chinese Traditional', 22), ('Choliya', 22), ('City Pop', 22),
('Cải lương', 22), ('Dangdut', 22), ('Dân Ca', 22), ('Filipino Folk', 22),
('Gamelan', 22), ('Ghazal', 22), ('Hokkien pop', 22), ('I-Pop', 22),
('Indian Classical', 22), ('J Rock', 22), ('J-Pop', 22), ('Jaipong', 22),
('Japanese Traditional', 22), ('K-Pop', 22), ('Keroncong', 22),
('Khmer Pop', 22), ('Korean Traditional', 22), ('Kundiman', 22),
('Kyrgyz Folk', 22), ('Lao Traditional', 22), ('Lollywood', 22),
('Luk Thung', 22), ('Mando Pop', 22), ('Molam', 22), ('Newa', 22),
('Nhạc Vàng', 22), ('Pakistani Classical', 22), ('Pakistani Pop', 22),
('Pashto Pop', 22), ('Persian Pop', 22), ('Pop Sunda', 22),
('Proto Visual Kei', 22), ('Rajasthani Folk', 22), ('Roadshow Music', 22),
('Saung', 22), ('Shashmaqam', 22), ('Shidaiqu', 22), ('Tajik Folk', 22),
('Tamil Film Music', 22), ('Thai Classical', 22), ('Toi', 22),
('Uyghur Pop', 22), ('V-Pop', 22), ('Vietnamese Traditional', 22),

-- 19. Sous-genres de 'Classical / Opera' (id_parent = 23)
('Baroque', 23), ('Chamber Music', 23), ('Choral Music', 23),
('Classical', 23), ('Minimalism', 23), ('Modern Classical', 23), ('Opera', 23),

-- 20. Sous-genres de 'Other' (id_parent = 24)
('Armenian Pop', 24), ('Australian Indigenous Music', 24), ('Balkan Pop', 24),
('Bhajan', 24), ('Bluegrass', 24), ('Buddhist Traditional', 24),
('Bulgarian Traditional', 24), ('Celtic Folk', 24), ('Chanson', 24),
('Chip Tune', 24), ('Christian Traditional', 24), ('Christmas', 24),
('Dungeon Synth', 24), ('Field Recordings', 24), ('Greek Traditional', 24),
('Halloween', 24), ('Himene Tarava', 24), ('Imene tuki', 24),
('Interview', 24), ('Irish Traditional', 24), ('Italian Traditional', 24),
('Joik', 24), ('Keiji Haino Music', 24), ('Leftfield Pop', 24),
('Library', 24), ('Live Performance', 24), ('Manele pop', 24),
('Nasheed', 24), ('Native American Rock', 24), ('Nordic Folk', 24),
('North American Indigenous Music', 24), ('Northumbrian Folk', 24),
('Norweigan Folk', 24), ('Portugese Fado', 24), ('Qawwali', 24),
('Rabiz', 24), ('Soundtrack', 24), ('Space Age Pop', 24),
('Spirituals', 24), ('Spoken Word', 24), ('Talk', 24), ('Video Game Music', 24)
ON CONFLICT DO NOTHING;

-- ==============================================================================
-- CREATION DES VUES ANALYTICS
-- ==============================================================================
CREATE OR REPLACE VIEW analytics_concerts AS
SELECT projet.id_projet,
       projet.nom_projet,
       concert.date_heure::date AS date_evenement,
       concert.type_evenement,
       concert.zone_geographique,
       1::bigint AS nombre_concerts
FROM "Concert" concert
JOIN "ProjetMusical" projet ON projet.id_projet = concert.id_projet;

CREATE OR REPLACE VIEW analytics_ecoutes AS
SELECT projet.id_projet,
       projet.nom_projet,
       plateforme.nom_plateforme,
       releve.date_releve,
       releve.type_indicateur,
       releve.valeur_compteur
FROM "ReleveMetrique" releve
JOIN "PresenceWeb" presence ON presence.id_presence = releve.id_presence
JOIN "Plateforme" plateforme ON plateforme.id_plateforme = presence.id_plateforme
JOIN "ProjetMusical" projet ON projet.id_projet = presence.id_projet
WHERE releve.type_indicateur IN ('Ecoutes_Mensuelles', 'Ecoutes_Cumulees')
   OR releve.type_indicateur LIKE 'Streams%';

CREATE OR REPLACE VIEW analytics_sorties AS
SELECT projet.id_projet,
       projet.nom_projet,
       morceau.id_morceau,
       morceau.titre_morceau,
       morceau.date_sortie,
       1::bigint AS nombre_morceaux_sortis
FROM "Morceau" morceau
JOIN "ProjetMusical" projet ON projet.id_projet = morceau.id_projet
WHERE morceau.date_sortie IS NOT NULL;

CREATE OR REPLACE VIEW analytics_collaborations AS
SELECT projet.id_projet,
       projet.nom_projet,
       collaboration.id_collaboration,
       collaboration.date_collaboration,
       collaboration.role_artistique,
       1::bigint AS nombre_collaborations,
       morceau.id_morceau,
       morceau.titre_morceau,
       personne.id_personne AS id_personne_collaboratrice,
       personne.prenom AS prenom_personne_collaboratrice,
       personne.nom_civil AS nom_personne_collaboratrice,
       projet_collaborateur.id_projet AS id_projet_collaborateur,
       projet_collaborateur.nom_projet AS nom_projet_collaborateur,
       COALESCE(
            NULLIF(CONCAT_WS(' ', personne.prenom, personne.nom_civil), ''),
            projet_collaborateur.nom_projet
        ) AS nom_collaborateur
FROM "CollaborationMorceau" collaboration
JOIN "Morceau" morceau ON morceau.id_morceau = collaboration.id_morceau
JOIN "ProjetMusical" projet ON projet.id_projet = morceau.id_projet
LEFT JOIN "Personne" personne ON personne.id_personne = collaboration.id_personne
LEFT JOIN "ProjetMusical" projet_collaborateur ON projet_collaborateur.id_projet = collaboration.id_projet
WHERE collaboration.date_collaboration IS NOT NULL;

CREATE OR REPLACE VIEW analytics_statuts_juridiques AS
SELECT projet.id_projet,
       projet.nom_projet,
             statut.libelle_statut AS statut_juridique,
       historique.date_debut,
       historique.date_fin
FROM "HistoriqueStatutJuridique" historique
JOIN "ProjetMusical" projet ON projet.id_projet = historique.id_projet
JOIN "StatutJuridique" statut
    ON statut.id_statut_juridique = historique.id_statut_juridique;

CREATE OR REPLACE VIEW analytics_formations AS
SELECT projet.id_projet,
       projet.nom_projet,
       formation.nom_formation,
       formation.organisme_formateur,
       suivi.date_suivi,
       1::bigint AS nombre_formations
FROM "ProjetFormation" suivi
JOIN "ProjetMusical" projet ON projet.id_projet = suivi.id_projet
JOIN "Formation" formation ON formation.id_formation = suivi.id_formation;

CREATE OR REPLACE VIEW analytics_accompagnements AS
SELECT projet.id_projet,
       projet.nom_projet,
       programme.nom_programme,
       programme.organisme_organisateur,
       make_date(suivi.annee_participation, 1, 1) AS date_participation,
       suivi.est_laureat,
       1::bigint AS nombre_programmes
FROM "SuiviAccompagnement" suivi
JOIN "ProjetMusical" projet ON projet.id_projet = suivi.id_projet
JOIN "ProgrammeAccompagnement" programme ON programme.id_programme = suivi.id_programme;
