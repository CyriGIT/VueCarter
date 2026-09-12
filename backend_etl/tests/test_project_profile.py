import unittest
from datetime import date
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError

from backend_etl.main import app, update_project
from backend_etl.schemas.project import ProjectUpdateRequest


def project_payload(**overrides):
    values = {
        "nom": "Projet test",
        "dateCreation": date(2026, 1, 1),
        "statutJuridiqueId": 2,
        "statutJuridique": "Association",
        "suisaInscrit": True,
        "hasLocal": False,
        "hasFicheTechnique": True,
        "hasMerch": False,
        "personalPageUrl": "https://instagram.com/projet-test",
        "personalPageSiteName": "Instagram",
        "objectifsCourtTerme": "Sortir un EP.",
        "objectifsMoyenTerme": "Développer une tournée européenne.",
    }
    values.update(overrides)
    return ProjectUpdateRequest(**values)


class ProjectProfileContractTests(unittest.TestCase):
    def test_accepts_known_and_custom_sites(self):
        self.assertEqual(project_payload().personalPageSiteName, "Instagram")
        custom = project_payload(
            personalPageUrl="https://artiste.example",
            personalPageSiteName="Portfolio officiel",
        )
        self.assertEqual(custom.personalPageSiteName, "Portfolio officiel")

    def test_requires_a_complete_http_page_pair(self):
        for overrides in (
            {"personalPageSiteName": None},
            {"personalPageUrl": None},
            {"personalPageUrl": "ftp://instagram.com/projet-test"},
            {"personalPageUrl": "https://example.com", "personalPageSiteName": "Instagram"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                project_payload(**overrides)

    def test_normalizes_empty_optional_fields(self):
        payload = project_payload(
            personalPageUrl=" ",
            personalPageSiteName=" ",
            objectifsCourtTerme=" ",
            objectifsMoyenTerme=None,
        )
        self.assertIsNone(payload.personalPageUrl)
        self.assertIsNone(payload.personalPageSiteName)
        self.assertIsNone(payload.objectifsCourtTerme)
        self.assertIsNone(payload.objectifsMoyenTerme)

    def test_project_update_contract_exposes_profile_fields(self):
        schema = app.openapi()["components"]["schemas"]
        request_properties = schema["ProjectUpdateRequest"]["properties"]
        response_properties = schema["ProjectUpdateResponse"]["properties"]
        for field in (
            "personalPageUrl",
            "personalPageSiteName",
            "objectifsCourtTerme",
            "objectifsMoyenTerme",
        ):
            self.assertIn(field, request_properties)
            self.assertIn(field, response_properties)


class ProjectProfilePersistenceTests(unittest.TestCase):
    def test_update_maps_profile_fields_to_sql_and_response(self):
        db = MagicMock()
        current_status = MagicMock()
        current_status.mappings.return_value.first.return_value = {
            "id": 2,
            "libelle": "Association",
        }
        resolved_status = MagicMock()
        resolved_status.mappings.return_value.first.return_value = {
            "id": 2,
            "libelle": "Association",
        }
        updated = MagicMock()
        updated.mappings.return_value.first.return_value = {
            "id": 1,
            "nom": "Projet test",
            "dateCreation": date(2026, 1, 1),
            "statutJuridiqueId": 2,
            "statutJuridique": "Association",
            "suisaInscrit": True,
            "hasLocal": False,
            "hasFicheTechnique": True,
            "hasMerch": False,
            "personalPageUrl": "https://instagram.com/projet-test",
            "personalPageSiteName": "Instagram",
            "objectifsCourtTerme": "Sortir un EP.",
            "objectifsMoyenTerme": "Développer une tournée européenne.",
        }
        db.execute.side_effect = [current_status, resolved_status, updated]

        result = update_project(1, project_payload(), db, {"role": "admin"})

        update_sql = str(db.execute.call_args_list[2].args[0])
        update_params = db.execute.call_args_list[2].args[1]
        self.assertIn("page_personnelle_url", update_sql)
        self.assertEqual(update_params["personal_page_site_name"], "Instagram")
        self.assertEqual(update_params["objectifs_court_terme"], "Sortir un EP.")
        self.assertEqual(result["personalPageUrl"], "https://instagram.com/projet-test")
        db.commit.assert_called_once_with()

    def test_artist_outside_project_is_forbidden_before_update(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as context:
            update_project(1, project_payload(), db, {"role": "artiste", "id_personne": 999})

        self.assertEqual(context.exception.status_code, 403)
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()