# Endpoints de synchronisation des données externes (Spotify, ...)
# - POST /etl/sync/{platform} : rafraîchit les métriques agrégées et les persiste (ReleveMetrique)
# - GET  /etl/spotify/{projectId}/catalog : albums + tracklist, renvoyés à la volée (non persistés,
#   conformément aux CGU Spotify qui interdisent la mise en cache au-delà de l'usage immédiat)

from datetime import date
import json
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend_etl.core.dependencies import get_current_user
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur
from backend_etl.schemas.etl import (
    ConnectorStatusResponse,
    EtlSyncRequest,
    EtlSyncResponse,
    Mx3Band,
    Mx3BandSearchResponse,
    Mx3ConnectRequest,
    Mx3ConnectResponse,
    Mx3Gig,
    Mx3GigsResponse,
    ProjectConnectorsResponse,
    SpotifyAlbum,
    SpotifyCatalogResponse,
    SpotifyConnectRequest,
    SpotifyConnectResponse,
    SpotifyImportImageResponse,
    SpotifyImportRequest,
    SpotifyImportResponse,
    SpotifyTrack,
    SyncedMetricResponse,
)
from backend_etl.services.mx3_service import (
    Mx3ApiError,
    Mx3AuthError,
    Mx3NotFoundError,
    mx3_service,
)
from backend_etl.services.asset_storage import delete_managed_file
from backend_etl.services.spotify_service import (
    SpotifyApiError,
    SpotifyAuthError,
    SpotifyNotFoundError,
    spotify_service,
)

router = APIRouter(prefix="/etl", tags=["ETL"])

SPOTIFY_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")


def _raise_spotify_import_integrity_error(db: Session, error: IntegrityError) -> None:
    db.rollback()
    constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    detail = (
        "Ce morceau est déjà rattaché à un autre projet avec le même code ISRC."
        if constraint_name == "Morceau_code_isrc_key"
        else "Impossible d’enregistrer la sélection Spotify à cause d’un conflit de données."
    )
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from error


def _execute_spotify_import_write(db: Session, statement, parameters: dict):
    try:
        return db.execute(statement, parameters)
    except IntegrityError as error:
        _raise_spotify_import_integrity_error(db, error)


def _extract_spotify_artist_id(identifiant_api: str) -> str:
    value = identifiant_api.strip()
    if value.startswith(("http://", "https://")):
        parsed_url = urlparse(value)
        path_parts = parsed_url.path.strip("/").split("/")
        is_artist_url = (
            parsed_url.netloc.lower() == "open.spotify.com"
            and len(path_parts) == 2
            and path_parts[0] == "artist"
        )
        artist_id = path_parts[1] if is_artist_url else ""
    else:
        artist_id = value.rsplit(":", 1)[-1]
    if not SPOTIFY_ID_PATTERN.fullmatch(artist_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Identifiant Spotify invalide. Reliez à nouveau le projet à un artiste Spotify.",
        )
    return artist_id


def _assert_project_access(
    db: Session,
    current_user: Utilisateur,
    project_id: int,
    *,
    write: bool = False,
) -> None:
    if current_user.role == "accompagnant":
        if write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès en lecture seule.")
        assignment = db.execute(
            text('''
                SELECT 1
                FROM "AffectationAccompagnement"
                WHERE id_projet = :project_id AND id_expert = :id_personne
            '''),
            {"project_id": project_id, "id_personne": current_user.id_personne},
        ).first()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce projet ne vous est pas affecté.",
            )
        return
    if current_user.role != "artiste":
        return
    membership = db.execute(
        text('''
            SELECT 1
            FROM "MembreProjet" mp
            WHERE mp.id_projet = :project_id
              AND mp.id_personne = :id_personne
              AND mp.date_depart IS NULL
        '''),
        {"project_id": project_id, "id_personne": current_user.id_personne},
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce projet ne vous appartient pas.",
        )


