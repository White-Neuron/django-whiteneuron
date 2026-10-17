"""Regression tests for the hardening / performance changes."""
import asyncio
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import translation

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


class I18nCatalogRegressionTests(TestCase):
    """makemessages can't read _() inside f-strings: such strings silently dropped out of
    the Vietnamese catalog in 0.4.0.0 (marked obsolete, so missing from django.mo)."""

    GETTEXT_FUNCS = {"_", "gettext", "gettext_lazy", "pgettext", "pgettext_lazy", "ngettext", "ngettext_lazy"}

    @staticmethod
    def _python_files():
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[1]
        for path in root.rglob("*.py"):
            if "migrations" in path.parts or path.name.startswith("tests"):
                continue
            yield root, path

    def _func_name(self, call):
        return getattr(call.func, "id", None) or getattr(call.func, "attr", None)

    def test_no_gettext_inside_fstrings(self):
        import ast
        found = []
        for root, path in self._python_files():
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.JoinedStr):
                    for call in ast.walk(node):
                        if isinstance(call, ast.Call) and self._func_name(call) in self.GETTEXT_FUNCS:
                            found.append(f"{path.relative_to(root)}:{call.lineno}")
        self.assertEqual(found, [], "move these _() calls out of the f-strings so makemessages sees them")

    def test_python_msgids_are_in_the_vietnamese_catalog(self):
        import ast
        import gettext
        import pathlib

        mo = pathlib.Path(__file__).resolve().parents[1] / "locale" / "vi" / "LC_MESSAGES" / "django.mo"
        with mo.open("rb") as fh:
            catalog = gettext.GNUTranslations(fh)._catalog
        missing = {}
        for root, path in self._python_files():
            for call in ast.walk(ast.parse(path.read_text())):
                if (isinstance(call, ast.Call) and self._func_name(call) in {"_", "gettext", "gettext_lazy"}
                        and call.args and isinstance(call.args[0], ast.Constant)
                        and isinstance(call.args[0].value, str) and call.args[0].value):
                    msgid = call.args[0].value
                    if msgid not in catalog:
                        with translation.override("vi"):
                            if str(translation.gettext(msgid)) == msgid:  # not covered by Django/Unfold either
                                missing.setdefault(msgid, f"{path.relative_to(root)}:{call.lineno}")
        self.assertEqual(missing, {}, "run scripts/makemessages.sh, translate, then scripts/compilemessages.sh")

    def test_dashboard_kpi_is_fully_translated(self):
        from whiteneuron.dashboard.views import dashboard_callback

        request = RequestFactory().get("/admin/", {"time": "today"})
        with translation.override("vi"):
            kpi = dashboard_callback(request, {})["kpi"][0]
        self.assertIn("trong", kpi["title"])
        self.assertIn("tiến trình từ lần cuối", str(kpi["footer"]))
        self.assertIn("ngày", str(kpi["footer"]))


class UiModalCssRegressionTests(TestCase):
    def test_ui_modal_overrides_unfold_dialog_rule(self):
        # Unfold's unlayered `dialog {...}` beat daisyUI's layered .ui-modal (narrow white
        # column, no overlay); styles.css must carry the dialog.ui-modal override.
        import pathlib

        css = (pathlib.Path(__file__).resolve().parents[1] / "static" / "base" / "css" / "styles.css").read_text()
        rule = css[css.index("dialog.ui-modal{"):]
        rule = rule[: rule.index("}")]
        for decl in ("position:fixed", "inset:0", "translate:none", "width:100%", "padding:0"):
            self.assertIn(decl, rule)


class AnnouncementContentTests(TestCase):
    def _get(self):
        from whiteneuron.base.views import get_announcement_content
        return get_announcement_content(RequestFactory().get("/announcement/"))

    @override_settings(ANNOUNCEMENT_CONTENT_HTML_FILE="does-not-exist/announcement.html")
    def test_missing_template_returns_empty_content(self):
        with self.assertLogs("whiteneuron.base.views", level="WARNING"):
            response = self._get()
        self.assertEqual((response.status_code, response.content), (200, b""))

    @override_settings(ANNOUNCEMENT_CONTENT_HTML_FILE=None)
    def test_unset_setting_returns_empty_content(self):
        response = self._get()  # used to return None (500)
        self.assertEqual((response.status_code, response.content), (200, b""))


