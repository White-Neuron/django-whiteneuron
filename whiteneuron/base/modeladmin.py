from unfold.admin import ModelAdmin as UnfoldAdmin

from django.http import HttpRequest, HttpResponseRedirect
from django.http.response import HttpResponseRedirectBase
from django.db.models.query import QuerySet
from urllib.parse import parse_qsl, urlencode, urlparse
from django.contrib.admin.views.main import ChangeList
from collections import OrderedDict
from typing import Any, Sequence

import ast
import contextvars
import json
from django.urls import reverse

from unfold.contrib.forms.widgets import WysiwygWidget as UnfoldWysiwygWidget
from whiteneuron.base.widgets import WysiwygWidget, CKEditor5Widget, MarkdownEditorWidget
from unfold.widgets import UnfoldAdminSplitDateTimeWidget
from django.db import models, transaction

from .utils import timeit
from .models import User, BaseModel
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.templatetags.static import static
from whiteneuron.notification.models import Notification
from .filters import FieldSelectionFilter

_current_request = contextvars.ContextVar('wn_admin_request', default=None)
_changelist_classes = {}


def request_changelist(base):
    """ChangeList subclass applying the per-user page size / grid view (built once per base)."""
    cls = _changelist_classes.get(base)
    if cls is None:
        class RequestChangeList(base):
            def get_results(self, request):
                self.list_per_page = self.model_admin._per_page_for(request)
                self.wn_grid_view = self.model_admin._grid_view_for(request)
                return super().get_results(request)

        cls = _changelist_classes[base] = RequestChangeList
    return cls

from django.urls import path
from django.shortcuts import render

from django.utils.translation import gettext_lazy as _
from django.utils.text import format_lazy

from django.contrib import admin

from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    AutocompleteSelectMultipleFilter,
    MultipleDropdownFilter,
    DropdownFilter,
    MultipleChoicesDropdownFilter,
    ChoicesCheckboxFilter,
    ChoicesRadioFilter,
    BooleanRadioFilter,
    RangeDateFilter, RangeDateTimeFilter
)

from unfold.paginator import InfinitePaginator

def get_verbose_name_field(model, field):
    try:
        parts = field.split('__')
        current_model = model
        labels = []
        for part in parts:
            f = current_model._meta.get_field(part)
            labels.append(str(f.verbose_name))
            if hasattr(f, 'related_model') and f.related_model:
                current_model = f.related_model
        return ' / '.join(labels)
    except Exception:
        return field

