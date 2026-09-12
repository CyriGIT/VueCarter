import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

import jwt
from fastapi import HTTPException

from backend_etl.routers.analytics import build_metabase_dashboard_url, get_metabase_embed_url


class MetabaseEmbedTests(unittest.TestCase):
    @patch("backend_etl.routers.analytics.settings.METABASE_SITE_URL", "http://localhost:3000/")
    @patch("backend_etl.routers.analytics.settings.METABASE_DASHBOARD_ID", "12")
    @patch(
        "backend_etl.routers.analytics.settings.METABASE_EMBEDDING_SECRET_KEY",
        "test-secret-at-least-32-characters-long",
    )
    def test_builds_a_short_lived_signed_dashboard_url(self):
        url = build_metabase_dashboard_url()
        token = url.split("/embed/dashboard/", 1)[1].split("#", 1)[0]
        payload = jwt.decode(
            token,
            "test-secret-at-least-32-characters-long",
            algorithms=["HS256"],
        )

        self.assertTrue(url.startswith("http://localhost:3000/embed/dashboard/"))
        self.assertEqual(payload["resource"], {"dashboard": 12})
        self.assertEqual(payload["params"], {})
        self.assertIn("exp", payload)
        self.assertTrue(url.endswith("#bordered=false&titled=false&theme=night"))

    @patch("backend_etl.routers.analytics.settings.METABASE_DASHBOARD_ID", None)
    @patch("backend_etl.routers.analytics.settings.METABASE_EMBEDDING_SECRET_KEY", None)
    def test_rejects_missing_metabase_configuration(self):
        with self.assertRaises(HTTPException) as context:
            build_metabase_dashboard_url()

        self.assertEqual(context.exception.status_code, 503)

    @patch("backend_etl.routers.analytics.settings.METABASE_SITE_URL", "http://localhost:3000")
    @patch("backend_etl.routers.analytics.settings.METABASE_DASHBOARD_ID", "12")
    @patch(
        "backend_etl.routers.analytics.settings.METABASE_EMBEDDING_SECRET_KEY",
        "test-secret-at-least-32-characters-long",
    )
    def test_accompanying_user_receives_locked_assigned_project_filter(self):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = [1, 4]

        response = get_metabase_embed_url(
            current_user=SimpleNamespace(role="accompagnant", id_personne=15),
            db=db,
        )
        token = response["url"].split("/embed/dashboard/", 1)[1].split("#", 1)[0]
        payload = jwt.decode(
            token,
            "test-secret-at-least-32-characters-long",
            algorithms=["HS256"],
        )

        self.assertEqual(payload["params"], {"filtre_par_projet": [1, 4]})
        self.assertEqual(db.execute.call_args.args[1], {"id_personne": 15})
        self.assertIn('FROM "AffectationAccompagnement"', str(db.execute.call_args.args[0]))

    def test_accompanying_user_without_assignment_is_rejected(self):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = []

        with self.assertRaises(HTTPException) as context:
            get_metabase_embed_url(
                current_user=SimpleNamespace(role="accompagnant", id_personne=15),
                db=db,
            )

        self.assertEqual(context.exception.status_code, 403)

    def test_accompanying_account_without_person_is_rejected_before_query(self):
        db = MagicMock()

        with self.assertRaises(HTTPException) as context:
            get_metabase_embed_url(
                current_user=SimpleNamespace(role="accompagnant", id_personne=None),
                db=db,
            )

        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_called()

    @patch("backend_etl.routers.analytics.build_metabase_dashboard_url")
    def test_jury_keeps_unfiltered_cohort_dashboard(self, build_url):
        build_url.return_value = "http://metabase/embed/dashboard/token"

        get_metabase_embed_url(
            current_user=SimpleNamespace(role="expert_jury", id_personne=11),
            db=MagicMock(),
        )

        build_url.assert_called_once_with({})

    def test_artist_cannot_access_analytics(self):
        with self.assertRaises(HTTPException) as context:
            get_metabase_embed_url(
                current_user=SimpleNamespace(role="artiste", id_personne=1),
                db=MagicMock(),
            )

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()