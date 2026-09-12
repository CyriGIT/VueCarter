import unittest

from backend_etl.services.account_identity_service import resolve_display_name


class ResolveDisplayNameTests(unittest.TestCase):
    def test_prefers_account_display_name(self) -> None:
        result = resolve_display_name("Administration Démo", "Autre", "Nom", "admin@example.com")

        self.assertEqual(result, "Administration Démo")

    def test_falls_back_to_linked_person_name(self) -> None:
        result = resolve_display_name(None, "Jury Alpha", "Démo", "jury.alpha@example.com")

        self.assertEqual(result, "Jury Alpha Démo")

    def test_falls_back_to_email_without_any_name(self) -> None:
        result = resolve_display_name("  ", None, None, "service@example.com")

        self.assertEqual(result, "service@example.com")


if __name__ == "__main__":
    unittest.main()
