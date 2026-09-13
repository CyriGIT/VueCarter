-- ==============================================================================
-- SCRIPT D'INSERTION DE DONNÉES FACTICES COMPLET (V9)
-- Minimum 6 à 10 occurrences par table métier & Traçabilité Diachronique
-- ==============================================================================

-- ==============================================================================
-- 1. PERSONNES (Artistes, Membres, Intervenants, Experts et Jurys)
-- ==============================================================================
INSERT INTO "Personne" (id_personne, no_ipi, nom_civil, prenom, date_naissance, genre, adresse, npa, ville, canton, telephone, email, est_expert) VALUES
(1, NULL, 'Démo', 'Artiste Alpha', '2002-05-12', 'Homme', 'Adresse fictive 1', '2073', 'Enges', 'Neuchâtel', NULL, 'artiste.alpha@example.com', FALSE),
(2, NULL, 'Démo', 'Artiste Bêta', '1998-03-22', 'Homme', 'Adresse fictive 2', '2520', 'La Neuveville', 'Berne', NULL, 'artiste.beta@example.com', FALSE),
(3, NULL, 'Démo', 'Artiste Gamma', '2001-11-05', 'Femme', 'Adresse fictive 3', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'artiste.gamma@example.com', FALSE),
(4, NULL, 'Démo', 'Membre Delta', '1995-04-18', 'Homme', 'Adresse fictive 4', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'membre.delta@example.com', FALSE),
(5, NULL, 'Démo', 'Artiste Epsilon', '2006-08-19', 'Homme', 'Adresse fictive 5', '2022', 'Bevaix', 'Neuchâtel', NULL, 'artiste.epsilon@example.com', FALSE),
(6, NULL, 'Démo', 'Artiste Zêta', '2005-01-30', 'Autre', 'Adresse fictive 6', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'artiste.zeta@example.com', FALSE),
(7, NULL, 'Démo', 'Gestionnaire', '1985-06-15', 'Homme', 'Adresse fictive 7', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'gestionnaire@example.com', TRUE),
(8, NULL, 'Démo', 'Artiste Eta', '2000-02-14', 'Homme', 'Adresse fictive 8', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'artiste.eta@example.com', FALSE),
(9, NULL, 'Démo', 'Artiste Thêta', '2000-09-27', 'Femme', 'Adresse fictive 9', '2300', 'La Chaux-de-Fonds', 'Neuchâtel', NULL, 'artiste.theta@example.com', FALSE),
(10, NULL, 'Démo', 'Artiste Iota', '2004-04-10', 'Homme', 'Adresse fictive 10', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'artiste.iota@example.com', FALSE),
(11, NULL, 'Démo', 'Jury Alpha', '1978-01-20', 'Homme', 'Adresse fictive 11', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'jury.alpha@example.com', TRUE),
(12, NULL, 'Démo', 'Jury Bêta', '1988-07-11', 'Femme', 'Adresse fictive 12', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'jury.beta@example.com', TRUE),
(13, NULL, 'Démo', 'Jury Gamma', '1983-12-04', 'Femme', 'Adresse fictive 13', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'jury.gamma@example.com', TRUE),
(14, NULL, 'Démo', 'Jury Delta', '1981-05-19', 'Homme', 'Adresse fictive 14', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'jury.delta@example.com', TRUE),
(15, NULL, 'Démo', 'Accompagnante', '1986-09-08', 'Femme', 'Adresse fictive 15', '2000', 'Neuchâtel', 'Neuchâtel', NULL, 'accompagnante@example.com', TRUE)
ON CONFLICT (id_personne) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"Personne"', 'id_personne'),
	COALESCE((SELECT MAX(id_personne) FROM "Personne"), 1)
);

-- ==============================================================================
-- 2. COMPTES UTILISATEURS APPLICATIFS (RBAC)
-- ==============================================================================
-- Hash bcrypt pour '1234' : $2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa
INSERT INTO "CompteUtilisateur" (email, mot_de_passe_hash, nom_affichage, id_role, id_personne) VALUES
('admin@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Administration Démo', 1, NULL),
('gestionnaire@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Gestionnaire Démo', 2, 7),
('jury.alpha@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Jury Alpha', 3, 11),
('jury.beta@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Jury Bêta', 3, 12),
('jury.gamma@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Jury Gamma', 3, 13),
('jury.delta@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Jury Delta', 3, 14),
('artiste.alpha@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Artiste Alpha', 4, 1),
('artiste.beta@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Artiste Bêta', 4, 2),
('artiste.gamma@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Artiste Gamma', 4, 3),
('artiste.epsilon@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Artiste Epsilon', 4, 5),
('accompagnante@example.com', '$2b$12$v5tzOU4e/42neDih5CvVneDryvUwHu869qYhJcnxpDTlulPuHtRYa', 'Accompagnante Démo', (SELECT id_role FROM "RoleUtilisateur" WHERE lower(libelle_role) = 'accompagnant'), 15)
ON CONFLICT (email) DO NOTHING;

