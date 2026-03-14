from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
	ROOT_URLCONF="whiteneuron.base.test_urls",
	SECURE_SSL_REDIRECT=False,
	UNFOLD={
		"ENVIRONMENT": None,
		"DASHBOARD_CALLBACK": None,
		"SIDEBAR": {"navigation": []},
	},
)
class AdminMainUrlsStatusTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		user_model = get_user_model()
		cls.admin_user = user_model.objects.create_superuser(
			username="admin_test_user",
			email="admin_test_user@example.com",
			password="Admin#Test123",
		)

	def test_admin_login_page_returns_200(self):
		response = self.client.get(reverse("admin:login"))
		self.assertEqual(response.status_code, 200)

	def test_admin_main_urls_return_200_for_superuser(self):
		self.client.force_login(self.admin_user)

		user_opts = self.admin_user._meta
		urls = [
			reverse("admin:index"),
			reverse(f"admin:{user_opts.app_label}_{user_opts.model_name}_changelist"),
			reverse(f"admin:{user_opts.app_label}_{user_opts.model_name}_add"),
			reverse(
				f"admin:{user_opts.app_label}_{user_opts.model_name}_change",
				args=[self.admin_user.pk],
			),
		]

		for url in urls:
			with self.subTest(url=url):
				response = self.client.get(url)
				self.assertEqual(response.status_code, 200)