class ModelAdmin(UnfoldAdmin):

    show_history = True  # Show history panel in change form, data from Notification model
    change_form_template = 'admin/wn_change_form.html'

    # MAX OBJECTS PER PAGE
    list_per_page = 50

    list_fullwidth = True
    list_horizontal_scrollbar_top = True
    action_buttons_top = False
    action_buttons = True

    warn_unsaved_form = True

    use_infinite_paginator = True

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        models.DateTimeField: {
            "widget": UnfoldAdminSplitDateTimeWidget,
        },
    }

    text_field_widget= 'wysiwyg' # options: 'wysiwyg', 'ckeditor', 'mdeditor', ''

    enable_field_selection_filter = True
    list_filter_submit = True
    list_filter_sheet = True

    has_display_links = True

    default_toggle_sidebar= True

    meta_class_in_fieldsets = 'collapse' # options: 'collapse', 't' (for always show)

    @property
    def search_help_text(self):
        fields = ', '.join([str(get_verbose_name_field(self.model, f)) for f in self.search_fields])
        return format_lazy(_('Search by {fields}'), fields=fields)

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        if self.text_field_widget == 'ckeditor':
            self.formfield_overrides[models.TextField]["widget"]= CKEditor5Widget(
                    attrs={"class": "django_ckeditor_5"})
        elif self.text_field_widget == 'mdeditor':
            self.formfield_overrides[models.TextField]["widget"]= MarkdownEditorWidget()
        elif self.text_field_widget == '':
            self.formfield_overrides[models.TextField] = {}

    def has_module_permission(self, request: HttpRequest) -> bool:
        return super().has_module_permission(request)

    def _fix_preserved_filters(self, request, response):
        """Fix Django bug: add_preserved_filters() uses dict(parse_qsl()) which drops duplicate
        filter params. E.g. ?chapter__id__exact=29&chapter__id__exact=31 → only =31 kept after save.

        Root cause: get_preserved_filters() wraps filters in _changelist_filters=..., then
        add_preserved_filters() decodes via dict(parse_qsl(...)) losing repeated keys.

        Fix: read _changelist_filters directly from request.GET (inner filter string),
        detect duplicates, then rebuild the redirect URL with parse_qsl() which keeps all values.
        """
        if not isinstance(response, HttpResponseRedirectBase):
            return response
        # Inner filter string e.g. 'chapter__id__exact=29&chapter__id__exact=31'
        inner = request.GET.get('_changelist_filters', '')
        if not inner:
            return response
        pairs = parse_qsl(inner, keep_blank_values=True)
        keys = [k for k, v in pairs]
        if len(keys) == len(set(keys)):
            return response  # No duplicate keys — Django handled it correctly
        # Rebuild URL: strip the incorrectly-added filter params, then append all pairs correctly
        parsed = urlparse(response.url)
        filter_keys = {k for k, v in pairs}
        base_params = [(k, v) for k, v in parse_qsl(parsed.query) if k not in filter_keys]
        return HttpResponseRedirect(
            parsed._replace(query=urlencode(base_params + pairs)).geturl()
        )

    def response_post_save_change(self, request, obj):
        return self._fix_preserved_filters(request, super().response_post_save_change(request, obj))

    def response_post_save_add(self, request, obj):
        return self._fix_preserved_filters(request, super().response_post_save_add(request, obj))

    # Soft delete
    def get_actions(self, request: HttpRequest) -> OrderedDict[Any, Any]:
        actions = super().get_actions(request)
        if request.user.is_superuser:
            
            if 'delete_selected' in actions:
                actions['delete_selected'] = (self.soft_delete, 'delete_selected', self.soft_delete.short_description)
            
            # hard delete and restore actions only for superuser
            actions['hard_delete'] = (self.hard_delete, 'hard_delete', self.hard_delete.short_description)
            actions['restore'] = (self.restore, 'restore', self.restore.short_description)

            # Add the duplicate action to all ModelAdmins that inherit from this base class
            if 'duplicate_objects' not in actions:
                actions['duplicate_objects'] = self.get_action('duplicate_objects')
        
        return actions

    def _notify_bulk(self, request, queryset_objs, message, action, flag):
        """One notification (per superuser) summarising a bulk admin action."""
        objs = list(queryset_objs)
        if not objs:
            return
        names = ", ".join(f'"{obj}"' for obj in objs[:10]) + (" …" if len(objs) > 10 else "")
        text = message % {'name': objs[0]._meta.verbose_name, 'obj': names, 'user': request.user}
        Notification.notify_superusers(
            title=text, content=format_html('<p>{}</p>', text),
            action=action, flag=flag, action_by=request.user,
        )

    @staticmethod
    def _soft_delete_obj(request, obj, deleted):
        """Soft-delete / restore one object and record it in that object's history."""
        if isinstance(obj, BaseModel) and type(obj).delete is BaseModel.delete:
            obj.is_deleted = deleted
            obj.deleted_at = timezone.now() if deleted else None
            obj.save(notification=False)  # replaced by the specific notification below
            verb = _('has been soft-deleted by user') if deleted else _('has been restored by user')
            title = f'{obj._meta.verbose_name} "{obj}" ({obj.pk}) {verb} "{request.user}"'
            Notification.notify_superusers(
                title=title, content=format_html('<p>{}</p>', title),
                action='delete' if deleted else 'restore', flag='danger' if deleted else 'info',
                obj_link=obj.path() or None, action_by=request.user,
                changed_data=[{'field_name': 'is_deleted', 'old_value': not deleted, 'new_value': deleted}],
            )
            return True
        if deleted:
            obj.delete()
        else:
            obj.restore()
        return False

    def soft_delete(self, cl, request, queryset):
        objs = list(queryset)
        recorded = [obj for obj in objs if self._soft_delete_obj(request, obj, True)]
        others = [obj for obj in objs if obj not in recorded]
        self._notify_bulk(request, others, _('%(name)s %(obj)s has been soft-deleted by user "%(user)s"'), 'delete', 'danger')
    soft_delete.short_description = _('Delete selected records')

    def hard_delete(self, cl, request, queryset):
        objs = list(queryset)
        for obj in objs:
            if hasattr(obj, 'hard_delete'):
                obj.hard_delete()
            else:
                obj.delete()
        self._notify_bulk(request, objs, _('%(name)s %(obj)s has been hard-deleted by user "%(user)s"'), 'delete', 'danger')
    hard_delete.short_description = _('Hard delete selected records')

    def restore(self, cl, request, queryset):
        objs = list(queryset)
        recorded = [obj for obj in objs if self._soft_delete_obj(request, obj, False)]
        others = [obj for obj in objs if obj not in recorded]
        self._notify_bulk(request, others, _('%(name)s %(obj)s has been restored by user "%(user)s"'), 'restore', 'info')
    restore.short_description = _('Restore selected records')

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        if request.user.is_superuser and getattr(request.user, 'show_softdelete', False):
            if hasattr(self.model, 'objects_all'):
                qs = self.model.objects_all.all()
                ordering = self.get_ordering(request)
                return qs.order_by(*ordering) if ordering else qs
        return super().get_queryset(request)

    def delete_model(self, request, obj):
        if not self._soft_delete_obj(request, obj, True):
            self._notify_bulk(request, [obj], _('%(name)s %(obj)s has been soft-deleted by user "%(user)s"'), 'delete', 'danger')

    show_meta_filter = True
    def get_list_filter(self, request: HttpRequest) -> Sequence[str]:
        if self.enable_field_selection_filter and FieldSelectionFilter not in self.list_filter:
            self.list_filter = tuple(self.list_filter) + (FieldSelectionFilter,)
        
        list_filter = super().get_list_filter(request)

        # check nếu model có trường sau thì mới thêm vào list_filter
        if self.show_meta_filter:
            fields_extra = [['created_at', RangeDateFilter],
                            ['created_by', AutocompleteSelectMultipleFilter],
                            ['updated_at', RangeDateFilter],
                            ['updated_by', AutocompleteSelectMultipleFilter]]
            if request.user.is_superuser: #is_hidden
                fields_extra += [['is_hidden', BooleanRadioFilter],
                                 ['is_deleted', BooleanRadioFilter]]
            for field in fields_extra:
                if not field in list_filter:
                    if field[0] in [f.name for f in self.model._meta.fields]:
                        list_filter += (field,)

        

        return list_filter

    def get_readonly_fields(self, request: HttpRequest, obj: Any | None = ...) -> list[str] | tuple[Any, ...]:
        declared = super().get_readonly_fields(request, obj)
        # build a new container: `+=` on the class-level list grew it on every request.
        # Keep the declared type (list or tuple) so subclasses can still `+ [...]`/`+ (...)`.
        model_fields = {f.name for f in self.model._meta.fields}
        extra = [f for f in ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')
                 if f in model_fields and f not in declared]
        container = list if isinstance(declared, list) else tuple
        return container([*declared, *extra])
    

    
    def get_list_display_links(self, request, list_display):
        if not self.has_display_links:
            return None
        fields= super().get_list_display_links(request, list_display)
        if fields is None:  # list_display_links = None: links disabled on purpose
            return None
        fields = list(fields)
        if not self.action_buttons:
            try:
                fields.remove('buttons')
            except:
                pass
            return fields
        
        if self.action_buttons_top:
            try:
                fields.remove('buttons')
            except Exception:
                pass
        if len(fields) == 0:
            if list_display[0] != 'buttons':
                fields = [list_display[0]]
            else:
                fields = [list_display[1]]
        if self._grid_view_for(request):
            fields = ['grid_item_header']
        return fields
    
    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        list_display = super().get_list_display(request)
        filtered_list_display = request.GET.getlist(FieldSelectionFilter.parameter_name, None)
        # print(filtered_list_display)
        if "All" in filtered_list_display:
            list_display = [field for field, _ in FieldSelectionFilter.lookups(None, request, self) if field != 'default']
        elif 'default' in filtered_list_display or not filtered_list_display:
            # default list_display
            list_display = list(list_display)
        else:
            # Only accept known columns: Django calls any non-field name on each row,
            # so an arbitrary ?display_fields=delete would run obj.delete() on a GET.
            allowed = {field for field, _ in FieldSelectionFilter.lookups(None, request, self)} - {'default'}
            allowed.update(f for f in list_display if isinstance(f, str))
            list_display = [f for f in filtered_list_display if f in allowed and f != 'buttons']
            if not list_display:
                list_display = list(super().get_list_display(request))
        # check nếu model có trường sau thì mới thêm vào list_display
        # fields_extra = ['updated_at', 'updated_by']
        fields_extra = []
        if request.user.is_superuser and request.user.show_softdelete:
            fields_extra += ['is_deleted']
        for field in fields_extra:
            if field in [f.name for f in self.model._meta.fields]:
                if not field in list_display:
                    list_display += (field,)
        if 'buttons' in list_display:
            # xóa buttons cũ
            list_display = list(list_display)
            list_display.remove('buttons')

        if self.action_buttons:
            if self.action_buttons_top:
                list_display= ['buttons'] + list(list_display)
            else:
                list_display += ['buttons',]

        if self._grid_view_for(request):
            # keep column order stable (set() shuffled it on every request)
            list_display = ['grid_item_header'] + [f for f in list_display if f != 'grid_item_header']
            if self.grid_exclude_fields_list_display:
                for field in self.grid_exclude_fields_list_display:
                    try:
                        list_display.remove(field)
                    except Exception:
                        pass
        return list_display
    
    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        objs = list(queryset)
        recorded = [obj for obj in objs if self._soft_delete_obj(request, obj, True)]
        others = [obj for obj in objs if obj not in recorded]
        self._notify_bulk(request, others, _('%(name)s %(obj)s has been soft-deleted by user "%(user)s"'), 'delete', 'danger')

    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> type[ChangeList]:
        # ModelAdmin instances are shared by all threads/users: keep per-request values
        # on the request / ChangeList, never on `self`.
        _current_request.set(request)  # used by buttons(), which Django calls without request
        return request_changelist(super().get_changelist(request, **kwargs))

    @property
    def request(self):
        """Backward compatibility: ``self.request`` used to be set (unsafely) on the
        shared admin instance; it now returns the request of the current context."""
        return _current_request.get()

    @request.setter
    def request(self, value):
        _current_request.set(value)

    def _view_state(self, request, name, default, parse):
        """Per-user list setting (grid view, page size): from POST, else remembered in the session."""
        cache = request.__dict__.setdefault('_wn_view_state', {})
        key = f"wn:{self.model._meta.label_lower}:{name}"
        if key in cache:
            return cache[key]
        value = parse(request.POST.get(name)) if request.method == 'POST' else None
        if value is None:
            value = request.session.get(key, default)
        elif request.session.get(key) != value:
            request.session[key] = value
        cache[key] = value
        return value

    def _grid_view_for(self, request):
        if not self.using_grid_view:
            return False
        return self._view_state(request, 'grid_view', bool(self.grid_view),
                                lambda raw: {'0': False, '1': True}.get(raw))

    def _per_page_for(self, request):
        def parse(raw):
            try:
                value = int(raw)
            except (TypeError, ValueError):
                return None
            return value if value in self.page_sizes else None
        value = self._view_state(request, 'per_page', self.list_per_page, parse)
        return value if value in self.page_sizes or value == self.list_per_page else self.list_per_page
    
    def get_fieldsets(self, request: HttpRequest, obj: Any | None = ...) -> list[tuple[str, dict]]:
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets = list(fieldsets)
        # check nếu model có trường sau thì mới thêm vào fieldsets
        meta_fields = []
        fields= [f for sf in fieldsets for f in sf[1]['fields']] # flatten fieldsets 
        fields_extra = ['created_at', 'created_by', 'updated_at', 'updated_by']
        if request.user.is_superuser: #is_hidden
            fields_extra= ['is_hidden', 'is_deleted'] + fields_extra
        for field in fields_extra:
            if field not in fields and field in [f.name for f in self.model._meta.fields]: # check if field not in fieldsets and in model
                meta_fields.append(field)
        if meta_fields:
            if 'created_at' in meta_fields and 'created_by' in meta_fields:
                meta_fields.remove('created_at')
                meta_fields.remove('created_by')
                meta_fields.append(('created_at', 'created_by'))
            if 'updated_at' in meta_fields and 'updated_by' in meta_fields:
                meta_fields.remove('updated_at')
                meta_fields.remove('updated_by')
                meta_fields.append(('updated_at', 'updated_by'))
            fieldsets.append((_('Meta'), {'fields': meta_fields, 'classes': [self.meta_class_in_fieldsets]}))
        return fieldsets
    
    def buttons(self, obj):
        request = _current_request.get()
        url_name = f'admin:{obj._meta.app_label}_{obj._meta.model_name}'
        size = 'width: 18px; height: 18px;'
        links = []
        if request is not None and self.has_change_permission(request, obj):
            links.append(('btn-edit', reverse(url_name + '_change', args=[obj.pk]), 'base/images/edit.svg', _('Edit')))
        else:
            links.append(('btn-view', reverse(url_name + '_change', args=[obj.pk]), 'base/images/icon-viewlink.svg', _('View')))
        if request is not None and self.has_delete_permission(request, obj):
            links.append(('btn-delete btn-danger', reverse(url_name + '_delete', args=[obj.pk]), 'base/images/delete.svg', _('Delete')))
        # format_html escapes the pk too (CharField primary keys are user data)
        return format_html(
            '<div id="action_buttons_{}" class="action_buttons grid gap-1 grid-cols-{}" style="width: {}px;">{}</div>',
            obj.pk, len(links), 33 * len(links),
            format_html_join(' ', '<a class="{} col-span-1" href="{}" title="{}"><img src="{}" alt="{}" style="{}"></a>',
                             ((cls, url, label, static(icon), label, size) for cls, url, icon, label in links)),
        )

    buttons.short_description = ''

    # GRID VIEW
    using_grid_view = True # True if you want to use grid view, False if you want to use list view
    grid_view = False # Default grid view is False, set to True to use grid view
    grid_exclude_fields_list_display = []
    grid_cols= 4
    page_sizes = [5, 10, 20, 50, 100, 200]
    using_page_size = True # True if you want to use page size, False if you want to use default list_per_page

    def changelist_view(self, request, extra_context = None):
        extra_context = extra_context or {}
        extra_context["sidebar_default"] = self.default_toggle_sidebar
        extra_context["sidebar_model_key"] = (
            f"{self.model._meta.app_label}_{self.model._meta.model_name}"
        )
        extra_context['using_grid_view'] = self.using_grid_view
        grid_view = self._grid_view_for(request)
        if grid_view:
            extra_context['grid_view'] = grid_view

        # Truyền danh sách số lượng hiển thị vào context
        if extra_context is None:
            extra_context = {}
        extra_context['using_page_size'] = self.using_page_size
        extra_context['page_sizes'] = self.page_sizes
        extra_context['grid_cols'] = self.grid_cols

        if self.default_toggle_sidebar is not None:
            if request.session.get("toggle_sidebar") != self.default_toggle_sidebar:  # avoid a session write (Set-Cookie) on every page
                request.session["toggle_sidebar"] = self.default_toggle_sidebar
        res = super().changelist_view(request, extra_context)
        return res
    
    def has_view_history_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self.has_change_permission(request, obj)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["sidebar_default"] = self.default_toggle_sidebar
        extra_context["sidebar_model_key"] = (
            f"{self.model._meta.app_label}_{self.model._meta.model_name}"
        )
        if self.default_toggle_sidebar is not None:
            if request.session.get("toggle_sidebar") != self.default_toggle_sidebar:  # avoid a session write (Set-Cookie) on every page
                request.session["toggle_sidebar"] = self.default_toggle_sidebar

        can_view_history = self.show_history and self.has_view_history_permission(request)
        extra_context['show_history'] = can_view_history
        if can_view_history and object_id:
            try:
                obj_link = reverse(
                    'admin:%s_%s_change' % (self.model._meta.app_label, self.model._meta.model_name),
                    args=[object_id],
                )
                # Query notifications for one superuser — each event is recorded once per superuser,
                # so filtering by one superuser gives exactly one entry per event.
                # Prefer request.user if superuser to avoid extra DB query.
                ref_user = request.user if request.user.is_superuser else User.objects.filter(is_superuser=True, is_active=True).order_by("pk").first()
                notifications = []
                if ref_user:
                    qs = (
                        Notification.objects
                        .filter(obj_link=obj_link, user=ref_user)
                        .select_related('action_by')
                        .order_by('-created_at')[:50]
                    )
                    for notif in qs:
                        try:
                            notif.parsed_changed_data = json.loads(notif.changed_data) if notif.changed_data else []
                        except ValueError:
                            try:  # rows saved before changed_data was JSON
                                notif.parsed_changed_data = ast.literal_eval(notif.changed_data)
                            except Exception:
                                notif.parsed_changed_data = []
                        except Exception:
                            notif.parsed_changed_data = []
                        notifications.append(notif)
                extra_context['history_notifications'] = notifications
            except Exception:
                extra_context['history_notifications'] = []

        return super().changeform_view(request, object_id, form_url, extra_context)
    
    # GridItemHeader
    def grid_item_header(self, obj):
        # TODO: implement this method to return the header of the grid item
        return format_html('<div class="grid-item-header">{}</div>', obj)
    grid_item_header.short_description = 'Header'

    # action make a copy of the current object
    @admin.action(description=_('Duplicate selected objects'), permissions=['add'])
    def duplicate_objects(self, request, queryset):
        from uuid import uuid4
        duplicated = 0
        for obj in list(queryset):
            # copy many-to-many values too (they are lost when only the row is copied)
            m2m = {f.name: list(getattr(obj, f.name).all()) for f in obj._meta.many_to_many
                   if f.remote_field.through._meta.auto_created}
            obj.pk = None  # This will create a new object when saved
            obj._state.adding = True
            # Regenerate UUID to avoid unique constraint violation
            if any(f.name == 'uuid' and isinstance(f, models.UUIDField) for f in obj._meta.fields):
                obj.uuid = uuid4()
            if hasattr(obj, 'name'):
                obj.name = f"{obj.name} (Copy)"
            elif hasattr(obj, 'title'):
                obj.title = f"{obj.title} (Copy)"
            try:
                with transaction.atomic():
                    obj.save()
                    for name, values in m2m.items():
                        getattr(obj, name).set(values)
            except Exception as e:
                self.message_user(request, _('Error duplicating object: %(error)s') % {'error': e}, level='error')
                continue
            duplicated += 1

        self.message_user(request, _('%(count)d object(s) duplicated successfully.') % {'count': duplicated})