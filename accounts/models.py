from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid
from datetime import datetime

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

class Phone(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    number = models.CharField(max_length=20)

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


# ? Allow google/facebook registration and login (OAuth2, all roles)

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



