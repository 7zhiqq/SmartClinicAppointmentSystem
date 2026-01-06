from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from accounts.models import PatientProfile, Phone, User
from django.utils.text import slugify
from django.core.exceptions import ValidationError
import random


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked after a user successfully authenticates via a social provider,
        but before the login is fully processed.
        """
        # If user is already logged in, link the social account
        if request.user.is_authenticated:
            return
        
        # Check if user exists with this email
        if sociallogin.is_existing:
            return
        
        # Get email from social account
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return
        
        # Check if a user with this email already exists
        try:
            existing_user = User.objects.get(email__iexact=email)
            # Connect the social account to the existing user
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass

    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Allow automatic signup for all Google accounts
        """
        return True

    def populate_user(self, request, sociallogin, data):
        """
        Populate user data from social account
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Get data from Google
        extra_data = sociallogin.account.extra_data
        
        # Set first name and last name from Google
        if 'given_name' in extra_data:
            user.first_name = extra_data['given_name']
        if 'family_name' in extra_data:
            user.last_name = extra_data['family_name']
        
        # ✅ Set email (already validated by Google)
        if 'email' in extra_data:
            user.email = extra_data['email'].lower()
        
        # Auto-generate username from email
        if not user.username:
            email = extra_data.get('email', '')
            if email:
                # Use email prefix as base username
                base_username = email.split('@')[0]
                base_username = slugify(base_username).replace('-', '_')
                
                # Ensure username is unique
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user.username = username
        
        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Set role to patient for Google sign-ups
        user.role = 'patient'
        user.save()
        
        # Create PatientProfile
        try:
            PatientProfile.objects.create(user=user)
        except Exception as e:
            print(f"Error creating PatientProfile: {e}")
        
        return user


class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """
        Only allow patients to sign up directly.
        Other roles require invitation.
        """
        return True
    
    def save_user(self, request, user, form, commit=True):
        """
        Saves a new user with patient role.
        """
        user = super().save_user(request, user, form, commit=False)
        user.role = 'patient'
        
        # ✅ Ensure email is lowercase for consistency
        if user.email:
            user.email = user.email.lower()
        
        if commit:
            user.save()
        
        return user
    
    def clean_email(self, email):
        """
        ✅ Validate email uniqueness (case-insensitive)
        """
        email = email.lower()
        
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        
        return email