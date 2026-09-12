import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend_etl.routers.etl import _extract_spotify_artist_id, import_spotify_selection
from backend_etl.schemas.etl import SpotifyImportRequest
from backend_etl.services.spotify_service import SpotifyApiError


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def first(self):
        return self.value

    def scalar_one(self):
        return self.value


class FakeSession:
    def __init__(self):
        self.tracks = {}
        self.albums = {}
        self.commit_count = 0
        self.rollback_count = 0
        self.fail_track_insert = False

    def execute(self, statement, parameters=None):
        sql = str(statement)
        parameters = parameters or {}
        if 'SELECT id_morceau, code_isrc' in sql:
            track = self.tracks.get(parameters["titre"])
            return FakeResult(
                SimpleNamespace(id_morceau=track["id_morceau"], code_isrc=track["isrc"])
                if track else None
            )
        if 'WHERE code_isrc = :isrc' in sql:
            track = next(
                (item for item in self.tracks.values() if item["isrc"] == parameters["isrc"]),
                None,
            )
            return FakeResult(
                SimpleNamespace(id_morceau=track["id_morceau"], id_projet=track["project_id"])
                if track else None
            )
        if 'UPDATE "Morceau"' in sql:
            track = next(item for item in self.tracks.values() if item["id_morceau"] == parameters["track_id"])
            if parameters["isrc"]:
                track["isrc"] = parameters["isrc"]
            if parameters["date_sortie"]:
                track["date_sortie"] = parameters["date_sortie"]
            return FakeResult()
        if 'INSERT INTO "Morceau"' in sql:
            if self.fail_track_insert:
                original_error = SimpleNamespace(
                    diag=SimpleNamespace(constraint_name="Morceau_pkey")
                )
                raise IntegrityError(sql, parameters, original_error)
            self.tracks[parameters["titre"]] = {
                **parameters,
                "id_morceau": len(self.tracks) + 1,
                "isrc": parameters["isrc"],
            }
            return FakeResult()
        if 'SELECT id_type FROM "TypeAsset"' in sql:
            return FakeResult(7)
        if 'SELECT 1 FROM "Asset"' in sql:
            return FakeResult((1,) if parameters["titre"] in self.albums else None)
        if 'INSERT INTO "Asset"' in sql:
            self.albums[parameters["titre"]] = parameters
            return FakeResult()
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


