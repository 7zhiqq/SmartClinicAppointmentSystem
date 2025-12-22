from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Phone
from .validators import validate_ph_phone_number, normalize_ph_phone_number


class RegisterForm(UserCreationForm):
    phone = forms.CharField(
        max_length=20,
        required=True,
        validators=[validate_ph_phone_number],
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '09xxxxxxxxx or +639xxxxxxxxx',
            }
        )
    )

    email = forms.EmailField(
        label="",
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'Email Address'}
        )
    )

    first_name = forms.CharField(
        max_length=255,
        label="",
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'First Name'}
        )
    )

    last_name = forms.CharField(
        max_length=255,
        label="",
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Last Name'}
        )
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )

    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            from .models import Phone
            from .validators import normalize_ph_phone_number
            Phone.objects.create(
                user=user,
                number=normalize_ph_phone_number(self.cleaned_data["phone"])
            )

        return user

    
    def clean_phone(self):
        phone = normalize_ph_phone_number(self.cleaned_data['phone'])
        if Phone.objects.filter(number=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone

