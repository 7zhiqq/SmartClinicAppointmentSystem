from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid
from datetime import datetime, timedelta
from .validators import validate_ph_phone_number
from django.core.exceptions import ValidationError

# generate unique ID function
def generate_unique_id(user, model, letter):
    first = user.first_name[:1].upper() if user.first_name else "X"
    last = user.last_name[:1].upper() if user.last_name else "X"
    initials = first + last

    year = str(datetime.now().year)[2:]

    count = model.objects.filter(
        user__date_joined__year=datetime.now().year
    ).count() + 1

    return f"{letter}{initials}{year}{str(count).zfill(2)}"


# Custom User Model
class User(AbstractUser):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('staff', 'Staff'),
        ('doctor', 'Doctor'),
        ('manager', 'Manager'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='patient'
    )
    
    # ✅ ADD THIS: Enforce unique email
    email = models.EmailField(unique=True, blank=False)

    class Meta:
        # Optional: Add this to improve query performance
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return self.username


class Phone(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    number = models.CharField(
        max_length=20,
        validators=[validate_ph_phone_number],
        unique=True
    )

    def save(self, *args, **kwargs):
        from .validators import normalize_ph_phone_number
        normalized = normalize_ph_phone_number(self.number)
        if not normalized:
            raise ValidationError("Invalid phone number.")
        self.number = normalized
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number


# Invitation Model
class Invite(models.Model):
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.role}"

    def is_expired(self):
        """Check if the invite link has expired (24 hours)"""
        expiry_time = self.created_at + timedelta(hours=24)
        return datetime.now(self.created_at.tzinfo) > expiry_time

    def is_valid(self):
        """Check if the invite is still valid (not expired and not used)"""
        return not self.is_expired() and not self.used

    @property
    def expires_at(self):
        """Return the expiration datetime"""
        return self.created_at + timedelta(hours=24)

    @property
    def time_remaining(self):
        """Return remaining time in hours"""
        if self.is_expired():
            return 0
        remaining = self.expires_at - datetime.now(self.created_at.tzinfo)
        return max(0, remaining.total_seconds() / 3600)


# TODO: Add gender field to all profiles
# TODO: Add profile picture field to all profiles (patient: optional, doctor/staff/manager: mandatory)

#Patient Profile Model
class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    patient_id = models.CharField(max_length=20, unique=True, blank=True)

    def save(self, *args, **kwargs):
        self.first_name = self.user.first_name
        self.last_name = self.user.last_name

        if not self.patient_id:
            from .models import generate_unique_id
            self.patient_id = generate_unique_id(self.user, PatientProfile, "P")
        super().save(*args, **kwargs)

# Doctor Profile Model
class DoctorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    doctor_id = models.CharField(max_length=20, unique=True, blank=True)

    def save(self, *args, **kwargs):
        self.first_name = self.user.first_name
        self.last_name = self.user.last_name

        # Generate doctor_id
        if not self.doctor_id:
            from .models import generate_unique_id
            self.doctor_id = generate_unique_id(self.user, DoctorProfile, "D")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.doctor_id} - {self.user.get_full_name()}"

# Staff Profile Model
class StaffProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    staff_id = models.CharField(max_length=20, unique=True, blank=True)

    def save(self, *args, **kwargs):
        self.first_name = self.user.first_name
        self.last_name = self.user.last_name

        # Generate staff_id if not already set
        if not self.staff_id:
            from .models import generate_unique_id
            self.staff_id = generate_unique_id(self.user, StaffProfile, "S")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff_id} - {self.user.get_full_name()}"

# Manager Profile Model
class ManagerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    manager_id = models.CharField(max_length=20, unique=True, blank=True)

    def save(self, *args, **kwargs):
        self.first_name = self.user.first_name
        self.last_name = self.user.last_name

        # Generate manager_id if not already set
        if not self.manager_id:
            from .models import generate_unique_id
            self.manager_id = generate_unique_id(self.user, ManagerProfile, "M")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.manager_id} - {self.user.get_full_name()}"