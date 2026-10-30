from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from unfold.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    # As AuthenticationForm's own field: redefined without them, the label read "Password" in every language
    password = forms.CharField(label=_("Password"), strip=False, widget=forms.PasswordInput(render_value=True))

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["password"].widget.attrs["class"]+= ""

