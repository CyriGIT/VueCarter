import unittest
from unittest.mock import Mock, patch

from backend_etl.services.mx3_service import Mx3AuthError, Mx3Service


class Mx3ServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = Mx3Service()

    @patch("backend_etl.services.mx3_service.settings")
    @patch("backend_etl.services.mx3_service.requests")
    def test_searches_bands_and_reuses_token(self, requests_mock, settings_mock):
        settings_mock.mx3_is_configured = True
        settings_mock.SRGSSR_OAUTH_TOKEN_URL = "https://oauth.test/token"
        settings_mock.SRGSSR_MX3_API_BASE_URL = "https://api.test"
        settings_mock.SRGSSR_MX3_CONSUMER_KEY = "key"
        settings_mock.SRGSSR_MX3_CONSUMER_SECRET = "secret"
        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: {"access_token": "token", "expires_in": 3600},
        )
        requests_mock.get.return_value = Mock(
            status_code=200,
            json=lambda: {"response": [{"status": "Ok", "bands": [{"id": 42, "name": "Projet Epsilon"}]}]},
        )

        first = self.service.search_bands("Projet Epsilon")
        second = self.service.search_bands("Projet Epsilon")

        self.assertEqual(first, [{"id": 42, "name": "Projet Epsilon"}])
        self.assertEqual(second, first)
        requests_mock.post.assert_called_once()
        self.assertEqual(requests_mock.get.call_args.kwargs["headers"]["accept"], "application/json")

    @patch("backend_etl.services.mx3_service.settings")
    @patch("backend_etl.services.mx3_service.requests")
    def test_reads_single_performance_object(self, requests_mock, settings_mock):
        settings_mock.mx3_is_configured = True
        settings_mock.SRGSSR_OAUTH_TOKEN_URL = "https://oauth.test/token"
        settings_mock.SRGSSR_MX3_API_BASE_URL = "https://api.test"
        settings_mock.SRGSSR_MX3_CONSUMER_KEY = "key"
        settings_mock.SRGSSR_MX3_CONSUMER_SECRET = "secret"
        requests_mock.post.return_value = Mock(status_code=200, json=lambda: {"access_token": "token"})
        requests_mock.get.return_value = Mock(
            status_code=200,
            json=lambda: {"response": [{"performances": {"name": "Club Gig", "date": "20260827T20:00:00.000Z"}}]},
        )

        gigs = self.service.get_band_gigs(42)

        self.assertEqual(gigs[0]["name"], "Club Gig")

    @patch("backend_etl.services.mx3_service.settings")
    @patch("backend_etl.services.mx3_service.requests")
    def test_reads_wrapped_singular_band_detail(self, requests_mock, settings_mock):
        settings_mock.mx3_is_configured = True
        settings_mock.SRGSSR_OAUTH_TOKEN_URL = "https://oauth.test/token"
        settings_mock.SRGSSR_MX3_API_BASE_URL = "https://api.test"
        settings_mock.SRGSSR_MX3_CONSUMER_KEY = "key"
        settings_mock.SRGSSR_MX3_CONSUMER_SECRET = "secret"
        requests_mock.post.return_value = Mock(status_code=200, json=lambda: {"access_token": "token"})
        requests_mock.get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "response": {
                    "status": "Ok",
                    "band": {
                        "id": {"type": "integer", "value": "103214"},
                        "name": {"value": "Novia"},
                        "city": {},
                        "public-page-url": {"value": "https://mx3.ch/novia"},
                    },
                }
            },
        )

        band = self.service.get_band(103214)

        self.assertEqual(band["id"], "103214")
        self.assertEqual(band["name"], "Novia")
        self.assertIsNone(band["city"])
        self.assertEqual(band["public_page_url"], "https://mx3.ch/novia")

    @patch.object(Mx3Service, "get_band")
    def test_extracts_available_band_metrics_without_fake_zeroes(self, get_band_mock):
        get_band_mock.return_value = {
            "listening_count": "589",
            "profile_views_count": 7561,
            "playlists_count": None,
            "singles_count": "11",
        }

        metrics = self.service.get_band_stats(103214)

        self.assertEqual(metrics, {
            "Ecoutes_Cumulees": 589,
            "Vues_Profil": 7561,
            "Singles_Publies": 11,
        })

    @patch.object(Mx3Service, "get_band")
    def test_rejects_invalid_band_metric(self, get_band_mock):
        get_band_mock.return_value = {"listening_count": "inconnu"}

        with self.assertRaisesRegex(Exception, "n'est pas numérique"):
            self.service.get_band_stats(103214)

    @patch("backend_etl.services.mx3_service.settings")
    def test_rejects_missing_credentials(self, settings_mock):
        settings_mock.mx3_is_configured = False

        with self.assertRaisesRegex(Mx3AuthError, "ne sont pas configurés"):
            self.service.search_bands("Test")


if __name__ == "__main__":
    unittest.main()