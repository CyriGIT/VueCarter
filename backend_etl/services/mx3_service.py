import time
from typing import Any, Optional

import requests

from backend_etl.core.config import settings


class Mx3AuthError(RuntimeError):
    pass


class Mx3NotFoundError(RuntimeError):
    pass


class Mx3ApiError(RuntimeError):
    pass


MX3_METRIC_FIELDS = {
    "listening_count": "Ecoutes_Cumulees",
    "profile_views_count": "Vues_Profil",
    "playlists_count": "Playlists",
    "singles_count": "Singles_Publies",
}


def _extract_collection(payload: dict, key: str) -> list[dict]:
    response: Any = payload.get("response", payload)
    wrappers = response if isinstance(response, list) else [response]
    items: list[dict] = []
    for wrapper in wrappers:
        if not isinstance(wrapper, dict):
            continue
        value = wrapper.get(key, [])
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            items.append(value)
    return items


def _unwrap_value(value: Any) -> Any:
    if isinstance(value, dict):
        if not value:
            return None
        if str(value.get("nil", "")).lower() == "true":
            return None
        if "value" in value:
            return value["value"]
    return value


def _extract_band(payload: dict) -> Optional[dict]:
    response: Any = payload.get("response", payload)
    wrappers = response if isinstance(response, list) else [response]
    for wrapper in wrappers:
        if not isinstance(wrapper, dict):
            continue
        raw_band = wrapper.get("band")
        if not isinstance(raw_band, dict):
            continue
        return {
            key.replace("-", "_"): _unwrap_value(value)
            for key, value in raw_band.items()
        }
    return None


class Mx3Service:
    def __init__(self) -> None:
        self._access_token: Optional[str] = None
        self._token_expires_at = 0.0

    def _get_access_token(self) -> str:
        if not settings.mx3_is_configured:
            raise Mx3AuthError("Les identifiants SRG SSR MX3 ne sont pas configurés.")
        if self._access_token and time.time() < self._token_expires_at - 30:
            return self._access_token

        response = requests.post(
            settings.SRGSSR_OAUTH_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(settings.SRGSSR_MX3_CONSUMER_KEY, settings.SRGSSR_MX3_CONSUMER_SECRET),
            timeout=10,
        )
        if response.status_code != 200:
            raise Mx3AuthError("Impossible d'obtenir un jeton SRG SSR MX3.")

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise Mx3AuthError("La réponse OAuth SRG SSR MX3 ne contient aucun jeton.")
        self._access_token = access_token
        self._token_expires_at = time.time() + int(payload.get("expires_in", 3600))
        return access_token

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        response = requests.get(
            f"{settings.SRGSSR_MX3_API_BASE_URL}{path}",
            headers={
                "Authorization": f"Bearer {self._get_access_token()}",
                "accept": "application/json",
            },
            params=params,
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            raise Mx3NotFoundError("Ressource MX3 introuvable.")
        if response.status_code == 401:
            self._access_token = None
            raise Mx3AuthError("Le jeton SRG SSR MX3 est invalide ou expiré.")
        if response.status_code == 403:
            raise Mx3ApiError("Le quota de l'API SRG SSR MX3 est dépassé.")
        raise Mx3ApiError(f"Erreur SRG SSR MX3 ({response.status_code}).")

    def search_bands(self, query: str) -> list[dict]:
        return _extract_collection(self._get("/bands", params={"query": query}), "bands")

    def get_band(self, band_id: int) -> dict:
        band = _extract_band(self._get(f"/bands/{band_id}"))
        if not band:
            raise Mx3NotFoundError("Groupe MX3 introuvable.")
        return band

    def get_band_stats(self, band_id: int) -> dict[str, int]:
        band = self.get_band(band_id)
        metrics: dict[str, int] = {}
        for field, indicator in MX3_METRIC_FIELDS.items():
            raw_value = band.get(field)
            if raw_value is None:
                continue
            try:
                value = int(raw_value)
            except (TypeError, ValueError) as error:
                raise Mx3ApiError(f"La métrique MX3 '{field}' n'est pas numérique.") from error
            if value < 0:
                raise Mx3ApiError(f"La métrique MX3 '{field}' ne peut pas être négative.")
            metrics[indicator] = value
        return metrics

    def get_band_gigs(self, band_id: int) -> list[dict]:
        return _extract_collection(self._get(f"/bands/{band_id}/gigs"), "performances")


mx3_service = Mx3Service()