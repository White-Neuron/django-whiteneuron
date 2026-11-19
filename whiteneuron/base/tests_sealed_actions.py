"""#93: detail actions apply to the version the user saw; file size checked before upload."""
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.http import HttpResponseRedirect
from django.test import TestCase, override_settings
from django.urls import path, reverse
from unittest import mock

from unfold.decorators import action

from whiteneuron.feedbacks.models import FeedbackData

from .modeladmin import ModelAdmin
from .sealed import SEAL_PARAM, sealed

User = get_user_model()
from .sites import base_admin_site

site = type(base_admin_site)(name="sealtest")  # the core's site class, a second instance


class SealedFeedbackAdmin(ModelAdmin):
    actions_detail = ["approve", "plain"]
    upload_max_mb = 2

    @action(description="Approve", url_path="approve")
    @sealed(version=lambda obj: obj.updated_at.isoformat())
    def approve(self, request, object_id):
        FeedbackData.objects.filter(pk=object_id).update(note="approved")
        return HttpResponseRedirect("/done/")

    @action(description="Plain", url_path="plain")
    def plain(self, request, object_id):
        return HttpResponseRedirect("/done/")


site.register(FeedbackData, SealedFeedbackAdmin)
from .urls_testing import urlpatterns as _package_urls  # noqa: E402

urlpatterns = [path("sealtest/", site.urls), *_package_urls]


@override_settings(ROOT_URLCONF=__name__)
class SealedActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.other = User.objects.create_superuser("other", "o@example.com", "pw")

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.fb = FeedbackData.objects.create(user=self.root, content_type=ContentType.objects.get_for_model(Group),
                                              object_id="1", message="m")
        self.client.force_login(self.root)

    def _paths(self, user=None):
        """The detail-action links of the change page, as render_change_form leaves them."""
        from django.test import RequestFactory

        admin = site._registry[FeedbackData]
        request = RequestFactory().get("/")
        request.user = user or self.root
        object_id = str(self.fb.pk)
        nav = admin._get_actions_navigation(admin.actions_detail, admin.get_actions_detail(request, object_id), object_id)
        context = {"actions_detail": nav}
        with mock.patch("unfold.admin.ModelAdmin.render_change_form", return_value=None):
            admin.render_change_form(request, context, change=True, obj=self.fb)
        return {item["title"]: item["path"] for item in context["actions_detail"]}

    def _errors(self, response):
        from django.contrib.messages import get_messages

        return " ".join(str(m) for m in get_messages(response.wsgi_request))

    def _approved(self):
        self.fb.refresh_from_db()
        return self.fb.note == "approved"

    def test_the_page_signs_sealed_actions_only(self):
        paths = self._paths()
        self.assertIn(SEAL_PARAM, parse_qs(urlparse(paths["Approve"]).query))
        self.assertNotIn("?", paths["Plain"])

    def test_the_action_runs_with_the_token_of_the_page(self):
        response = self.client.get(self._paths()["Approve"])
        self.assertEqual(response["Location"], "/done/")
        self.assertTrue(self._approved())

    def test_a_record_changed_since_the_page_opened_is_refused(self):
        url = self._paths()["Approve"]
        FeedbackData.objects.filter(pk=self.fb.pk).update(updated_at=self.fb.updated_at + timedelta(seconds=5))
        response = self.client.get(url)
        self.assertFalse(self._approved())
        self.assertEqual(response["Location"], reverse("sealtest:feedbacks_feedbackdata_change", args=[self.fb.pk]))
        self.assertIn("The content has changed since you opened the page", self._errors(response))

    def test_missing_forged_or_foreign_tokens_are_refused(self):
        base = reverse("sealtest:feedbacks_feedbackdata_approve", args=[self.fb.pk])
        self.client.get(base)
        self.client.get(base + "?" + SEAL_PARAM + "=forged")
        url = self._paths()["Approve"]
        self.client.force_login(self.other)
        self.client.get(url)   # issued to root
        self.assertFalse(self._approved())

    @override_settings(WN_ACTION_SEAL_MAX_AGE=-1)
    def test_an_expired_token_is_refused(self):
        self.client.get(self._paths()["Approve"])
        self.assertFalse(self._approved())

    def test_file_inputs_carry_the_size_limit(self):
        admin = site._registry[FeedbackData]
        from django.db import models

        field = admin.formfield_for_dbfield(models.FileField(name="upload"), None)
        self.assertEqual(field.widget.attrs["data-wn-max-bytes"], str(2 * 1024 * 1024))
        self.assertIn("2 MB", field.widget.attrs["data-wn-max-message"])
        admin.upload_max_mb = None
        try:
            field = admin.formfield_for_dbfield(models.FileField(name="upload"), None)
            self.assertNotIn("data-wn-max-bytes", field.widget.attrs)   # off by default
        finally:
            admin.upload_max_mb = 2
