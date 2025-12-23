from django.db import models
from django.db.models import Avg
from django.conf import settings
from django.utils import timezone
from datetime import date, datetime
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

# Patient ID Generator
def generate_patient_id(prefix="P"):
    year = datetime.now().year
    rand = uuid.uuid4().hex[:4].upper()
    return f"{prefix}{year}{rand}"

# -------------------- PATIENT MODELS --------------------
class PatientInfo(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile"
    )

    patient_id = models.CharField(max_length=20, primary_key=True, editable=False)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    birthdate = models.DateField()
    age = models.PositiveIntegerField(blank=True, null=True)
    blood_type = models.CharField(
        max_length=3,
        choices=[("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
                 ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-")],
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='patients_created'
    )

    class Meta:
        ordering = ["patient_id"]

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = generate_patient_id("P")

        if self.birthdate:
            today = date.today()
            self.age = today.year - self.birthdate.year - (
                (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_id} - {self.user.get_full_name()}"

class DependentPatient(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female")]

    patient_id = models.CharField(max_length=20, primary_key=True, editable=False)
    guardian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dependent_patients"
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=20, blank=True, null=True)
    birthdate = models.DateField()
    age = models.PositiveIntegerField(blank=True, null=True)
    blood_type = models.CharField(
        max_length=3,
        choices=[("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
                 ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-")],
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='dependents_created'
    )

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = generate_patient_id("D")

        if self.birthdate:
            today = date.today()
            self.age = today.year - self.birthdate.year - (
                (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
            )

        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

# -------------------- PATIENT MEDICAL INFO --------------------
class PatientVitals(models.Model):
    patient = models.ForeignKey(PatientInfo, on_delete=models.CASCADE, related_name="vitals")
    recorded_at = models.DateTimeField(auto_now_add=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='vitals_created'
    )

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name_plural = "Patient Vitals"

    def __str__(self):
        return f"{self.patient.patient_id} - {self.recorded_at:%Y-%m-%d %H:%M}"

class PatientAllergy(models.Model):
    patient = models.ForeignKey(PatientInfo, on_delete=models.CASCADE, related_name="allergies")
    allergy_name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='allergies_created'
    )

    class Meta:
        ordering = ["allergy_name"]
        verbose_name_plural = "Patient Allergies"

    def __str__(self):
        return f"{self.patient.patient_id} - {self.allergy_name}"

class PatientMedication(models.Model):
    patient = models.ForeignKey(PatientInfo, on_delete=models.CASCADE, related_name="medications")
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    prescribed_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='medications_created'
    )

    class Meta:
        ordering = ["-prescribed_at"]
        verbose_name_plural = "Patient Medications"

    def __str__(self):
        return f"{self.patient.patient_id} - {self.medication_name}"

# -------------------- DEPENDENT MEDICAL INFO --------------------
class DependentPatientVitals(models.Model):
    dependent_patient = models.ForeignKey(DependentPatient, on_delete=models.CASCADE, related_name="vitals")
    recorded_at = models.DateTimeField(auto_now_add=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='dependent_vitals_created'
    )

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name_plural = "Dependent Patient Vitals"

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.recorded_at:%Y-%m-%d %H:%M}"

class DependentPatientAllergy(models.Model):
    dependent_patient = models.ForeignKey(DependentPatient, on_delete=models.CASCADE, related_name="allergies")
    allergy_name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='dependent_allergies_created'
    )

    class Meta:
        ordering = ["allergy_name"]
        verbose_name_plural = "Dependent Patient Allergies"

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.allergy_name}"

class DependentPatientMedication(models.Model):
    dependent_patient = models.ForeignKey(DependentPatient, on_delete=models.CASCADE, related_name="medications")
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    prescribed_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='dependent_medications_created'
    )

    class Meta:
        ordering = ["-prescribed_at"]
        verbose_name_plural = "Dependent Patient Medications"

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.medication_name}"

    dependent_patient = models.ForeignKey(
        DependentPatient,
        on_delete=models.CASCADE,
        related_name="medications"
    )
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    prescribed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-prescribed_at"]
        verbose_name = "Dependent Patient Medication"
        verbose_name_plural = "Dependent Patient Medications"

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.medication_name}"

# -------------------- DOCTOR MODELS --------------------
class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='specializations_created'
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DoctorInfo(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_info"
    )
    profile_picture = models.ImageField(upload_to="doctors/profiles/", blank=True, null=True)
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.PROTECT,
        related_name="doctors",
        null=True,
        blank=True
    )
    license_number = models.CharField(max_length=100, unique=True)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(blank=True, null=True)
    is_rejected = models.BooleanField(default=False)
    rejected_at = models.DateTimeField(null=True, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True, null=True)
    qualifications = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='doctors_created'
    )

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        specialization_name = self.specialization.name if self.specialization else "General"
        return f"Dr. {self.user.first_name} {self.user.last_name} - {specialization_name}, {self.years_experience} yrs experience"


