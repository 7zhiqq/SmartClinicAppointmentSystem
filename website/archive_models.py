from django.db import models
from django.conf import settings
from django.utils import timezone
import json


class ArchivedPatientInfo(models.Model):
    """Archived patient information"""
    original_patient_id = models.CharField(max_length=20, db_index=True)
    user_id = models.IntegerField(null=True, blank=True)
    user_username = models.CharField(max_length=150)
    user_email = models.EmailField()
    user_full_name = models.CharField(max_length=301)
    
    gender = models.CharField(max_length=1)
    birthdate = models.DateField()
    age = models.PositiveIntegerField()
    blood_type = models.CharField(max_length=3, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Audit fields
    archived_at = models.DateTimeField(default=timezone.now)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='archived_patients'
    )
    archive_reason = models.TextField(blank=True, null=True)
    
    # JSON field for additional data
    additional_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-archived_at']
        verbose_name = 'Archived Patient Info'
        verbose_name_plural = 'Archived Patient Info'
    
    def __str__(self):
        return f"Archived: {self.original_patient_id} - {self.user_full_name}"


class ArchivedDependentPatient(models.Model):
    """Archived dependent patient information"""
    original_patient_id = models.CharField(max_length=20, db_index=True)
    guardian_id = models.IntegerField(null=True, blank=True)
    guardian_username = models.CharField(max_length=150)
    
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=1)
    phone = models.CharField(max_length=20, blank=True, null=True)
    birthdate = models.DateField()
    age = models.PositiveIntegerField()
    blood_type = models.CharField(max_length=3, blank=True, null=True)
    
    # Audit fields
    archived_at = models.DateTimeField(default=timezone.now)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='archived_dependents'
    )
    archive_reason = models.TextField(blank=True, null=True)
    
    additional_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-archived_at']
        verbose_name = 'Archived Dependent Patient'
        verbose_name_plural = 'Archived Dependent Patients'
    
    def __str__(self):
        return f"Archived: {self.original_patient_id} - {self.first_name} {self.last_name}"


class ArchivedAppointment(models.Model):
    """Archived appointment information"""
    original_appointment_id = models.IntegerField(db_index=True)
    appointment_type = models.CharField(max_length=20)  # 'self' or 'dependent'
    
    patient_name = models.CharField(max_length=301)
    doctor_name = models.CharField(max_length=301)
    doctor_specialization = models.CharField(max_length=100, blank=True, null=True)
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20)
    
    # Audit fields
    archived_at = models.DateTimeField(default=timezone.now)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='archived_appointments'
    )
    archive_reason = models.TextField(blank=True, null=True)
    
    additional_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-archived_at']
        verbose_name = 'Archived Appointment'
        verbose_name_plural = 'Archived Appointments'
    
    def __str__(self):
        return f"Archived Appointment #{self.original_appointment_id}: {self.patient_name}"


class ArchivedMedicalRecord(models.Model):
    """Archived medical record information"""
    original_record_id = models.IntegerField(db_index=True)
    patient_id_str = models.CharField(max_length=20)
    patient_name = models.CharField(max_length=301)
    
    reason_for_visit = models.TextField()
    symptoms = models.TextField()
    diagnosis = models.TextField()
    created_at = models.DateTimeField()
    
    # Store prescriptions as JSON
    prescriptions = models.JSONField(default=list, blank=True)
    
    # Audit fields
    archived_at = models.DateTimeField(default=timezone.now)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='archived_medical_records'
    )
    archive_reason = models.TextField(blank=True, null=True)
    
    additional_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-archived_at']
        verbose_name = 'Archived Medical Record'
        verbose_name_plural = 'Archived Medical Records'
    
    def __str__(self):
        return f"Archived Record #{self.original_record_id}: {self.patient_name}"


class ArchivedDoctorInfo(models.Model):
    """Archived doctor information"""
    original_doctor_id = models.IntegerField(db_index=True)
    user_id = models.IntegerField(null=True, blank=True)
    user_username = models.CharField(max_length=150)
    user_full_name = models.CharField(max_length=301)
    user_email = models.EmailField()
    
    specialization = models.CharField(max_length=100, blank=True, null=True)
    license_number = models.CharField(max_length=100)
    years_experience = models.PositiveIntegerField()
    bio = models.TextField(blank=True, null=True)
    qualifications = models.TextField(blank=True, null=True)
    
    was_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Audit fields
    archived_at = models.DateTimeField(default=timezone.now)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='archived_doctors'
    )
    archive_reason = models.TextField(blank=True, null=True)
    
    additional_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-archived_at']
        verbose_name = 'Archived Doctor Info'
        verbose_name_plural = 'Archived Doctor Info'
    
    def __str__(self):
        return f"Archived Doctor: {self.user_full_name}"


class DeletedRecord(models.Model):
    """Track permanently deleted records for audit purposes"""
    model_name = models.CharField(max_length=100)
    original_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=200)
    
    deleted_at = models.DateTimeField(default=timezone.now)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='deleted_records'
    )
    deletion_reason = models.TextField(blank=True, null=True)
    
    # Store snapshot of deleted data
    data_snapshot = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-deleted_at']
        verbose_name = 'Deleted Record'
        verbose_name_plural = 'Deleted Records'
    
    def __str__(self):
        return f"Deleted {self.model_name} #{self.original_id} at {self.deleted_at}"