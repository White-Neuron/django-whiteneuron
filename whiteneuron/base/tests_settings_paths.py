"""#50: templates rendered twice, static files found twice, the project's .env ignored."""
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class SettingsPathsRegressionTests(TestCase):
    def test_admin_page_renders_its_overlays_once(self):
        root = User.objects.create_superuser("root", "r@example.com", "pw")
        self.client.force_login(root)
        html = self.client.get(reverse("admin:index")).content.decode()
        self.assertEqual(html.count('id="toast-container"'), 1)
        self.assertEqual(html.count('id="loading-overlay"'), 1)

    def test_package_static_files_are_found_once(self):
        from django.contrib.staticfiles import finders

        self.assertEqual(len(finders.find("base/js/whiteneuron.js", find_all=True)), 1)


class ProjectDotenvTests(SimpleTestCase):
    def _setting_from(self, cwd, env, expr="s.RATE_LIMIT_REQUESTS"):
        import os
        import subprocess
        import sys
        import tempfile

        base = {k: v for k, v in os.environ.items() if k not in ("RATE_LIMIT_REQUESTS", "WN_ENV_FILE")}
        base.update(PYTHONPATH=str(Path(__file__).resolve().parents[2]), DEBUG="True", **env)
        # a script file, like manage.py: with `python -c`, python-dotenv searches the cwd anyway
        with tempfile.TemporaryDirectory() as scripts:
            script = Path(scripts, "manage.py")
            script.write_text(f"import whiteneuron.base.settings as s\nprint({expr})\n")
            return subprocess.run([sys.executable, str(script)], cwd=cwd, env=base,
                                  capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]

    def test_the_projects_dotenv_is_loaded(self):
        import tempfile

        with tempfile.TemporaryDirectory() as project:
            Path(project, ".env").write_text("RATE_LIMIT_REQUESTS=7\n")
            self.assertEqual(self._setting_from(project, {}), "7")

    def test_wn_env_file_points_at_another_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as project:
            Path(project, "prod.env").write_text("RATE_LIMIT_REQUESTS=9\n")
            self.assertEqual(self._setting_from(project, {"WN_ENV_FILE": str(Path(project, "prod.env"))}), "9")

    def test_a_missing_wn_env_file_is_an_error(self):
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as project:
            with self.assertRaises(subprocess.CalledProcessError) as raised:
                self._setting_from(project, {"WN_ENV_FILE": str(Path(project, "typo.env"))})
            self.assertIn("WN_ENV_FILE is set but there is no file", raised.exception.stderr)