class SpotifyImportTests(unittest.TestCase):
    def test_extracts_raw_and_uri_spotify_artist_ids(self):
        artist_id = "4Z8W4fKeB5YxbusRsdQVPb"

        self.assertEqual(_extract_spotify_artist_id(artist_id), artist_id)
        self.assertEqual(_extract_spotify_artist_id(f"spotify:artist:{artist_id}"), artist_id)
        self.assertEqual(
            _extract_spotify_artist_id(f"https://open.spotify.com/artist/{artist_id}?si=test"),
            artist_id,
        )

    def test_rejects_seeded_spotify_placeholder(self):
        with self.assertRaises(HTTPException) as context:
            _extract_spotify_artist_id("spotify:artist:mock1")

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("Reliez à nouveau", context.exception.detail)

    def test_imports_selection_then_skips_duplicates(self):
        session = FakeSession()
        payload = SpotifyImportRequest(
            tracks=[
                {
                    "spotifyId": "track-1",
                    "titre": "Test Track",
                    "durationMs": 125000,
                    "releaseDate": "2026-08",
                }
            ],
            albums=[
                {
                    "spotifyId": "album-1",
                    "titre": "Test Album",
                    "releaseDate": "2026-08",
                },
                {
                    "spotifyId": "album-2",
                    "titre": "Test Album Year",
                    "releaseDate": "2025",
                },
            ],
        )
        current_user = SimpleNamespace(role="admin")

        with patch(
            "backend_etl.routers.etl.spotify_service.get_track",
            return_value={"external_ids": {"isrc": "CH1234567890"}},
        ) as get_track:
            first_result = import_spotify_selection(4, payload, session, current_user)
            second_result = import_spotify_selection(4, payload, session, current_user)

        self.assertEqual((first_result.tracksImported, first_result.albumsImported), (1, 2))
        self.assertEqual((second_result.tracksImported, second_result.albumsImported), (0, 0))
        self.assertEqual(session.tracks["Test Track"]["duree"], "00:02:05")
        self.assertEqual(session.tracks["Test Track"]["isrc"], "CH1234567890")
        self.assertEqual(session.tracks["Test Track"]["date_sortie"], "2026-08-01")
        get_track.assert_called_once_with("track-1")
        self.assertEqual(session.albums["Test Album"]["date_creation"], "2026-08-01")
        self.assertEqual(session.albums["Test Album Year"]["date_creation"], "2025-01-01")
        self.assertEqual(
            json.loads(session.albums["Test Album"]["metadonnees"]),
            {"spotify_id": "album-1"},
        )
        self.assertEqual(session.commit_count, 2)

    def test_backfills_isrc_for_an_existing_track(self):
        session = FakeSession()
        session.tracks["Existing Track"] = {"id_morceau": 12, "isrc": None, "project_id": 4}
        payload = SpotifyImportRequest(
            tracks=[{
                "spotifyId": "track-12",
                "titre": "Existing Track",
                "durationMs": 180000,
                "releaseDate": "2024",
            }]
        )

        with patch(
            "backend_etl.routers.etl.spotify_service.get_track",
            return_value={"external_ids": {"isrc": "CH0987654321"}},
        ):
            result = import_spotify_selection(4, payload, session, SimpleNamespace(role="admin"))

        self.assertEqual(result.tracksImported, 0)
        self.assertEqual(session.tracks["Existing Track"]["isrc"], "CH0987654321")
        self.assertEqual(session.tracks["Existing Track"]["date_sortie"], "2024-01-01")

    def test_rejects_isrc_already_attached_to_another_project(self):
        session = FakeSession()
        session.tracks["Other Project Track"] = {
            "id_morceau": 20,
            "isrc": "CH1122334455",
            "project_id": 5,
        }
        payload = SpotifyImportRequest(
            tracks=[{
                "spotifyId": "track-conflict",
                "titre": "Conflicting Track",
                "durationMs": 180000,
            }]
        )

        with patch(
            "backend_etl.routers.etl.spotify_service.get_track",
            return_value={"external_ids": {"isrc": "CH1122334455"}},
        ), self.assertRaises(HTTPException) as context:
            import_spotify_selection(4, payload, session, SimpleNamespace(role="admin"))

        self.assertEqual(context.exception.status_code, 409)
        self.assertIn("autre projet", context.exception.detail)
        self.assertEqual(session.rollback_count, 1)
        self.assertEqual(session.commit_count, 0)

    def test_rolls_back_an_integrity_error(self):
        session = FakeSession()
        session.fail_track_insert = True
        payload = SpotifyImportRequest(
            tracks=[{
                "spotifyId": "track-primary-key-conflict",
                "titre": "New Track",
                "durationMs": 180000,
            }]
        )

        with patch(
            "backend_etl.routers.etl.spotify_service.get_track",
            return_value={"external_ids": {}},
        ), self.assertRaises(HTTPException) as context:
            import_spotify_selection(4, payload, session, SimpleNamespace(role="admin"))

        self.assertEqual(context.exception.status_code, 409)
        self.assertIn("conflit de données", context.exception.detail)
        self.assertEqual(session.rollback_count, 1)
        self.assertEqual(session.commit_count, 0)

    def test_rolls_back_when_spotify_fails_mid_selection(self):
        session = FakeSession()
        payload = SpotifyImportRequest(
            tracks=[
                {"spotifyId": "track-1", "titre": "First Track", "durationMs": 180000},
                {"spotifyId": "track-2", "titre": "Second Track", "durationMs": 180000},
            ]
        )

        with patch(
            "backend_etl.routers.etl.spotify_service.get_track",
            side_effect=[{"external_ids": {"isrc": "CH0000000001"}}, SpotifyApiError("API unavailable")],
        ), self.assertRaises(HTTPException) as context:
            import_spotify_selection(4, payload, session, SimpleNamespace(role="admin"))

        self.assertEqual(context.exception.status_code, 502)
        self.assertEqual(session.rollback_count, 1)
        self.assertEqual(session.commit_count, 0)


if __name__ == "__main__":
    unittest.main()