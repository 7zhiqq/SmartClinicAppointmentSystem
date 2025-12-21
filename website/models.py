from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date, datetime
import uuid
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# ==================== PATIENT ABSTRACTION ====================
class PatientBase(models.Model):
    """Abstract base for all patient types"""
    patient_id = models.CharField(max_length=20, unique=True, editable=False)
    gender_choices = [("M", "Male"), ("F", "Female")]
    gender = models.CharField(max_length=1, choices=gender_choices)
    birthdate = models.DateField()
    age = models.PositiveIntegerField(blank=True, null=True)
    blood_type = models.CharField(
        max_length=3,
        choices=[
            ("A+", "A+"), ("A-", "A-"),
            ("B+", "B+"), ("B-", "B-"),
            ("AB+", "AB+"), ("AB-", "AB-"),
            ("O+", "O+"), ("O-", "O-"),
        ],
        blank=True,
        null=True
    )
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.birthdate:
            today = date.today()
            self.age = today.year - self.birthdate.year - (
                (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
            )
        super().save(*args, **kwargs)

    def get_full_name(self):
        raise NotImplementedError

    def get_contact_email(self):
        raise NotImplementedError

# ==================== PATIENT INFO (Self) ====================
class PatientInfo(PatientBase):
    """Patient with user account"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile"
    )

    class Meta:
        ordering = ["patient_id"]
        verbose_name = "Patient"

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = self._generate_patient_id("P")
        # Sync phone from user
        if self.user.phone and not self.phone:
            from accounts.models import Phone
            phone_obj = Phone.objects.filter(user=self.user).first()
            if phone_obj:
                self.phone = phone_obj.number
        super().save(*args, **kwargs)

    def _generate_patient_id(self, prefix):
        from django.utils import timezone
        year = timezone.now().year
        rand = uuid.uuid4().hex[:4].upper()
        return f"{prefix}{year}{rand}"

    def get_full_name(self):
        return self.user.get_full_name()

    def get_contact_email(self):
        return self.user.email

    def __str__(self):
        return f"{self.patient_id} - {self.get_full_name()}"

# ==================== DEPENDENT PATIENT ====================
class DependentPatient(PatientBase):
    """Dependent of a patient"""
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    guardian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dependent_patients"
    )

    class Meta:
        ordering = ["patient_id"]
        verbose_name = "Dependent Patient"

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = self._generate_patient_id("D")
        super().save(*args, **kwargs)

    def _generate_patient_id(self, prefix):
        year = datetime.now().year
        rand = uuid.uuid4().hex[:4].upper()
        return f"{prefix}{year}{rand}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_contact_email(self):
        """Get guardian's email since dependent has no email"""
        return self.guardian.email

    @property
    def full_name(self):
        return self.get_full_name()

    def __str__(self):
        return f"{self.patient_id} - {self.get_full_name()}"

# ==================== APPOINTMENT (Redesigned) ====================
class Appointment(models.Model):
    """
    Single appointment model using content types for polymorphic patient reference.
    No nullable fields!
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    # Doctor (always required)
    doctor = models.ForeignKey(
        'DoctorInfo',
        on_delete=models.PROTECT,
        related_name="appointments"
    )

    # Polymorphic patient reference
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('patientinfo', 'dependentpatient')}
    )
    object_id = models.CharField(max_length=50)
    patient_object = GenericForeignKey('content_type', 'object_id')

    # Appointment details (never null)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['doctor', 'start_time']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")
        
        # Check for conflicts
        conflicts = Appointment.objects.filter(
            doctor=self.doctor,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
            status='approved'
        ).exclude(pk=self.pk)
        
        if conflicts.exists():
            raise ValidationError("Time slot conflicts with another appointment")

    def get_patient(self):
        """Retrieve the actual patient object"""
        return self.patient_object

    def get_patient_name(self):
        """Get patient full name"""
        patient = self.get_patient()
        return patient.get_full_name() if patient else "Unknown"

    def get_patient_email(self):
        """Get patient contact email"""
        patient = self.get_patient()
        return patient.get_contact_email() if patient else None

    def __str__(self):
        return f"{self.get_patient_name()} with Dr. {self.doctor.user.get_full_name()} on {self.start_time.date()}"

# ==================== VITALS ====================
class PatientVitals(models.Model):
    """Vitals for PatientInfo"""
    patient = models.ForeignKey(
        PatientInfo,
        on_delete=models.CASCADE,
        related_name="vitals"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    height_cm = models.FloatField(blank=True, null=True)
    weight_kg = models.FloatField(blank=True, null=True)
    blood_pressure = models.CharField(max_length=20, blank=True, default="")
    heart_rate = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.patient.patient_id} - {self.recorded_at:%Y-%m-%d %H:%M}"

class DependentPatientVitals(models.Model):
    """Vitals for DependentPatient"""
    dependent_patient = models.ForeignKey(
        DependentPatient,
        on_delete=models.CASCADE,
        related_name="vitals"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    height_cm = models.FloatField(blank=True, null=True)
    weight_kg = models.FloatField(blank=True, null=True)
    blood_pressure = models.CharField(max_length=20, blank=True, default="")
    heart_rate = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.recorded_at:%Y-%m-%d %H:%M}"

# ==================== ALLERGIES ====================
class PatientAllergy(models.Model):
    """Allergies for PatientInfo"""
    patient = models.ForeignKey(
        PatientInfo,
        on_delete=models.CASCADE,
        related_name="allergies"
    )
    allergy_name = models.CharField(max_length=255)
    severity = models.CharField(
        max_length=20,
        choices=[('mild', 'Mild'), ('moderate', 'Moderate'), ('severe', 'Severe')],
        default='mild'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["allergy_name"]
        unique_together = ('patient', 'allergy_name')

    def __str__(self):
        return f"{self.patient.patient_id} - {self.allergy_name}"

class DependentPatientAllergy(models.Model):
    """Allergies for DependentPatient"""
    dependent_patient = models.ForeignKey(
        DependentPatient,
        on_delete=models.CASCADE,
        related_name="allergies"
    )
    allergy_name = models.CharField(max_length=255)
    severity = models.CharField(
        max_length=20,
        choices=[('mild', 'Mild'), ('moderate', 'Moderate'), ('severe', 'Severe')],
        default='mild'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["allergy_name"]
        unique_together = ('dependent_patient', 'allergy_name')

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.allergy_name}"

# ==================== MEDICATIONS ====================
class PatientMedication(models.Model):
    """Medications for PatientInfo"""
    patient = models.ForeignKey(
        PatientInfo,
        on_delete=models.CASCADE,
        related_name="medications"
    )
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["medication_name"]

    def __str__(self):
        return f"{self.patient.patient_id} - {self.medication_name}"

class DependentPatientMedication(models.Model):
    """Medications for DependentPatient"""
    dependent_patient = models.ForeignKey(
        DependentPatient,
        on_delete=models.CASCADE,
        related_name="medications"
    )
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["medication_name"]

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.medication_name}"

# ==================== MEDICAL RECORDS ====================
class MedicalRecord(models.Model):
    """Medical record for both patient types"""
    # Polymorphic patient reference
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('patientinfo', 'dependentpatient')}
    )
    object_id = models.CharField(max_length=50)
    patient_object = GenericForeignKey('content_type', 'object_id')

    # Record details
    doctor = models.ForeignKey(
        'DoctorInfo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_records"
    )
    reason_for_visit = models.TextField()
    symptoms = models.TextField()
    diagnosis = models.TextField()
    prescription = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def get_patient(self):
        """Retrieve the actual patient object"""
        return self.patient_object

    def get_patient_name(self):
        """Get patient full name"""
        patient = self.get_patient()
        return patient.get_full_name() if patient else "Unknown"

    def __str__(self):
        return f"Medical Record - {self.get_patient_name()} ({self.created_at.date()})"

# ==================== DOCTOR INFO (unchanged but improved) ====================
class DoctorInfo(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_info"
    )
    profile_picture = models.ImageField(
        upload_to="doctors/profiles/",
        blank=True,
        default=""
    )
    specialization = models.ForeignKey(
        'Specialization',
        on_delete=models.PROTECT,
        related_name="doctors"
    )
    license_number = models.CharField(max_length=100, unique=True)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(blank=True, null=True)
    is_rejected = models.BooleanField(default=False)
    rejected_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialization}"

class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class DoctorAvailability(models.Model):
    WEEKDAYS = [
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"),
        (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
    ]

    doctor = models.ForeignKey(
        DoctorInfo,
        on_delete=models.CASCADE,
        related_name="availabilities"
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ("doctor", "weekday", "start_time", "end_time")
        ordering = ["weekday", "start_time"]

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.get_weekday_display()} ({self.start_time}–{self.end_time})"

class CustomDoctorAvailability(models.Model):
    doctor = models.ForeignKey(
        DoctorInfo,
        on_delete=models.CASCADE,
        related_name="custom_availabilities"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ("doctor", "date", "start_time", "end_time")

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"

class CompletedAppointment(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='completed_record'
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Completed: {self.appointment.get_patient_name()} on {self.completed_at.strftime('%Y-%m-%d %H:%M')}"