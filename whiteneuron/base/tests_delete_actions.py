"""#34: hard delete acted on the first click; soft delete was described as a permanent delete."""
from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.fallback import FallbackStorage
from unittest import mock

from django.test import RequestFactory, TestCase

from whiteneuron.feedbacks.models import FeedbackData

from .modeladmin import ModelAdmin
from .sites import base_admin_site
from .testing import package_test_settings

User = get_user_model()


def plain_admin(model):
    # the package's own BaseModel admins forbid deleting: a plain one shows the base behavior
    return ModelAdmin(model, base_admin_site)


@package_test_settings()
class DeleteActionConfirmationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")

    def setUp(self):
        self.record = FeedbackData.objects.create(
            user=self.root, content_type=ContentType.objects.get_for_model(Group), object_id="1", message="probe")
        self.admin = plain_admin(FeedbackData)
        # the cascade check asks the registered admin for permission: register the plain one
        patcher = mock.patch.dict(base_admin_site._registry, {FeedbackData: self.admin})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _request(self, data=None, user=None):
        request = RequestFactory().post("/", data or {})
        request.user = user or self.root
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def _act(self, action, data=None, user=None):
        request = self._request(data, user)
        func = self.admin.get_actions(request)[action][0]
        response = func(self.admin, request, FeedbackData.objects_all.filter(pk=self.record.pk))
        if response is not None:
            response.render()
        return response

    def _exists(self):
        return FeedbackData.objects_all.filter(pk=self.record.pk).exists()

    def test_hard_delete_first_post_only_confirms(self):
        response = self._act("hard_delete")
        self.assertContains(response, "This cannot be undone")
        self.assertContains(response, 'name="wn_confirm"')
        self.assertContains(response, 'name="action" value="hard_delete"')
        self.assertTrue(self._exists())

    def test_hard_delete_needs_delete_typed(self):
        self.assertIsNotNone(self._act("hard_delete", {"post": "yes", "wn_confirm": "delete"}))
        self.assertTrue(self._exists())
        self.assertIsNone(self._act("hard_delete", {"post": "yes", "wn_confirm": "DELETE"}))
        self.assertFalse(self._exists())

    def test_soft_delete_confirms_a_move_to_the_trash(self):
        response = self._act("delete_selected")
        self.assertContains(response, "to the trash")
        self.assertNotContains(response, "related items will be deleted")
        self.assertFalse(FeedbackData.objects_all.get(pk=self.record.pk).is_deleted)
        self.assertIsNone(self._act("delete_selected", {"post": "yes"}))
        self.assertTrue(FeedbackData.objects_all.get(pk=self.record.pk).is_deleted)

    def test_soft_delete_confirmation_also_for_staff(self):
        staff = User.objects.create_user("staff", password="pw", is_staff=True)
        from django.contrib.auth.models import Permission

        staff.user_permissions.set(Permission.objects.filter(
            content_type__app_label="feedbacks", codename__in=["view_feedbackdata", "delete_feedbackdata"]))
        staff = User.objects.get(pk=staff.pk)  # fresh permission cache
        self.assertNotIn("hard_delete", self.admin.get_actions(self._request(user=staff)))
        self.assertContains(self._act("delete_selected", user=staff), "to the trash")

    def test_delete_button_on_a_record_says_trash(self):
        request = RequestFactory().get("/")
        request.user = self.root
        response = self.admin.delete_view(request, str(self.record.pk))
        response.render()
        self.assertContains(response, "to the trash")
        self.assertNotContains(response, "related items will be deleted")

    def test_real_deletes_keep_djangos_cascade_page(self):
        group = Group.objects.create(name="g")
        group_admin = plain_admin(Group)
        request = self._request()
        response = group_admin.get_actions(request)["delete_selected"][0](group_admin, request, Group.objects.all())
        response.render()
        self.assertNotContains(response, "to the trash")
        self.assertTrue(Group.objects.filter(pk=group.pk).exists())
        self.assertIsInstance(group_admin, django_admin.ModelAdmin)

    def test_confirmation_is_translated(self):
        from django.utils import translation

        with translation.override("vi"):
            self.assertContains(self._act("delete_selected"), "vào thùng rác")
            self.assertContains(self._act("hard_delete"), "không thể hoàn tác")