@package_test_settings()
class GuestLoginButtonTests(TestCase):
    FORM = 'id="guest-login-form"'

    def setUp(self):
        self.ACTION = f'action="{reverse("guest_login")}"'
        # AutoGuestLoginMiddleware (if enabled) would log the guest in instead of showing the form
        self.client.cookies["skip_auto_guest"] = "1"

    def _login_page(self, **params):
        page = self.client.get(reverse("admin:login"), params)
        self.assertEqual(page.status_code, 200)
        return page

    def _guest_form(self, page):
        html = page.content.decode()
        start = html.index(self.FORM)
        return html[start:html.index("</form>", start)]

    def test_shown_as_styled_button_with_guest_user(self):
        User.objects.create(username="guest", is_staff=True)
        form = self._guest_form(self._login_page(next="/admin/"))
        self.assertIn('name="next" value="/admin/"', form)
        # the raw <button> used bg-secondary-600, which is not compiled: no background at all
        self.assertIn("bg-base-100", form)
        self.assertNotIn("bg-secondary-600", form)

    def test_hidden_when_guest_cannot_log_in(self):
        # the button used to show regardless; clicking it then did nothing
        self.assertNotContains(self._login_page(), self.ACTION)
        for fields in ({"is_staff": False}, {"is_staff": True, "is_active": False}):
            User.objects.filter(username="guest").delete()
            User.objects.create(username="guest", **fields)
            self.assertNotContains(self._login_page(), self.ACTION)

    def test_guest_login_view(self):
        url = reverse("guest_login")
        response = self.client.post(url, {"next": "/admin/base/user/"}, follow=True)
        # the failure keeps ?next so a password login still lands where the user was going
        self.assertRedirects(response, f"{reverse('admin:login')}?next=/admin/base/user/")
        self.assertContains(response, "Guest login is not available.")

        guest = User.objects.create(username="guest", is_staff=True)
        response = self.client.post(url, {"next": "/admin/"})
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), guest.pk)

    def test_guest_login_view_rejects_unsafe_next(self):
        User.objects.create(username="guest", is_staff=True)
        for next_url in ("https://evil.example/", "http://testserver/admin/"):
            self.client.logout()
            response = self.client.post(reverse("guest_login"), {"next": next_url}, secure=True)
            self.assertRedirects(response, reverse("admin:index"), fetch_redirect_response=False)

    def test_guest_login_view_with_login_required_middleware(self):
        from django.conf import settings
        guest = User.objects.create(username="guest", is_staff=True)
        middleware = [*settings.MIDDLEWARE, "django.contrib.auth.middleware.LoginRequiredMiddleware"]
        with self.settings(MIDDLEWARE=middleware):
            response = self.client.post(reverse("guest_login"), {"next": "/admin/"})
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), guest.pk)

    def test_logged_in_user_can_switch_to_guest(self):
        # the login page renders for any logged-in user without admin access (and for staff after a
        # failed password POST); the button must not just bounce them back
        guest = User.objects.create(username="guest", is_staff=True)
        for user in (User.objects.create_user("plain", password="pw"), User.objects.create_user("staff", is_staff=True)):
            self.client.force_login(user)
            response = self.client.post(reverse("guest_login"), {"next": "/admin/"})
            self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
            self.assertEqual(int(self.client.session["_auth_user_id"]), guest.pk)
        self.client.force_login(User.objects.get(username="plain"))
        self.assertContains(self._login_page(), self.FORM)

    def test_session_write_error_shows_message(self):
        # database-backed sessions on a read-only database fail inside login(), before request.user is set
        from django.db import OperationalError

        User.objects.create(username="guest", is_staff=True)
        with mock.patch("whiteneuron.base.utils.login", side_effect=OperationalError("readonly")):
            with self.assertLogs("whiteneuron.base.views", level="ERROR"):
                response = self.client.post(reverse("guest_login"), {"next": "/admin/"}, follow=True)
        self.assertRedirects(response, f"{reverse('admin:login')}?next=/admin/")
        self.assertContains(response, "Guest login is not available.")

    def test_lookup_error_does_not_break_login_page(self):
        from django.db import DatabaseError

        with mock.patch("whiteneuron.base.utils.User.objects.filter", side_effect=DatabaseError):
            with self.assertLogs("whiteneuron.base.utils", level="ERROR"):
                page = self._login_page()
        self.assertNotContains(page, self.ACTION)
        self.assertContains(page, 'id="login-form"')

    def test_guest_login_with_read_only_database(self):
        # demo mode: saving last_login fails after the session is set; the guest is still logged in
        from django.contrib.auth.models import update_last_login
        from django.contrib.auth.signals import user_logged_in
        from django.db import OperationalError

        def readonly(**kwargs):
            raise OperationalError("attempt to write a readonly database")

        guest = User.objects.create(username="guest", is_staff=True)
        # Django connects update_last_login with this dispatch_uid; swap it for a failing save
        self.assertTrue(user_logged_in.disconnect(dispatch_uid="update_last_login"))
        user_logged_in.connect(readonly, dispatch_uid="update_last_login")
        try:
            with self.assertLogs("whiteneuron.base.utils", level="WARNING"):
                response = self.client.post(reverse("guest_login"), {"next": "/admin/base/user/"})
        finally:
            user_logged_in.disconnect(dispatch_uid="update_last_login")
            user_logged_in.connect(update_last_login, dispatch_uid="update_last_login")
        self.assertRedirects(response, "/admin/base/user/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), guest.pk)


    def _with_logged_in_receiver(self, receiver):
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.connect(receiver, dispatch_uid="test_guest_receiver")
        self.addCleanup(user_logged_in.disconnect, dispatch_uid="test_guest_receiver")

    def test_other_database_errors_are_not_swallowed(self):
        # only the read-only last_login failure is tolerated; e.g. an IntegrityError from a
        # user_logged_in receiver used to be logged as "read-only database?" and the login kept
        from django.db import IntegrityError

        def broken(**kwargs):
            raise IntegrityError("duplicate key")

        User.objects.create(username="guest", is_staff=True)
        self._with_logged_in_receiver(broken)
        with self.assertLogs("whiteneuron.base.views", level="ERROR"):
            response = self.client.post(reverse("guest_login"), {"next": "/admin/"}, follow=True)
        self.assertRedirects(response, f"{reverse('admin:login')}?next=/admin/")
        self.assertContains(response, "Guest login is not available.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_failed_switch_keeps_current_session(self):
        # DB-backed sessions on a read-only DB: login() flushes, then the delete fails. The user
        # must stay logged in (no 500 from SessionMiddleware saving the emptied session)
        from django.db import OperationalError
        from whiteneuron.base import utils

        User.objects.create(username="guest", is_staff=True)
        plain = User.objects.create_user("plain", password="pw")
        self.client.force_login(plain)

        def flush_then_fail(request, *args, **kwargs):
            request.session.clear()
            raise OperationalError("attempt to write a readonly database")

        with mock.patch.object(utils, "login", flush_then_fail), self.assertLogs("whiteneuron.base.views", level="ERROR"):
            response = self.client.post(reverse("guest_login"), {"next": "/admin/"})
        self.assertRedirects(response, f"{reverse('admin:login')}?next=/admin/", fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), plain.pk)


    @override_settings(SESSION_ENGINE="django.contrib.sessions.backends.db")
    def test_failed_switch_with_db_sessions_keeps_user_logged_in(self):
        # flush() deletes the old session row: the restored data must be saved under a new key
        from django.db import IntegrityError

        def broken(**kwargs):
            raise IntegrityError("duplicate key")

        User.objects.create(username="guest", is_staff=True)
        plain = User.objects.create_user("plain", password="pw")
        self.client.force_login(plain)
        self._with_logged_in_receiver(broken)
        with self.assertLogs("whiteneuron.base.views", level="ERROR"):
            self.client.post(reverse("guest_login"), {"next": "/admin/"})
        self.assertEqual(int(self.client.session["_auth_user_id"]), plain.pk)


@package_test_settings()
class AutoGuestLoginMiddlewareTests(TestCase):
    def _call(self, path):
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.sessions.backends.signed_cookies import SessionStore
        from django.http import HttpResponse
        from whiteneuron.base.middleware import AutoGuestLoginMiddleware

        request = RequestFactory().get(path)
        request.user, request.session = AnonymousUser(), SessionStore()
        return request, AutoGuestLoginMiddleware(lambda r: HttpResponse("page"))(request)

    def test_next_is_a_url_not_a_route_name(self):
        # redirect() used to reverse() ?next as a URL name: NoReverseMatch on ?next=foo
        guest = User.objects.create(username="guest", is_staff=True)
        request, response = self._call("/admin/login/?next=foo")
        self.assertEqual((response.status_code, response["Location"]), (302, "foo"))
        self.assertEqual(request.user, guest)

    def test_unsafe_next_is_ignored(self):
        User.objects.create(username="guest", is_staff=True)
        request, response = self._call("/admin/login/?next=https://evil.example/")
        self.assertEqual(response.content, b"page")

    def test_failed_auto_login_does_not_loop(self):
        # request.user stayed the guest after a failed login: the admin login view redirected to
        # /admin/, which sent the anonymous user back to the login page, forever
        from django.contrib.auth.signals import user_logged_in
        from django.db import IntegrityError

        def broken(**kwargs):
            raise IntegrityError("duplicate key")

        User.objects.create(username="guest", is_staff=True)
        user_logged_in.connect(broken, dispatch_uid="test_auto_guest_receiver")
        self.addCleanup(user_logged_in.disconnect, dispatch_uid="test_auto_guest_receiver")
        with self.assertLogs("whiteneuron.base.middleware", level="ERROR"):
            request, response = self._call("/admin/login/?next=/admin/")
        self.assertEqual(response.content, b"page")
        self.assertFalse(request.user.is_authenticated)

        # end to end, with the middleware where settings put it: the login page renders
        from django.conf import settings

        middleware = [m for m in settings.MIDDLEWARE if not m.endswith("AutoGuestLoginMiddleware")]
        middleware.insert(
            middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
            "whiteneuron.base.middleware.AutoGuestLoginMiddleware",
        )
        with self.settings(MIDDLEWARE=middleware), self.assertLogs("whiteneuron.base.middleware", level="ERROR"):
            page = self.client.get(reverse("admin:login"), {"next": "/admin/"})
        self.assertEqual(page.status_code, 200)
