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
