import unittest

from fastapi import HTTPException

from backend_etl.core.dependencies import require_admin, require_grant_manager
from backend_etl.models.user import Utilisateur


class RequireAdminTests(unittest.TestCase):
    @staticmethod
    def _user(role_id: int) -> Utilisateur:
        user = Utilisateur()
        user.id_role = role_id
        user.est_actif = True
        return user

    def test_admin_is_allowed(self):
        admin = self._user(1)

        self.assertIs(require_admin(admin), admin)

    def test_non_admin_roles_are_forbidden(self):
        for role_id in (2, 3, 4):
            with self.subTest(role_id=role_id), self.assertRaises(HTTPException) as context:
                require_admin(self._user(role_id))

            self.assertEqual(context.exception.status_code, 403)
            self.assertEqual(context.exception.detail, "Accès réservé aux administrateurs.")


class RequireGrantManagerTests(unittest.TestCase):
    @staticmethod
    def _user(role_id: int) -> Utilisateur:
        user = Utilisateur()
        user.id_role = role_id
        user.est_actif = True
        return user

    def test_admin_and_case_manager_are_allowed(self):
        for role_id in (1, 2):
            with self.subTest(role_id=role_id):
                user = self._user(role_id)
                self.assertIs(require_grant_manager(user), user)

    def test_jury_and_artist_are_forbidden(self):
        for role_id in (3, 4):
            with self.subTest(role_id=role_id), self.assertRaises(HTTPException) as context:
                require_grant_manager(self._user(role_id))

            self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()