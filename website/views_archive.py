from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Q

from website.models import PatientInfo, DependentPatient, DoctorInfo, Appointment, DependentAppointment
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