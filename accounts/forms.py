from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

# ? Implement email verification after registration
# ? Add CAPTCHA to prevent bot registrations

class RegisterForm(UserCreationForm):
    phone = forms.CharField(
        max_length=20,
        required=True,
        label="",
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Phone Number'}
        )
    )

    specialization = forms.CharField(
        max_length=100,
        required=False,  
        label="",
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Specialization (Doctors only)'}
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customize username field
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['username'].label = ''
        self.fields['username'].help_text = (
            '<span class="form-text text-muted">'
            '<small>Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.</small>'
            '</span>'
        )

        # Customize password1 field
        # TODO: Remove rule: Can't be too similar to other personal info
        # TODO: Add password strength meter
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password1'].label = ''
        self.fields['password1'].help_text = (
            '<ul class="form-text text-muted small">'
            "<li>Your password can't be too similar to your other personal information.</li>"
            "<li>Your password must contain at least 8 characters.</li>"
            "<li>Your password can't be a commonly used password.</li>"
            "<li>Your password can't be entirely numeric.</li>"
            '</ul>'
        )

        # Customize password2 field
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
        self.fields['password2'].label = ''
        self.fields['password2'].help_text = (
            '<span class="form-text text-muted">'
            '<small>Enter the same password as before, for verification.</small>'
            '</span>'
        )

        # Customize phone field
        self.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
        self.fields['phone'].label = ''
