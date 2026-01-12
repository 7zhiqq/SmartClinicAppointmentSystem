from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Phone
from .validators import validate_ph_phone_number, normalize_ph_phone_number
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model


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
        required=True,  # ✅ Make email required
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

    def clean_email(self):
        """Validate that email is unique"""
        email = self.cleaned_data.get('email')
        
        if not email:
            raise forms.ValidationError("Email address is required.")
        
        # Check if email already exists
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        
        return email.lower()  # Store emails in lowercase for consistency
    
    def clean_phone(self):
        """Validate and normalize phone number"""
        phone = normalize_ph_phone_number(self.cleaned_data['phone'])
        if Phone.objects.filter(number=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()  # Ensure lowercase
        
        if commit:
            user.save()
            from .models import Phone
            from .validators import normalize_ph_phone_number
            Phone.objects.create(
                user=user,
                number=normalize_ph_phone_number(self.cleaned_data["phone"])
            )

        return user
    
User = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        """
        Correct user lookup for custom user model
        """
        return User.objects.filter(
            email__iexact=email,
            is_active=True
        )