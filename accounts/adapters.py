from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from accounts.models import PatientProfile, Phone
from website.models import PatientInfo
from accounts.validators import normalize_ph_phone_number


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
            from accounts.models import User
            existing_user = User.objects.get(email=email)
            # Connect the social account to the existing user
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Set role to patient for Google sign-ups
        user.role = 'patient'
        
        # Get data from Google
        extra_data = sociallogin.account.extra_data
        
        # Set first name and last name from Google
        if 'given_name' in extra_data:
            user.first_name = extra_data['given_name']
        if 'family_name' in extra_data:
            user.last_name = extra_data['family_name']
        
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
        
        if commit:
            user.save()
        
        return user