from allauth.account.forms import LoginForm as AllauthLoginForm
from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _
from reference_data.constants import GREATER_ACCRA_DISTRICT_NAMES
from reference_data.models import Location

from .models import FACILITY_TYPE_CHOICES
from .models import POSITION_CHOICES
from .models import User


class UserLoginForm(AllauthLoginForm):
    def clean(self):
        cleaned_data = super().clean()
        login = cleaned_data.get("login")
        if login:
            inactive = User.objects.filter(email__iexact=login, is_active=False).first()
            if inactive:
                raise forms.ValidationError(
                    "Your account is pending administrator approval. Please wait for activation."
                )
        return cleaned_data


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        fields = ("email",)
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


class UserSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150, required=True, label="First Name")
    last_name = forms.CharField(max_length=150, required=True, label="Last Name")
    phone = forms.CharField(max_length=20, required=True, label="Phone Number")
    health_facility = forms.CharField(max_length=255, required=True, label="Health Facility Name")
    district = forms.ModelChoiceField(
        queryset=Location.objects.filter(
            is_active=True, district_name__in=GREATER_ACCRA_DISTRICT_NAMES
        ).order_by("district_name"),
        required=True,
        label="District",
        empty_label="Select District",
    )
    position = forms.ChoiceField(choices=POSITION_CHOICES, required=True, label="Position/Job Title")
    facility_type = forms.ChoiceField(choices=FACILITY_TYPE_CHOICES, required=True, label="Facility Type")

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone = self.cleaned_data["phone"]
        user.health_facility = self.cleaned_data["health_facility"]
        user.district = self.cleaned_data["district"]
        user.position = self.cleaned_data["position"]
        user.facility_type = self.cleaned_data["facility_type"]
        user.is_active = False
        user.save()
        return user


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """
