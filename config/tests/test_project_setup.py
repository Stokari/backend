from django.conf import settings
from django.core.mail import mailers
from django.test import SimpleTestCase, override_settings
from django.urls import resolve


class ProjectSetupTests(SimpleTestCase):
    def test_secret_key_is_configured(self):
        self.assertTrue(settings.SECRET_KEY)

    def test_timezone_support_is_enabled(self):
        self.assertTrue(settings.USE_TZ)

    def test_admin_url_resolves(self):
        match = resolve("/admin/")
        self.assertEqual(match.namespace, "admin")
        self.assertEqual(match.url_name, "index")

    def test_api_docs_urls_resolve(self):
        self.assertEqual(resolve("/api/schema/").url_name, "schema")
        self.assertEqual(resolve("/api/docs/").url_name, "swagger-ui")
        self.assertEqual(resolve("/api/redoc/").url_name, "redoc")

    def test_cors_and_allowed_hosts_configured(self):
        self.assertIsInstance(settings.ALLOWED_HOSTS, list)
        self.assertIsInstance(settings.CORS_ALLOWED_ORIGINS, list)
        self.assertGreater(len(settings.ALLOWED_HOSTS), 0)
        self.assertGreater(len(settings.CORS_ALLOWED_ORIGINS), 0)

    def test_static_and_media_roots_configured(self):
        self.assertTrue(settings.STATIC_ROOT)
        self.assertTrue(settings.MEDIA_ROOT)

    @override_settings(
        MAILERS={
            "default": {
                "BACKEND": "django.core.mail.backends.console.EmailBackend",
            }
        }
    )
    def test_default_mailer_uses_console_backend(self):
        self.assertEqual(
            settings.MAILERS["default"]["BACKEND"],
            "django.core.mail.backends.console.EmailBackend",
        )
        self.assertEqual(
            mailers.default.__class__.__module__,
            "django.core.mail.backends.console",
        )
