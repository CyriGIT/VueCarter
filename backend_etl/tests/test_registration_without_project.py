import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from backend_etl.main import create_project
from backend_etl.routers.auth import register
from backend_etl.schemas.auth import RegisterSchema
from backend_etl.schemas.project import ProjectCreateRequest


class RegistrationWithoutProjectTests(unittest.TestCase):
    @patch("backend_etl.routers.auth.create_access_token", return_value="token")
    @patch("backend_etl.routers.auth.get_password_hash", return_value="hash")
    def test_registration_creates_only_person_and_account(self, _hash, _token):
        db = MagicMock()
        existing = MagicMock()
        existing.first.return_value = None
        person = MagicMock()
        person.one.return_value = SimpleNamespace(id_personne=25)
        account = MagicMock()
        account.one.return_value = SimpleNamespace(id_utilisateur=30)
        db.execute.side_effect = [existing, person, account]

        result = register(
            RegisterSchema(
                email="new.artist@example.com",
                password="password",
                nom="Artiste",
                prenom="Nouvel",
                commune="Neuchâtel",
                genre="Autre",
                date_naissance="2000-01-02",
            ),
            db=db,
        )

        statements = "\n".join(str(call.args[0]) for call in db.execute.call_args_list)
        self.assertIn('INSERT INTO "Personne"', statements)
        self.assertIn('INSERT INTO "CompteUtilisateur"', statements)
        self.assertNotIn('INSERT INTO "ProjetMusical"', statements)
        self.assertNotIn('INSERT INTO "MembreProjet"', statements)
        self.assertEqual(result["role"], "artiste")
        db.commit.assert_called_once_with()

    def test_artist_without_person_cannot_create_orphan_project(self):
        db = MagicMock()

        with self.assertRaises(HTTPException) as context:
            create_project(
                ProjectCreateRequest(nom="Projet différé"),
                db=db,
                auth_payload={"role": "artiste", "id_personne": None},
            )

        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_called()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()