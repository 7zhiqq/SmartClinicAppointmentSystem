from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from accounts.models import User, Phone

from website.models import (PatientInfo,
    DependentPatient,
    DoctorInfo,
    Appointment,
    DependentAppointment,
    MedicalRecord,
    ActivityLog,
    Prescription,
    PatientAllergy,
    DependentPatientAllergy,
    DependentPatientMedication,
    PatientMedication,
    PatientVitals,
    DependentPatientVitals
)
from website.archive_models import (
    ArchivedPatientInfo, ArchivedDependentPatient, ArchivedDoctorInfo,
    ArchivedAppointment, ArchivedMedicalRecord, DeletedRecord
)
from website.services.archive_service import ArchiveService, DeleteService


# ==================== PATIENT ARCHIVE/DELETE ====================

@login_required
def archive_patient(request, pk):
    """Archive a patient (staff only)"""
    if request.user.role != 'staff':
        messages.error(request, "Access denied.")
        return redirect('home')
    
    patient = get_object_or_404(PatientInfo, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        try:
            ArchiveService.archive_patient(pk, request.user, reason)
            messages.success(request, f"Patient {patient.user.get_full_name()} has been archived successfully.")
            return redirect('patient_list')
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error archiving patient: {str(e)}")
    
    return render(request, 'archive/confirm_archive_patient.html', {
        'patient': patient,
        'patient_type': 'self'
    })


@login_required
def archive_dependent(request, pk):
    """Archive a dependent patient"""
    if request.user.role not in ['patient', 'staff']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Patients can only archive their own dependents
    if request.user.role == 'patient':
        dependent = get_object_or_404(DependentPatient, pk=pk, guardian=request.user)
    else:
        dependent = get_object_or_404(DependentPatient, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        try:
            ArchiveService.archive_dependent(pk, request.user, reason)
            messages.success(request, f"Dependent {dependent.full_name} has been archived successfully.")
            
            if request.user.role == 'patient':
                return redirect('medical_records')
            else:
                return redirect('patient_list')
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error archiving dependent: {str(e)}")
    
    return render(request, 'archive/confirm_archive_patient.html', {
        'patient': dependent,
        'patient_type': 'dependent'
    })


@login_required
def delete_patient(request, pk):
    """Permanently delete a patient (staff only)"""
    if request.user.role != 'staff':
        messages.error(request, "Access denied.")
        return redirect('home')
    
    patient = get_object_or_404(PatientInfo, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        patient_name = patient.user.get_full_name()
        
        try:
            DeleteService.delete_with_audit(patient, request.user, reason)
            messages.success(request, f"Patient {patient_name} has been permanently deleted.")
            return redirect('patient_list')
        except Exception as e:
            messages.error(request, f"Error deleting patient: {str(e)}")
    
    return render(request, 'archive/confirm_delete_patient.html', {
        'patient': patient,
        'patient_type': 'self'
    })


# ==================== DOCTOR ARCHIVE/DELETE ====================

@login_required
def archive_doctor(request, doctor_id):
    """Archive a doctor (manager only)"""
    if request.user.role != 'manager':
        messages.error(request, "Access denied.")
        return redirect('home')
    
    doctor = get_object_or_404(DoctorInfo, id=doctor_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        try:
            ArchiveService.archive_doctor(doctor_id, request.user, reason)
            messages.success(request, f"Doctor {doctor.user.get_full_name()} has been archived successfully.")
            return redirect('manager_users')
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error archiving doctor: {str(e)}")
    
    return render(request, 'archive/confirm_archive_doctor.html', {
        'doctor': doctor
    })


# ==================== APPOINTMENT DELETE ====================

@login_required
def delete_appointment(request, pk):
    """Permanently delete an appointment"""
    if request.user.role not in ['staff', 'doctor']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Try to find as regular or dependent appointment
    appointment = None
    is_dependent = False
    
    try:
        appointment = Appointment.objects.get(pk=pk)
    except Appointment.DoesNotExist:
        try:
            appointment = DependentAppointment.objects.get(pk=pk)
            is_dependent = True
        except DependentAppointment.DoesNotExist:
            messages.error(request, "Appointment not found.")
            return redirect('appointments')
    
    # Verify permissions
    if request.user.role == 'doctor':
        if not is_dependent and appointment.doctor != request.user.doctor_info:
            messages.error(request, "Access denied.")
            return redirect('doctor_appointments')
        elif is_dependent and appointment.doctor != request.user.doctor_info:
            messages.error(request, "Access denied.")
            return redirect('doctor_appointments')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        try:
            DeleteService.delete_with_audit(appointment, request.user, reason)
            messages.success(request, "Appointment has been permanently deleted.")
            
            if request.user.role == 'staff':
                return redirect('appointments')
            else:
                return redirect('doctor_appointments')
        except Exception as e:
            messages.error(request, f"Error deleting appointment: {str(e)}")
    
    return render(request, 'archive/confirm_delete_appointment.html', {
        'appointment': appointment,
        'is_dependent': is_dependent
    })


# ==================== ARCHIVE LISTS ====================

@login_required
def archived_patients_list(request):
    """View archived patients (staff only)"""
    if request.user.role != 'staff':
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Get archived self patients
    archived_self = ArchivedPatientInfo.objects.all()
    
    # Get archived dependents
    archived_dependents = ArchivedDependentPatient.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        archived_self = archived_self.filter(
            Q(user_full_name__icontains=search_query) |
            Q(original_patient_id__icontains=search_query) |
            Q(user_email__icontains=search_query)
        )
        archived_dependents = archived_dependents.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(original_patient_id__icontains=search_query)
        )
    
    # Combine and sort by archived_at (most recent first)
    all_patients = []
    
    # Add self patients with type marker
    for patient in archived_self:
        patient.patient_type = 'self'
        all_patients.append(patient)
    
    # Add dependent patients with type marker
    for patient in archived_dependents:
        patient.patient_type = 'dependent'
        all_patients.append(patient)
    
    # Sort by archived_at descending
    all_patients.sort(key=lambda x: x.archived_at, reverse=True)
    
    return render(request, 'archive/archived_patients.html', {
        'archived_self': archived_self,
        'archived_dependents': archived_dependents,
        'all_patients': all_patients,
        'search_query': search_query
    })


@login_required
def archived_doctors_list(request):
    """View archived doctors (manager only)"""
    if request.user.role != 'manager':
        messages.error(request, "Access denied.")
        return redirect('home')
    
    archived_doctors = ArchivedDoctorInfo.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        archived_doctors = archived_doctors.filter(
            Q(user_full_name__icontains=search_query) |
            Q(user_email__icontains=search_query) |
            Q(license_number__icontains=search_query)
        )
    
    return render(request, 'archive/archived_doctors.html', {
        'archived_doctors': archived_doctors,
        'search_query': search_query
    })


@login_required
def archived_appointments_list(request):
    """View archived appointments"""
    if request.user.role not in ['staff', 'doctor']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    archived_appointments = ArchivedAppointment.objects.all()
    
    # Filter by doctor if doctor role
    if request.user.role == 'doctor':
        doctor_name = request.user.get_full_name()
        archived_appointments = archived_appointments.filter(doctor_name__icontains=doctor_name)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        archived_appointments = archived_appointments.filter(
            Q(patient_name__icontains=search_query) |
            Q(doctor_name__icontains=search_query)
        )
    
    return render(request, 'archive/archived_appointments.html', {
        'archived_appointments': archived_appointments,
        'search_query': search_query
    })


@login_required
def deleted_records_list(request):
    """View deleted records audit log (manager/staff only)"""
    if request.user.role not in ['manager', 'staff']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    deleted_records = DeletedRecord.objects.all()
    
    # Filter by model type
    model_filter = request.GET.get('model', '').strip()
    if model_filter:
        deleted_records = deleted_records.filter(model_name=model_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        deleted_records = deleted_records.filter(
            Q(object_repr__icontains=search_query) |
            Q(deletion_reason__icontains=search_query)
        )
    
    # Get unique model names for filter
    model_names = DeletedRecord.objects.values_list('model_name', flat=True).distinct()
    
    return render(request, 'archive/deleted_records.html', {
        'deleted_records': deleted_records,
        'model_names': model_names,
        'search_query': search_query,
        'model_filter': model_filter
    })


# ==================== AJAX VIEWS ====================

@login_required
def archived_patient_details_ajax(request, pk):
    """AJAX view to fetch archived patient details"""
    if request.user.role != 'staff':
        return JsonResponse({'html': '<p class="muted">Access denied.</p>'})
    
    try:
        # Get patient type from query parameter
        patient_type = request.GET.get('type', 'self')
        patient = None
        
        if patient_type == 'self':
            patient = ArchivedPatientInfo.objects.filter(pk=pk).first()
        else:
            patient = ArchivedDependentPatient.objects.filter(pk=pk).first()
        
        if not patient:
            return JsonResponse({'html': '<p class="muted">Patient not found.</p>'})
        
        from django.template.loader import render_to_string
        html = render_to_string(
            'archive/partials/archived_patient_details.html',
            {
                'patient': patient,
                'patient_type': patient_type
            },
            request=request
        )
        
        return JsonResponse({'html': html})
    
    except Exception as e:
        return JsonResponse({'html': f'<p class="muted">Error: {str(e)}</p>'})
    
# ==================== APPOINTMENT ARCHIVE ====================

@login_required
def archive_appointment_view(request, pk):
    """Archive a regular appointment"""
    if request.user.role not in ['staff', 'manager']:
        messages.error(request, "Access denied")
        return redirect('home')
    
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # Check if appointment can be archived
    if appointment.status not in ['completed', 'rejected', 'no_show']:
        messages.error(request, "Only completed, rejected, or no-show appointments can be archived")
        return redirect('appointments')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        try:
            ArchiveService.archive_appointment(pk, request.user, reason)
            messages.success(request, f"Appointment archived successfully")
            return redirect('appointments')
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error archiving appointment: {str(e)}")
    
    return render(request, 'archive/confirm_archive_appointment.html', {
        'appointment': appointment,
        'is_dependent': False
    })


@login_required
def archive_dependent_appointment_view(request, pk):
    """Archive a dependent appointment"""
    if request.user.role not in ['staff', 'manager']:
        messages.error(request, "Access denied")
        return redirect('home')
    
    appointment = get_object_or_404(DependentAppointment, pk=pk)
    
    # Check if appointment can be archived
    if appointment.status not in ['completed', 'rejected', 'no_show']:
        messages.error(request, "Only completed, rejected, or no-show appointments can be archived")
        return redirect('appointments')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        try:
            ArchiveService.archive_dependent_appointment(pk, request.user, reason)
            messages.success(request, f"Appointment archived successfully")
            return redirect('appointments')
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error archiving appointment: {str(e)}")
    
    return render(request, 'archive/confirm_archive_appointment.html', {
        'appointment': appointment,
        'is_dependent': True
    })


@login_required
def bulk_archive_appointments(request):
    """Bulk archive old appointments"""
    if request.user.role not in ['staff', 'manager']:
        messages.error(request, "Access denied")
        return redirect('home')
    
    if request.method == 'POST':
        days = int(request.POST.get('days', 90))
        
        try:
            count = ArchiveService.bulk_archive_old_appointments(days, request.user)
            messages.success(request, f"Successfully archived {count} appointments older than {days} days")
            return redirect('appointments')
        except Exception as e:
            messages.error(request, f"Error during bulk archive: {str(e)}")
    
    return render(request, 'archive/bulk_archive_appointments.html')


@login_required
def restore_archived_appointment(request, pk):
    """Restore an archived appointment"""
    if request.user.role not in ['staff', 'manager']:
        messages.error(request, "Access denied")
        return redirect('home')
    
    if request.method == 'POST':
        try:
            restored = ArchiveService.restore_appointment(pk)
            messages.success(request, "Appointment restored successfully")
            return redirect('archived_appointments')
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error restoring appointment: {str(e)}")
        
        return redirect('archived_appointments')
    
    # GET request - show confirmation
    from website.archive_models import ArchivedAppointment
    archived = get_object_or_404(ArchivedAppointment, pk=pk)
    
    return render(request, 'archive/confirm_restore_appointment.html', {
        'archived': archived
    })


# ==================== UPDATE YOUR archived_appointments_list VIEW ====================

@login_required
def archived_appointments_list(request):
    """View archived appointments - UPDATED"""
    from website.archive_models import ArchivedAppointment
    
    # Permission check
    if request.user.role == 'patient':
        # Patients see their own archived appointments
        patient_name = request.user.get_full_name()
        archived_appointments = ArchivedAppointment.objects.filter(
            patient_name__icontains=patient_name
        )
    elif request.user.role == 'doctor':
        # Doctors see their archived appointments
        doctor_name = request.user.get_full_name()
        archived_appointments = ArchivedAppointment.objects.filter(
            doctor_name__icontains=doctor_name
        )
    elif request.user.role in ['staff', 'manager']:
        # Staff/Manager see all archived appointments
        archived_appointments = ArchivedAppointment.objects.all()
    else:
        messages.error(request, "Access denied")
        return redirect('home')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        from django.db.models import Q
        archived_appointments = archived_appointments.filter(
            Q(patient_name__icontains=search_query) |
            Q(doctor_name__icontains=search_query) |
            Q(doctor_specialization__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        archived_appointments = archived_appointments.filter(status=status_filter)
    
    # Filter by appointment type
    type_filter = request.GET.get('type', '').strip()
    if type_filter:
        archived_appointments = archived_appointments.filter(appointment_type=type_filter)
    
    return render(request, 'archive/archived_appointments.html', {
        'archived_appointments': archived_appointments,
        'search_query': search_query,
        'status_filter': status_filter,
        'type_filter': type_filter
    })


@login_required
def deleted_record_snapshot_ajax(request, pk):
    """AJAX view to fetch deleted record snapshot data"""
    if request.user.role not in ['staff', 'manager']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        record = DeletedRecord.objects.get(pk=pk)
        
        # Format the deleted_at datetime
        deleted_at_formatted = record.deleted_at.strftime("%B %d, %Y at %I:%M %p")
        
        # Get deleted_by name
        deleted_by_name = record.deleted_by.get_full_name() if record.deleted_by else "System"
        
        # Prepare response data
        data = {
            'model_name': record.model_name,
            'original_id': record.original_id,
            'object_repr': record.object_repr,
            'deleted_at': deleted_at_formatted,
            'deleted_by': deleted_by_name,
            'deletion_reason': record.deletion_reason or '',
            'data_snapshot': record.data_snapshot if record.data_snapshot else {}
        }
        
        return JsonResponse(data)
    
    except DeletedRecord.DoesNotExist:
        return JsonResponse({'error': 'Record not found'}, status=404)
    
    except Exception as e:
        return JsonResponse({'error': f'Error loading data: {str(e)}'}, status=500)
    
@login_required
def deleted_doctor_details(request, pk):
    """View detailed information about a deleted/archived doctor"""
    if request.user.role not in ['manager', 'staff']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Try to get archived doctor
    archived_doctor = get_object_or_404(ArchivedDoctorInfo, pk=pk)
    
    # Parse additional_data for extra information
    additional_data = archived_doctor.additional_data or {}
    
    context = {
        'doctor': archived_doctor,
        'additional_data': additional_data,
    }
    
    return render(request, 'archive/deleted_doctor_details.html', context)


@login_required
def archived_doctor_details_ajax(request, pk):
    """AJAX view to fetch archived doctor details"""
    if request.user.role not in ['manager', 'staff']:
        return JsonResponse({'html': '<p class="muted">Access denied.</p>'})
    
    try:
        doctor = ArchivedDoctorInfo.objects.get(pk=pk)
        
        from django.template.loader import render_to_string
        html = render_to_string(
            'archive/partials/archived_doctor_details.html',
            {'doctor': doctor},
            request=request
        )
        
        return JsonResponse({'html': html})
    
    except ArchivedDoctorInfo.DoesNotExist:
        return JsonResponse({'html': '<p class="muted">Doctor not found.</p>'})
    
    except Exception as e:
        return JsonResponse({'html': f'<p class="muted">Error: {str(e)}</p>'})
    

@login_required
def archived_patient_detailed_records(request, pk, patient_type='self'):
    """View detailed records for an archived patient"""
    if request.user.role != 'staff':
        messages.error(request, "Access denied.")
        return redirect('home')
    
    try:
        # Get the archived patient
        if patient_type == 'self':
            patient = ArchivedPatientInfo.objects.get(pk=pk)
            patient.patient_type = 'self'
        else:
            patient = ArchivedDependentPatient.objects.get(pk=pk)
            patient.patient_type = 'dependent'
        
        # Get archived medical records
        medical_records = ArchivedMedicalRecord.objects.filter(
            patient_id_str=patient.original_patient_id
        ).order_by('-created_at')
        
        # Get archived appointments
        appointments = ArchivedAppointment.objects.filter(
            patient_name=patient.user_full_name if patient_type == 'self' else f"{patient.first_name} {patient.last_name}"
        ).order_by('-start_time')
        
        # Parse additional data
        additional_data = patient.additional_data or {}
        
        # Get counts
        vitals_count = additional_data.get('vitals_count', 0)
        allergies_count = additional_data.get('allergies_count', 0)
        medications_count = additional_data.get('medications_count', 0)
        medical_records_count = medical_records.count()
        appointments_count = appointments.count()
        
        # Extract latest vitals
        latest_vitals = None
        if additional_data.get('latest_vitals'):
            class LatestVitals:
                pass
            vitals_data = additional_data['latest_vitals']
            latest_vitals = LatestVitals()
            latest_vitals.blood_pressure = vitals_data.get('blood_pressure', 'N/A')
            latest_vitals.heart_rate = vitals_data.get('heart_rate', 'N/A')
            latest_vitals.height_cm = vitals_data.get('height_cm', 'N/A')
            latest_vitals.weight_kg = vitals_data.get('weight_kg', 'N/A')
            latest_vitals.recorded_at = vitals_data.get('recorded_at', '')
        
        # Extract allergies
        allergies = []
        if additional_data.get('allergies'):
            for allergy_data in additional_data['allergies']:
                class Allergy:
                    pass
                allergy = Allergy()
                allergy.allergy_name = allergy_data.get('allergy_name', 'Unknown')
                allergies.append(allergy)
        
        # Extract medications
        medications = []
        if additional_data.get('medications'):
            for med_data in additional_data['medications']:
                class Medication:
                    pass
                medication = Medication()
                medication.medication_name = med_data.get('medication_name', 'Unknown')
                medication.dosage = med_data.get('dosage', 'N/A')
                medication.frequency = med_data.get('frequency', 'N/A')
                medication.prescribed_at = med_data.get('prescribed_at', '')
                medications.append(medication)
        
        context = {
            'patient': patient,
            'medical_records': medical_records,
            'appointments': appointments,
            'allergies': allergies,
            'medications': medications,
            'latest_vitals': latest_vitals,
            'vitals_count': vitals_count,
            'allergies_count': allergies_count,
            'medications_count': medications_count,
            'medical_records_count': medical_records_count,
            'appointments_count': appointments_count,
        }
        
        return render(request, 'archive/archived_patient_records.html', context)
    
    except (ArchivedPatientInfo.DoesNotExist, ArchivedDependentPatient.DoesNotExist):
        messages.error(request, "Archived patient not found.")
        return redirect('archived_patients')
    
    except Exception as e:
        print(f"Error in archived_patient_detailed_records: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error loading patient records: {str(e)}")
        return redirect('archived_patients')
    

@login_required
def confirm_restore_patient(request, pk, patient_type='self'):
    """Show confirmation page for restoring an archived patient"""
    if request.user.role != 'staff':
        messages.error(request, "Access denied.")
        return redirect('home')
    
    try:
        if patient_type == 'self':
            patient = ArchivedPatientInfo.objects.get(pk=pk)
        else:
            patient = ArchivedDependentPatient.objects.get(pk=pk)
        
        # Count related archived records
        if patient_type == 'self':
            medical_records_count = ArchivedMedicalRecord.objects.filter(
                patient_id_str=patient.original_patient_id
            ).count()
        else:
            medical_records_count = ArchivedMedicalRecord.objects.filter(
                patient_id_str=patient.original_patient_id
            ).count()
        
        appointments_count = ArchivedAppointment.objects.filter(
            patient_name=patient.user_full_name if patient_type == 'self' else f"{patient.first_name} {patient.last_name}"
        ).count()
        
        additional_data = patient.additional_data or {}
        vitals_count = additional_data.get('vitals_count', 0)
        allergies_count = additional_data.get('allergies_count', 0)
        medications_count = additional_data.get('medications_count', 0)
        
        context = {
            'patient': patient,
            'patient_type': patient_type,
            'medical_records_count': medical_records_count,
            'appointments_count': appointments_count,
            'vitals_count': vitals_count,
            'allergies_count': allergies_count,
            'medications_count': medications_count,
        }
        
        return render(request, 'archive/confirm_restore_patient.html', context)
    
    except (ArchivedPatientInfo.DoesNotExist, ArchivedDependentPatient.DoesNotExist):
        messages.error(request, "Archived patient not found.")
        return redirect('archived_patients')
    
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('archived_patients')


@login_required
def restore_patient(request, pk, patient_type='self'):
    """Restore an archived patient and optionally their records"""
    if request.user.role != 'staff':
        messages.error(request, "Access denied.")
        return redirect('home')
    
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('archived_patients')
    
    try:
        restore_records = request.POST.get('restore_records', 'on') == 'on'
        
        if patient_type == 'self':
            archived_patient = ArchivedPatientInfo.objects.get(pk=pk)
            
            # Get or create user (user should still exist)
            try:
                user = User.objects.get(id=archived_patient.user_id)
            except User.DoesNotExist:
                messages.error(request, "Cannot restore: Original user account no longer exists.")
                return redirect('archived_patients')
            
            # Restore PatientInfo
            restored_patient = PatientInfo.objects.create(
                patient_id=archived_patient.original_patient_id,
                user=user,
                gender=archived_patient.gender,
                birthdate=archived_patient.birthdate,
                age=archived_patient.age,
                blood_type=archived_patient.blood_type or None,
            )
            
            # Restore phone if available
            if archived_patient.phone_number:
                Phone.objects.update_or_create(
                    user=user,
                    defaults={'number': archived_patient.phone_number}
                )
            
            patient_name = user.get_full_name()
            
        else:  # dependent
            archived_patient = ArchivedDependentPatient.objects.get(pk=pk)
            
            # Get guardian
            try:
                guardian = User.objects.get(id=archived_patient.guardian_id)
            except User.DoesNotExist:
                messages.error(request, "Cannot restore: Guardian account no longer exists.")
                return redirect('archived_patients')
            
            # Restore DependentPatient
            restored_patient = DependentPatient.objects.create(
                patient_id=archived_patient.original_patient_id,
                guardian=guardian,
                first_name=archived_patient.first_name,
                last_name=archived_patient.last_name,
                gender=archived_patient.gender,
                phone=archived_patient.phone or None,
                birthdate=archived_patient.birthdate,
                age=archived_patient.age,
                blood_type=archived_patient.blood_type or None,
            )
            
            patient_name = f"{archived_patient.first_name} {archived_patient.last_name}"
        
        # Restore related records if option is checked
        if restore_records:
            # Restore medical records
            archived_medical_records = ArchivedMedicalRecord.objects.filter(
                patient_id_str=archived_patient.original_patient_id
            )
            
            for archived_record in archived_medical_records:
                # Restore medical record
                if patient_type == 'self':
                    medical_record = MedicalRecord.objects.create(
                        patient=restored_patient,
                        patient_id_str=archived_record.patient_id_str,
                        reason_for_visit=archived_record.reason_for_visit,
                        symptoms=archived_record.symptoms,
                        diagnosis=archived_record.diagnosis,
                        created_at=archived_record.created_at,
                    )
                else:
                    medical_record = MedicalRecord.objects.create(
                        dependent_patient=restored_patient,
                        patient_id_str=archived_record.patient_id_str,
                        reason_for_visit=archived_record.reason_for_visit,
                        symptoms=archived_record.symptoms,
                        diagnosis=archived_record.diagnosis,
                        created_at=archived_record.created_at,
                    )
                
                # Restore prescriptions for this record
                if archived_record.prescriptions:
                    for prescription_data in archived_record.prescriptions:
                        Prescription.objects.create(
                            medical_record=medical_record,
                            medication_name=prescription_data.get('medication_name', ''),
                            dosage=prescription_data.get('dosage', ''),
                            frequency=prescription_data.get('frequency', ''),
                            notes=prescription_data.get('notes', ''),
                            prescribed_at=prescription_data.get('prescribed_at', timezone.now()),
                        )
            
            # Restore appointments
            archived_appointments = ArchivedAppointment.objects.filter(
                patient_name=patient_name
            )
            
            for archived_appt in archived_appointments:
                if patient_type == 'self':
                    Appointment.objects.create(
                        patient=restored_patient.user,
                        doctor_id=archived_appt.additional_data.get('doctor_id'),
                        start_time=archived_appt.start_time,
                        end_time=archived_appt.end_time,
                        status=archived_appt.status,
                    )
                else:
                    DependentAppointment.objects.create(
                        dependent_patient=restored_patient,
                        doctor_id=archived_appt.additional_data.get('doctor_id'),
                        start_time=archived_appt.start_time,
                        end_time=archived_appt.end_time,
                        status=archived_appt.status,
                    )
        
        # Restore medications and allergies from additional_data
        additional_data = archived_patient.additional_data or {}
        
        # Restore allergies
        if additional_data.get('allergies'):
            for allergy_data in additional_data['allergies']:
                if patient_type == 'self':
                    PatientAllergy.objects.create(
                        patient=restored_patient,
                        allergy_name=allergy_data.get('allergy_name', ''),
                    )
                else:
                    DependentPatientAllergy.objects.create(
                        dependent_patient=restored_patient,
                        allergy_name=allergy_data.get('allergy_name', ''),
                    )
        
        # Restore medications
        if additional_data.get('medications'):
            for med_data in additional_data['medications']:
                prescribed_at = med_data.get('prescribed_at', '')
                try:
                    # Parse ISO format datetime string
                    if prescribed_at:
                        from dateutil import parser
                        prescribed_at = parser.isoparse(prescribed_at)
                    else:
                        prescribed_at = timezone.now()
                except:
                    prescribed_at = timezone.now()
                
                if patient_type == 'self':
                    PatientMedication.objects.create(
                        patient=restored_patient,
                        medication_name=med_data.get('medication_name', ''),
                        dosage=med_data.get('dosage', ''),
                        frequency=med_data.get('frequency', ''),
                        prescribed_at=prescribed_at,
                    )
                else:
                    DependentPatientMedication.objects.create(
                        dependent_patient=restored_patient,
                        medication_name=med_data.get('medication_name', ''),
                        dosage=med_data.get('dosage', ''),
                        frequency=med_data.get('frequency', ''),
                        prescribed_at=prescribed_at,
                    )
        
        # Restore vitals
        if additional_data.get('latest_vitals') and restore_records:
            vitals_data = additional_data['latest_vitals']
            try:
                recorded_at = vitals_data.get('recorded_at', '')
                if recorded_at:
                    from dateutil import parser
                    recorded_at = parser.isoparse(recorded_at)
                else:
                    recorded_at = timezone.now()
            except:
                recorded_at = timezone.now()
            
            if patient_type == 'self':
                PatientVitals.objects.create(
                    patient=restored_patient,
                    height_cm=vitals_data.get('height_cm'),
                    weight_kg=vitals_data.get('weight_kg'),
                    blood_pressure=vitals_data.get('blood_pressure'),
                    heart_rate=vitals_data.get('heart_rate'),
                    recorded_at=recorded_at,
                )
            else:
                DependentPatientVitals.objects.create(
                    dependent_patient=restored_patient,
                    height_cm=vitals_data.get('height_cm'),
                    weight_kg=vitals_data.get('weight_kg'),
                    blood_pressure=vitals_data.get('blood_pressure'),
                    heart_rate=vitals_data.get('heart_rate'),
                    recorded_at=recorded_at,
                )
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='create',
            model_name=f"{'PatientInfo' if patient_type == 'self' else 'DependentPatient'} (Restored)",
            object_id=str(restored_patient.patient_id if hasattr(restored_patient, 'patient_id') else restored_patient.pk),
            related_object_repr=str(restored_patient),
            description=f"Restored archived {'patient' if patient_type == 'self' else 'dependent'}"
        )
        
        # Delete archived records
        archived_patient.delete()
        
        messages.success(
            request, 
            f"{'Patient' if patient_type == 'self' else 'Dependent'} {patient_name} has been restored successfully."
        )
        
        return redirect('patient_list')
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error restoring patient: {str(e)}")
        return redirect('archived_patients')