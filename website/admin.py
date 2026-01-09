from django.contrib import admin
from .models import (
    PatientInfo, 
    DependentPatient, 
    PatientVitals, 
    PatientAllergy, 
    PatientMedication,
    DependentPatientVitals,
    DependentPatientAllergy,
    DependentPatientMedication,
    Specialization,
    DoctorInfo,
    ActivityLog
)

class PatientVitalsInline(admin.TabularInline):
    model = PatientVitals
    extra = 1
    fields = ["height_cm", "weight_kg", "blood_pressure", "heart_rate", "recorded_at"]
    readonly_fields = ["recorded_at"]

class PatientAllergyInline(admin.TabularInline):
    model = PatientAllergy
    extra = 1
    fields = ["allergy_name"]

class PatientMedicationInline(admin.TabularInline):
    model = PatientMedication
    extra = 1
    fields = ["medication_name", "dosage", "frequency"]
    
@admin.register(PatientInfo)
class PatientInfoAdmin(admin.ModelAdmin):
    list_display = ["patient_id", "user", "gender", "birthdate", "age", "blood_type"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    list_filter = ["gender", "blood_type"]

    inlines = [PatientVitalsInline, PatientAllergyInline, PatientMedicationInline]
    
class DependentPatientVitalsInline(admin.TabularInline):
    model = DependentPatientVitals
    extra = 1
    fields = ["height_cm", "weight_kg", "blood_pressure", "heart_rate", "recorded_at"]
    readonly_fields = ["recorded_at"]

class DependentPatientAllergyInline(admin.TabularInline):
    model = DependentPatientAllergy
    extra = 1
    fields = ["allergy_name"]

class DependentPatientMedicationInline(admin.TabularInline):
    model = DependentPatientMedication
    extra = 1
    fields = ["medication_name", "dosage", "frequency"]

@admin.register(DependentPatient)
class DependentPatientAdmin(admin.ModelAdmin):
    list_display = ["patient_id", "first_name", "last_name", "guardian", "gender", "birthdate", "age", "blood_type"]
    search_fields = ["first_name", "last_name", "guardian__username"]
    list_filter = ["gender", "blood_type"]

    inlines = [DependentPatientVitalsInline, DependentPatientAllergyInline, DependentPatientMedicationInline]
    

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)    

@admin.register(DoctorInfo)
class DoctorInfoAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "specialization",
        "years_experience",
        "is_approved",
    )
    
    search_fields = (
        "user__first_name",
        "user__last_name",
        "license_number",
    )
    
    list_filter = ("is_approved", "specialization")
    ordering = ("user__last_name",)
    
    # Add a fieldset to include bio and qualifications
    fieldsets = (
        (None, {
            "fields": ("user", "profile_picture", "specialization", "license_number", "years_experience")
        }),
        ("Details", {
            "fields": ("bio", "qualifications")
        }),
        ("Approval Status", {
            "fields": ("is_approved", "approved_at", "is_rejected", "rejected_at")
        }),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action_type', 'model_name', 'related_object_repr')
    list_filter = ('action_type', 'model_name', 'user')
    search_fields = ('description', 'model_name', 'user__username', 'related_object_repr')
    date_hierarchy = 'timestamp'

from website.archive_models import (
    ArchivedPatientInfo, ArchivedDependentPatient, ArchivedAppointment,
    ArchivedMedicalRecord, ArchivedDoctorInfo, DeletedRecord
)

@admin.register(ArchivedPatientInfo)
class ArchivedPatientInfoAdmin(admin.ModelAdmin):
    list_display = ['original_patient_id', 'user_full_name', 'archived_at', 'archived_by']
    search_fields = ['user_full_name', 'original_patient_id', 'user_email']
    list_filter = ['archived_at', 'gender']
    readonly_fields = ['archived_at']

@admin.register(ArchivedDependentPatient)
class ArchivedDependentPatientAdmin(admin.ModelAdmin):
    list_display = ['original_patient_id', 'first_name', 'last_name', 'archived_at']
    search_fields = ['first_name', 'last_name', 'original_patient_id']
    list_filter = ['archived_at', 'gender']

@admin.register(ArchivedDoctorInfo)
class ArchivedDoctorInfoAdmin(admin.ModelAdmin):
    list_display = ['user_full_name', 'specialization', 'archived_at']
    search_fields = ['user_full_name', 'license_number']
    list_filter = ['archived_at', 'was_approved']

@admin.register(ArchivedAppointment)
class ArchivedAppointmentAdmin(admin.ModelAdmin):
    list_display = ['original_appointment_id', 'patient_name', 'doctor_name', 'start_time', 'archived_at']
    search_fields = ['patient_name', 'doctor_name']
    list_filter = ['archived_at', 'status', 'appointment_type']

@admin.register(ArchivedMedicalRecord)
class ArchivedMedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['original_record_id', 'patient_name', 'created_at', 'archived_at']
    search_fields = ['patient_name', 'patient_id_str']
    list_filter = ['archived_at']

@admin.register(DeletedRecord)
class DeletedRecordAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'original_id', 'object_repr', 'deleted_at', 'deleted_by']
    search_fields = ['object_repr', 'model_name', 'original_id']
    list_filter = ['deleted_at', 'model_name']
    readonly_fields = ['deleted_at', 'data_snapshot']