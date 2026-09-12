# Client pour l'API Web Spotify — flux Client Credentials (données publiques de catalogue uniquement)
# Spec de référence : https://developer.spotify.com/reference/web-api/open-api-schema.yaml
# Respect des conditions Spotify : les réponses ne sont pas mises en cache/persistées au-delà de l'usage immédiat,
# seules des métriques agrégées (followers, popularité) sont stockées en base.

import time
from typing import Optional

import requests

from backend_etl.core.config import settings

TOKEN_URL = "https://accounts.spotify.com/api/token"
MAX_RETRIES = 3


class SpotifyAuthError(RuntimeError):
    pass


class SpotifyNotFoundError(RuntimeError):
    pass


class SpotifyApiError(RuntimeError):
    pass


class SpotifyService:
    """Encapsule l'authentification et les appels en lecture seule à l'API Web Spotify."""

    def __init__(self) -> None:
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _get_access_token(self) -> str:
        if not settings.spotify_is_configured:
            raise SpotifyAuthError("Les identifiants Spotify (client id/secret) ne sont pas configurés.")

        # Réutilise le jeton tant qu'il reste valide (marge de sécurité de 30s)
        if self._access_token and time.time() < self._token_expires_at - 30:
            return self._access_token

        response = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET),
            timeout=10,
        )
        if response.status_code != 200:
            raise SpotifyAuthError("Impossible d'obtenir un jeton d'accès Spotify (identifiants invalides).")

        payload = response.json()
        self._access_token = payload["access_token"]
        self._token_expires_at = time.time() + payload.get("expires_in", 3600)
        return self._access_token

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Effectue un GET authentifié, avec backoff exponentiel sur 429 et erreurs 5xx."""
        token = self._get_access_token()
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            response = requests.get(
                f"{settings.SPOTIFY_WEB_API_BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=10,
            )

            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                raise SpotifyNotFoundError(f"Ressource Spotify introuvable : {path}")
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue
            if response.status_code >= 500:
                last_error = SpotifyApiError(f"Erreur serveur Spotify ({response.status_code}) sur {path}")
                time.sleep(2 ** attempt)
                continue

            # 400/401/403 et autres erreurs client : pas de retry, message renvoyé par l'API
            detail = response.json().get("error", {}).get("message", response.text)
            raise SpotifyApiError(f"Erreur Spotify ({response.status_code}) : {detail}")

        raise last_error or SpotifyApiError(f"Échec de l'appel Spotify après {MAX_RETRIES} tentatives : {path}")

    def get_artist(self, artist_id: str) -> dict:
        """Infos publiques d'un artiste : nom, genres, popularité, followers."""
        return self._get(f"/artists/{artist_id}")

    def get_artist_albums(self, artist_id: str, market: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Liste des albums/singles publiés par l'artiste.
        Plafonné à 10 : cette app Spotify (mode développement, quota non étendu)
        rejette silencieusement (\"Invalid limit\") toute valeur supérieure sur cet endpoint,
        malgré un maximum documenté de 50."""
        params = {"limit": limit, "include_groups": "album,single"}
        if market:
            params["market"] = market
        return self._get(f"/artists/{artist_id}/albums", params=params).get("items", [])

    def get_album_tracks(self, album_id: str, market: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Tracklist d'un album (endpoint non déprécié)."""
        params = {"limit": limit}
        if market:
            params["market"] = market
        return self._get(f"/albums/{album_id}/tracks", params=params).get("items", [])

    def get_track(self, track_id: str) -> dict:
        """Détail d'un morceau, notamment son code ISRC dans external_ids."""
        return self._get(f"/tracks/{track_id}")

    def get_artist_stats(self, artist_id: str) -> dict:
        """Métriques agrégées destinées à être persistées (ReleveMetrique) (malheureusement dépréciées)."""
        artist = self.get_artist(artist_id)
        return {
            "followers": artist.get("followers", {}).get("total", 0),
            "popularity": artist.get("popularity", 0),
        }


spotify_service = SpotifyService()
