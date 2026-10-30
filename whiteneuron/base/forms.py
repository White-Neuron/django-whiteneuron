from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from unfold.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    # As AuthenticationForm's own field: redefined without its label, it read "Password" in every language;
    # with render_value=True, a failed sign-in wrote the password typed back into the page's HTML
    password = forms.CharField(
        label=_("Password"), strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["password"].widget.attrs["class"]+= ""

