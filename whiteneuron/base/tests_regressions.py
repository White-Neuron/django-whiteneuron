"""Regression tests for the hardening / performance changes."""
import asyncio
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from whiteneuron.base.middleware import get_client_ip
from whiteneuron.base.testing import package_test_settings
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


@package_test_settings()
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


@package_test_settings()
class FeedbackPermissionTests(TestCase):
    def test_change_permission_is_enough(self):
        from django.contrib.auth.models import Permission

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


@package_test_settings()
class FieldSelectionRestrictionTests(TestCase):
    """The column picker must only offer fields the admin itself exposes."""

    def setUp(self):
        from django.contrib.sessions.backends.signed_cookies import SessionStore

        self.request = RequestFactory().get("/")
        self.request.session = SessionStore()
        self.request.user = User.objects.create_superuser("picker", "p@example.com", "pw")

    def columns(self, admin, *selected):
        self.request.GET = self.request.GET.copy()
        self.request.GET.setlist("display_fields", list(selected))
        return list(admin.get_list_display(self.request))

    def test_all_respects_admin_fields(self):
        class RestrictedAppAdmin(ModelAdmin):
            fields = ["name", "category"]
            action_buttons = False

        admin = RestrictedAppAdmin(App, AdminSite())
        shown = self.columns(admin, "All")
        self.assertIn("name", shown)
        for hidden in ("url", "permission", "thumbnail_url", "icon"):
            self.assertNotIn(hidden, shown)
        # asking for a hidden field explicitly is refused too
        self.assertNotIn("url", self.columns(admin, "url"))

    def test_all_respects_exclude_and_fieldsets(self):
        class ExcludeAdmin(ModelAdmin):
            exclude = ["url"]
            action_buttons = False

        class FieldsetAdmin(ModelAdmin):
            fieldsets = ((None, {"fields": ("name", ("icon", "category"))}),)
            action_buttons = False

        self.assertNotIn("url", self.columns(ExcludeAdmin(App, AdminSite()), "All"))
        shown = self.columns(FieldsetAdmin(App, AdminSite()), "All")
        self.assertEqual({"name", "icon", "category"} & set(shown), {"name", "icon", "category"})
        self.assertNotIn("url", shown)

    def test_user_admin_uses_change_form_not_add_form(self):
        from whiteneuron.base.sites import base_admin_site

        from whiteneuron.base.filters import FieldSelectionFilter

        offered = {k for k, _ in FieldSelectionFilter.lookups(None, self.request, base_admin_site._registry[User])}
        self.assertTrue({"date_joined", "last_login", "uuid"} <= offered)  # change form only, not add_fieldsets

    def test_admin_whose_fieldsets_need_an_object_falls_back(self):
        class Fragile(ModelAdmin):
            action_buttons = False
            list_display = ["name"]

            def get_fieldsets(self, request, obj=None):
                raise AttributeError("needs a saved object")

        self.assertEqual(self.columns(Fragile(App, AdminSite()), "All"), ["name"])

    def test_password_never_offered(self):
        from whiteneuron.base.sites import base_admin_site

        user_admin = base_admin_site._registry[User]
        self.assertNotIn("password", self.columns(user_admin, "All"))
        self.assertNotIn("password", self.columns(user_admin, "password"))

    def test_every_registered_admin_offers_only_form_fields(self):
        from django.contrib.admin.utils import flatten_fieldsets

        from whiteneuron.base.filters import FieldSelectionFilter
        from whiteneuron.base.sites import base_admin_site

        for model, model_admin in base_admin_site._registry.items():
            if not hasattr(model_admin, "enable_field_selection_filter"):
                continue
            with self.subTest(admin=type(model_admin).__name__):
                # the change form of an (unsaved) object: what an editor sees for a row
                form_fields = set(flatten_fieldsets(model_admin.get_fieldsets(self.request, model())))
                offered = {k for k, _ in FieldSelectionFilter.lookups(None, self.request, model_admin)} - {"default"}
                self.assertLessEqual(offered, form_fields)
                self.assertNotIn("password", offered)