def _assert_project_exists(db: Session, project_id: int) -> None:
    project = db.execute(
        text('SELECT 1 FROM "ProjetMusical" WHERE id_projet = :project_id'),
        {"project_id": project_id},
    ).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable.",
        )


def _connection_platform_id(db: Session, project_id: int, platform_name: str) -> int | None:
    platform = db.execute(text('''
        SELECT plateforme.id_plateforme, plateforme.est_actif,
               EXISTS (
                   SELECT 1 FROM "PresenceWeb" presence
                   WHERE presence.id_projet = :project_id
                     AND presence.id_plateforme = plateforme.id_plateforme
               ) AS already_connected
        FROM "Plateforme" plateforme
        WHERE lower(plateforme.nom_plateforme) = lower(:platform_name)
    '''), {"project_id": project_id, "platform_name": platform_name}).mappings().first()
    if not platform:
        return None
    if not platform["est_actif"] and not platform["already_connected"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La plateforme {platform_name} est désactivée.",
        )
    return platform["id_plateforme"]


def _get_spotify_presence(db: Session, project_id: int) -> str:
    presence = db.execute(
        text('''
            SELECT pw.id_presence, pw.identifiant_api
            FROM "PresenceWeb" pw
            JOIN "Plateforme" pl ON pl.id_plateforme = pw.id_plateforme
            WHERE pw.id_projet = :project_id AND pl.nom_plateforme = 'Spotify'
        '''),
        {"project_id": project_id},
    ).mappings().first()

    if not presence or not presence["identifiant_api"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun profil Spotify lié à ce projet.",
        )
    return presence


def _get_mx3_presence(db: Session, project_id: int):
    presence = db.execute(
        text('''
            SELECT pw.id_presence, pw.identifiant_api
            FROM "PresenceWeb" pw
            JOIN "Plateforme" pl ON pl.id_plateforme = pw.id_plateforme
            WHERE pw.id_projet = :project_id AND lower(pl.nom_plateforme) = 'mx3'
        '''),
        {"project_id": project_id},
    ).mappings().first()
    if not presence or not presence["identifiant_api"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun groupe MX3 lié à ce projet.",
        )
    return presence


def _mx3_band_response(band: dict) -> Mx3Band:
    return Mx3Band(
        id=int(band["id"]),
        name=band.get("name") or "Groupe sans nom",
        city=band.get("city"),
        profileUrl=band.get("public_page_url") or band.get("permalink"),
        imageUrl=band.get("url_for_image_list") or band.get("image"),
    )


def _upsert_metrics(db: Session, id_presence: int, metrics: dict[str, int], snapshot_date: date) -> None:
    for indicator, value in metrics.items():
        db.execute(
            text('''
                INSERT INTO "ReleveMetrique" (
                    id_presence, date_releve, type_indicateur, valeur_compteur
                )
                VALUES (:id_presence, :date_releve, :type_indicateur, :valeur_compteur)
                ON CONFLICT (id_presence, date_releve, type_indicateur)
                DO UPDATE SET valeur_compteur = EXCLUDED.valeur_compteur
            '''),
            {
                "id_presence": id_presence,
                "date_releve": snapshot_date,
                "type_indicateur": indicator,
                "valeur_compteur": value,
            },
        )


