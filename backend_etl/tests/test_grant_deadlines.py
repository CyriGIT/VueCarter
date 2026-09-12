import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from backend_etl.main import app
from backend_etl.routers.grant_deadlines import (
    create_grant_deadline,
    declare_grant_application,
    list_upcoming_grant_deadlines,
    update_grant_deadline,
)
from backend_etl.schemas.grant_deadline import GrantApplicationWrite, GrantDeadlineUpdate, GrantDeadlineWrite


def valid_write(**overrides):
    values = {
        "bailleur": "Fondation Exemple",
        "dateProchaineSoumission": date.today() + timedelta(days=30),
        "urlFormulaire": "https://example.test/formulaire",
    }
    values.update(overrides)
    return GrantDeadlineWrite(**values)


class GrantDeadlineContractTests(unittest.TestCase):
    def test_accepts_http_url_and_upcoming_date(self):
        payload = valid_write(bailleur="  Fondation Exemple  ")

        self.assertEqual(payload.bailleur, "Fondation Exemple")

    def test_rejects_invalid_values(self):
        invalid_overrides = (
            {"bailleur": "   "},
            {"urlFormulaire": "ftp://example.test/formulaire"},
            {"urlFormulaire": "https://"},
            {"dateProchaineSoumission": date.today() - timedelta(days=1)},
        )
        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                valid_write(**overrides)

    def test_allows_archiving_an_expired_deadline(self):
        payload = GrantDeadlineUpdate(
            bailleur="Fondation Exemple",
            dateProchaineSoumission=date.today() - timedelta(days=1),
            urlFormulaire="https://example.test/formulaire",
            estActif=False,
        )

        self.assertFalse(payload.estActif)

    def test_openapi_exposes_no_delete(self):
        paths = app.openapi()["paths"]

        self.assertIn("get", paths["/api/grant-deadlines"])
        self.assertIn("post", paths["/api/grant-deadlines"])
        self.assertIn("get", paths["/api/grant-deadlines/manage"])
        self.assertIn("patch", paths["/api/grant-deadlines/{item_id}"])
        self.assertNotIn("delete", paths["/api/grant-deadlines/{item_id}"])


class GrantDeadlinePersistenceTests(unittest.TestCase):
    def test_artist_list_filters_and_orders_upcoming_active_rows(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.all.return_value = []

        list_upcoming_grant_deadlines(db, MagicMock())

        sql = str(db.execute.call_args.args[0])
        self.assertIn("est_actif AND date_prochaine_soumission >= CURRENT_DATE", sql)
        self.assertIn("ORDER BY date_prochaine_soumission", sql)

    def test_create_commits_and_returns_row(self):
        db = MagicMock()
        expected = {
            "id": 3,
            "bailleur": "Fondation Exemple",
            "dateProchaineSoumission": date.today() + timedelta(days=30),
            "urlFormulaire": "https://example.test/formulaire",
            "estActif": True,
        }
        db.execute.return_value.mappings.return_value.first.return_value = expected

        result = create_grant_deadline(valid_write(), db, MagicMock())

        self.assertEqual(result, expected)
        db.commit.assert_called_once_with()

    def test_missing_update_rolls_back_without_commit(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        payload = GrantDeadlineUpdate(**valid_write().model_dump(), estActif=True)

        with self.assertRaises(HTTPException) as context:
            update_grant_deadline(999, payload, db, MagicMock())

        self.assertEqual(context.exception.status_code, 404)
        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()


class GrantApplicationPersistenceTests(unittest.TestCase):
    def test_artist_member_declares_application(self):
        db = MagicMock()
        membership = MagicMock()
        membership.first.return_value = (1,)
        deadline = MagicMock()
        deadline.mappings.return_value.first.return_value = {
            "id_echeance": 2,
            "bailleur": "Fondation Exemple",
            "date_prochaine_soumission": date.today() + timedelta(days=10),
        }
        inserted = MagicMock()
        inserted.mappings.return_value.one.return_value = {
            "deadlineId": 2,
            "dateDepot": date.today(),
        }
        db.execute.side_effect = [membership, deadline, inserted]
        user = MagicMock(role="artiste", id_personne=5)

        result = declare_grant_application(
            1,
            GrantApplicationWrite(deadlineId=2, dateDepot=date.today()),
            db,
            user,
        )

        self.assertEqual(result["deadlineId"], 2)
        self.assertIn("ON CONFLICT", str(db.execute.call_args_list[2].args[0]))
        db.commit.assert_called_once_with()

    def test_non_artist_cannot_declare_application(self):
        db = MagicMock()

        with self.assertRaises(HTTPException) as context:
            declare_grant_application(
                1,
                GrantApplicationWrite(deadlineId=2, dateDepot=date.today()),
                db,
                MagicMock(role="accompagnant", id_personne=15),
            )

        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_called()

    def test_duplicate_maps_to_conflict_and_rolls_back(self):
        db = MagicMock()
        db.execute.side_effect = IntegrityError("duplicate", {}, Exception())

        with self.assertRaises(HTTPException) as context:
            create_grant_deadline(valid_write(), db, MagicMock())

        self.assertEqual(context.exception.status_code, 409)
        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