@package_test_settings()
class SecondReviewRegressionTests(TestCase):
    def setUp(self):
        from django.contrib.sessions.backends.signed_cookies import SessionStore

        self.root = User.objects.create_superuser("rev2", "rev2@example.com", "pw")
        self.request = RequestFactory().get("/")
        self.request.session = SessionStore()
        self.request.user = self.root

    def test_buttons_escape_primary_key(self):
        from whiteneuron.base.modeladmin import _current_request

        admin = ModelAdmin(App, AdminSite())
        app = App(pk=1, name="x")
        app.pk = '1"><img src=x onerror=alert(1)>'
        _current_request.set(self.request)
        with mock.patch("whiteneuron.base.modeladmin.reverse", return_value="/admin/x/"):
            html = str(admin.buttons(app))
        self.assertNotIn("<img src=x", html)
        self.assertIn("&quot;&gt;&lt;img", html)

    def test_list_display_links_none(self):
        class NoLinks(ModelAdmin):
            list_display_links = None

        admin = NoLinks(App, AdminSite())
        self.assertIsNone(admin.get_list_display_links(self.request, ["name", "buttons"]))

    def test_request_property_backward_compatible(self):
        admin = ModelAdmin(App, AdminSite())
        admin.get_changelist(self.request)
        self.assertIs(admin.request, self.request)

    def test_translation_without_api_key_is_a_failure(self):
        from whiteneuron.contrib.wn_modeltranslation import utils

        with mock.patch.object(utils, "client", None):
            result = utils.translate_object(App(pk=1, name="x"))
        self.assertFalse(result["success"])

    def test_safe_href_rejects_whitespace_tricks(self):
        from whiteneuron.base.html_sanitize import is_safe_href, sanitize_html

        for href in ("/\t/evil.com", "/\n/evil.com", "//evil.com", "/\\evil.com", "javascript:alert(1)"):
            self.assertFalse(is_safe_href(href), repr(href))
        self.assertTrue(is_safe_href("/admin/base/app/1/change/"))
        self.assertNotIn("evil", sanitize_html('<a href="/&#9;/evil.com">x</a>'))

    @override_settings(WN_ADMIN_THEMES=[])
    def test_empty_theme_list_disables_picker(self):
        from whiteneuron.base.templatetags.wn_theme import wn_admin_themes

        self.assertEqual(wn_admin_themes(), [])

    def test_collector_survives_cache_outage(self):
        from whiteneuron.monitoring import collector
        from whiteneuron.monitoring.models import MetricSample

        data = collector.snapshot()
        with mock.patch.object(collector.cache, "set", side_effect=ConnectionError), \
                mock.patch.object(collector.cache, "add", side_effect=ConnectionError):
            self.assertIsNotNone(collector.record(data, force=True))
            collector.beat()  # must not raise
        self.assertEqual(MetricSample.objects.count(), 1)

    def test_websocket_rejection_uses_4401(self):
        from whiteneuron.notification.consumers import NotificationConsumer
        from django.contrib.auth.models import AnonymousUser

        consumer = NotificationConsumer()
        consumer.scope = {"user": AnonymousUser()}
        consumer.accept = mock.AsyncMock()
        consumer.close = mock.AsyncMock()
        asyncio.run(consumer.connect())
        consumer.accept.assert_awaited_once()
        consumer.close.assert_awaited_once_with(code=4401)


@package_test_settings()
class AdminTemplateRegressionTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser("tpl", "tpl@example.com", "pw")
        self.client.force_login(self.root)

    def test_toolbar_controls_render_without_search_fields(self):
        # IntervalScheduleAdmin has list_filter but no search_fields: the filter button, grid
        # toggle and page-size picker used to disappear with the search box
        page = self.client.get(reverse("admin:django_celery_beat_intervalschedule_changelist"))
        self.assertEqual(page.status_code, 200)
        self.assertFalse(page.context["cl"].search_fields)
        self.assertContains(page, 'class="filter-open-button')
        self.assertContains(page, 'name="grid_view"')
        self.assertContains(page, 'name="per_page"')
        self.assertNotContains(page, 'id="changelist-search"')

    def test_next_disabled_on_last_full_page(self):
        # a full last page used to keep "Next" active, linking to a page that doesn't exist
        url = reverse("admin:base_user_changelist")
        cl = self.client.get(url).context["cl"]
        per_page = cl.list_per_page
        missing = -cl.result_count % per_page + per_page  # at least two full pages
        User.objects.bulk_create(User(username=f"pad{i}") for i in range(missing))
        cl = self.client.get(url).context["cl"]
        self.assertEqual(cl.result_count % per_page, 0)
        last = cl.paginator.num_pages
        self.assertGreater(last, 1)
        page = self.client.get(url, {"p": last})
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, f"?p={last + 1}")
        # the Previous button itself (not just the page-number link) is enabled
        self.assertContains(page, f'href="?p={last - 1}" class="ui-btn')

    def test_show_all_ignored_by_django_keeps_pagination(self):
        # ?all is kept by search/filter links; with more rows than list_max_show_all
        # Django ignores it and still paginates, so Next must stay usable
        url = reverse("admin:base_user_changelist")
        User.objects.bulk_create(User(username=f"many{i}") for i in range(210))
        page = self.client.get(url, {"all": ""})
        cl = page.context["cl"]
        self.assertTrue(cl.show_all)
        self.assertFalse(cl.can_show_all)
        self.assertGreater(cl.paginator.num_pages, 1)
        self.assertContains(page, 'p=2" class="ui-btn')

    def test_show_all_disables_both_buttons(self):
        url = reverse("admin:base_user_changelist")
        User.objects.bulk_create(User(username=f"few{i}") for i in range(60))
        page = self.client.get(url, {"all": ""})
        cl = page.context["cl"]
        self.assertTrue(cl.show_all and cl.can_show_all)
        self.assertEqual(page.content.decode().count('aria-disabled="true"'), 2)

    def test_previous_disabled_on_first_page(self):
        url = reverse("admin:base_user_changelist")
        User.objects.bulk_create(User(username=f"one{i}") for i in range(60))
        page = self.client.get(url)
        self.assertEqual(page.context["cl"].page_num, 1)
        self.assertContains(page, 'aria-disabled="true">Previous', count=1)
        self.assertContains(page, 'p=2" class="ui-btn')