@router.get("/projects/{project_id}/connectors", response_model=ProjectConnectorsResponse)
def get_project_connectors(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _assert_project_exists(db, project_id)
    _assert_project_access(db, current_user, project_id)

    presences = db.execute(
        text('''
            SELECT lower(pl.nom_plateforme) AS platform,
                   pw.url_profil AS "profileUrl",
                   pw.identifiant_api AS "externalId",
                   COALESCE(latest_metrics.items, '[]'::jsonb) AS metrics,
                   latest_metrics.last_sync AS "lastSync"
            FROM "PresenceWeb" pw
            JOIN "Plateforme" pl ON pl.id_plateforme = pw.id_plateforme
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(
                           jsonb_build_object(
                               'type', latest.type_indicateur,
                               'value', latest.valeur_compteur,
                               'date', latest.date_releve::text
                           )
                           ORDER BY latest.type_indicateur
                       ) AS items,
                       MAX(latest.date_releve)::text AS last_sync
                FROM (
                    SELECT DISTINCT ON (rm.type_indicateur)
                           rm.type_indicateur, rm.valeur_compteur, rm.date_releve
                    FROM "ReleveMetrique" rm
                    WHERE rm.id_presence = pw.id_presence
                    ORDER BY rm.type_indicateur, rm.date_releve DESC, rm.id_releve DESC
                ) latest
            ) latest_metrics ON TRUE
            WHERE pw.id_projet = :project_id
              AND lower(pl.nom_plateforme) IN ('spotify', 'mx3')
        '''),
        {"project_id": project_id},
    ).mappings().all()

    statuses = {
        "spotify": ConnectorStatusResponse(connected=False),
        "mx3": ConnectorStatusResponse(connected=False),
    }
    for presence in presences:
        metrics = presence["metrics"]
        primary_metric = metrics[0] if metrics else None
        is_connected = True
        if presence["platform"] == "spotify":
            spotify_id = (presence["externalId"] or "").strip().rsplit(":", 1)[-1]
            is_connected = bool(SPOTIFY_ID_PATTERN.fullmatch(spotify_id))
        statuses[presence["platform"]] = ConnectorStatusResponse(
            connected=is_connected,
            profileUrl=presence["profileUrl"] if is_connected else None,
            externalId=presence["externalId"] if is_connected else None,
            metrics=metrics,
            metricValue=primary_metric["value"] if primary_metric else None,
            metricType=primary_metric["type"] if primary_metric else None,
            lastSync=presence["lastSync"],
        )

    return ProjectConnectorsResponse(**statuses)


@router.get("/mx3/bands", response_model=Mx3BandSearchResponse)
def search_mx3_bands(
    query: str,
    current_user: Utilisateur = Depends(get_current_user),
):
    del current_user
    clean_query = query.strip()
    if len(clean_query) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Saisissez au moins 2 caractères pour rechercher un groupe MX3.",
        )
    try:
        bands = mx3_service.search_bands(clean_query)
    except Mx3AuthError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except Mx3ApiError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    return Mx3BandSearchResponse(
        bands=[_mx3_band_response(band) for band in bands if band.get("id") is not None]
    )


