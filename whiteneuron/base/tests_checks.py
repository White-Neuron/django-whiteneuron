"""System checks of the base app."""
from django.core import checks
from django.test import SimpleTestCase, override_settings

from .checks import untracked_url_names_check
from .testing import package_test_settings


@package_test_settings()
class UntrackedUrlNamesCheckTests(SimpleTestCase):
    def _ids(self):
        return [m.id for m in untracked_url_names_check()]

    @override_settings(WN_UNTRACKED_URL_NAMES=["admin:index", "admin:no_such_view"])
    def test_warns_about_names_that_do_not_resolve(self):
        messages = untracked_url_names_check()
        self.assertEqual([m.id for m in messages], ["whiteneuron.W002"])
        self.assertIn("admin:no_such_view", messages[0].msg)
        self.assertNotIn("admin:index", messages[0].msg)
        self.assertIn("whiteneuron.W002", [m.id for m in checks.run_checks(tags=[checks.Tags.urls])])

    @override_settings(WN_UNTRACKED_URL_NAMES=["admin:index"])
    def test_quiet_when_every_name_resolves(self):
        self.assertEqual(self._ids(), [])

    @override_settings(WN_UNTRACKED_URL_NAMES=[])
    def test_quiet_by_default(self):
        self.assertEqual(self._ids(), [])

    @override_settings(WN_UNTRACKED_URL_NAMES=["admin:base_app_change"])
    def test_a_name_with_arguments_is_reported_with_the_reason(self):
        messages = untracked_url_names_check()
        self.assertEqual([m.id for m in messages], ["whiteneuron.W002"])
        self.assertIn("without arguments", messages[0].hint)
