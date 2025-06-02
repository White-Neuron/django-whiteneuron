from django import forms
from django.conf import settings
from unfold.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    password = forms.CharField(widget=forms.PasswordInput(render_value=True))

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["password"].widget.attrs["class"]+= ""

