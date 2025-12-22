from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date, datetime
import uuid

# Patient ID Generator
def generate_patient_id(prefix="P"):
    year = datetime.now().year
    rand = uuid.uuid4().hex[:4].upper()
    return f"{prefix}{year}{rand}"

# Patient/Dependent Patient Information
class PatientInfo(models.Model):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile"
    )

    patient_id = models.CharField(
        max_length=20,
        primary_key=True,
        editable=False
    )

    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES
    )

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

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["patient_id"]

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = generate_patient_id(prefix="P")

        if self.birthdate:
            today = date.today()
            self.age = today.year - self.birthdate.year - (
                (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_id} - {self.user.get_full_name()}"
    
    
class DependentPatient(models.Model):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    patient_id = models.CharField(
        max_length=20,
        primary_key=True,
        editable=False
    )

    guardian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dependent_patients"
    )

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES
    )

    phone = models.CharField(max_length=20, blank=True, null=True)
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

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = generate_patient_id(prefix="D")

        if self.birthdate:
            today = date.today()
            self.age = today.year - self.birthdate.year - (
                (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
            )

        super().save(*args, **kwargs)
        
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

# Patient Medical Information: Vitals
class PatientVitals(models.Model):
    patient = models.ForeignKey(
        PatientInfo,
        on_delete=models.CASCADE,
        related_name="vitals"
    )

    recorded_at = models.DateTimeField(auto_now_add=True)

    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = "Patient Vital"
        verbose_name_plural = "Patient Vitals"

    def __str__(self):
        return f"{self.patient.patient_id} - {self.recorded_at:%Y-%m-%d %H:%M}"
    
# Patient Medical Information: Allergies
class PatientAllergy(models.Model):
    patient = models.ForeignKey(
        PatientInfo,
        on_delete=models.CASCADE,
        related_name="allergies"
    )

    allergy_name = models.CharField(max_length=255)

    class Meta:
        ordering = ["allergy_name"]
        verbose_name = "Patient Allergy"
        verbose_name_plural = "Patient Allergies"

    def __str__(self):
        return f"{self.patient.patient_id} - {self.allergy_name}"

# Patient Medical Information: Medications
class PatientMedication(models.Model):
    patient = models.ForeignKey(
        PatientInfo,
        on_delete=models.CASCADE,
        related_name="medications"
    )
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)

    class Meta:
        ordering = ["medication_name"]
        verbose_name = "Patient Medication"
        verbose_name_plural = "Patient Medications"

    def __str__(self):
        return f"{self.patient.patient_id} - {self.medication_name}"

# Dependent Patient Medical Information: Vitals
class DependentPatientVitals(models.Model):
    dependent_patient = models.ForeignKey(
        DependentPatient,
        on_delete=models.CASCADE,
        related_name="vitals"
    )

    recorded_at = models.DateTimeField(auto_now_add=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = "Dependent Patient Vital"
        verbose_name_plural = "Dependent Patient Vitals"

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.recorded_at:%Y-%m-%d %H:%M}"

# Dependent Patient Medical Information: Allergies
class DependentPatientAllergy(models.Model):
    dependent_patient = models.ForeignKey(
        DependentPatient,
        on_delete=models.CASCADE,
        related_name="allergies"
    )
    allergy_name = models.CharField(max_length=255)

    class Meta:
        ordering = ["allergy_name"]
        verbose_name = "Dependent Patient Allergy"
        verbose_name_plural = "Dependent Patient Allergies"

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.allergy_name}"

# Dependent Patient Medical Information: Medications
class DependentPatientMedication(models.Model):
    dependent_patient = models.ForeignKey(
        DependentPatient,
        on_delete=models.CASCADE,
        related_name="medications"
    )
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)

    class Meta:
        ordering = ["medication_name"]
        verbose_name = "Dependent Patient Medication"
        verbose_name_plural = "Dependent Patient Medications"

    def __str__(self):
        return f"{self.dependent_patient.patient_id} - {self.medication_name}"

class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)

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
    
    profile_picture = models.ImageField(
        upload_to="doctors/profiles/", 
        blank=True, 
        null=True
    )

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


    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} - {self.specialization}"

class Appointment(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    doctor = models.ForeignKey(DoctorInfo, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, default="pending")

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.start_time}"
    
    @property
    def patient_name(self):
        return self.patient.get_full_name()

class DependentAppointment(models.Model):
    dependent_patient = models.ForeignKey(
        DependentPatient,
        on_delete=models.CASCADE
    )
    doctor = models.ForeignKey(DoctorInfo, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, default="pending")

    def __str__(self):
        return f"{self.dependent_patient.full_name} - {self.start_time}"

    @property
    def patient_name(self):
        return self.dependent_patient.full_name
    
class DoctorAvailability(models.Model):
    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    doctor = models.ForeignKey(
        "DoctorInfo",
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
    doctor = models.ForeignKey(DoctorInfo, on_delete=models.CASCADE, related_name="custom_availabilities")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"

class CompletedAppointment(models.Model):
    appointment = models.OneToOneField('Appointment', on_delete=models.CASCADE, related_name='completed_record')
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        patient_name = self.appointment.patient.get_full_name() if self.appointment.patient else self.appointment.dependent_patient.full_name
        return f"Completed: {patient_name} on {self.completed_at.strftime('%Y-%m-%d %H:%M')}"
    
class MedicalRecord(models.Model):
    # Either a PatientInfo or DependentPatient
    patient = models.ForeignKey('PatientInfo', null=True, blank=True, on_delete=models.CASCADE)
    dependent_patient = models.ForeignKey('DependentPatient', null=True, blank=True, on_delete=models.CASCADE)
    
    patient_id_str = models.CharField(max_length=20, editable=False)  # generated ID for reference

    reason_for_visit = models.TextField()
    symptoms = models.TextField()
    diagnosis = models.TextField()
    prescription = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if self.patient:
            self.patient_id_str = self.patient.patient_id
        elif self.dependent_patient:
            self.patient_id_str = self.dependent_patient.patient_id
        super().save(*args, **kwargs)