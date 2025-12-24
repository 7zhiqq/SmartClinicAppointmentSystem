"""
Service layer for archiving and deleting records
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
import json

from website.models import (
    PatientInfo, DependentPatient, Appointment, DependentAppointment,
    MedicalRecord, Prescription, DoctorInfo, ActivityLog
)
from website.archive_models import (
    ArchivedPatientInfo, ArchivedDependentPatient, ArchivedAppointment,
    ArchivedMedicalRecord, ArchivedDoctorInfo, DeletedRecord
)
from accounts.models import Phone


class ArchiveService:
    """Service for archiving records"""
    
    @staticmethod
    @transaction.atomic
    def archive_patient(patient_id, user, reason=""):
        """Archive a patient and all related data"""
        try:
            patient = PatientInfo.objects.get(pk=patient_id)
        except PatientInfo.DoesNotExist:
            raise ValidationError("Patient not found")
        
        # Get phone number
        phone_number = ""
        try:
            phone = Phone.objects.get(user=patient.user)
            phone_number = phone.number
        except Phone.DoesNotExist:
            pass
        
        # Archive patient info
        archived_patient = ArchivedPatientInfo.objects.create(
            original_patient_id=patient.patient_id,
            user_id=patient.user.id,
            user_username=patient.user.username,
            user_email=patient.user.email,
            user_full_name=patient.user.get_full_name(),
            gender=patient.gender,
            birthdate=patient.birthdate,
            age=patient.age,
            blood_type=patient.blood_type or "",
            phone_number=phone_number,
            archived_by=user,
            archive_reason=reason,
            additional_data={
                'vitals_count': patient.vitals.count(),
                'allergies_count': patient.allergies.count(),
                'medications_count': patient.medications.count(),
            }
        )
        
        # Archive related appointments
        appointments = Appointment.objects.filter(patient=patient.user)
        for appt in appointments:
            ArchiveService._archive_appointment(appt, user, reason, 'self')
        
        # Archive related medical records
        medical_records = MedicalRecord.objects.filter(patient=patient)
        for record in medical_records:
            ArchiveService._archive_medical_record(record, user, reason)
        
        # Log activity
        ActivityLog.objects.create(
            user=user,
            action_type='delete',
            model_name='PatientInfo',
            object_id=str(patient.patient_id),
            related_object_repr=str(patient),
            description=f"Archived patient: {reason}"
        )
        
        # Delete the original patient (cascade will handle related records)
        patient.delete()
        
        return archived_patient
    
    @staticmethod
    @transaction.atomic
    def archive_dependent(dependent_id, user, reason=""):
        """Archive a dependent patient and related data"""
        try:
            dependent = DependentPatient.objects.get(pk=dependent_id)
        except DependentPatient.DoesNotExist:
            raise ValidationError("Dependent patient not found")
        
        # Archive dependent info
        archived_dependent = ArchivedDependentPatient.objects.create(
            original_patient_id=dependent.patient_id,
            guardian_id=dependent.guardian.id,
            guardian_username=dependent.guardian.username,
            first_name=dependent.first_name,
            last_name=dependent.last_name,
            gender=dependent.gender,
            phone=dependent.phone or "",
            birthdate=dependent.birthdate,
            age=dependent.age,
            blood_type=dependent.blood_type or "",
            archived_by=user,
            archive_reason=reason,
            additional_data={
                'vitals_count': dependent.vitals.count(),
                'allergies_count': dependent.allergies.count(),
                'medications_count': dependent.medications.count(),
            }
        )
        
        # Archive related appointments
        appointments = DependentAppointment.objects.filter(dependent_patient=dependent)
        for appt in appointments:
            ArchiveService._archive_appointment(appt, user, reason, 'dependent')
        
        # Archive related medical records
        medical_records = MedicalRecord.objects.filter(dependent_patient=dependent)
        for record in medical_records:
            ArchiveService._archive_medical_record(record, user, reason)
        
        # Log activity
        ActivityLog.objects.create(
            user=user,
            action_type='delete',
            model_name='DependentPatient',
            object_id=str(dependent.patient_id),
            related_object_repr=str(dependent),
            description=f"Archived dependent: {reason}"
        )
        
        # Delete the original dependent
        dependent.delete()
        
        return archived_dependent
    
    @staticmethod
    def _archive_appointment(appointment, user, reason, appt_type):
        """Helper to archive an appointment"""
        if appt_type == 'self':
            patient_name = appointment.patient.get_full_name()
        else:
            patient_name = appointment.dependent_patient.full_name
        
        doctor_name = appointment.doctor.user.get_full_name()
        doctor_spec = appointment.doctor.specialization.name if appointment.doctor.specialization else ""
        
        return ArchivedAppointment.objects.create(
            original_appointment_id=appointment.id,
            appointment_type=appt_type,
            patient_name=patient_name,
            doctor_name=doctor_name,
            doctor_specialization=doctor_spec,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            status=appointment.status,
            archived_by=user,
            archive_reason=reason
        )
    
    @staticmethod
    def _archive_medical_record(record, user, reason):
        """Helper to archive a medical record"""
        # Get patient name
        if record.patient:
            patient_name = record.patient.user.get_full_name()
        elif record.dependent_patient:
            patient_name = record.dependent_patient.full_name
        else:
            patient_name = "Unknown"
        
        # Serialize prescriptions
        prescriptions_data = []
        for prescription in record.prescriptions.all():
            prescriptions_data.append({
                'medication_name': prescription.medication_name,
                'dosage': prescription.dosage,
                'frequency': prescription.frequency,
                'notes': prescription.notes or "",
                'prescribed_at': prescription.prescribed_at.isoformat()
            })
        
        return ArchivedMedicalRecord.objects.create(
            original_record_id=record.id,
            patient_id_str=record.patient_id_str,
            patient_name=patient_name,
            reason_for_visit=record.reason_for_visit,
            symptoms=record.symptoms,
            diagnosis=record.diagnosis,
            created_at=record.created_at,
            prescriptions=prescriptions_data,
            archived_by=user,
            archive_reason=reason
        )
    
    @staticmethod
    @transaction.atomic
    def archive_doctor(doctor_id, user, reason=""):
        """Archive a doctor and related data"""
        try:
            doctor = DoctorInfo.objects.get(pk=doctor_id)
        except DoctorInfo.DoesNotExist:
            raise ValidationError("Doctor not found")
        
        # Archive doctor info
        archived_doctor = ArchivedDoctorInfo.objects.create(
            original_doctor_id=doctor.id,
            user_id=doctor.user.id,
            user_username=doctor.user.username,
            user_full_name=doctor.user.get_full_name(),
            user_email=doctor.user.email,
            specialization=doctor.specialization.name if doctor.specialization else "",
            license_number=doctor.license_number,
            years_experience=doctor.years_experience,
            bio=doctor.bio or "",
            qualifications=doctor.qualifications or "",
            was_approved=doctor.is_approved,
            approved_at=doctor.approved_at,
            archived_by=user,
            archive_reason=reason,
            additional_data={
                'availabilities_count': doctor.availabilities.count(),
                'custom_availabilities_count': doctor.custom_availabilities.count(),
            }
        )
        
        # Archive appointments
        self_appointments = Appointment.objects.filter(doctor=doctor)
        for appt in self_appointments:
            ArchiveService._archive_appointment(appt, user, reason, 'self')
        
        dependent_appointments = DependentAppointment.objects.filter(doctor=doctor)
        for appt in dependent_appointments:
            ArchiveService._archive_appointment(appt, user, reason, 'dependent')
        
        # Log activity
        ActivityLog.objects.create(
            user=user,
            action_type='delete',
            model_name='DoctorInfo',
            object_id=str(doctor.id),
            related_object_repr=str(doctor),
            description=f"Archived doctor: {reason}"
        )
        
        # Delete the original doctor
        doctor.delete()
        
        return archived_doctor


class DeleteService:
    """Service for permanent deletion with audit trail"""
    
    @staticmethod
    @transaction.atomic
    def delete_with_audit(model_instance, user, reason=""):
        """Delete a record and create audit trail"""
        model_name = model_instance.__class__.__name__
        original_id = str(model_instance.pk)
        object_repr = str(model_instance)
        
        # Create snapshot
        snapshot = {}
        for field in model_instance._meta.fields:
            field_name = field.name
            field_value = getattr(model_instance, field_name)
            
            # Convert to JSON-serializable format
            if hasattr(field_value, 'isoformat'):
                snapshot[field_name] = field_value.isoformat()
            elif isinstance(field_value, (str, int, float, bool, type(None))):
                snapshot[field_name] = field_value
            else:
                snapshot[field_name] = str(field_value)
        
        # Create deleted record
        deleted_record = DeletedRecord.objects.create(
            model_name=model_name,
            original_id=original_id,
            object_repr=object_repr,
            deleted_by=user,
            deletion_reason=reason,
            data_snapshot=snapshot
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=user,
            action_type='delete',
            model_name=model_name,
            object_id=original_id,
            related_object_repr=object_repr,
            description=f"Permanently deleted: {reason}"
        )
        
        # Delete the instance
        model_instance.delete()
        
        return deleted_record