import json
import random

from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView, TemplateView
from unfold.views import UnfoldModelAdminViewMixin


class HomeView(RedirectView):
    pattern_name = "admin:base_app_changelist"