@router.put("/mx3/{project_id}/connect", response_model=Mx3ConnectResponse)
def connect_mx3(
    project_id: int,
    payload: Mx3ConnectRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _assert_project_exists(db, project_id)
    _assert_project_access(db, current_user, project_id, write=True)
    id_plateforme = _connection_platform_id(db, project_id, "MX3")
    try:
        band = mx3_service.get_band(payload.bandId)
    except Mx3AuthError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except Mx3NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except Mx3ApiError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    normalized_band = _mx3_band_response(band)
    if id_plateforme is None:
        id_plateforme = db.execute(
            text('''
            INSERT INTO "Plateforme" (nom_plateforme, type_plateforme)
            VALUES ('MX3', 'Musique et concerts')
            ON CONFLICT (lower(trim(nom_plateforme)))
            DO UPDATE SET type_plateforme = EXCLUDED.type_plateforme
            RETURNING id_plateforme
        ''')
        ).scalar_one()
    db.execute(
        text('''
            INSERT INTO "PresenceWeb" (id_projet, id_plateforme, url_profil, identifiant_api)
            VALUES (:project_id, :id_plateforme, :url_profil, :band_id)
            ON CONFLICT (id_projet, id_plateforme)
            DO UPDATE SET url_profil = EXCLUDED.url_profil, identifiant_api = EXCLUDED.identifiant_api
        '''),
        {
            "project_id": project_id,
            "id_plateforme": id_plateforme,
            "url_profil": normalized_band.profileUrl or "https://mx3.ch",
            "band_id": str(normalized_band.id),
        },
    )
    db.commit()
    return Mx3ConnectResponse(connected=True, band=normalized_band)


@router.get("/mx3/{project_id}/gigs", response_model=Mx3GigsResponse)
def get_mx3_gigs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _assert_project_exists(db, project_id)
    _assert_project_access(db, current_user, project_id)
    presence = _get_mx3_presence(db, project_id)
    try:
        band_id = int(presence["identifiant_api"])
        performances = mx3_service.get_band_gigs(band_id)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Identifiant MX3 invalide.") from error
    except Mx3AuthError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except Mx3NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except Mx3ApiError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    gigs = [
        Mx3Gig(
            name=performance.get("name") or "Concert MX3",
            date=performance.get("date") or "",
            bandName=performance.get("band_name"),
            stageName=performance.get("stage_name"),
            location=performance.get("location"),
            locationUrl=performance.get("location_url"),
            ticketUrl=performance.get("shopping_url"),
        )
        for performance in performances
    ]
    return Mx3GigsResponse(bandId=band_id, gigs=gigs)


@router.post("/sync/{platform}", response_model=EtlSyncResponse)
def sync_platform(
    platform: str,
    payload: EtlSyncRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    if platform not in {"spotify", "mx3"}:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Synchronisation non implémentée pour la plateforme '{platform}'.",
        )

    _assert_project_exists(db, payload.projectId)
    _assert_project_access(db, current_user, payload.projectId, write=True)
    snapshot_date = date.today()

    if platform == "mx3":
        presence = _get_mx3_presence(db, payload.projectId)
        try:
            band_id = int(presence["identifiant_api"])
            metrics = mx3_service.get_band_stats(band_id)
        except (TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Identifiant MX3 invalide.",
            ) from error
        except Mx3AuthError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except Mx3NotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except Mx3ApiError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    else:
        presence = _get_spotify_presence(db, payload.projectId)
        artist_id = _extract_spotify_artist_id(presence["identifiant_api"])
        try:
            stats = spotify_service.get_artist_stats(artist_id)
        except SpotifyAuthError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except SpotifyNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except SpotifyApiError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        metrics = {"Followers": stats["followers"]}

    _upsert_metrics(db, presence["id_presence"], metrics, snapshot_date)
    db.commit()

    return EtlSyncResponse(
        platform=platform,
        syncedAt=snapshot_date.isoformat(),
        metrics=[SyncedMetricResponse(type=indicator, value=value) for indicator, value in metrics.items()],
    )


@router.get("/spotify/{project_id}/catalog", response_model=SpotifyCatalogResponse)
def get_spotify_catalog(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Récupère à la volée artiste + albums + tracklist (non persisté)."""
    _assert_project_access(db, current_user, project_id)
    presence = _get_spotify_presence(db, project_id)
    artist_id = _extract_spotify_artist_id(presence["identifiant_api"])

    try:
        artist = spotify_service.get_artist(artist_id)
        albums = spotify_service.get_artist_albums(artist_id)
        catalog_albums = []
        for album in albums:
            tracks = spotify_service.get_album_tracks(album["id"])
            catalog_albums.append(
                SpotifyAlbum(
                    id=album["id"],
                    name=album["name"],
                    release_date=album.get("release_date", ""),
                    album_type=album.get("album_type", ""),
                    tracks=[
                        SpotifyTrack(
                            id=track["id"],
                            name=track["name"],
                            track_number=track.get("track_number", 0),
                            duration_ms=track.get("duration_ms", 0),
                            release_date=album.get("release_date", ""),
                        )
                        for track in tracks
                    ],
                )
            )
    except SpotifyAuthError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except SpotifyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SpotifyApiError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    return SpotifyCatalogResponse(
        artist_id=artist["id"],
        artist_name=artist["name"],
        followers=artist.get("followers", {}).get("total", 0),
        popularity=artist.get("popularity", 0),
        genres=artist.get("genres", []),
        albums=catalog_albums,
    )


@router.put("/spotify/{project_id}/connect", response_model=SpotifyConnectResponse)
def connect_spotify(
    project_id: int,
    payload: SpotifyConnectRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Lie un projet à un artiste Spotify (crée ou met à jour la PresenceWeb)."""
    _assert_project_access(db, current_user, project_id, write=True)
    id_plateforme = _connection_platform_id(db, project_id, "Spotify")
    if id_plateforme is None:
        raise HTTPException(status_code=404, detail="Plateforme Spotify introuvable.")
    artist_id = _extract_spotify_artist_id(payload.artistId)

    try:
        artist = spotify_service.get_artist(artist_id)
    except SpotifyAuthError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except SpotifyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SpotifyApiError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    db.execute(
        text('''
            INSERT INTO "PresenceWeb" (id_projet, id_plateforme, url_profil, identifiant_api)
            VALUES (:project_id, :id_plateforme, :url_profil, :artist_id)
            ON CONFLICT (id_projet, id_plateforme)
            DO UPDATE SET url_profil = EXCLUDED.url_profil, identifiant_api = EXCLUDED.identifiant_api
        '''),
        {
            "project_id": project_id,
            "id_plateforme": id_plateforme,
            "url_profil": f"https://open.spotify.com/artist/{artist_id}",
            "artist_id": artist_id,
        },
    )
    db.commit()

    return SpotifyConnectResponse(
        connected=True,
        artistId=artist["id"],
        artistName=artist["name"],
        followers=artist.get("followers", {}).get("total", 0),
    )


@router.post("/spotify/{project_id}/import", response_model=SpotifyImportResponse)
def import_spotify_selection(
    project_id: int,
    payload: SpotifyImportRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Enregistre en base les morceaux/albums Spotify choisis par l'artiste."""
    _assert_project_access(db, current_user, project_id, write=True)

    tracks_imported = 0
    for track in payload.tracks:
        existing = db.execute(
            text('''
                SELECT id_morceau, code_isrc
                FROM "Morceau"
                WHERE id_projet = :project_id AND titre_morceau = :titre
            '''),
            {"project_id": project_id, "titre": track.titre},
        ).first()
        if existing and existing.code_isrc:
            continue

        try:
            spotify_track = spotify_service.get_track(track.spotifyId)
        except SpotifyAuthError as error:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except SpotifyNotFoundError as error:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except SpotifyApiError as error:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
        isrc = spotify_track.get("external_ids", {}).get("isrc")

        if isrc:
            isrc_owner = db.execute(
                text('''
                    SELECT id_morceau, id_projet
                    FROM "Morceau"
                    WHERE code_isrc = :isrc
                '''),
                {"isrc": isrc},
            ).first()
            if isrc_owner:
                if isrc_owner.id_projet == project_id:
                    continue
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ce morceau est déjà rattaché à un autre projet avec le même code ISRC.",
                )

        release_date = track.releaseDate
        if release_date and len(release_date) == 4:
            release_date = f"{release_date}-01-01"
        elif release_date and len(release_date) == 7:
            release_date = f"{release_date}-01"

        if existing:
            if isrc or release_date:
                _execute_spotify_import_write(
                    db,
                    text('''
                        UPDATE "Morceau"
                        SET code_isrc = COALESCE(:isrc, code_isrc),
                            date_sortie = COALESCE(:date_sortie, date_sortie)
                        WHERE id_morceau = :track_id
                    '''),
                    {"track_id": existing.id_morceau, "isrc": isrc, "date_sortie": release_date},
                )
            continue

        total_seconds = track.durationMs // 1000
        duree = f"{total_seconds // 3600:02d}:{(total_seconds % 3600) // 60:02d}:{total_seconds % 60:02d}"
        _execute_spotify_import_write(
            db,
            text('''
                INSERT INTO "Morceau" (id_projet, titre_morceau, duree, code_isrc, date_sortie)
                VALUES (:project_id, :titre, :duree, :isrc, :date_sortie)
            '''),
            {
                "project_id": project_id,
                "titre": track.titre,
                "duree": duree,
                "isrc": isrc,
                "date_sortie": release_date,
            },
        )
        tracks_imported += 1

    albums_imported = 0
    if payload.albums:
        id_type_disque = db.execute(
            text('SELECT id_type FROM "TypeAsset" WHERE libelle = \'Disque/Release\'')
        ).scalar_one()
        for album in payload.albums:
            existing = db.execute(
                text('SELECT 1 FROM "Asset" WHERE id_projet = :project_id AND titre = :titre'),
                {"project_id": project_id, "titre": album.titre},
            ).first()
            if existing:
                continue
            release_date = album.releaseDate
            if release_date and len(release_date) == 4:
                release_date = f"{release_date}-01-01"
            elif release_date and len(release_date) == 7:
                release_date = f"{release_date}-01"
            _execute_spotify_import_write(
                db,
                text('''
                    INSERT INTO "Asset" (id_projet, id_type, titre, date_creation, metadonnees, chemin_stockage)
                    VALUES (:project_id, :id_type, :titre, :date_creation, CAST(:metadonnees AS JSONB), :chemin_stockage)
                '''),
                {
                    "project_id": project_id,
                    "id_type": id_type_disque,
                    "titre": album.titre,
                    "date_creation": release_date,
                    "metadonnees": json.dumps({"spotify_id": album.spotifyId}),
                    "chemin_stockage": f"https://open.spotify.com/album/{album.spotifyId}",
                },
            )
            albums_imported += 1

    try:
        db.commit()
    except IntegrityError as error:
        _raise_spotify_import_integrity_error(db, error)
    return SpotifyImportResponse(tracksImported=tracks_imported, albumsImported=albums_imported)


@router.post("/spotify/{project_id}/import-image", response_model=SpotifyImportImageResponse)
def import_spotify_image(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Récupère la photo de profil de l'artiste Spotify lié et la définit comme visuel officiel du projet."""
    _assert_project_access(db, current_user, project_id, write=True)
    presence = _get_spotify_presence(db, project_id)
    artist_id = _extract_spotify_artist_id(presence["identifiant_api"])

    try:
        artist = spotify_service.get_artist(artist_id)
    except SpotifyAuthError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except SpotifyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SpotifyApiError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    images = artist.get("images") or []
    if not images:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet artiste Spotify n'a pas de photo de profil disponible.",
        )
    image_url = images[0]["url"]

    db.execute(text('''
        INSERT INTO "TypeAsset" (libelle, description)
        VALUES ('Image', 'Visuel officiel du projet')
        ON CONFLICT DO NOTHING
    '''))
    id_type_image = db.execute(
        text('SELECT id_type FROM "TypeAsset" WHERE lower(trim(libelle)) = lower(\'Image\')')
    ).scalar_one()

    previous_urls = db.execute(
        text('SELECT chemin_stockage FROM "Asset" WHERE id_projet = :project_id AND id_type = :id_type'),
        {"project_id": project_id, "id_type": id_type_image},
    ).scalars().all()
    db.execute(
        text('DELETE FROM "Asset" WHERE id_projet = :project_id AND id_type = :id_type'),
        {"project_id": project_id, "id_type": id_type_image},
    )
    db.execute(
        text('''
            INSERT INTO "Asset" (id_projet, id_type, titre, chemin_stockage)
            VALUES (:project_id, :id_type, 'Visuel officiel (Spotify)', :url)
        '''),
        {"project_id": project_id, "id_type": id_type_image, "url": image_url},
    )
    db.commit()
    for previous_url in previous_urls:
        delete_managed_file(previous_url)

    return SpotifyImportImageResponse(avatarUrl=image_url)
