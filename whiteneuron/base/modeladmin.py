from unfold.admin import ModelAdmin as UnfoldAdmin

from django.http import HttpRequest, HttpResponseRedirect
from django.http.response import HttpResponseRedirectBase
from django.db.models.query import QuerySet
from urllib.parse import parse_qsl, urlencode, urlparse
from django.utils.safestring import mark_safe
from django.contrib.admin.views.main import ChangeList
from collections import OrderedDict
from typing import Any, Sequence

import ast
from django.urls import reverse, reverse_lazy

from unfold.contrib.forms.widgets import WysiwygWidget as UnfoldWysiwygWidget
from whiteneuron.base.widgets import WysiwygWidget, CKEditor5Widget, MarkdownEditorWidget
from unfold.widgets import UnfoldAdminSplitDateTimeWidget
from django.db import models

from .utils import timeit
from .models import User
from whiteneuron.notification.models import Notification
from .filters import FieldSelectionFilter

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
    compressed_fields = True

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

    def soft_delete(self, cl, request, queryset):
        for obj in queryset:
            title= _('%(name)s "%(obj)s" has been soft-deleted by user "%(user)s"') % {'name': obj._meta.verbose_name, 'obj': obj, 'user': request.user}
            content_html= _('%(name)s "%(obj)s" has been soft-deleted by user "%(user)s"') % {'name': obj._meta.verbose_name, 'obj': obj, 'user': request.user}
            obj.delete()
            # send notification to superuser when delete successfully
            for user in User.objects.filter(is_superuser= True):
                Notification.objects.create(user= user, title= title,
                                            action_by= request.user,
                                            flag= 'danger',
                                            action= 'delete',
                                            content= content_html)
    soft_delete.short_description = _('Delete selected records')

    def hard_delete(self, cl, request, queryset):
        for obj in queryset:
            title= _('%(name)s "%(obj)s" has been hard-deleted by user "%(user)s"') % {'name': obj._meta.verbose_name, 'obj': obj, 'user': request.user}
            content_html= _('%(name)s "%(obj)s" has been hard-deleted by user "%(user)s"') % {'name': obj._meta.verbose_name, 'obj': obj, 'user': request.user}
            if hasattr(obj, 'hard_delete'):
                obj.hard_delete()
            else:
                obj.delete()
            # send notification to superuser when delete successfully
            for user in User.objects.filter(is_superuser= True):
                Notification.objects.create(user= user, title= title,
                                            action_by= request.user,
                                            flag= 'danger',
                                            action= 'delete',
                                            content= content_html)
    hard_delete.short_description = _('Hard delete selected records')

    def restore(self, cl, request, queryset):
        for obj in queryset:
            title= _('%(name)s "%(obj)s" has been restored by user "%(user)s"') % {'name': obj._meta.verbose_name, 'obj': obj, 'user': request.user}
            content_html= _('%(name)s "%(obj)s" has been restored by user "%(user)s"') % {'name': obj._meta.verbose_name, 'obj': obj, 'user': request.user}
            obj.restore(request)
            # send notification to superuser when delete successfully
            for user in User.objects.filter(is_superuser= True):
                Notification.objects.create(user= user, title= title,
                                            action_by= request.user,
                                            flag= 'info',
                                            action= 'restore',
                                            content= content_html)
    restore.short_description = _('Restore selected records')

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        if request.user.is_superuser and request.user.show_softdelete:
            if hasattr(self.model, 'objects_all'):
                return self.model.objects_all.all()
        return self.model.objects.all()

    def delete_model(self, request, obj):
        title= _('%(name)s "%(obj)s" has been soft-deleted by user "%(user)s"') % {'name': obj._meta.verbose_name, 'obj': obj, 'user': request.user}
        content_html= _('%(name)s "%(obj)s" has been soft-deleted by user "%(user)s"') % {'name': obj._meta.verbose_name, 'obj': obj, 'user': request.user}
        super().delete_model(request, obj)
        # send notification to superuser when delete successfully
        for user in User.objects.filter(is_superuser= True):
            Notification.objects.create(user= user, title= title,
                                        action_by= request.user,
                                        flag= 'danger',
                                        action= 'delete',
                                        content= content_html)



    show_meta_filter = True
    def get_list_filter(self, request: HttpRequest) -> Sequence[str]:
        if self.enable_field_selection_filter:
            if FieldSelectionFilter not in self.list_filter:
                self.list_filter =  tuple(self.list_filter) + (FieldSelectionFilter,)
        
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
        readonly_fields = super().get_readonly_fields(request, obj)
        # check nếu model có trường sau thì mới thêm vào readonly_fields
        for field in ['id', 'created_at', 'created_by', 'updated_at', 'updated_by']:
            if field in [f.name for f in self.model._meta.fields]:
                readonly_fields += (field,)
        return readonly_fields
    

    
    def get_list_display_links(self, request, list_display):
        if not self.has_display_links:
            return None
        fields= super().get_list_display_links(request, list_display)
        if not self.action_buttons:
            try:
                fields.remove('buttons')
            except:
                pass
            return fields
        
        if self.action_buttons_top:
            try:
                fields.remove('buttons')
            except:
                pass
        if len(fields) == 0:
            if list_display[0] != 'buttons':
                fields = [list_display[0]]
            else:
                fields = [list_display[1]]
        grid_view= int(request.POST.get('grid_view', self.grid_view))
        if grid_view:
            fields = ['grid_item_header']
        return fields
    
    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        list_display = super().get_list_display(request)
        filtered_list_display = request.GET.getlist(FieldSelectionFilter.parameter_name, None)
        # print(filtered_list_display)
        if "All" in filtered_list_display:
            list_display = [field for field, _ in FieldSelectionFilter.lookups(None, request, self)]
        elif 'default' in filtered_list_display or not filtered_list_display:
            # default list_display
            list_display = list(list_display)
        else:
            list_display = filtered_list_display
        try:
            list_display.remove('default')
        except:
            pass
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

        grid_view= int(request.POST.get('grid_view', self.grid_view))
        if grid_view:
            list_display = list(set(['grid_item_header'] + list(list_display)))
            if self.grid_exclude_fields_list_display:
                for field in self.grid_exclude_fields_list_display:
                    try:
                        list_display.remove(field)
                    except:
                        pass
        return list_display
    
    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        for object in queryset:
            object.delete()
        return None
    
    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> type[ChangeList]:
        self.request = request #trick to use request in buttons
        return super().get_changelist(request, **kwargs)
    
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
            fieldsets.append((_('Meta'), {'fields': meta_fields, 'classes': ["collapse"]}))
        return fieldsets
    
    def buttons(self, obj):
        svg_url_edit = '/static/base/images/edit.svg'
        svg_url_delete = '/static/base/images/delete.svg'
        svg_url_view = '/static/base/images/icon-viewlink.svg'

        button_edit = ''
        button_delete = ''
        button_view = ''
        
        width = 18
        height = 18

        path= f'admin:{obj._meta.app_label}_{obj._meta.model_name}'
        path_change= reverse_lazy(path + '_change', args=[obj.pk])
        path_delete= reverse_lazy(path + '_delete', args=[obj.pk])
        c= 0
        if self.has_change_permission(self.request, obj):
            button_edit = f'<a class="btn-edit col-span-1" href="{path_change}"> <img src="{svg_url_edit}" alt="{_("Edit")}" style="width: {width}px; height: {height}px;"></a>'
            c+= 1
        else:
            button_view = f'<a class="btn-view col-span-1" href="{path_change}"> <img src="{svg_url_view}" alt="{_("View")}" style="width: {width}px; height: {height}px;"></a>'
            c+= 1

        if self.has_delete_permission(self.request, obj):
            c+= 1
            button_delete = f'<a class="btn-delete btn-danger col-span-1" href="{path_delete}"> <img src="{svg_url_delete}" alt="{_("Delete")}" style="width: {width}px; height: {height}px;"></a>'

        return mark_safe(f'''
                         <div id="action_buttoms_{obj.pk}" class="action_buttoms grid gap-1 grid-cols-{c}" style="width: {33*c}px;">{button_view} {button_edit} {button_delete} </div> 
                         ''')

    buttons.short_description = ''

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        # Lấy đối tượng chính vừa được lưu
        parent_object = form.instance

        # Duyệt qua tất cả các formset của các đối tượng con
        for formset in formsets:
            # Duyệt qua các đối tượng con trong formset
            for inline_form in formset.forms:
                if inline_form.has_changed():
                    child_object = inline_form.instance
                    # Thực hiện hành động tùy chỉnh, chẳng hạn như gọi hàm save
                    child_object.save()


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
        if not self.using_grid_view:
            grid_view= False
        else:
            grid_view= int(request.POST.get('grid_view', self.grid_view))
        
        self.grid_view = grid_view
        if grid_view:
            extra_context = extra_context or {}
            extra_context['grid_view'] = grid_view

            # self.list_display_links= list(set(list(self.list_display_links) + ['grid_item_header']))
            # self.list_display= self.get_list_display(request)


        # Xác định số lượng hiển thị từ request
        per_page = self.list_per_page
        if 'per_page' in request.POST:
            try:
                per_page = int(request.POST.get('per_page'))
                if per_page in self.page_sizes:
                    self.list_per_page = per_page
            except ValueError:
                pass  # Giữ nguyên giá trị mặc định nếu không hợp lệ

        # Truyền danh sách số lượng hiển thị vào context
        if extra_context is None:
            extra_context = {}
        extra_context['using_page_size'] = self.using_page_size
        extra_context['page_sizes'] = self.page_sizes
        extra_context['grid_cols'] = self.grid_cols

        if self.default_toggle_sidebar is not None:
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
                ref_user = request.user if request.user.is_superuser else User.objects.filter(is_superuser=True).first()
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
                            notif.parsed_changed_data = ast.literal_eval(notif.changed_data) if notif.changed_data else []
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
        return mark_safe(f'<div class="grid-item-header">{obj}</div>')
    grid_item_header.short_description = 'Header'

    # action make a copy of the current object
    @admin.action(description=_('Duplicate selected objects'), permissions=['add'])
    def duplicate_objects(self, request, queryset):
        for obj in queryset:
            obj.pk = None  # This will create a new object when saved
            # obj.name = f"{obj.name} (Copy)"
            try:
                obj.save()
            except Exception as e:
                self.message_user(request, _(f'Error duplicating object: {e}'), level='error')
                continue

        message = _(f'{queryset.count()} object(s) duplicated successfully.')
        self.message_user(request, message)