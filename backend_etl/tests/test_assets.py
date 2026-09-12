import unittest
from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.datastructures import Headers, UploadFile

from backend_etl.main import app, create_project_asset, delete_project_asset
from backend_etl.core.config import settings
from backend_etl.schemas.project import AssetWriteRequest
from backend_etl.services.asset_storage import delete_managed_file, store_upload


class NoQuerySession:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("A database query must not run for a forbidden role.")


class MissingMembershipResult:
    def first(self):
        return None


class MissingMembershipSession:
    def execute(self, *_args, **_kwargs):
        return MissingMembershipResult()


def asset_payload(**overrides):
    values = {
        "titre": "Programme de scène",
        "date": date(2026, 8, 30),
        "typeId": 1,
        "url": "https://example.test/programme.pdf",
        "metadata": {"distribution": {"artistes": 3}},
        "isJourneyEvent": True,
        "eventSource": "RTS Culture",
    }
    values.update(overrides)
    return AssetWriteRequest(**values)


class AssetContractTests(unittest.TestCase):
    def test_accepts_nested_metadata_and_journey_event(self):
        payload = asset_payload()

        self.assertEqual(payload.metadata["distribution"]["artistes"], 3)
        self.assertEqual(payload.eventSource, "RTS Culture")

    def test_rejects_non_json_metadata_values(self):
        with self.assertRaises(ValidationError):
            asset_payload(metadata={"publication": date(2026, 8, 30)})

    def test_rejects_non_object_metadata_root(self):
        for metadata in (["live"], "live", 3):
            with self.subTest(metadata=metadata), self.assertRaises(ValidationError):
                asset_payload(metadata=metadata)

    def test_requires_exactly_one_asset_type(self):
        with self.assertRaises(ValidationError):
            asset_payload(typeId=None, typeLibelle=None)
        with self.assertRaises(ValidationError):
            asset_payload(typeId=1, typeLibelle="Autre")

    def test_requires_date_for_journey_event(self):
        with self.assertRaises(ValidationError):
            asset_payload(date=None)

    def test_rejects_non_http_url(self):
        with self.assertRaises(ValidationError):
            asset_payload(url="file:///tmp/programme.pdf")

    def test_discards_event_source_when_not_an_event(self):
        payload = asset_payload(isJourneyEvent=False)

        self.assertIsNone(payload.eventSource)


class AssetAuthorizationTests(unittest.TestCase):
    def test_expert_cannot_create_or_delete_asset(self):
        auth_payload = {"role": "expert_jury", "id_personne": 11}
        for action in (
            lambda: create_project_asset(1, asset_payload(), NoQuerySession(), auth_payload),
            lambda: delete_project_asset(1, 1, NoQuerySession(), auth_payload),
        ):
            with self.assertRaises(HTTPException) as context:
                action()
            self.assertEqual(context.exception.status_code, 403)

    def test_artist_outside_project_cannot_create_asset(self):
        with self.assertRaises(HTTPException) as context:
            create_project_asset(
                1,
                asset_payload(),
                MissingMembershipSession(),
                {"role": "artiste", "id_personne": 999},
            )

        self.assertEqual(context.exception.status_code, 403)


class AssetOpenApiTests(unittest.TestCase):
    def test_asset_routes_are_exposed(self):
        paths = app.openapi()["paths"]

        self.assertIn("get", paths["/api/asset-types"])
        self.assertIn("post", paths["/api/projects/{project_id}/assets"])
        self.assertIn("patch", paths["/api/projects/{project_id}/assets/{asset_id}"])
        self.assertIn("delete", paths["/api/projects/{project_id}/assets/{asset_id}"])
        self.assertIn("post", paths["/api/projects/{project_id}/assets/upload"])
        self.assertIn("patch", paths["/api/projects/{project_id}/assets/{asset_id}/upload"])


class AssetStorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.previous_storage_dir = settings.ASSET_STORAGE_DIR
        self.previous_public_url = settings.ASSET_PUBLIC_BASE_URL
        self.previous_max_bytes = settings.ASSET_MAX_BYTES
        settings.ASSET_STORAGE_DIR = Path(self.temporary_directory.name)
        settings.ASSET_PUBLIC_BASE_URL = "http://test/uploads"
        settings.ASSET_MAX_BYTES = 1024

    async def asyncTearDown(self):
        settings.ASSET_STORAGE_DIR = self.previous_storage_dir
        settings.ASSET_PUBLIC_BASE_URL = self.previous_public_url
        settings.ASSET_MAX_BYTES = self.previous_max_bytes
        self.temporary_directory.cleanup()

    def upload(self, filename: str, content_type: str, content: bytes) -> UploadFile:
        return UploadFile(
            BytesIO(content),
            filename=filename,
            headers=Headers({"content-type": content_type}),
        )

    async def test_stores_with_uuid_inside_project_directory(self):
        url = await store_upload(
            7,
            self.upload("../../programme.pdf", "application/pdf", b"%PDF-1.7\ncontent"),
        )

        stored_path = settings.ASSET_STORAGE_DIR / url.removeprefix("http://test/uploads/")
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.parent, settings.ASSET_STORAGE_DIR / "7")
        self.assertNotEqual(stored_path.name, "programme.pdf")

        delete_managed_file(url)
        self.assertFalse(stored_path.exists())

    async def test_rejects_signature_mismatch_and_oversize(self):
        with self.assertRaises(HTTPException) as mismatch:
            await store_upload(1, self.upload("image.png", "image/png", b"not-a-png"))
        self.assertEqual(mismatch.exception.status_code, 415)

        with self.assertRaises(HTTPException) as oversize:
            await store_upload(1, self.upload("large.pdf", "application/pdf", b"%PDF-" + b"x" * 1024))
        self.assertEqual(oversize.exception.status_code, 413)
        self.assertFalse(any(path.is_file() for path in settings.ASSET_STORAGE_DIR.rglob("*")))

    async def test_external_url_is_never_deleted(self):
        external_file = settings.ASSET_STORAGE_DIR / "external.pdf"
        external_file.write_bytes(b"%PDF-test")

        delete_managed_file("https://example.test/external.pdf")

        self.assertTrue(external_file.exists())


if __name__ == "__main__":
    unittest.main()