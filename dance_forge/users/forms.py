from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):  # type: ignore[name-defined]  # django-stubs is missing the class, thats why the error is thrown: typeddjango/django-stubs#2555
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set email as not required if it exists
        if "email" in self.fields:
            self.fields["email"].required = False
        else:
            # Add email field if it doesn't exist
            self.fields["email"] = forms.EmailField(
                label=_("Email (optional)"), required=False, widget=forms.EmailInput()
            )

    def clean(self):
        cleaned_data = super().clean()
        # If email is missing from cleaned_data, set it to empty string
        if "email" not in cleaned_data:
            cleaned_data["email"] = ""
        return cleaned_data


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set email as not required if it exists
        if "email" in self.fields:
            self.fields["email"].required = False
        else:
            # Add email field if it doesn't exist
            self.fields["email"] = forms.EmailField(
                label=_("Email (optional)"), required=False, widget=forms.EmailInput()
            )

    def clean(self):
        cleaned_data = super().clean()
        # If email is missing from cleaned_data, set it to empty string
        if "email" not in cleaned_data:
            cleaned_data["email"] = ""
        return cleaned_data
