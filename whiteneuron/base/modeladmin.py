from unfold.admin import ModelAdmin as UnfoldAdmin

from django.http import HttpRequest
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.contrib.admin.views.main import ChangeList
from collections import OrderedDict
from typing import Any, Sequence

from django.urls import reverse_lazy

from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.widgets import UnfoldAdminSplitDateTimeWidget
from django.db import models

from .utils import timeit
from .models import User
from whiteneuron.notification.models import Notification
from .filters import FieldSelectionFilter

from django.urls import path
from django.shortcuts import render

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

def get_verbose_name_field(model, field):
    try:
        return str(model._meta.get_field(field).verbose_name)
    except:
        return field

class ModelAdmin(UnfoldAdmin):

    # MAX OBJECTS PER PAGE
    list_per_page = 50

    list_fullwidth = True
    list_horizontal_scrollbar_top = True
    action_buttons_top = False
    action_buttons = True

    warn_unsaved_form = True
    compressed_fields = True

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        models.DateTimeField: {
            "widget": UnfoldAdminSplitDateTimeWidget,
        },
    }

    enable_field_selection_filter = True
    list_filter_submit = True
    list_filter_sheet = True

    has_display_links = True

    default_toggle_sidebar= True

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.search_help_text= f'Search by {", ".join([get_verbose_name_field(model, f) for f in self.search_fields])}'

    def has_module_permission(self, request: HttpRequest) -> bool:
        return super().has_module_permission(request)

    # Soft delete
    def get_actions(self, request: HttpRequest) -> OrderedDict[Any, Any]:
        actions = super().get_actions(request)
        actions['delete_selected'] = (self.soft_delete, 'delete_selected', self.soft_delete.short_description)
        if request.user.is_superuser:
            # hard delete and restore
            actions['hard_delete'] = (self.hard_delete, 'hard_delete', self.hard_delete.short_description)
            actions['restore'] = (self.restore, 'restore', self.restore.short_description)
        return actions

    def soft_delete(self, cl, request, queryset):
        for obj in queryset:
            title= f"{obj._meta.verbose_name} \"{obj}\" has been soft-deleted by user \"{request.user}\""
            content_html= f"{obj._meta.verbose_name} \"{obj}\" has been soft-deleted by user \"{request.user}\""
            obj.delete()
            # send notification to superuser when delete successfully
            for user in User.objects.filter(is_superuser= True):
                Notification.objects.create(user= user, title= title,
                                            flag= 'danger',
                                            action= 'delete',
                                            content= content_html)
    soft_delete.short_description = 'Delete selected records'

    def hard_delete(self, cl, request, queryset):
        for obj in queryset:
            title= f"{obj._meta.verbose_name} \"{obj}\" has been hard-deleted by user \"{request.user}\""
            content_html= f"{obj._meta.verbose_name} \"{obj}\" has been hard-deleted by user \"{request.user}\""
            if hasattr(obj, 'hard_delete'):
                obj.hard_delete()
            else:
                obj.delete()
            # send notification to superuser when delete successfully
            for user in User.objects.filter(is_superuser= True):
                Notification.objects.create(user= user, title= title,
                                            flag= 'danger',
                                            action= 'delete',
                                            content= content_html)
    hard_delete.short_description = 'Hard delete selected records'

    def restore(self, cl, request, queryset):
        for obj in queryset:
            title= f"{obj._meta.verbose_name} \"{obj}\" has been restored by user \"{request.user}\""
            content_html= f"{obj._meta.verbose_name} \"{obj}\" has been restored by user \"{request.user}\""
            obj.restore(request)
            # send notification to superuser when delete successfully
            for user in User.objects.filter(is_superuser= True):
                Notification.objects.create(user= user, title= title,
                                            flag= 'info',
                                            action= 'restore',
                                            content= content_html)
    restore.short_description = 'Restore selected records'

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        if request.user.is_superuser:
            if hasattr(self.model, 'objects_all'):
                return self.model.objects_all.all()
        return self.model.objects.all()

    def delete_model(self, request, obj):
        title= f"{obj._meta.verbose_name} \"{obj}\" has been soft-deleted by user \"{request.user}\""
        content_html= f"{obj._meta.verbose_name} \"{obj}\" has been soft-deleted by user \"{request.user}\""
        super().delete_model(request, obj)
        # send notification to superuser when delete successfully
        for user in User.objects.filter(is_superuser= True):
            Notification.objects.create(user= user, title= title,
                                        flag= 'danger',
                                        action= 'delete',
                                        content= content_html)
    
    # def save_model(self, request, obj, form, change):
        # save created_by and updated_by when create or update
        # title= ''
        # content_html= ''
        # action= ''
        # user= request.user
        # obj_link= f"/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.id}/change/"
        # if not change: # check if the object is being created
        #     obj.updated_by= user
        #     obj.created_by= user
        #     action= 'create'
        #     title= f"New {obj._meta.verbose_name} \"{obj}\" has been created by user \"{obj.created_by}\""
        #     content_html= f"New {obj._meta.verbose_name} <a href='{obj_link}'>{obj}</a> has been created by user \"{obj.created_by}\""

        # # check if the object is being updated with a new version
        # else:
        #     fields_changed= []
        #     isUpdate= False
        #     if hasattr(obj.__class__, 'objects_all'):
        #         old= obj.__class__.objects_all.get(pk= obj.pk)
        #     else:
        #         old= obj.__class__.objects.get(pk= obj.pk)

        #     for attr in obj.__dict__:
        #         if attr in ['_state', 'created_at', 'created_by', 'updated_at', 'updated_by']:
        #             continue
        #         # kiểm tra attr có phải là field không
        #         if not hasattr(obj.__class__, attr):
        #             continue
        #         # print(attr)
        #         try:
        #             if getattr(obj, attr) != getattr(old, attr):
        #                 isUpdate= True
        #                 fields_changed.append((attr, getattr(old, attr), getattr(obj, attr)))
        #         except Exception as e:
        #             print(e)
        #             pass
        #     if isUpdate:
        #         obj.updated_by= user
        #         action= 'update'
        #         title= f"{obj._meta.verbose_name} \"{obj}\" has been updated by user \"{obj.updated_by}\""
        #         content_html= f"{obj._meta.verbose_name} \"{obj}\" has been updated by user \"{obj.updated_by}\" with the following changes: <ul>"
        #         for field in fields_changed:
        #             content_html+= f"<li>{field[0].verbose_name if hasattr(field[0], 'verbose_name') else field[0]}: {field[1]} -> {field[2]}</li>"
        #         content_html+= "</ul>"
        # super().save_model(request, obj, form, change)
        # send notification to superuser when create or update successfully
        # if title:
        #     for user in User.objects.filter(is_superuser= True):
        #         obj= Notification.objects.create(user= user, title= title,
        #                                     flag= 'info',
        #                                     action= action,
        #                                     obj_link= obj_link,
        #                                     content= content_html)
        #         obj.alert(request) # send alert to user



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
        if request.user.is_superuser: #is_hidden
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
            fieldsets.append(('Meta', {'fields': meta_fields, 'classes': ["tab"]}))
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
            button_edit = f'<a class="btn-edit col-span-1" href="{path_change}"> <img src="{svg_url_edit}" alt="Sửa" style="width: {width}px; height: {height}px;"></a>'
            c+= 1
        else:
            button_view = f'<a class="btn-view col-span-1" href="{path_change}"> <img src="{svg_url_view}" alt="Xem" style="width: {width}px; height: {height}px;"></a>'
            c+= 1

        if self.has_delete_permission(self.request, obj):
            c+= 1
            button_delete = f'<a class="btn-delete btn-danger col-span-1" href="{path_delete}"> <img src="{svg_url_delete}" alt="Xóa" style="width: {width}px; height: {height}px;"></a>'

        return mark_safe(f'''
                         <div id="action_buttoms" class="grid gap-1 grid-cols-{c}" style="width: {33*c}px;">{button_view} {button_edit} {button_delete} </div> 
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

    def changelist_view(self, request, extra_context = None):
        extra_context = extra_context or {}
        extra_context['using_grid_view'] = self.using_grid_view
        if not self.using_grid_view:
            grid_view= False
        else:
            grid_view= int(request.POST.get('grid_view', self.grid_view))
        
        self.grid_view = grid_view
        if grid_view:
            extra_context = extra_context or {}
            extra_context['grid_view'] = grid_view
            self.list_display_links= list(set(list(self.list_display_links) + ['grid_item_header']))
            self.list_display= self.get_list_display(request)

        # Xác định số lượng hiển thị từ request
        per_page = self.list_per_page
        if 'per_page' in request.POST:
            try:
                per_page = int(request.POST.get('per_page'))
                if per_page in [5, 10, 20, 50, 100, 200]:
                    self.list_per_page = per_page
            except ValueError:
                pass  # Giữ nguyên giá trị mặc định nếu không hợp lệ

        # Truyền danh sách số lượng hiển thị vào context
        if extra_context is None:
            extra_context = {}
        extra_context['page_sizes'] = self.page_sizes
        extra_context['grid_cols'] = self.grid_cols

        if self.default_toggle_sidebar is not None:
            request.session["toggle_sidebar"] = self.default_toggle_sidebar
        res = super().changelist_view(request, extra_context)
        return res
    
    def changeform_view(self, request, object_id = None, form_url = "", extra_context = None):
        if self.default_toggle_sidebar is not None:
            request.session["toggle_sidebar"] = self.default_toggle_sidebar
        return super().changeform_view(request, object_id, form_url, extra_context)
    
    # GridItemHeader
    def grid_item_header(self, obj):
        # TODO: implement this method to return the header of the grid item
        return mark_safe(f'<div class="grid-item-header">{obj}</div>')
    grid_item_header.short_description = 'Header'