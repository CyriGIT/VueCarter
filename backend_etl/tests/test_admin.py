import unittest

from fastapi import HTTPException
from pydantic import ValidationError

from backend_etl.main import app
from backend_etl.routers.admin import _validate_style_parent
from backend_etl.schemas.admin import ExpertInvitationWrite


class AdminApiContractTests(unittest.TestCase):
    def test_all_catalog_resources_expose_list_create_and_update(self):
        paths = app.openapi()["paths"]
        resources = (
            "legal-statuses",
            "phase-types",
            "styles",
            "programs",
            "formations",
            "professional-structures",
            "venues",
            "platforms",
        )

        for resource in resources:
            with self.subTest(resource=resource):
                self.assertEqual(set(paths[f"/api/admin/{resource}"]), {"get", "post"})
                self.assertEqual(set(paths[f"/api/admin/{resource}/{{item_id}}"]), {"patch"})

    def test_admin_api_has_no_delete_operation(self):
        admin_paths = {
            path: operations
            for path, operations in app.openapi()["paths"].items()
            if path.startswith("/api/admin")
        }

        self.assertTrue(admin_paths)
        self.assertFalse(any("delete" in operations for operations in admin_paths.values()))

    def test_style_cannot_be_its_own_parent(self):
        with self.assertRaises(HTTPException) as context:
            _validate_style_parent(db=None, style_id=12, parent_id=12)

        self.assertEqual(context.exception.status_code, 422)

    def test_invitation_rejects_unsupported_role(self):
        payload = {
            "prenom": "Test",
            "nom": "Admin",
            "email": "test@example.com",
            "role": "admin",
            "dateNaissance": "1990-01-01",
            "genre": "Autre",
            "npa": "2000",
            "ville": "Neuchâtel",
        }

        with self.assertRaises(ValidationError):
            ExpertInvitationWrite.model_validate(payload)

    def test_invitation_accepts_accompanying_role(self):
        payload = {
            "prenom": "Accompagnante",
            "nom": "Démo",
            "email": "accompagnante@example.com",
            "role": "accompagnant",
            "dateNaissance": "1986-09-08",
            "genre": "Femme",
            "npa": "2000",
            "ville": "Neuchâtel",
        }

        invitation = ExpertInvitationWrite.model_validate(payload)

        self.assertEqual(invitation.role, "accompagnant")


if __name__ == "__main__":
    unittest.main()