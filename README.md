# Vue Carter

Vue Carter est une application web de suivi et d'accompagnement de projets musicaux, réalisée dans le cadre d'un travail de bachelor IG-TPart 2026. Elle centralise les profils d'artistes, les projets, les membres, les concerts, les morceaux, les documents, les campagnes d'évaluation et les indicateurs de parcours.

L'application propose des espaces adaptés aux artistes, gestionnaires, membres de jury, accompagnants et administrateurs. Elle repose sur Vue 3 et Tailwind CSS pour l'interface, FastAPI pour l'API, PostgreSQL pour les données et Metabase pour les analyses.

> Vue Carter est distribué uniquement sous forme de code source dans ce dépôt GitHub. Aucune version compilée ou installable n'est fournie : l'application doit être lancée en environnement de développement.

## Prérequis

Avant de commencer, installer :

- [Git](https://git-scm.com/);
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) avec Docker Compose;
- Python avec le module `venv`;
- Node.js `22.18` ou une version `24.12` ou supérieure;
- npm, fourni avec Node.js.

Les ports suivants doivent être disponibles :

| Service | Port local |
|---|---:|
| Frontend Vue | `5173` |
| API FastAPI | `8000` |
| Metabase | `3000` |
| PostgreSQL | `5433` |

Les commandes ci-dessous sont prévues pour Windows PowerShell.

## Installation

### 1. Récupérer le projet

```powershell
git clone https://github.com/CyriGIT/ParcoursArtistes.git
cd ParcoursArtistes
```

### 2. Configurer l'environnement

Créer le fichier local `.env` à partir du modèle fourni :

```powershell
Copy-Item .env.example .env
```

Le cœur de l'application peut fonctionner localement sans clé de service externe. Pour sécuriser les jetons de connexion, ajouter toutefois une valeur aléatoire propre à votre installation dans `.env` :

```dotenv
SECRET_KEY=remplacer-par-une-longue-valeur-aleatoire
```

Ne jamais enregistrer le fichier `.env` ni de véritables clés d'API dans Git.

### 3. Installer le backend Python

Depuis la racine du dépôt :

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Installer le frontend

Les sources Vue et leur configuration sont déjà présentes. Il ne faut pas exécuter `npm create vue`.

```powershell
Set-Location frontend
npm install
Set-Location ..
```

### 5. Démarrer PostgreSQL et Metabase

Ouvrir Docker Desktop, puis exécuter depuis la racine du dépôt :

```powershell
docker compose up -d
docker compose exec postgres pg_isready -U postgres -d parcours_artiste
```

La seconde commande doit indiquer que PostgreSQL accepte les connexions.

### 6. Initialiser une base neuve

Exécuter le script de création V12 une seule fois sur une base vide :

```powershell
Get-Content -Raw .\2026-09-06_creation_base_parcoursartiste_v12.sql |
    docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d parcours_artiste
```

Les migrations SQL historiques ne sont pas nécessaires lorsque la base est créée directement avec ce script.

### 7. Charger les données de démonstration (facultatif)

Pour découvrir immédiatement les différents parcours de l'application :

```powershell
Get-Content -Raw .\2026-09-06_Insert-MockData_V7.sql |
    docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d parcours_artiste
```

Ces données sont destinées uniquement au développement. Les comptes de démonstration utilisent tous le mot de passe `1234` :

| Rôle | Adresse e-mail |
|---|---|
| Administrateur | `admin@example.com` |
| Gestionnaire | `gestionnaire@example.com` |
| Jury | `jury.alpha@example.com` |
| Artiste | `artiste.alpha@example.com` |
| Accompagnante | `accompagnante@example.com` |

Sans données de démonstration, un nouvel artiste peut créer son compte depuis la page d'inscription. Les comptes associés aux autres rôles doivent être créés ou invités par l'administration.

## Lancement

Vue Carter utilise trois processus. Exécuter chaque bloc dans un terminal PowerShell distinct.

### Terminal 1 : services Docker

```powershell
docker compose up -d
```

Cette commande démarre PostgreSQL et Metabase.

### Terminal 2 : API FastAPI

