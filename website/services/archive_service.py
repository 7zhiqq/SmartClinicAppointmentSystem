"""
Service layer for archiving and deleting records
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

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

    @staticmethod
    @transaction.atomic
    def archive_appointment(appointment_id, user=None, reason=''):
        """
        Archive a regular appointment
        """
        from website.models import Appointment
        
        appointment = Appointment.objects.select_for_update().get(pk=appointment_id)
        
        # Only archive completed, rejected, or no_show appointments
        if appointment.status not in ['completed', 'rejected', 'no_show']:
            raise ValidationError("Only completed, rejected, or no-show appointments can be archived")
        
        # Create archived record
        archived = ArchivedAppointment.objects.create(
            original_appointment_id=appointment.id,
            appointment_type='self',
            patient_name=appointment.patient.get_full_name(),
            doctor_name=appointment.doctor.user.get_full_name(),
            doctor_specialization=appointment.doctor.specialization.name if appointment.doctor.specialization else None,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            status=appointment.status,
            archived_by=user,
            archive_reason=reason or 'Manual archive',
            additional_data={
                'patient_id': appointment.patient.id,
                'doctor_id': appointment.doctor.id,
                'created_by_id': appointment.created_by.id if appointment.created_by else None
            }
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=user,
            action_type='delete',
            model_name='Appointment',
            object_id=str(appointment.id),
            related_object_repr=str(appointment),
            description=f'Archived appointment (reason: {reason or "Manual archive"})'
        )
        
        # Delete original
        appointment.delete()
        
        return archived
    
    @staticmethod
    @transaction.atomic
    def archive_dependent_appointment(appointment_id, user=None, reason=''):
        """
        Archive a dependent appointment
        """
        from website.models import DependentAppointment
        
        appointment = DependentAppointment.objects.select_for_update().get(pk=appointment_id)
        
        # Only archive completed, rejected, or no_show appointments
        if appointment.status not in ['completed', 'rejected', 'no_show']:
            raise ValidationError("Only completed, rejected, or no-show appointments can be archived")
        
        # Create archived record
        archived = ArchivedAppointment.objects.create(
            original_appointment_id=appointment.id,
            appointment_type='dependent',
            patient_name=appointment.dependent_patient.full_name,
            doctor_name=appointment.doctor.user.get_full_name(),
            doctor_specialization=appointment.doctor.specialization.name if appointment.doctor.specialization else None,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            status=appointment.status,
            archived_by=user,
            archive_reason=reason or 'Manual archive',
            additional_data={
                'dependent_patient_id': appointment.dependent_patient.patient_id,
                'guardian_id': appointment.dependent_patient.guardian.id,
                'doctor_id': appointment.doctor.id,
                'created_by_id': appointment.created_by.id if appointment.created_by else None
            }
        )
        
        # Log activity
        ActivityLog.objects.create(
            user=user,
            action_type='delete',
            model_name='DependentAppointment',
            object_id=str(appointment.id),
            related_object_repr=str(appointment),
            description=f'Archived dependent appointment (reason: {reason or "Manual archive"})'
        )
        
        # Delete original
        appointment.delete()
        
        return archived
    
    @staticmethod
    def bulk_archive_old_appointments(days=90, user=None):
        """
        Auto-archive appointments older than specified days
        Returns count of archived appointments
        """
        from django.db.models import Q
        
        cutoff_date = timezone.now() - timedelta(days=days)
        count = 0
        
        # Archive regular appointments
        old_appointments = Appointment.objects.filter(
            Q(status='completed') | Q(status='rejected') | Q(status='no_show'),
            start_time__lt=cutoff_date
        )
        
        for appointment in old_appointments:
            try:
                ArchiveService.archive_appointment(
                    appointment.id, 
                    user=user, 
                    reason=f'Auto-archived (older than {days} days)'
                )
                count += 1
            except Exception as e:
                print(f"Error archiving appointment {appointment.id}: {e}")
        
        # Archive dependent appointments
        old_dependent = DependentAppointment.objects.filter(
            Q(status='completed') | Q(status='rejected') | Q(status='no_show'),
            start_time__lt=cutoff_date
        )
        
        for appointment in old_dependent:
            try:
                ArchiveService.archive_dependent_appointment(
                    appointment.id,
                    user=user,
                    reason=f'Auto-archived (older than {days} days)'
                )
                count += 1
            except Exception as e:
                print(f"Error archiving dependent appointment {appointment.id}: {e}")
        
        return count
    
    @staticmethod
    @transaction.atomic
    def restore_appointment(archived_id):
        """
        Restore an archived appointment back to active
        Returns the restored appointment
        """
        archived = ArchivedAppointment.objects.get(pk=archived_id)
        
        # Check if it was a regular or dependent appointment
        if archived.appointment_type == 'self':
            # Get patient and doctor from additional_data
            patient_id = archived.additional_data.get('patient_id')
            doctor_id = archived.additional_data.get('doctor_id')
            
            if not patient_id or not doctor_id:
                raise ValidationError("Cannot restore: missing patient or doctor information")
            
            from accounts.models import User
            patient = User.objects.get(pk=patient_id)
            doctor = DoctorInfo.objects.get(pk=doctor_id)
            
            # Restore appointment
            restored = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                start_time=archived.start_time,
                end_time=archived.end_time,
                status=archived.status
            )
            
        else:  # dependent
            dependent_patient_id = archived.additional_data.get('dependent_patient_id')
            doctor_id = archived.additional_data.get('doctor_id')
            
            if not dependent_patient_id or not doctor_id:
                raise ValidationError("Cannot restore: missing patient or doctor information")
            
            dependent = DependentPatient.objects.get(patient_id=dependent_patient_id)
            doctor = DoctorInfo.objects.get(pk=doctor_id)
            
            restored = DependentAppointment.objects.create(
                dependent_patient=dependent,
                doctor=doctor,
                start_time=archived.start_time,
                end_time=archived.end_time,
                status=archived.status
            )
        
        # Delete archived record
        archived.delete()
        
        return restored

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