import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from backend_etl.main import get_projects
from backend_etl.routers.etl import _assert_project_access
from backend_etl.routers.evaluation_campaigns import list_campaign_evaluations, list_campaigns


class AccompanyingAccessTests(unittest.TestCase):
    @patch("backend_etl.routers.evaluation_campaigns._campaign_rows", return_value=[])
    def test_campaign_list_filters_on_assigned_projects(self, campaign_rows):
        user = SimpleNamespace(role="accompagnant", id_personne=15)

        result = list_campaigns(db=MagicMock(), current_user=user)

        self.assertEqual(result, [])
        where = campaign_rows.call_args.args[1]
        params = campaign_rows.call_args.args[2]
        self.assertIn('JOIN "AffectationAccompagnement" acces', where)
        self.assertEqual(params, {"expert_id": 15})

    @patch("backend_etl.routers.evaluation_campaigns.get_evaluation_summary")
    @patch("backend_etl.routers.evaluation_campaigns.get_campaign")
    def test_campaign_evaluations_filter_on_assigned_projects(self, _get_campaign, get_summary):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = [1, 9]
        get_summary.side_effect = lambda _db, campaign_id, project_id, person_id: {
            "campaignId": campaign_id,
            "projectId": project_id,
            "personId": person_id,
        }
        user = SimpleNamespace(role="accompagnant", id_personne=15)

        result = list_campaign_evaluations(1, db=db, current_user=user)

        statement = str(db.execute.call_args.args[0])
        params = db.execute.call_args.args[1]
        self.assertIn('JOIN "AffectationAccompagnement" acces', statement)
        self.assertEqual(params, {"campaign_id": 1, "expert_id": 15})
        self.assertEqual([item["projectId"] for item in result], [1, 9])

    def test_project_list_filters_on_current_accompanying_person(self):
        db = MagicMock()
        projects_result = MagicMock()
        projects_result.mappings.return_value.all.return_value = []
        db.execute.return_value = projects_result

        result = get_projects(db=db, auth_payload={"role": "accompagnant", "id_personne": 15})

        self.assertEqual(result, [])
        statement = str(db.execute.call_args.args[0])
        params = db.execute.call_args.args[1]
        self.assertIn('FROM "AffectationAccompagnement" assignment', statement)
        self.assertIn('assignment.id_expert = :id_personne', statement)
        self.assertEqual(params["id_personne"], 15)

    def test_accompanying_account_without_person_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            get_projects(db=MagicMock(), auth_payload={"role": "accompagnant", "id_personne": None})

        self.assertEqual(context.exception.status_code, 403)

    def test_assigned_accompanying_user_can_read_project_etl_data(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = (1,)
        user = SimpleNamespace(role="accompagnant", id_personne=15)

        _assert_project_access(db, user, project_id=1)

        self.assertEqual(db.execute.call_args.args[1], {"project_id": 1, "id_personne": 15})

    def test_unassigned_accompanying_user_cannot_read_project_etl_data(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = None
        user = SimpleNamespace(role="accompagnant", id_personne=15)

        with self.assertRaises(HTTPException) as context:
            _assert_project_access(db, user, project_id=2)

        self.assertEqual(context.exception.status_code, 403)

    def test_accompanying_user_cannot_write_etl_data(self):
        db = MagicMock()
        user = SimpleNamespace(role="accompagnant", id_personne=15)

        with self.assertRaises(HTTPException) as context:
            _assert_project_access(db, user, project_id=1, write=True)

        self.assertEqual(context.exception.status_code, 403)
        db.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()