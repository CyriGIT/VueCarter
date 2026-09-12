import unittest

from backend_etl.models.user import Utilisateur


class UserRoleTests(unittest.TestCase):
    def test_accompanying_role_is_resolved(self):
        user = Utilisateur(id_role=5)

        self.assertEqual(user.role, "accompagnant")

    def test_unknown_role_fails_closed(self):
        user = Utilisateur(id_role=999)

        self.assertEqual(user.role, "unknown")


if __name__ == "__main__":
    unittest.main()