-- ==============================================================================
-- 3. PROJETS MUSICAUX & DIAGNOSTIC EMBRAYAGE
-- ==============================================================================
INSERT INTO "ProjetMusical" (id_projet, nom_projet, bio_courte, est_groupe, langue_chant, statut_juridique, for_juridique, date_creation, est_inscrit_suisa, possede_local_repetition, possede_fiche_technique, possede_merchandising, a_contact_pro_studio, id_categorie_actuelle, id_statut_juridique) VALUES
(1, 'Projet Alpha', 'Projet pop-urbain fictif utilisé pour illustrer un parcours artistique structuré.', FALSE, 'Français', 'Association', 'Enges', '2023-01-10', TRUE, TRUE, TRUE, TRUE, TRUE, 2, (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association')),
(2, 'Projet Bêta', 'Projet rap fictif utilisé pour illustrer le suivi d’une activité régionale.', FALSE, 'Français', 'Association', 'La Neuveville', '2022-06-15', TRUE, FALSE, TRUE, TRUE, TRUE, 2, (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association')),
(3, 'Projet Gamma', 'Duo électronique fictif combinant synthétiseurs et textures vocales.', TRUE, 'Français', 'Association', 'Neuchâtel', '2023-09-01', FALSE, TRUE, TRUE, FALSE, FALSE, 1, (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association')),
(4, 'Projet Delta', 'Projet trap fictif utilisé pour illustrer une progression numérique et scénique.', FALSE, 'Français', 'Association', 'Bevaix', '2024-02-01', TRUE, TRUE, TRUE, TRUE, TRUE, 2, (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association')),
(5, 'Projet Epsilon', 'Projet hybride fictif entre musique électronique et rap.', FALSE, 'Français', 'Aucun', 'Neuchâtel', '2024-05-15', FALSE, FALSE, FALSE, TRUE, FALSE, 1, (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Aucun')),
(6, 'Projet Zêta', 'Formation rock fictive utilisée pour illustrer un parcours de diffusion.', TRUE, 'Anglais', 'Association', 'Neuchâtel', '2020-11-12', TRUE, TRUE, TRUE, TRUE, TRUE, 2, (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association')),
(7, 'Projet Eta', 'Formation pop-jazz fictive utilisée pour les scénarios de démonstration.', TRUE, 'Français', 'Association', 'La Chaux-de-Fonds', '2023-03-20', TRUE, TRUE, TRUE, FALSE, TRUE, 2, (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association')),
(8, 'Projet Thêta', 'Projet rap fictif utilisé pour illustrer un dossier en développement.', FALSE, 'Français', 'Indépendant', 'Neuchâtel', '2020-04-10', TRUE, TRUE, TRUE, FALSE, TRUE, 1, (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Indépendant'))
ON CONFLICT (id_projet) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"ProjetMusical"', 'id_projet'),
	COALESCE((SELECT MAX(id_projet) FROM "ProjetMusical"), 1)
);

-- ==============================================================================
-- 4. HISTORISATION DES STATUTS JURIDIQUES & CATÉGORIES ARTISTES
-- ==============================================================================
-- Suivi de la structuration administrative (Idéalement : passage d'aucun/indépendant vers Association)
DELETE FROM "HistoriqueStatutJuridique"
WHERE id_projet BETWEEN 1 AND 8;

INSERT INTO "HistoriqueStatutJuridique" (id_projet, statut_juridique, id_statut_juridique, date_debut, date_fin) VALUES
(1, 'Indépendant', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Indépendant'), '2023-01-10', '2024-03-31'),
(1, 'Association', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association'), '2024-04-01', NULL),
(2, 'Aucun', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Aucun'), '2022-06-15', '2023-11-30'),
(2, 'Association', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association'), '2023-12-01', NULL),
(3, 'Association', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association'), '2023-09-01', NULL),
(4, 'Aucun', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Aucun'), '2024-02-01', '2024-10-15'),
(4, 'Association', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association'), '2024-10-16', NULL),
(5, 'Aucun', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Aucun'), '2024-05-15', NULL),
(6, 'Indépendant', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Indépendant'), '2020-11-12', '2022-04-30'),
(6, 'Association', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association'), '2022-05-01', NULL),
(7, 'Association', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Association'), '2023-03-20', NULL),
(8, 'Indépendant', (SELECT id_statut_juridique FROM "StatutJuridique" WHERE libelle_statut = 'Indépendant'), '2020-04-10', NULL);

-- Journalisation diachronique des catégories (Amateur -> Émergent)
DELETE FROM "HistoriqueCategorie"
WHERE id_projet BETWEEN 1 AND 8;

INSERT INTO "HistoriqueCategorie" (id_projet, id_categorie, date_debut, date_fin) VALUES
(1, 1, '2023-01-10', '2024-06-30'),
(1, 2, '2024-07-01', NULL),
(2, 1, '2022-06-15', '2023-12-31'),
(2, 2, '2024-01-01', NULL),
(3, 1, '2023-09-01', NULL),
(4, 1, '2024-02-01', '2024-12-31'),
(4, 2, '2025-01-01', NULL),
(5, 1, '2024-05-15', NULL),
(6, 1, '2020-11-12', '2022-05-31'),
(6, 2, '2022-06-01', NULL),
(7, 1, '2023-03-20', '2024-09-30'),
(7, 2, '2024-10-01', NULL),
(8, 1, '2020-04-10', NULL);

-- Membres de groupes
INSERT INTO "MembreProjet" (id_projet, id_personne, date_arrivee, date_depart, role_dans_groupe) VALUES
(1, 1, '2023-01-10', NULL, 'Chant & Composition'),
(2, 2, '2022-06-15', NULL, 'Rappeur principal'),
(3, 3, '2023-09-01', NULL, 'Chant & Claviers'),
(3, 4, '2023-09-01', NULL, 'Machines & Synthétiseurs'),
(4, 5, '2024-02-01', NULL, 'Auteur-Interprète'),
(5, 6, '2024-05-15', NULL, 'Production & Voix'),
(6, 8, '2020-11-12', NULL, 'Guitare & Chant'),
(7, 9, '2023-03-20', NULL, 'Chant & Flûte'),
(8, 10, '2020-04-10', NULL, 'Rappeur & Auteur')
ON CONFLICT DO NOTHING;

-- Cycles de vie du projet
INSERT INTO "PhaseProjet" (id_phase, id_projet, nom_phase, id_type_phase, date_debut, date_fin) VALUES
(1, 1, 'Idéation', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Idéation'), '2023-01-10', '2023-08-30'),
(2, 1, 'Création', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Création'), '2023-09-01', '2024-06-30'),
(3, 1, 'Diffusion', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Diffusion'), '2024-07-01', NULL),
(4, 2, 'Diffusion', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Diffusion'), '2023-01-01', NULL),
(5, 3, 'Création', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Création'), '2023-09-01', NULL),
(6, 4, 'Diffusion', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Diffusion'), '2024-06-01', NULL),
(7, 5, 'Idéation', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Idéation'), '2024-05-15', NULL),
(8, 6, 'Diffusion', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Diffusion'), '2022-06-01', NULL),
(9, 7, 'Diffusion', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Diffusion'), '2024-10-01', NULL),
(10, 8, 'Création', (SELECT id_type_phase FROM "TypePhaseProjet" WHERE nom_phase = 'Création'), '2024-01-10', NULL)
ON CONFLICT (id_phase) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"PhaseProjet"', 'id_phase'),
	COALESCE((SELECT MAX(id_phase) FROM "PhaseProjet"), 1)
);

-- Styles musicaux attribués aux projets
INSERT INTO "ProjetStyle" (id_projet, id_style, est_style_principal) VALUES
(1, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Hyperpop' LIMIT 1), TRUE),
(1, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Emo Rap' LIMIT 1), FALSE),
(2, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Trap' LIMIT 1), TRUE),
(2, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Drill' LIMIT 1), FALSE),
(3, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Electronica' LIMIT 1), TRUE),
(3, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Ambient' LIMIT 1), FALSE),
(4, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Trap' LIMIT 1), TRUE),
(4, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Cloud Rap' LIMIT 1), FALSE),
(5, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Witch House' LIMIT 1), TRUE),
(6, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Garage Rock' LIMIT 1), TRUE),
(6, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Psychedelic Rock' LIMIT 1), FALSE),
(7, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Afrobeats' LIMIT 1), TRUE),
(7, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Contemporary Jazz' LIMIT 1), FALSE),
(8, (SELECT id_style FROM "StyleMusical" WHERE nom_style = 'Classic Hip Hop' LIMIT 1), TRUE)
ON CONFLICT DO NOTHING;

-- ==============================================================================
-- 5. ACCOMPAGNEMENT, FORMATIONS, ENTOURAGE & FINANCEMENT
-- ==============================================================================
INSERT INTO "ProgrammeAccompagnement" (id_programme, nom_programme, organisme_organisateur) VALUES
(1, 'Embrayage', 'Organisme Démo'),
(2, 'Programme Démo Bêta', 'Organisme Démo Bêta'),
(3, 'Résidences Démo', 'Fondation Démo'),
(4, 'Programme Démo Delta', 'Réseau Démo'),
(5, 'Programme Démo Epsilon', 'Association Démo'),
(6, 'Programme Live Démo', 'École Démo')
ON CONFLICT (id_programme) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"ProgrammeAccompagnement"', 'id_programme'),
	COALESCE((SELECT MAX(id_programme) FROM "ProgrammeAccompagnement"), 1)
);

INSERT INTO "SuiviAccompagnement" (id_projet, id_programme, annee_participation, est_laureat) VALUES
(1, 1, 2025, TRUE),
(2, 2, 2024, TRUE),
(3, 1, 2026, TRUE),
(4, 1, 2025, TRUE),
(4, 5, 2024, TRUE),
(6, 4, 2023, TRUE),
(7, 3, 2024, TRUE),
(8, 1, 2024, FALSE)
ON CONFLICT DO NOTHING;

INSERT INTO "Formation" (id_formation, nom_formation, organisme_formateur) VALUES
(1, 'Gestion administrative et droits d’auteur', 'Organisme Démo'),
(2, 'Structuration juridique en association culturelle', 'Centre de formation Démo'),
(3, 'Préparation scénique et résidence live', 'Organisme Démo'),
(4, 'Stratégie de sortie digitale et promotion', 'Centre de formation Démo'),
(5, 'Négociation de contrats et droits voisins', 'Association Démo'),
(6, 'Gestion de tournées et logistique export', 'Bureau Export Démo')
ON CONFLICT (id_formation) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"Formation"', 'id_formation'),
	COALESCE((SELECT MAX(id_formation) FROM "Formation"), 1)
);

INSERT INTO "ProjetFormation" (id_projet, id_formation, date_suivi) VALUES
(1, 1, '2025-02-15'),
(1, 3, '2025-04-10'),
(2, 2, '2024-05-20'),
(3, 1, '2025-10-12'),
(4, 1, '2025-02-15'),
(4, 4, '2025-03-20'),
(6, 3, '2023-04-05'),
(6, 6, '2024-01-18'),
(7, 5, '2024-11-18')
ON CONFLICT DO NOTHING;

INSERT INTO "StructureProfessionnelle" (id_structure, nom_structure, type_structure, contact_email, pays) VALUES
(1, 'Label Démo Alpha', 'Label', 'label.alpha@example.com', 'Suisse'),
(2, 'Management Démo', 'Management', 'management@example.com', 'Suisse'),
(3, 'Studio Démo', 'Studio', 'studio@example.com', 'Suisse'),
(4, 'Booking Démo', 'Agence Booking', 'booking@example.com', 'Suisse'),
(5, 'Label Démo Bêta', 'Label', 'label.beta@example.com', 'Suisse'),
(6, 'Édition Démo', 'Édition', 'edition@example.com', 'Suisse')
ON CONFLICT (id_structure) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"StructureProfessionnelle"', 'id_structure'),
	COALESCE((SELECT MAX(id_structure) FROM "StructureProfessionnelle"), 1)
);

INSERT INTO "ProjetStructure" (id_projet, id_structure, date_debut, date_fin) VALUES
(1, 3, '2024-01-15', NULL),
(2, 1, '2023-06-01', NULL),
(4, 2, '2025-01-10', NULL),
(6, 4, '2022-09-01', NULL),
(6, 5, '2021-03-15', NULL),
(7, 6, '2024-06-01', NULL),
(8, 3, '2022-02-01', '2023-08-30')
ON CONFLICT DO NOTHING;

INSERT INTO "SoutienFinancier" (id_soutien, id_projet, bailleur, montant_demande, montant_octroye, annee, statut) VALUES
(1, 1, 'Collectivité Démo Alpha', 5000.00, 3000.00, 2024, 'Octroyé'),
(2, 1, 'Fondation Démo Alpha', 8000.00, 5000.00, 2025, 'Octroyé'),
(3, 2, 'Collectivité Démo Bêta', 4000.00, 4000.00, 2023, 'Octroyé'),
(4, 4, 'Fondation Démo Bêta', 6000.00, 0.00, 2025, 'Refusé'),
(5, 6, 'Collectivité Démo Gamma', 10000.00, 7500.00, 2023, 'Octroyé'),
(6, 6, 'Fondation Démo Gamma', 8000.00, 8000.00, 2024, 'Octroyé'),
(7, 7, 'Collectivité Démo Delta', 4500.00, 3500.00, 2024, 'Octroyé'),
(8, 8, 'Collectivité Démo Alpha', 3000.00, 1500.00, 2023, 'Octroyé')
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"SoutienFinancier"', 'id_soutien'),
	COALESCE((SELECT MAX(id_soutien) FROM "SoutienFinancier"), 1)
);

-- ==============================================================================
-- 6. ASSETS, MORCEAUX, COLLABORATIONS & EVENEMENTS MARQUANTS
-- ==============================================================================
INSERT INTO "Asset" (id_asset, id_projet, id_personne, id_type, titre, date_creation, metadonnees, chemin_stockage, est_featured_roster) VALUES
(1, 1, NULL, 1, 'Projet Alpha - EP Démo', '2024-05-10', '{"nb_titres": 5, "format": "Digital", "isrc_root": "CH00000"}', '/storage/assets/projet_alpha_ep.zip', FALSE),
(2, 1, NULL, 2, 'Clip Démo - Signal Rouge', '2024-06-01', '{"realisateur": "Studio Démo", "youtube_url": "https://example.com/video-1"}', '/storage/assets/signal_rouge.mp4', TRUE),
(3, 1, NULL, 3, 'Presskit Projet Alpha 2025', '2025-01-15', '{"version": "2.1", "pages": 4}', '/storage/assets/presskit_projet_alpha.pdf', TRUE),
(4, 4, NULL, 2, 'Projet Delta - Session Live', '2024-09-12', '{"realisateur": "Studio Démo", "youtube_url": "https://example.com/video-2"}', '/storage/assets/projet_delta_live.mp4', TRUE),
(5, 6, NULL, 4, 'Fiche technique et rider', '2024-04-01', '{"patch_inputs": 16, "retours": 4}', '/storage/assets/projet_zeta_rider.pdf', TRUE),
(6, 6, NULL, 2, 'Session live de démonstration', '2024-05-20', '{"youtube_url": "https://example.com/video-3"}', '/storage/assets/projet_zeta_live.mp4', TRUE),
(7, 7, NULL, 1, 'Projet Eta - Album "Horizons"', '2024-11-01', '{"label": "Label Démo", "format": "Vinyle / Digital"}', '/storage/assets/projet_eta_horizons.zip', TRUE),
(8, NULL, 1, 3, 'Photo de presse Artiste Alpha', '2024-02-10', '{"photographe": "Photographe Démo"}', '/storage/avatars/artiste_alpha.jpg', FALSE),
(9, 8, NULL, 1, 'Projet Thêta - Single "Ville Haute"', '2023-10-15', '{"format": "Digital"}', '/storage/assets/projet_theta_ville_haute.wav', TRUE)
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"Asset"', 'id_asset'),
	(SELECT MAX(id_asset) FROM "Asset")
);

INSERT INTO "Morceau" (id_morceau, id_projet, titre_morceau, duree, annee_composition, date_sortie, est_reprise, code_isrc, cle_suisa, est_top_track) VALUES
(1, 1, 'Signal Rouge', '00:03:15', 2024, '2024-06-01', FALSE, 'CH0000000001', 'DEMO-0001', TRUE),
(2, 1, 'Vitesse Lumière', '00:02:45', 2024, '2024-05-10', FALSE, 'CH0000000002', 'DEMO-0002', TRUE),
(3, 1, 'Éclipse', '00:03:40', 2024, '2024-05-10', FALSE, 'CH0000000003', 'DEMO-0003', TRUE),
(4, 2, 'Ligne Nord', '00:03:10', 2023, '2023-04-12', FALSE, 'CH0000000004', 'DEMO-0004', TRUE),
(5, 4, 'Rivage', '00:02:30', 2024, '2024-06-15', FALSE, 'CH0000000005', 'DEMO-0005', TRUE),
(6, 6, 'Écho Solaire', '00:04:12', 2023, '2023-09-01', FALSE, 'CH0000000006', 'DEMO-0006', TRUE),
(7, 7, 'Matin Gris', '00:03:55', 2024, '2024-11-01', FALSE, 'CH0000000007', 'DEMO-0007', TRUE),
(8, 8, 'Ville Haute', '00:03:05', 2023, '2023-10-15', FALSE, 'CH0000000008', 'DEMO-0008', TRUE)
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"Morceau"', 'id_morceau'),
	(SELECT MAX(id_morceau) FROM "Morceau")
);

INSERT INTO "ContenuAsset" (id_asset, id_morceau, ordre_apparition) VALUES
(1, 1, 1),
(1, 2, 2),
(1, 3, 3),
(7, 7, 1),
(9, 8, 1)
ON CONFLICT DO NOTHING;

INSERT INTO "CollaborationMorceau" (id_collaboration, id_morceau, id_projet, id_personne, role_artistique, date_collaboration) VALUES
(1, 1, NULL, 4, 'Mixage & Mastering', '2024-04-15'),
(2, 2, 2, NULL, 'Featuring (Projet Bêta)', '2024-03-20'),
(3, 4, NULL, 6, 'Beatmaker / Production', '2023-02-10'),
(4, 5, NULL, 1, 'Co-composition', '2024-05-01'),
(5, 6, NULL, 8, 'Production arrangement', '2023-07-15'),
(6, 8, NULL, 2, 'Featuring (Artiste Bêta)', '2023-08-20')
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"CollaborationMorceau"', 'id_collaboration'),
	COALESCE((SELECT MAX(id_collaboration) FROM "CollaborationMorceau"), 1)
);


INSERT INTO "CompositionMorceau" (id_composition, id_morceau, id_personne, role_composition, pourcentage_droits) VALUES
(1, 1, 1, 'Compositeur & Parolier', 100.00),
(2, 2, 1, 'Compositeur', 60.00),
(3, 2, 2, 'Parolier (Feat)', 40.00),
(4, 4, 2, 'Auteur', 50.00),
(5, 5, 5, 'Auteur-Compositeur', 100.00),
(6, 6, 8, 'Compositeur', 100.00),
(7, 7, 9, 'Parolière & Compositrice', 100.00),
(8, 8, 10, 'Auteur-Interprète', 100.00)
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"CompositionMorceau"', 'id_composition'),
	COALESCE((SELECT MAX(id_composition) FROM "CompositionMorceau"), 1)
);


INSERT INTO "EvenementParcours" (id_evenement, id_projet, type_evenement, titre_evenement, date_evenement, media_source, url_preuve) VALUES
(1, 1, 'Passage Radio', 'Diffusion du single Signal Rouge', '2024-06-20', 'Radio Démo', 'https://example.com/evenements/1'),
(2, 1, 'Sélection Tremplin', 'Sélection dans un tremplin fictif', '2025-03-01', 'Festival Démo', 'https://example.com/evenements/2'),
(3, 4, 'Presse', 'Chronique découverte fictive', '2024-11-15', 'Média Démo', 'https://example.com/evenements/3'),
(4, 6, 'Sélection Showcase', 'Sélection dans un showcase fictif', '2023-03-24', 'Showcase Démo', 'https://example.com/evenements/4'),
(5, 6, 'Concert Remarquable', 'Concert dans un festival fictif', '2024-06-02', 'Festival Démo', 'https://example.com/evenements/5'),
(6, 7, 'Passage Radio', 'Interview et session acoustique', '2025-01-10', 'Radio Démo', 'https://example.com/evenements/6'),
(7, 2, 'Passage Radio', 'Session freestyle fictive', '2023-11-05', 'Radio Démo', 'https://example.com/evenements/7'),
(8, 8, 'Presse', 'Article fictif sur une scène locale', '2023-12-18', 'Média Démo', 'https://example.com/evenements/8')
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"EvenementParcours"', 'id_evenement'),
	COALESCE((SELECT MAX(id_evenement) FROM "EvenementParcours"), 1)
);


-- ==============================================================================
-- 7. LIEUX, TOURNÉES, CONCERTS & LOGISTIQUE
-- ==============================================================================
INSERT INTO "Venue" (id_venue, nom_venue, adresse, ville, npa, pays, valeur_pairs, est_festival) VALUES
(1, 'Salle Démo Neuchâtel', 'Adresse fictive 101', 'Neuchâtel', '2000', 'Suisse', 8, FALSE),
(2, 'Club Démo Fribourg', 'Adresse fictive 102', 'Fribourg', '1700', 'Suisse', 10, FALSE),
(3, 'Festival Démo Neuchâtel', 'Adresse fictive 103', 'Neuchâtel', '2000', 'Suisse', 9, TRUE),
(4, 'Salle Démo Lausanne', 'Adresse fictive 104', 'Lausanne', '1003', 'Suisse', 8, FALSE),
(5, 'Club Démo Paris', 'Adresse fictive 105', 'Paris', '75012', 'France', 7, FALSE),
(6, 'Salle Démo Fribourg', 'Adresse fictive 106', 'Fribourg', '1700', 'Suisse', 9, FALSE),
(7, 'Salle Démo Nyon', 'Adresse fictive 107', 'Nyon', '1260', 'Suisse', 8, FALSE),
(8, 'Festival Démo Lausanne', 'Adresse fictive 108', 'Lausanne', '1003', 'Suisse', 9, TRUE)
ON CONFLICT (id_venue) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"Venue"', 'id_venue'),
	COALESCE((SELECT MAX(id_venue) FROM "Venue"), 1)
);

INSERT INTO "Tournee" (id_tournee, id_projet, nom_tournee, date_debut_globale, date_fin_globale) VALUES
(1, 1, 'Tournée Alpha', '2024-10-01', '2025-05-30'),
(2, 6, 'Tournée Zêta', '2024-05-01', '2024-06-15'),
(3, 4, 'Tournée Delta', '2025-03-01', '2025-08-30'),
(4, 7, 'Tournée Eta', '2024-10-15', '2025-02-28'),
(5, 2, 'Tournée Bêta', '2023-09-01', '2024-04-30'),
(6, 8, 'Tournée Thêta', '2023-11-01', '2024-02-15')
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"Tournee"', 'id_tournee'),
	COALESCE((SELECT MAX(id_tournee) FROM "Tournee"), 1)
);


INSERT INTO "Concert" (id_concert, id_projet, id_venue, id_tournee, date_heure, type_evenement, zone_geographique, cachet_brut, est_optionnel) VALUES
(1, 1, 1, 1, '2024-10-18 21:00:00', 'Concert', 'Local/Neuchâtel', 600.00, FALSE),
(2, 1, 2, 1, '2025-02-14 22:00:00', 'Concert', 'Hors Canton', 1200.00, FALSE),
(3, 1, 5, 1, '2025-05-10 20:30:00', 'Concert', 'International/Hors Suisse', 800.00, FALSE),
(4, 1, 1, NULL, '2025-01-20 10:00:00', 'Résidence', 'Local/Neuchâtel', 400.00, FALSE),
(5, 4, 3, 3, '2025-06-13 19:30:00', 'Concert', 'Local/Neuchâtel', 2500.00, FALSE),
(6, 6, 2, 2, '2024-06-02 18:00:00', 'Concert', 'Hors Canton', 1800.00, FALSE),
(7, 6, 5, 2, '2024-05-15 21:00:00', 'Concert', 'International/Hors Suisse', 950.00, FALSE),
(8, 7, 8, 4, '2024-09-14 17:00:00', 'Showcase', 'Hors Canton', 1100.00, FALSE),
(9, 2, 4, 5, '2023-10-12 21:30:00', 'Concert', 'Hors Canton', 850.00, FALSE),
(10, 8, 1, 6, '2023-12-02 20:30:00', 'Concert', 'Local/Neuchâtel', 500.00, FALSE)
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"Concert"', 'id_concert'),
	COALESCE((SELECT MAX(id_concert) FROM "Concert"), 1)
);

INSERT INTO "Setlist" (id_setlist, id_concert, id_morceau, ordre_passage) VALUES
(1, 1, 1, 1),
(2, 1, 2, 2),
(3, 1, 3, 3),
(4, 2, 1, 1),
(5, 2, 2, 2),
(6, 6, 6, 1),
(7, 8, 7, 1),
(8, 10, 8, 1)
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"Setlist"', 'id_setlist'),
	COALESCE((SELECT MAX(id_setlist) FROM "Setlist"), 1)
);


INSERT INTO "TrajetLogistique" (id_trajet, id_projet, id_concert, date_heure_depart, valeur_defrayement) VALUES
(1, 1, 2, '2025-02-14 14:00:00', 120.00),
(2, 1, 3, '2025-05-09 08:00:00', 450.00),
(3, 6, 7, '2024-05-14 07:30:00', 520.00),
(4, 2, 9, '2023-10-12 15:00:00', 90.00),
(5, 4, 5, '2025-06-13 16:00:00', 50.00),
(6, 7, 8, '2024-09-14 10:00:00', 110.00)
ON CONFLICT DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"TrajetLogistique"', 'id_trajet'),
	COALESCE((SELECT MAX(id_trajet) FROM "TrajetLogistique"), 1)
);


-- ==============================================================================
-- 8. PLATEFORMES, PRÉSENCES WEB & MÉTRIQUES D'ÉVOLUTION DIACHRONIQUE
-- ==============================================================================
INSERT INTO "Plateforme" (id_plateforme, nom_plateforme, type_plateforme) VALUES
(1, 'Instagram', 'Social Media'),
(2, 'YouTube', 'Video'),
(3, 'Spotify', 'Streaming'),
(4, 'TikTok', 'Social Media')
ON CONFLICT (id_plateforme) DO NOTHING;

INSERT INTO "Plateforme" (nom_plateforme, type_plateforme)
VALUES ('MX3', 'Musique et concerts')
ON CONFLICT (lower(trim(nom_plateforme)))
DO UPDATE SET type_plateforme = EXCLUDED.type_plateforme;

SELECT setval(
	pg_get_serial_sequence('"Plateforme"', 'id_plateforme'),
	COALESCE((SELECT MAX(id_plateforme) FROM "Plateforme"), 1)
);

INSERT INTO "PresenceWeb" (id_presence, id_projet, id_plateforme, url_profil, identifiant_api) VALUES
(1, 1, 1, 'https://example.com/projet-alpha/instagram', 'demo_alpha_insta'),
(2, 1, 2, 'https://example.com/projet-alpha/youtube', 'demo_alpha_video'),
(3, 1, 3, 'https://example.com/projet-alpha/streaming', 'demo:artist:alpha'),
(4, 4, 1, 'https://example.com/projet-delta/instagram', 'demo_delta_insta'),
(5, 4, 2, 'https://example.com/projet-delta/youtube', 'demo_delta_video'),
(6, 4, 3, 'https://example.com/projet-delta/streaming', 'demo:artist:delta'),
(7, 6, 1, 'https://example.com/projet-zeta/instagram', 'demo_zeta_insta'),
(8, 6, 2, 'https://example.com/projet-zeta/youtube', 'demo_zeta_video'),
(9, 6, 3, 'https://example.com/projet-zeta/streaming', 'demo:artist:zeta'),
(10, 2, 1, 'https://example.com/projet-beta/instagram', 'demo_beta_insta'),
(11, 2, 3, 'https://example.com/projet-beta/streaming', 'demo:artist:beta')
ON CONFLICT (id_projet, id_plateforme) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"PresenceWeb"', 'id_presence'),
	COALESCE((SELECT MAX(id_presence) FROM "PresenceWeb"), 1)
);

-- Progression temporelle sur 3 périodes (Janv 2025, Juin 2025, Janv 2026)
INSERT INTO "ReleveMetrique" (id_presence, date_releve, type_indicateur, valeur_compteur) VALUES
-- 1. Projet Alpha
(1, '2025-01-15', 'Followers', 1200),
(1, '2025-06-15', 'Followers', 1950),
(1, '2026-01-15', 'Followers', 3400),
(1, '2026-01-15', 'Likes_Reel', 680),
(2, '2025-01-15', 'Abonnes', 450),
(2, '2025-06-15', 'Abonnes', 890),
(2, '2026-01-15', 'Abonnes', 1620),
(3, '2025-01-15', 'Ecoutes_Mensuelles', 4800),
(3, '2025-06-15', 'Ecoutes_Mensuelles', 14200),
(3, '2026-01-15', 'Ecoutes_Mensuelles', 38500),
(3, '2026-01-15', 'Streams_Track_1', 48500),
(3, '2026-01-15', 'Streams_Track_2', 32100),
(3, '2026-01-15', 'Streams_Track_3', 19800),

-- 2. Projet Delta
(4, '2025-01-15', 'Followers', 4500),
(4, '2025-06-15', 'Followers', 7800),
(4, '2026-01-15', 'Followers', 11200),
(4, '2026-01-15', 'Likes_Reel', 2400),
(5, '2025-01-15', 'Abonnes', 1200),
(5, '2026-01-15', 'Abonnes', 4300),
(6, '2025-01-15', 'Ecoutes_Mensuelles', 42000),
(6, '2025-06-15', 'Ecoutes_Mensuelles', 98000),
(6, '2026-01-15', 'Ecoutes_Mensuelles', 185000),
(6, '2026-01-15', 'Streams_Track_1', 195000),

-- 3. Projet Zêta
(7, '2025-01-15', 'Followers', 2100),
(7, '2025-06-15', 'Followers', 2550),
(7, '2026-01-15', 'Followers', 2900),
(8, '2025-01-15', 'Abonnes', 800),
(8, '2026-01-15', 'Abonnes', 1450),
(9, '2025-01-15', 'Ecoutes_Mensuelles', 8900),
(9, '2025-06-15', 'Ecoutes_Mensuelles', 11800),
(9, '2026-01-15', 'Ecoutes_Mensuelles', 15400),

-- 4. Projet Bêta
(10, '2025-01-15', 'Followers', 1800),
(10, '2026-01-15', 'Followers', 3100),
(11, '2025-01-15', 'Ecoutes_Mensuelles', 12000),
(11, '2026-01-15', 'Ecoutes_Mensuelles', 24500)
ON CONFLICT (id_presence, date_releve, type_indicateur) DO UPDATE
SET valeur_compteur = EXCLUDED.valeur_compteur;

-- ==============================================================================
-- 9. COMMISSIONS D'ATTRIBUTION & ÉVALUATIONS EXPERTS (EMBRAYAGE)
-- ==============================================================================
INSERT INTO "CampagneEvaluation" (id_campagne, nom_campagne, statut, date_debut, date_fin)
VALUES (1, 'Embrayage 2025-2026', 'ouverte', '2025-07-01', '2026-06-30')
ON CONFLICT (id_campagne) DO UPDATE SET
	nom_campagne = EXCLUDED.nom_campagne,
	statut = EXCLUDED.statut,
	date_debut = EXCLUDED.date_debut,
	date_fin = EXCLUDED.date_fin;

INSERT INTO "CampagneProjet" (id_campagne, id_projet)
SELECT 1, id_projet FROM "ProjetMusical"
ON CONFLICT DO NOTHING;

INSERT INTO "CampagneJure" (id_campagne, id_expert)
SELECT 1, id_personne
FROM "Personne"
WHERE lower(email) IN (
	'gestionnaire@example.com', 'jury.alpha@example.com', 'jury.beta@example.com',
	'jury.gamma@example.com', 'jury.delta@example.com'
)
ON CONFLICT DO NOTHING;

INSERT INTO "CampagneCritere" (id_campagne, id_critere, poids, ordre)
SELECT 1, id_critere, poids, ordre
FROM "CriteresEvaluation"
WHERE type_critere IN ('objectif', 'subjectif') AND est_actif
ON CONFLICT (id_campagne, id_critere) DO UPDATE SET
	poids = EXCLUDED.poids,
	ordre = EXCLUDED.ordre;

INSERT INTO "BilanEvaluation" (id_bilan, id_campagne, id_projet, date_evaluation, id_categorie_obtenue, remarques, statut_selection) VALUES
(1, 1, 1, '2025-06-30', 2, 'Projet très prometteur. Structuration administrative réussie et belle progression scénique.', 'selectionne'),
(2, 1, 4, '2025-06-30', 2, 'Excellents retours streaming. Signature d’un management professionnel en cours.', 'selectionne'),
(3, 1, 6, '2024-12-15', 2, 'Groupe très soudé, dates en export confirmées et autonomie technique exemplaire.', 'selectionne'),
(4, 1, 2, '2024-06-30', 2, 'Bonne maîtrise technique mais travail à poursuivre sur la cohérence de l’univers visuel.', 'selectionne'),
(5, 1, 3, '2025-06-30', 1, 'Projet encore en gestation, manque de matière scénique originale.', 'en_attente'),
(6, 1, 8, '2024-06-30', 1, 'Dossier incomplet et absence d’entourage professionnel.', 'refuse')
ON CONFLICT (id_bilan) DO NOTHING;

SELECT setval(
	pg_get_serial_sequence('"BilanEvaluation"', 'id_bilan'),
	COALESCE((SELECT MAX(id_bilan) FROM "BilanEvaluation"), 1)
);

INSERT INTO "AffectationAccompagnement" (id_projet, id_expert, date_affectation)
VALUES (1, 15, '2025-07-01 09:00:00+02')
ON CONFLICT (id_projet) DO UPDATE
SET id_expert = EXCLUDED.id_expert,
    date_affectation = EXCLUDED.date_affectation;


INSERT INTO "AppreciationExpert" (id_bilan, id_expert, id_critere, note, commentaire) VALUES
-- Bilan 1 (Projet Alpha)
(1, 7, 1, 5, 'Critères d’âge et d’ancrage neuchâtelois respectés à 100%.'),
(1, 7, 2, 7, 'Identité visuelle affirmée et écriture percutante.'),
(1, 7, 3, 5, 'Très forte assiduité lors des ateliers d’accompagnement.'),
(1, 7, 4, 2, 'Dossier très bien ficelé.'),

-- Bilan 2 (Projet Delta)
(2, 7, 1, 5, 'Artiste jeune de Bevaix avec fort potentiel.'),
(2, 7, 2, 8, 'Chiffres streaming impressionnants pour un projet émergent.'),

-- Bilan 3 (Projet Zêta)
(3, 7, 2, 7, 'Excellente prestation lors du festival de démonstration.'),

-- Bilan 4 (Projet Bêta)
(4, 7, 2, 6, 'Bonne technique rap, doit étoffer sa présence en dehors du canton.'),

-- Bilan 5 (Projet Gamma)
(5, 7, 3, 4, 'Beaucoup de motivation mais set live encore trop court.'),

-- Bilan 6 (Projet Thêta)
(6, 7, 4, 1, 'Manque les liens d’écoute et budget prévisionnel absent.')
ON CONFLICT (id_bilan, id_critere) DO NOTHING;

INSERT INTO "NoteEvaluateur" (id_bilan, id_expert, note) VALUES
(1, 7, 18),
(1, 11, 17),
(1, 13, 19),
(2, 12, 18),
(2, 14, 16),
(3, 11, 18)
ON CONFLICT (id_bilan, id_expert) DO UPDATE SET note = EXCLUDED.note;