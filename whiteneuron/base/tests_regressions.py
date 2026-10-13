"""Regression tests for the hardening / performance changes."""
import asyncio
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from whiteneuron.base.middleware import get_client_ip
from whiteneuron.base.modeladmin import ModelAdmin
from whiteneuron.base.models import App
from whiteneuron.notification.models import Notification

User = get_user_model()


class ClientIpTests(TestCase):
    rf = RequestFactory()

    def ip(self, xff=None, remote="10.0.0.2"):
        extra = {"REMOTE_ADDR": remote}
        if xff is not None:
            extra["HTTP_X_FORWARDED_FOR"] = xff
        return get_client_ip(self.rf.get("/", **extra))[0]

    def test_auto_uses_rightmost_public_hop(self):
        self.assertEqual(self.ip("6.6.6.6, 8.8.8.8"), "8.8.8.8")          # spoofed left entry ignored
        self.assertEqual(self.ip("8.8.8.8", remote="34.1.2.3"), "8.8.8.8")  # public load balancer

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_proxy_count_keeps_positions(self):
        # the proxy's own entry has a port: it must not be dropped (that would shift the index)
        self.assertEqual(self.ip("6.6.6.6, 203.0.113.9:51234"), "203.0.113.9")
        self.assertEqual(self.ip("[2001:db8::1]:443"), "2001:db8::1")

    @override_settings(IGNORE_X_FORWARDED_FOR=True)
    def test_ignore_flag(self):
        self.assertEqual(self.ip("8.8.8.8", remote="1.1.1.1"), "1.1.1.1")


class NewUserPasswordTests(TestCase):
    @mock.patch("whiteneuron.base.utils.send_email_login")
    def test_user_without_password_gets_one(self, send):
        with self.captureOnCommitCallbacks(execute=True):
            user = User.objects.create(username="bob", email="bob@example.com")
        user.refresh_from_db()
        self.assertTrue(user.password and user.has_usable_password())
        send.assert_called_once()

    @mock.patch("whiteneuron.base.utils.send_email_login")
    def test_password_set_by_create_user_is_kept(self, send):
        with self.captureOnCommitCallbacks(execute=True):
            user = User.objects.create_user("amy", "amy@example.com", "S3cret!pw")
        user.refresh_from_db()
        self.assertTrue(user.check_password("S3cret!pw"))
        send.assert_not_called()


class ReadonlyFieldsTests(TestCase):
    def test_declared_list_type_is_kept_and_not_mutated(self):
        class AppAdmin(ModelAdmin):
            readonly_fields = ["name"]

        admin = AppAdmin(App, AdminSite())
        request = RequestFactory().get("/")
        request.user = User(is_superuser=True)
        first = admin.get_readonly_fields(request)
        admin.get_readonly_fields(request)
        self.assertIsInstance(first, list)
        self.assertEqual(AppAdmin.readonly_fields, ["name"])  # class attribute untouched
        self.assertEqual(first.count("id"), 1)


class SoftDeleteHistoryTests(TestCase):
    def test_bulk_soft_delete_is_in_object_history(self):
        root = User.objects.create_superuser("root", "r@example.com", "pw")
        app = App.objects.create(name="probe")  # App doesn't override delete()
        Notification.objects.all().delete()
        admin = ModelAdmin(App, AdminSite())
        request = RequestFactory().post("/")
        request.user = root
        admin.delete_queryset(request, App.objects.filter(pk=app.pk))
        app = App.objects_all.get(pk=app.pk)
        self.assertTrue(app.is_deleted)
        note = Notification.objects.get(user=root)  # one entry, linked to the object
        self.assertEqual(note.obj_link, app.path())
        self.assertEqual(note.action, "delete")


class NotificationRoutingTests(TestCase):
    def test_staff_only_joins_own_group(self):
        from whiteneuron.notification.consumers import ADMIN_GROUP, NotificationConsumer, user_group

        staff = User.objects.create_user("staff", password="pw", is_staff=True)
        root = User.objects.create_superuser("root2", "r2@example.com", "pw")

        async def groups_for(user):
            consumer = NotificationConsumer()
            consumer.scope = {"user": user}
            consumer.channel_name = "c"
            consumer.channel_layer = mock.AsyncMock()
            consumer.accept = mock.AsyncMock()
            await consumer.connect()
            return consumer.joined

        self.assertEqual(asyncio.run(groups_for(staff)), [user_group(staff.pk)])
        self.assertEqual(asyncio.run(groups_for(root)), [user_group(root.pk), ADMIN_GROUP])


@override_settings(ROOT_URLCONF="whiteneuron.base.test_urls")
class FeedbackPermissionTests(TestCase):
    def test_change_permission_is_enough(self):
        from django.contrib.auth.models import Permission

        cache.clear()
        user = User.objects.create_user("editor", password="pw", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="change_app"))
        app = App.objects.create(name="x")
        self.client.force_login(user)
        response = self.client.post(
            reverse("feedback_endpoint"),
            data={"object_id": str(app.pk), "feedback_message": "hi", "model_name": "app", "app_label": "base"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)


class ExportChunkTests(TestCase):
    def test_export_reads_ids_in_chunks(self):
        from whiteneuron.contrib.wn_import_export import tasks
        from whiteneuron.file_management.models import ExcelFile

        users = [User.objects.create_user(f"u{i}") for i in range(5)]
        excel = ExcelFile.objects.create(title="t", status="pending", method="auto", is_public=False)
        with mock.patch.object(tasks, "EXPORT_CHUNK", 2):
            tasks.export(excel.pk, "base", "user", [u.pk for u in users], file_name="u.xlsx")
        excel.refresh_from_db()
        self.assertEqual(excel.status, "done", excel.description)
        import openpyxl
        sheet = openpyxl.load_workbook(excel.file.path).active
        self.assertEqual(sheet.max_row - 1, 5)
        excel.file.delete(save=False)
