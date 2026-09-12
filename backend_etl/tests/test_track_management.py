import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from backend_etl.main import app, delete_project_track


class TrackDeletionTests(unittest.TestCase):
    def test_admin_deletes_track_persistently(self):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = 12

        result = delete_project_track(4, 12, db, {"role": "admin"})

        sql = str(db.execute.call_args.args[0])
        self.assertIn('DELETE FROM "Morceau"', sql)
        self.assertEqual(db.execute.call_args.args[1], {"project_id": 4, "track_id": 12})
        self.assertEqual(result, {"trackId": 12})
        db.commit.assert_called_once_with()

    def test_missing_track_returns_not_found_without_commit(self):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = None

        with self.assertRaises(HTTPException) as context:
            delete_project_track(4, 99, db, {"role": "admin"})

        self.assertEqual(context.exception.status_code, 404)
        db.commit.assert_not_called()

    def test_delete_route_is_exposed(self):
        paths = app.openapi()["paths"]

        self.assertIn("delete", paths["/api/projects/{project_id}/tracks/{track_id}"])


if __name__ == "__main__":
    unittest.main()