# -------------------- APPOINTMENTS --------------------
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('no_show', 'No Show'),
    ]

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorInfo, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, default="pending", choices=STATUS_CHOICES)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='appointments_created'
    )

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.start_time}"

    @property
    def patient_name(self):
        return self.patient.get_full_name()


class DependentAppointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('no_show', 'No Show'),
    ]

    dependent_patient = models.ForeignKey(DependentPatient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorInfo, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, default="pending", choices=STATUS_CHOICES)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='dependent_appointments_created'
    )

    def __str__(self):
        return f"{self.dependent_patient.full_name} - {self.start_time}"

    @property
    def patient_name(self):
        return self.dependent_patient.full_name


# -------------------- DOCTOR AVAILABILITY --------------------
class DoctorAvailability(models.Model):
    WEEKDAYS = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
                (4, "Friday"), (5, "Saturday"), (6, "Sunday")]

    doctor = models.ForeignKey(DoctorInfo, on_delete=models.CASCADE, related_name="availabilities")
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='availabilities_created'
    )

    class Meta:
        unique_together = ("doctor", "weekday", "start_time", "end_time")
        ordering = ["weekday", "start_time"]

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.get_weekday_display()} ({self.start_time}–{self.end_time})"


class CustomDoctorAvailability(models.Model):
    doctor = models.ForeignKey(DoctorInfo, on_delete=models.CASCADE, related_name="custom_availabilities")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='custom_availabilities_created'
    )

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"


# -------------------- COMPLETED APPOINTMENT --------------------
class CompletedAppointment(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='completed_record')
    completed_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='completed_appointments_created'
    )

    def __str__(self):
        patient_name = self.appointment.patient.get_full_name()
        return f"Completed: {patient_name} on {self.completed_at.strftime('%Y-%m-%d %H:%M')}"


# -------------------- MEDICAL RECORDS --------------------
class MedicalRecord(models.Model):
    patient = models.ForeignKey(PatientInfo, null=True, blank=True, on_delete=models.CASCADE)
    dependent_patient = models.ForeignKey(DependentPatient, null=True, blank=True, on_delete=models.CASCADE)
    patient_id_str = models.CharField(max_length=20, editable=False)
    reason_for_visit = models.TextField()
    symptoms = models.TextField()
    diagnosis = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='medical_records_created'
    )

    def save(self, *args, **kwargs):
        if self.patient:
            self.patient_id_str = self.patient.patient_id
        elif self.dependent_patient:
            self.patient_id_str = self.dependent_patient.patient_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_id_str} - {self.reason_for_visit[:20]}"


class Prescription(models.Model):
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name="prescriptions")
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    prescribed_at = models.DateTimeField(default=timezone.now)
    create_medication = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='prescriptions_created'
    )

    class Meta:
        ordering = ["-prescribed_at"]

    def __str__(self):
        return f"{self.medical_record.patient_id_str} - {self.medication_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.create_medication:
            from .models import PatientMedication, DependentPatientMedication
            if self.medical_record.patient:
                PatientMedication.objects.create(
                    patient=self.medical_record.patient,
                    medication_name=self.medication_name,
                    dosage=self.dosage,
                    frequency=self.frequency,
                    prescribed_at=self.prescribed_at,
                    created_by=self.created_by
                )
            elif self.medical_record.dependent_patient:
                DependentPatientMedication.objects.create(
                    dependent_patient=self.medical_record.dependent_patient,
                    medication_name=self.medication_name,
                    dosage=self.dosage,
                    frequency=self.frequency,
                    prescribed_at=self.prescribed_at,
                    created_by=self.created_by
                )


# -------------------- DOCTOR RATINGS --------------------
class DoctorRating(models.Model):
    patient = models.ForeignKey(PatientInfo, on_delete=models.CASCADE, related_name='ratings')
    doctor = models.ForeignKey(DoctorInfo, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ratings_created'
    )

    class Meta:
        unique_together = ('patient', 'doctor')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient.user.get_full_name()} → {self.doctor.user.get_full_name()}: {self.rating}⭐"

    @property
    def average_rating(self):
        return self.ratings.aggregate(avg=Avg('rating'))['avg'] or 0

    @property
    def rating_count(self):
        return self.ratings.count()


# -------------------- ACTIVITY LOG --------------------
class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('login', 'Logged In'),
        ('logout', 'Logged Out'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    related_object_repr = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        user_name = self.user.get_full_name() if self.user else "System"
        return f"{self.timestamp:%Y-%m-%d %H:%M} | {user_name} {self.get_action_type_display()} {self.model_name} ({self.related_object_repr})"