Depuis la racine du dépôt :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
python -m uvicorn backend_etl.main:app --reload --port 8000
```

### Terminal 3 : frontend Vue

```powershell
Set-Location frontend
npm run dev
```

Une fois les services démarrés :

- application : <http://localhost:5173>;
- documentation interactive de l'API : <http://localhost:8000/docs>;
- Metabase : <http://localhost:3000>.

## Utilisation rapide

1. Ouvrir <http://localhost:5173> puis se connecter avec un compte de démonstration, ou créer un compte artiste.
2. Dans l'espace artiste, créer ou sélectionner un projet musical.
3. Compléter le profil du projet, puis renseigner ses membres, morceaux, concerts, documents, images et informations d'accompagnement.
4. Relier le projet à Spotify ou MX3 lorsque les clés correspondantes sont configurées dans `.env`.
5. Utiliser les espaces de gestion et d'expertise pour organiser les campagnes, attribuer les projets, effectuer les évaluations et consulter les analyses.

### Rôles disponibles

| Rôle | Fonctions principales |
|---|---|
| Artiste | Gérer son profil et ses projets musicaux, membres, concerts, morceaux et assets |
| Gestionnaire Case à Chocs | Organiser les campagnes, les affectations et le suivi des projets |
| Jury | Consulter et évaluer les projets qui lui sont attribués |
| Accompagnant | Suivre les projets qui lui sont affectés et consulter leurs analyses |
| Administrateur | Administrer les utilisateurs et les référentiels, et accéder aux différents espaces |

## Services optionnels

Les clés sont lues uniquement par FastAPI depuis le fichier `.env` à la racine. Elles ne doivent jamais être placées dans `frontend/.env` ni dans une variable préfixée par `VITE_`.

### Spotify

Renseigner `SPOTIFY_CLIENT_ID` et `SPOTIFY_CLIENT_SECRET` pour rechercher un artiste, consulter son catalogue, importer une sélection et synchroniser ses métriques publiques.

### MX3

Renseigner `SRGSSR_MX3_CONSUMER_KEY` et `SRGSSR_MX3_CONSUMER_SECRET` pour rechercher un groupe, consulter ses concerts et synchroniser ses métriques.

### Metabase

1. Ouvrir <http://localhost:3000> et terminer la configuration initiale.
2. Ajouter PostgreSQL avec l'hôte `postgres`, le port `5432`, la base `parcours_artiste`, l'utilisateur `postgres` et le mot de passe de développement `mysecretpassword`.
3. Créer un tableau de bord à partir des vues `analytics_*` présentes dans la base.
4. Activer l'intégration statique dans Metabase.
5. Renseigner `METABASE_EMBEDDING_SECRET_KEY`, `METABASE_DASHBOARD_ID` et `METABASE_SITE_URL=http://localhost:3000` dans `.env`.
6. Recréer Metabase et redémarrer FastAPI :

```powershell
docker compose up -d --force-recreate metabase
```

La page `/expert/analytics` demande à FastAPI une URL d'intégration signée. La clé Metabase n'est jamais envoyée au frontend.

### Stockage des fichiers

Les fichiers téléversés sont stockés dans `data/uploads` et servis sous <http://localhost:8000/uploads>. Les variables suivantes permettent d'adapter ce comportement :

- `ASSET_STORAGE_DIR` : dossier de stockage;
- `ASSET_PUBLIC_BASE_URL` : URL publique des fichiers;
- `ASSET_MAX_BYTES` : taille maximale d'un fichier, 25 Mo par défaut.

## Vérification

Depuis la racine du dépôt, avec l'environnement Python activé :

```powershell
python test_connexion.py
python -m unittest discover -s backend_etl/tests -v
```

Pour vérifier le frontend :

```powershell
Set-Location frontend
npm run type-check
npm run build
```

La commande `npm run build` sert uniquement à vérifier que les sources peuvent être compilées. Elle n'est pas nécessaire au lancement avec `npm run dev`.

## Arrêt

Arrêter les serveurs FastAPI et Vite avec `Ctrl+C`, puis arrêter les conteneurs :

```powershell
docker compose down
```

Cette commande conserve les données dans les volumes Docker. La commande `docker compose down -v` les supprimerait définitivement.

## Architecture et documentation

- [Architecture actuelle](Documentation/Architecture-ASIS)
- [Architecture cible](Documentation/ArchitectureCible.mmd)
