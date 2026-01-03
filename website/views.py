from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponse
from django.template.loader import render_to_string
from datetime import datetime, timedelta, date
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from calendar import monthrange
from django.db import transaction
from django.db.models import Q, Avg, Count
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt
from django import forms
from itertools import chain
from django.core.exceptions import ValidationError
from website.services.appointment_recommender import get_appointment_recommendations
from website.services.export_service import ReportExporter

from accounts.models import Phone, User

from .models import (
    PatientInfo,
    DependentPatient,
    DoctorInfo,
    Appointment,
    DependentAppointment,
    DoctorAvailability,
    CompletedAppointment,
    CustomDoctorAvailability,
    MedicalRecord,
    DoctorRating,
    ActivityLog,
    PatientVitals,
    DependentPatientVitals,
    PatientAllergy,
    DependentPatientAllergy,
    PatientMedication,
    DependentPatientMedication,
    Specialization
)

from .forms import (
    PatientInfoForm,
    UserBasicInfoForm,
    DependentPatientForm,
    PatientVitalsForm,
    PatientAllergyForm,
    PatientMedicationForm,
    DependentPatientVitalsForm,
    DependentPatientAllergyForm,
    DependentPatientMedicationForm,
    DoctorInfoForm,
    SpecializationForm,
    AppointmentForm,
    DoctorAvailabilityForm,
    CustomDoctorAvailabilityForm,
    MedicalRecordForm,
    PrescriptionForm,
    PrescriptionFormSet,
    GeneralSettingsForm,
    SecuritySettingsForm,
    DoctorRatingForm
)

def home(request):

    # LOGIN HANDLING
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            if user.role == "manager":
                return redirect("manager_dashboard")
            return redirect("home")

        messages.error(request, "Invalid username or password.")

    context = {}

    # AUTHENTICATED USERS
    if request.user.is_authenticated:
        user = request.user
        
        # DOCTOR DASHBOARD CONTEXT
        if user.role == "doctor":
            doctor_info = getattr(user, "doctor_info", None)
            context["doctor_info"] = doctor_info

            if doctor_info and doctor_info.is_approved:
                today = timezone.localdate()

                # -------------------------
                # Today's Appointments (BOTH self and dependent)
                # -------------------------
                today_self = Appointment.objects.filter(
                    doctor=doctor_info,
                    start_time__date=today
                ).select_related("patient")

                today_dependent = DependentAppointment.objects.filter(
                    doctor=doctor_info,
                    start_time__date=today
                ).select_related("dependent_patient")

                # Add appointment_type attribute for template usage
                for appt in today_self:
                    appt.appointment_type = "self"
                
                for appt in today_dependent:
                    appt.appointment_type = "dependent"

                today_appointments = sorted(
                    list(today_self) + list(today_dependent),
                    key=lambda x: x.start_time
                )

                context["today_appointments"] = today_appointments
                context["today_appointments_count"] = len(today_appointments)

                # -------------------------
                # Pending Appointments (BOTH self and dependent)
                # -------------------------
                pending_self = Appointment.objects.filter(
                    doctor=doctor_info,
                    status="pending"
                ).select_related("patient")

                pending_dependent = DependentAppointment.objects.filter(
                    doctor=doctor_info,
                    status="pending"
                ).select_related("dependent_patient")

                # Add appointment_type attribute
                for appt in pending_self:
                    appt.appointment_type = "self"
                
                for appt in pending_dependent:
                    appt.appointment_type = "dependent"

                pending_list = sorted(
                    list(pending_self) + list(pending_dependent),
                    key=lambda x: x.start_time
                )

                # Always set both values in context (even if empty list)
                context["pending_appointments_list"] = pending_list
                context["pending_appointments"] = len(pending_list)

                # -------------------------
                # Weekly Schedule Summary
                # -------------------------
                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                schedule_summary = []
                
                for weekday in range(7):
                    availability = doctor_info.availabilities.filter(weekday=weekday).first()
                    schedule_summary.append({
                        'day': day_names[weekday],
                        'available': availability is not None,
                        'start_time': availability.start_time.strftime('%I:%M %p') if availability else None,
                        'end_time': availability.end_time.strftime('%I:%M %p') if availability else None,
                    })
                
                context["schedule_summary"] = schedule_summary

                # -------------------------
                # Total Appointments
                # -------------------------
                context["total_appointments"] = (
                    Appointment.objects.filter(doctor=doctor_info).count()
                    + DependentAppointment.objects.filter(doctor=doctor_info).count()
                )

                # -------------------------
                # Completed This Month
                # -------------------------
                context["completed_appointments"] = (
                    Appointment.objects.filter(
                        doctor=doctor_info,
                        status="completed",
                        start_time__month=today.month,
                        start_time__year=today.year,
                    ).count()
                    + DependentAppointment.objects.filter(
                        doctor=doctor_info,
                        status="completed",
                        start_time__month=today.month,
                        start_time__year=today.year,
                    ).count()
                )

                # -------------------------
                # Total Unique Patients
                # -------------------------
                self_patients = Appointment.objects.filter(
                    doctor=doctor_info
                ).values_list("patient", flat=True).distinct()

                dependent_patients = DependentAppointment.objects.filter(
                    doctor=doctor_info
                ).values_list("dependent_patient", flat=True).distinct()

                context["total_patients"] = len(set(self_patients)) + len(set(dependent_patients))

                # -------------------------
                # Ratings
                # -------------------------
                rating_stats = DoctorRating.objects.filter(
                    doctor=doctor_info
                ).aggregate(
                    avg=Avg("rating"),
                    count=Count("id")
                )

                context["average_rating"] = (
                    round(rating_stats["avg"], 1)
                    if rating_stats["avg"] else "N/A"
                )
                context["total_ratings"] = rating_stats["count"]

                context["recent_reviews"] = DoctorRating.objects.filter(
                    doctor=doctor_info
                ).select_related("patient__user").order_by("-created_at")[:5]

        
        # PATIENT DASHBOARD CONTEXT 
        elif user.role == "patient":
            try:
                patient = PatientInfo.objects.get(user=user)
                context["patient"] = patient
                context["latest_vitals"] = patient.vitals.order_by("-recorded_at").first()
            except PatientInfo.DoesNotExist:
                context["patient"] = None
                context["latest_vitals"] = None

            dependents = DependentPatient.objects.filter(guardian=user)
            context["dependents_count"] = dependents.count()

            upcoming_self = Appointment.objects.filter(
                patient=user,
                start_time__gte=timezone.now(),
                status__in=["pending", "approved"],
            )

            upcoming_dependent = DependentAppointment.objects.filter(
                dependent_patient__in=dependents,
                start_time__gte=timezone.now(),
                status__in=["pending", "approved"],
            )

            upcoming = sorted(
                list(upcoming_self) + list(upcoming_dependent),
                key=lambda x: x.start_time,
            )

            context["upcoming_appointments"] = upcoming[:5]
            context["upcoming_appointments_count"] = len(upcoming)

            active_medications = patient.medications.count() if context["patient"] else 0
            for dep in dependents:
                active_medications += dep.medications.count()

            context["active_medications_count"] = active_medications

            medical_records = 0
            if context["patient"]:
                medical_records += MedicalRecord.objects.filter(patient=context["patient"]).count()
            for dep in dependents:
                medical_records += MedicalRecord.objects.filter(dependent_patient=dep).count()

            context["medical_records_count"] = medical_records

        # STAFF DASHBOARD CONTEXT
        elif user.role == "staff":
            today = timezone.localdate()
            
            # -------------------------
            # Today's Appointments
            # -------------------------
            today_self = Appointment.objects.filter(
                start_time__date=today
            ).select_related("patient", "doctor")
            
            today_dependent = DependentAppointment.objects.filter(
                start_time__date=today
            ).select_related("dependent_patient", "doctor")
            
            # Add appointment_type attribute
            for appt in today_self:
                appt.appointment_type = "self"
            
            for appt in today_dependent:
                appt.appointment_type = "dependent"
            
            today_appointments = sorted(
                list(today_self) + list(today_dependent),
                key=lambda x: x.start_time
            )
            
            context["today_appointments"] = today_appointments
            context["today_appointments_count"] = len(today_appointments)
            
            # -------------------------
            # Pending Appointments
            # -------------------------
            pending_self = Appointment.objects.filter(
                status="pending"
            ).select_related("patient", "doctor")
            
            pending_dependent = DependentAppointment.objects.filter(
                status="pending"
            ).select_related("dependent_patient", "doctor")
            
            # Add appointment_type attribute
            for appt in pending_self:
                appt.appointment_type = "self"
            
            for appt in pending_dependent:
                appt.appointment_type = "dependent"
            
            pending_list = sorted(
                list(pending_self) + list(pending_dependent),
                key=lambda x: x.start_time
            )
            
            context["pending_appointments_list"] = pending_list
            context["pending_appointments"] = len(pending_list)
            
            # -------------------------
            # Total Appointments Statistics
            # -------------------------
            context["total_appointments"] = (
                Appointment.objects.count() + 
                DependentAppointment.objects.count()
            )
            
            context["confirmed_appointments"] = (
                Appointment.objects.filter(status="approved").count() +
                DependentAppointment.objects.filter(status="approved").count()
            )
            
            context["completed_appointments"] = (
                Appointment.objects.filter(
                    status="completed",
                    start_time__month=today.month,
                    start_time__year=today.year
                ).count() +
                DependentAppointment.objects.filter(
                    status="completed",
                    start_time__month=today.month,
                    start_time__year=today.year
                ).count()
            )
            
            # -------------------------
            # Total Patients (Self + Dependents)
            # -------------------------
            total_self_patients = User.objects.filter(role='patient').count()
            total_dependents = DependentPatient.objects.count()
            context["total_patients"] = total_self_patients + total_dependents
            
            # -------------------------
            # Active Doctors
            # -------------------------
            context["active_doctors"] = DoctorInfo.objects.filter(is_approved=True).count()
            
            # -------------------------
            # Recent Activity (Last 10 actions)
            # -------------------------
            context["recent_activities"] = ActivityLog.objects.select_related('user').order_by('-timestamp')[:10]
            
            # -------------------------
            # Upcoming Appointments (Next 5)
            # -------------------------
            upcoming_self = Appointment.objects.filter(
                start_time__gte=timezone.now(),
                status__in=["pending", "approved"]
            ).select_related("patient", "doctor").order_by("start_time")[:5]
            
            upcoming_dependent = DependentAppointment.objects.filter(
                start_time__gte=timezone.now(),
                status__in=["pending", "approved"]
            ).select_related("dependent_patient", "doctor").order_by("start_time")[:5]
            
            # Add appointment_type
            for appt in upcoming_self:
                appt.appointment_type = "self"
            
            for appt in upcoming_dependent:
                appt.appointment_type = "dependent"
            
            upcoming = sorted(
                list(upcoming_self) + list(upcoming_dependent),
                key=lambda x: x.start_time
            )[:5]
            
            context["upcoming_appointments"] = upcoming
            
    return render(request, "home.html", context)

@login_required
def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")

@login_required
def account_settings(request):
    """Handle account settings for username, email, and password changes"""
    
    tab = request.POST.get('tab', 'general') if request.method == 'POST' else 'general'
    
    form_general = None
    form_security = None
    
    if request.method == 'POST':
        if tab == 'general':
            form_general = GeneralSettingsForm(request.POST)
            form_general.user_id = request.user.id
            
            if form_general.is_valid():
                user = request.user
                user.username = form_general.cleaned_data['username']
                user.email = form_general.cleaned_data['email']
                user.first_name = form_general.cleaned_data['first_name']
                user.last_name = form_general.cleaned_data['last_name']
                user.save()
                
                messages.success(request, "Your account information has been updated successfully.")
                return redirect('account_settings')
        
        elif tab == 'security':
            form_security = SecuritySettingsForm(request.POST)
            
            if form_security.is_valid():
                user = request.user
                current_password = form_security.cleaned_data['current_password']
                new_password = form_security.cleaned_data['new_password1']
                
                # Verify current password
                if not user.check_password(current_password):
                    form_security.add_error('current_password', 'Current password is incorrect.')
                else:
                    # Set new password
                    user.set_password(new_password)
                    user.save()
                    
                    # Keep the user logged in after password change
                    update_session_auth_hash(request, user)
                    
                    messages.success(request, "Your password has been changed successfully.")
                    return redirect('account_settings')
    
    # Initialize forms with current data
    if form_general is None:
        form_general = GeneralSettingsForm(initial={
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })
        form_general.user_id = request.user.id
    
    if form_security is None:
        form_security = SecuritySettingsForm()
    
    return render(request, 'account/settings.html', {
        'form_general': form_general,
        'form_security': form_security,
        'active_tab': tab,
    })
    
# DASHBOARD
@login_required
def medical_records(request):
    my_info = getattr(request.user, "patient_profile", None)
    dependents = request.user.dependent_patients.all() if hasattr(request.user, "dependent_patients") else []

    patients = []
    if my_info:
        patients.append(my_info)
    patients += list(dependents)

    return render(request, "patients/medical_records.html", {
        "patients": patients
    })
    
def patient_list(request):
    # Include both PatientInfo (self profiles) and DependentPatient entries
    patients = []

    # PatientInfo entries: mark patient_type = 'self'
    for p in PatientInfo.objects.all().select_related('user'):
        setattr(p, 'patient_type', 'self')
        patients.append(p)

    # Dependents: mark patient_type = 'dependent'
    for d in DependentPatient.objects.all():
        setattr(d, 'patient_type', 'dependent')
        patients.append(d)

    # Optionally sort by name or patient_id; keep insertion order for now
    return render(request, "staffs/patient_list.html", {"patients": patients})

def patient_details_ajax(request, pk):
    """
    AJAX view to fetch patient details (self or dependent) for staff/doctor.
    Always returns JSON with 'html' key.
    """
    try:
        user_role = getattr(request.user, 'role', None)
        patient = None
        patient_type = None

        # ---------- Identify patient ----------
        if user_role in ['staff', 'doctor']:
            patient = PatientInfo.objects.filter(pk=pk).first()
            if patient:
                patient_type = 'self'
        else:
            patient = PatientInfo.objects.filter(pk=pk, user=request.user).first()
            if patient:
                patient_type = 'self'

        if not patient:
            if user_role in ['staff', 'doctor']:
                patient = DependentPatient.objects.filter(pk=pk).first()
                if patient:
                    patient_type = 'dependent'
            else:
                patient = DependentPatient.objects.filter(pk=pk, guardian=request.user).first()
                if patient:
                    patient_type = 'dependent'

        if not patient:
            return JsonResponse({'html': '<p class="muted">Patient not found.</p>'})

        # ---------- Vitals ----------
        vitals = getattr(patient, 'vitals', None)
        vitals = vitals.last() if vitals else None

        # ---------- Medications ----------
        medications = getattr(patient, 'medications', None)
        medications = medications.all() if medications else []

        # ---------- Allergies ----------
        allergies = getattr(patient, 'allergies', None)
        allergies = allergies.all() if allergies else []

        # ---------- Medical History ----------
        if patient_type == 'self':
            medical_history = MedicalRecord.objects.filter(
                patient=patient
            ).order_by('-created_at')
        else:
            medical_history = MedicalRecord.objects.filter(
                dependent_patient=patient
            ).order_by('-created_at')

        # ---------- ✅ LAST VISIT (COMPLETED ONLY) ----------
        last_visit = None

        try:
            if patient_type == 'self' and getattr(patient, 'user', None):
                last_appointment = Appointment.objects.filter(
                    patient=patient.user,
                    status='completed'
                ).order_by('-start_time').first()

                last_visit = last_appointment.start_time if last_appointment else None

            elif patient_type == 'dependent':
                last_appointment = DependentAppointment.objects.filter(
                    dependent_patient=patient,
                    status='completed'
                ).order_by('-start_time').first()

                last_visit = last_appointment.start_time if last_appointment else None

        except Exception as e:
            print(f"Last visit error for patient {pk}: {e}")
            last_visit = None

        # ---------- Render ----------
        html = render_to_string(
            'patients/partials/patient_details.html',
            {
                "patient": patient,
                "patient_type": patient_type,
                "vitals": vitals,
                "medications": medications,
                "allergies": allergies,
                "medical_history": medical_history,
                "last_visit": last_visit,
                "user": request.user,
            },
            request=request
        )

        return JsonResponse({'html': html})

    except Exception as e:
        print(f"AJAX error for patient {pk}: {e}")
        return JsonResponse({
            'html': '<p class="muted">Failed to load patient details.</p>'
        })

@login_required
def doctor_patient_list(request):
    if getattr(request.user, "role", None) != "doctor":
        messages.error(request, "Access denied.")
        return redirect("home")

    doctor = request.user.doctor_info

    # Self patients (linked via Appointment)
    user_ids = Appointment.objects.filter(
        doctor=doctor
    ).values_list('patient_id', flat=True).distinct()

    # Dependent patients (linked via DependentAppointment)
    dependent_ids = DependentAppointment.objects.filter(
        doctor=doctor
    ).values_list('dependent_patient_id', flat=True).distinct()

    patients = []

    # Fetch self patients
    for p in PatientInfo.objects.filter(user_id__in=user_ids).select_related('user'):
        setattr(p, "patient_type", "self")
        patients.append(p)

    # Fetch dependent patients
    for d in DependentPatient.objects.filter(patient_id__in=dependent_ids):
        setattr(d, "patient_type", "dependent")
        patients.append(d)

    # Sort by name
    patients.sort(key=lambda x: x.user.get_full_name() if hasattr(x, 'user') else x.full_name)

    return render(request, "doctors/patient_list.html", {"patients": patients})

# USER PATIENT PROFILE
@login_required
def edit_my_patient_info(request):
    user = request.user

    try:
        patient_info = PatientInfo.objects.get(user=user)
    except PatientInfo.DoesNotExist:
        patient_info = PatientInfo(user=user)

    user_form = UserBasicInfoForm(request.POST or None, instance=user)
    patient_form = PatientInfoForm(request.POST or None, instance=patient_info)

    if request.method == "POST" and user_form.is_valid() and patient_form.is_valid():
        try:
            user_form.save()
            patient_instance = patient_form.save(commit=False)
            patient_instance.user = user
            patient_instance.save()

            # Log activity
            ActivityLog.objects.create(
                user=user,
                action_type="update",
                model_name="PatientInfo",
                object_id=patient_instance.patient_id,
                related_object_repr=str(patient_instance)
            )

            messages.success(request, "Profile updated successfully.")
            return redirect("medical_records")

        except ValidationError as e:
            for message in e.messages:
                messages.error(request, message)

    return render(request, "patients/edit_my_profile.html", {
        "user_form": user_form,
        "patient_form": patient_form,
    })


# DEPENDENT PATIENTS
@login_required
def add_dependent(request):
    if request.method == "POST":
        # Pass the guardian to the form
        form = DependentPatientForm(request.POST, guardian=request.user)
        if form.is_valid():
            dependent = form.save(commit=False)
            dependent.guardian = request.user
            dependent.save()

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type="create",
                model_name="DependentPatient",
                object_id=dependent.patient_id,
                related_object_repr=str(dependent)
            )

            messages.success(request, "Dependent patient added successfully.")
            return redirect("medical_records")
    else:
        # Pass the guardian to the form
        form = DependentPatientForm(guardian=request.user)

    return render(request, "patients/add_dependent.html", {"form": form})




@login_required
def edit_dependent(request, pk):
    dependent = get_object_or_404(
        DependentPatient,
        pk=pk,
        guardian=request.user
    )

    if request.method == "POST":
        # Pass the guardian to the form
        form = DependentPatientForm(request.POST, instance=dependent, guardian=request.user)
        if form.is_valid():
            dependent = form.save()

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type="update",
                model_name="DependentPatient",
                object_id=dependent.patient_id,
                related_object_repr=str(dependent)
            )

            messages.success(request, "Dependent patient updated.")
            return redirect("medical_records")
    else:
        # Pass the guardian to the form
        form = DependentPatientForm(instance=dependent, guardian=request.user)

    return render(request, "patients/edit_dependent.html", {"form": form})

#VITALS
@login_required
def add_patient_vitals(request, patient_type, pk):
    if patient_type == "self":
        patient = get_object_or_404(
            PatientInfo,
            pk=pk
        ) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(PatientInfo, pk=pk, user=request.user)
        form_class = PatientVitalsForm
    else:
        patient = get_object_or_404(
            DependentPatient,
            pk=pk
        ) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(DependentPatient, pk=pk, guardian=request.user)
        form_class = DependentPatientVitalsForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            vitals = form.save(commit=False)
            # AUTO-ASSIGN LOGGED-IN USER
            vitals.created_by = request.user
            
            if patient_type == "self":
                vitals.patient = patient
            else:
                vitals.dependent_patient = patient
            vitals.save()

            ActivityLog.objects.create(
                user=request.user,
                action_type='create',
                model_name=vitals.__class__.__name__,
                object_id=str(vitals.pk),
                related_object_repr=str(vitals)
            )

            messages.success(request, "Vitals added successfully.")
            return redirect("patient_list" if getattr(request.user, 'role', None) == 'staff' else "medical_records")
    else:
        form = form_class()

    return render(request, "patients/add_vitals.html", {"form": form, "patient": patient})



@login_required
def vital_history(request, patient_type, pk):
    # Permission check
    if request.user.role not in ['patient', 'staff', 'doctor']:
        messages.error(request, "Access denied")
        return redirect('home')

    if patient_type == 'self':
        if request.user.role == 'patient':
            patient = get_object_or_404(PatientInfo, pk=pk, user=request.user)
        else:
            patient = get_object_or_404(PatientInfo, pk=pk)

        vitals = patient.vitals.order_by('-recorded_at')

    elif patient_type == 'dependent':
        if request.user.role == 'patient':
            patient = get_object_or_404(DependentPatient, pk=pk, guardian=request.user)
        else:
            patient = get_object_or_404(DependentPatient, pk=pk)

        vitals = patient.vitals.order_by('-recorded_at')

    else:
        messages.error(request, "Invalid patient type")
        return redirect('home')

    return render(request, 'patients/vitals_history.html', {
        'patient': patient,
        'patient_type': patient_type,
        'vitals': vitals
    })
 
# ALLERGIES
@login_required
def add_patient_allergy(request, patient_type, pk):
    # Determine patient
    if patient_type == "self":
        patient = get_object_or_404(
            PatientInfo,
            pk=pk
        ) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(PatientInfo, pk=pk, user=request.user)
        form_class = PatientAllergyForm
    else:
        patient = get_object_or_404(
            DependentPatient,
            pk=pk
        ) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(DependentPatient, pk=pk, guardian=request.user)
        form_class = DependentPatientAllergyForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            allergy = form.save(commit=False)
            # AUTO-ASSIGN LOGGED-IN USER
            allergy.created_by = request.user
            
            # Assign the correct patient
            if patient_type == "self":
                allergy.patient = patient
            else:
                allergy.dependent_patient = patient
            allergy.save()

            ActivityLog.objects.create(
                user=request.user,
                action_type='create',
                model_name=allergy.__class__.__name__,
                object_id=str(allergy.pk),
                related_object_repr=str(allergy)
            )

            messages.success(request, "Allergy added successfully.")
            return redirect("patient_list" if getattr(request.user, 'role', None) == 'staff' else "medical_records")
    else:
        form = form_class()

    return render(request, "patients/add_allergy.html", {"form": form, "patient": patient})

# MEDICATIONS
@login_required
def add_patient_medication(request, patient_type, pk):
    if patient_type == "self":
        patient = get_object_or_404(
            PatientInfo,
            pk=pk
        ) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(PatientInfo, pk=pk, user=request.user)
        form_class = PatientMedicationForm
    else:
        patient = get_object_or_404(
            DependentPatient,
            pk=pk
        ) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(DependentPatient, pk=pk, guardian=request.user)
        form_class = DependentPatientMedicationForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            medication = form.save(commit=False)
            # AUTO-ASSIGN LOGGED-IN USER
            medication.created_by = request.user
            
            if patient_type == "self":
                medication.patient = patient
            else:
                medication.dependent_patient = patient
            medication.save()

            ActivityLog.objects.create(
                user=request.user,
                action_type='create',
                model_name=medication.__class__.__name__,
                object_id=str(medication.pk),
                related_object_repr=str(medication)
            )

            messages.success(request, "Medication added successfully.")
            return redirect("patient_list" if getattr(request.user, 'role', None) == 'staff' else "medical_records")
    else:
        form = form_class()

    return render(request, "patients/add_medication.html", {"form": form, "patient": patient})


@login_required
def medication_history(request, patient_type, pk):
    if patient_type == "self":
        patient = get_object_or_404(PatientInfo, pk=pk)
        medications = patient.medications.all()

    elif patient_type == "dependent":
        patient = get_object_or_404(DependentPatient, pk=pk)
        medications = patient.medications.all()

    else:
        return redirect("home")

    return render(request, "patients/medication_history.html", {
        "patient": patient,
        "patient_type": patient_type,
        "medications": medications,
    })
    
@login_required
def doctor_dashboard(request):
    if request.user.role != "doctor":
        return redirect("home")  # or wherever

    if not hasattr(request.user, "doctor_info"):
        return redirect("doctor_edit_info")  # redirect to form
    
    return render(request, "home.html")

# Doctor create or edit profile infomartion
@login_required
def doctor_edit_info(request):
    try:
        doctor_info = DoctorInfo.objects.get(user=request.user)
    except DoctorInfo.DoesNotExist:
        doctor_info = DoctorInfo(user=request.user)

    if request.method == "POST":
        form = DoctorInfoForm(request.POST, request.FILES, instance=doctor_info)
        if form.is_valid():
            doctor_info = form.save()

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type="update" if doctor_info.id else "create",
                model_name="DoctorInfo",
                object_id=str(doctor_info.id),
                related_object_repr=str(doctor_info)
            )

            messages.success(request, "Profile submitted successfully.")
            return redirect("home")
        else:
            messages.error(request, "Please fill all required fields.")
    else:
        form = DoctorInfoForm(instance=doctor_info)

    return render(request, "doctors/edit_info.html", {"form": form})

def doctor_approved_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role != "doctor":
            return redirect("home")

        doctor = getattr(request.user, "doctor_info", None)
        if not doctor or not doctor.is_approved:
            messages.warning(request, "You must have an approved profile to access this page.")
            return redirect("home")  # Redirect back to home, which handles pending view

        return view_func(request, *args, **kwargs)
    return wrapper

# Manage users (manager view)
@login_required
def manager_doctor_list(request):
    # Only managers can access
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")

    doctors = DoctorInfo.objects.all().order_by("user__last_name")
    pending_count = doctors.filter(is_approved=False, is_rejected=False).count()
    return render(request, "managers/users.html", {
        "doctors": doctors,
        'pending_count': pending_count,
    })

# approve doctors accounts when info is added
@login_required
def manager_approve_doctor(request, doctor_id):
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")

    doctor = get_object_or_404(DoctorInfo, id=doctor_id)

    if doctor.is_approved:
        messages.info(request, f"{doctor.user.get_full_name()} is already approved.")
    else:
        doctor.is_approved = True
        doctor.approved_at = timezone.now()
        doctor.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type="update",
            model_name="DoctorInfo",
            object_id=str(doctor.id),
            related_object_repr=f"Approved {doctor}"
        )

        # Send email notification
        subject = "Your Doctor Profile Has Been Approved"
        message = f"Hello {doctor.user.get_full_name()},\n\nYour doctor profile has been approved. You can now access all doctor features on the platform.\n\nBest regards,\nThe Team"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [doctor.user.email])

        messages.success(request, f"{doctor.user.get_full_name()} has been approved.")

    return redirect("manager_users_list")

@login_required
def manager_reject_doctor(request, doctor_id):
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")

    doctor = get_object_or_404(DoctorInfo, id=doctor_id)

    if doctor.is_approved:
        messages.warning(request, f"{doctor.user.get_full_name()} is already approved and cannot be rejected.")
    elif doctor.is_rejected:
        messages.info(request, f"{doctor.user.get_full_name()} has already been rejected.")
    else:
        doctor.is_rejected = True
        doctor.rejected_at = timezone.now()
        doctor.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type="update",
            model_name="DoctorInfo",
            object_id=str(doctor.id),
            related_object_repr=f"Rejected {doctor}"
        )

        # Send email
        subject = "Your Doctor Profile Has Been Rejected"
        message = f"Hello {doctor.user.get_full_name()},\n\nWe regret to inform you that your doctor profile has been rejected. Please review your submission and try again.\n\nBest regards,\nThe Team"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [doctor.user.email])

        messages.success(request, f"{doctor.user.get_full_name()} has been rejected.")

    return redirect("manager_users_list")


@login_required
def manager_add_specialization(request):
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")

    if request.method == "POST":
        form = SpecializationForm(request.POST)
        if form.is_valid():
            specialization = form.save()

            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action_type="create",
                model_name="Specialization",
                object_id=str(specialization.id),
                related_object_repr=str(specialization)
            )

            messages.success(request, "Specialization added successfully.")
            return redirect("manager_users_list")
    else:
        form = SpecializationForm()

    return render(request, "managers/add_specialization.html", {"form": form})

@login_required
def view_doctors(request):
    # Only allow staff or patients
    if request.user.role not in ["staff", "patient"]:
        messages.error(request, "Access denied.")
        return redirect("home")

    # Fetch only approved doctors and annotate with ratings
    approved_doctors = DoctorInfo.objects.filter(is_approved=True).select_related("user").annotate(
        average_rating=Avg('ratings__rating'),  # <--- use 'ratings' instead of 'rating'
        rating_count=Count('ratings')
    ).order_by("user__last_name")

    # Pass a stars list to template
    stars = [1, 2, 3, 4, 5]

    return render(request, "view_doctors.html", {
        "doctors": approved_doctors,
        "stars": stars
    })


@login_required
def patient_appointment_calendar(request):
    if request.user.role != "patient":
        return redirect("home")

    doctors = DoctorInfo.objects.filter(is_approved=True).select_related("user")

    return render(request, "calendar/patient_calendar.html", {
        "doctors": doctors
    })

@login_required
def appointment_details(request, pk):
    # Only patient can view their own appointment
    appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
    return render(request, "calendar/partials/patient_appointment_details.html", {"appointment": appointment})

@login_required
def book_appointment(request):
    if request.user.role != "patient":
        return redirect("home")

    doctor_id = request.GET.get("doctor")
    start = request.GET.get("start")
    end = request.GET.get("end")

    doctor = get_object_or_404(DoctorInfo, id=doctor_id)
    dependents = DependentPatient.objects.filter(guardian=request.user)

    if request.method == "POST":
        patient_type = request.POST.get("patient_type")  # "self" or dependent.patient_id

        with transaction.atomic():
            conflict_self = Appointment.objects.select_for_update().filter(
                doctor=doctor,
                start_time__lt=end,
                end_time__gt=start,
                status="approved"
            ).exists()

            conflict_dependent = DependentAppointment.objects.select_for_update().filter(
                doctor=doctor,
                start_time__lt=end,
                end_time__gt=start,
                status="approved"
            ).exists()

            if conflict_self or conflict_dependent:
                messages.error(request, "This time slot was just booked. Please choose another.")
                return redirect("patient_calendar")

            # Create appointment
            if patient_type == "self":
                appointment = Appointment.objects.create(
                    doctor=doctor,
                    patient=request.user,
                    start_time=start,
                    end_time=end,
                    status="pending"
                )
                ActivityLog.objects.create(
                    user=request.user,
                    action_type="create",
                    model_name="Appointment",
                    object_id=str(appointment.id),
                    related_object_repr=str(appointment)
                )
            else:
                dependent = get_object_or_404(
                    DependentPatient,
                    patient_id=patient_type,
                    guardian=request.user
                )
                appointment = DependentAppointment.objects.create(
                    doctor=doctor,
                    dependent_patient=dependent,
                    start_time=start,
                    end_time=end,
                    status="pending"
                )
                ActivityLog.objects.create(
                    user=request.user,
                    action_type="create",
                    model_name="DependentAppointment",
                    object_id=str(appointment.id),
                    related_object_repr=str(appointment)
                )

        messages.success(request, "Appointment requested successfully.")
        return redirect("patient_calendar")

    return render(request, "calendar/book.html", {
        "doctor": doctor,
        "start": start,
        "end": end,
        "dependents": dependents
    })
    
@login_required
@doctor_approved_required
def doctor_schedule(request):
    doctor = request.user.doctor_info
    schedules = doctor.availabilities.all()

    if request.method == "POST":
        form = DoctorAvailabilityForm(request.POST)
        if form.is_valid():
            availability = form.save(commit=False)
            availability.doctor = doctor
            # AUTO-ASSIGN LOGGED-IN USER
            availability.created_by = request.user
            availability.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action_type="create",
                model_name="DoctorAvailability",
                object_id=str(availability.id),
                related_object_repr=str(availability)
            )

            messages.success(request, "Availability added.")
            return redirect("doctor_schedule")
    else:
        form = DoctorAvailabilityForm()

    return render(request, "doctors/schedule.html", {
        "form": form,
        "schedules": schedules
    })


@login_required
@doctor_approved_required
def delete_availability(request, pk):
    availability = get_object_or_404(
        DoctorAvailability,
        pk=pk,
        doctor=request.user.doctor_info
    )
    availability.delete()
    
    ActivityLog.objects.create(
        user=request.user,
        action_type="delete",
        model_name="DoctorAvailability",
        object_id=str(pk),
        related_object_repr=str(availability)
    )

    messages.success(request, "Availability removed.")
    return redirect("doctor_schedule")


# views.py
@login_required
@doctor_approved_required
def doctor_custom_schedule(request):
    doctor = request.user.doctor_info
    custom_schedules = doctor.custom_availabilities.all()

    if request.method == "POST":
        form = CustomDoctorAvailabilityForm(request.POST)
        if form.is_valid():
            custom_avail = form.save(commit=False)
            custom_avail.doctor = doctor
            # AUTO-ASSIGN LOGGED-IN USER
            custom_avail.created_by = request.user
            custom_avail.save()
            
            ActivityLog.objects.create(
                user=request.user,
                action_type="create",
                model_name="CustomDoctorAvailability",
                object_id=str(custom_avail.id),
                related_object_repr=str(custom_avail)
            )

            messages.success(request, "Custom availability added successfully.")
            return redirect("doctor_custom_schedule")
    else:
        form = CustomDoctorAvailabilityForm()

    return render(request, "doctors/custom_schedule.html", {
        "form": form,
        "custom_schedules": custom_schedules
    })



@login_required
@doctor_approved_required
def delete_custom_availability(request, pk):
    availability = get_object_or_404(
        CustomDoctorAvailability,
        pk=pk,
        doctor=request.user.doctor_info
    )
    availability.delete()

    ActivityLog.objects.create(
        user=request.user,
        action_type="delete",
        model_name="CustomDoctorAvailability",
        object_id=str(pk),
        related_object_repr=str(availability)
    )

    messages.success(request, "Custom availability removed.")
    return redirect("doctor_custom_schedule")

@login_required
def doctor_available_days(request):
    """Return available days for a doctor in a given month (excluding past dates)"""
    doctor_id = request.GET.get("doctor_id")
    year = int(request.GET.get("year"))
    month = int(request.GET.get("month"))

    if not doctor_id:
        return JsonResponse([], safe=False)

    doctor = get_object_or_404(DoctorInfo, id=doctor_id)
    days_in_month = monthrange(year, month)[1]
    available_days = []
    
    # Get today's date for comparison
    today = date.today()

    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        
        # Skip past dates
        if d < today:
            continue
            
        weekday = d.weekday()

        # Check for custom availability first
        custom_avail = doctor.custom_availabilities.filter(date=d)
        if custom_avail.exists():
            availabilities = custom_avail
        else:
            # Use weekly availability
            availabilities = doctor.availabilities.filter(weekday=weekday)

        if not availabilities.exists():
            continue  # No availability this day

        # Approved appointments on this day (BOTH self and dependent)
        appointments = Appointment.objects.filter(
            doctor=doctor,
            start_time__date=d,
            status="approved"
        )
        
        dependent_appointments = DependentAppointment.objects.filter(
            doctor=doctor,
            start_time__date=d,
            status="approved"
        )
        
        # Combine booked times from both
        booked_times = []
        for a in appointments:
            booked_times.append((a.start_time.time(), a.end_time.time()))
        for da in dependent_appointments:
            booked_times.append((da.start_time.time(), da.end_time.time()))

        SLOT_MINUTES = 30
        day_has_free_slot = False

        for a in availabilities:
            current = datetime.combine(d, a.start_time)
            end = datetime.combine(d, a.end_time)
            
            # For today, skip past time slots
            now = timezone.now()
            if d == today:
                # Only show slots that are at least 1 hour in the future
                min_start_time = (now + timedelta(hours=1)).time()
                if a.start_time < min_start_time:
                    continue

            while current + timedelta(minutes=SLOT_MINUTES) <= end:
                slot_end = current + timedelta(minutes=SLOT_MINUTES)
                
                # For today, skip time slots that have already passed
                if d == today and current.time() < (now + timedelta(hours=1)).time():
                    current = slot_end
                    continue

                # Check if slot overlaps with any booked appointment (self or dependent)
                is_booked = any(
                    current.time() >= b_start and current.time() < b_end
                    for b_start, b_end in booked_times
                )

                if not is_booked:
                    day_has_free_slot = True
                    break

                current = slot_end

            if day_has_free_slot:
                break

        if day_has_free_slot:
            available_days.append(d.isoformat())

    return JsonResponse(available_days, safe=False)


@login_required
def doctor_daily_availability(request):
    """Return available time slots for a doctor on a specific date (excluding past times)"""
    doctor_id = request.GET.get("doctor_id")
    date_str = request.GET.get("date")  # YYYY-MM-DD

    if not doctor_id or not date_str:
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    # Don't allow booking on past dates
    if date_obj < date.today():
        return JsonResponse([], safe=False)

    weekday = date_obj.weekday()
    doctor = get_object_or_404(DoctorInfo, id=doctor_id)

    # 1️⃣ Check for custom availability for this date
    custom_availabilities = doctor.custom_availabilities.filter(date=date_obj)
    if custom_availabilities.exists():
        availabilities = custom_availabilities
    else:
        availabilities = doctor.availabilities.filter(weekday=weekday)

    if not availabilities.exists():
        return JsonResponse([], safe=False)

    # 2️⃣ Get BOTH self AND dependent approved appointments on this date
    self_appointments = Appointment.objects.filter(
        doctor=doctor,
        start_time__date=date_obj,
        status="approved"
    )
    
    dependent_appointments = DependentAppointment.objects.filter(
        doctor=doctor,
        start_time__date=date_obj,
        status="approved"
    )

    # 3️⃣ Build booked times list from BOTH types
    booked_times = []
    
    for a in self_appointments:
        booked_times.append((a.start_time.time(), a.end_time.time()))
    
    for da in dependent_appointments:
        booked_times.append((da.start_time.time(), da.end_time.time()))

    print(f"DEBUG: Date {date_obj}, Doctor {doctor_id}")
    print(f"DEBUG: Self appointments: {[f'{a.start_time.time()}-{a.end_time.time()}' for a in self_appointments]}")
    print(f"DEBUG: Dependent appointments: {[f'{da.start_time.time()}-{da.end_time.time()}' for da in dependent_appointments]}")
    print(f"DEBUG: Booked times: {booked_times}")

    slots = []
    SLOT_MINUTES = 30
    now = timezone.now()
    is_today = date_obj == date.today()

    for a in availabilities:
        start_time = getattr(a, "start_time", None)
        end_time = getattr(a, "end_time", None)

        if not start_time or not end_time:
            continue

        current = datetime.combine(date_obj, start_time)
        end = datetime.combine(date_obj, end_time)

        while current + timedelta(minutes=SLOT_MINUTES) <= end:
            slot_end = current + timedelta(minutes=SLOT_MINUTES)
            slot_time = current.time()

            # For today, only show slots at least 1 hour in the future
            if is_today:
                min_booking_time = (now + timedelta(hours=1)).time()
                if slot_time < min_booking_time:
                    current = slot_end
                    continue

            # Check if slot overlaps with ANY booked appointment (self or dependent)
            is_booked = False
            for booked_start, booked_end in booked_times:
                # Slot overlaps if: slot_time >= booked_start AND slot_time < booked_end
                if slot_time >= booked_start and slot_time < booked_end:
                    is_booked = True
                    break

            print(f"DEBUG: Slot {slot_time} - Available: {not is_booked}")

            slots.append({
                "time": current.strftime("%I:%M %p"),
                "available": not is_booked,
                "start": current.isoformat(),
                "end": slot_end.isoformat()
            })

            current = slot_end

    return JsonResponse(slots, safe=False)

@login_required
def doctor_available_days(request):

    doctor_id = request.GET.get("doctor_id")
    year = int(request.GET.get("year"))
    month = int(request.GET.get("month"))

    if not doctor_id:
        return JsonResponse([], safe=False)

    doctor = get_object_or_404(DoctorInfo, id=doctor_id)
    days_in_month = monthrange(year, month)[1]
    available_days = []
    
    # Get today's date for comparison
    today = date.today()

    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        
        # Skip past dates
        if d < today:
            continue
            
        weekday = d.weekday()

        # Check for custom availability first
        custom_avail = doctor.custom_availabilities.filter(date=d)
        if custom_avail.exists():
            availabilities = custom_avail
        else:
            # Use weekly availability
            availabilities = doctor.availabilities.filter(weekday=weekday)

        if not availabilities.exists():
            continue  # No availability this day

        # Approved appointments on this day (BOTH self and dependent)
        appointments = Appointment.objects.filter(
            doctor=doctor,
            start_time__date=d,
            status="approved"
        )
        
        dependent_appointments = DependentAppointment.objects.filter(
            doctor=doctor,
            start_time__date=d,
            status="approved"
        )
        
        # Combine booked times from both
        booked_times = []
        for a in appointments:
            booked_times.append((a.start_time.time(), a.end_time.time()))
        for da in dependent_appointments:
            booked_times.append((da.start_time.time(), da.end_time.time()))

        SLOT_MINUTES = 30
        day_has_free_slot = False

        for a in availabilities:
            current = datetime.combine(d, a.start_time)
            end = datetime.combine(d, a.end_time)
            
            # For today, skip past time slots
            now = timezone.now()
            if d == today:
                # Only show slots that are at least 1 hour in the future
                min_start_time = (now + timedelta(hours=1)).time()
                if a.start_time < min_start_time:
                    continue

            while current + timedelta(minutes=SLOT_MINUTES) <= end:
                slot_end = current + timedelta(minutes=SLOT_MINUTES)
                
                # For today, skip time slots that have already passed
                if d == today and current.time() < (now + timedelta(hours=1)).time():
                    current = slot_end
                    continue

                # Check if slot overlaps with any booked appointment (self or dependent)
                is_booked = any(
                    current.time() >= b_start and current.time() < b_end
                    for b_start, b_end in booked_times
                )

                if not is_booked:
                    day_has_free_slot = True
                    break

                current = slot_end

            if day_has_free_slot:
                break

        if day_has_free_slot:
            available_days.append(d.isoformat())

    return JsonResponse(available_days, safe=False)

@login_required
def staff_appointment_calendar(request):
    if request.user.role != "staff":
        return redirect("home")
    return render(request, "calendar/staff_calendar.html")

def get_event_color(status):
    """Return calendar event color based on appointment status"""
    colors = {
        'pending': '#ffc107',        # yellow
        'approved': '#28a745',       # green
        'completed': '#6c757d',      # gray
        'rejected': '#dc3545',       # red
        'no_show': '#17a2b8',        # blue/info
    }
    return colors.get(status, '#ffc107')  # default to yellow


@login_required
def calendar_events(request):
    user = request.user
    events = []

    if user.role == "staff":
        # Staff sees all appointments (excluding completed)
        appointments = Appointment.objects.exclude(status="completed").select_related(
            "patient", "doctor"
        )
        dependent_appointments = DependentAppointment.objects.exclude(status="completed").select_related(
            "dependent_patient", "doctor"
        )
        
        for a in appointments:
            try:
                patient_name = a.patient.get_full_name() if a.patient else "Unknown Patient"
                title = f"{patient_name} ({a.status})"
                color = get_event_color(a.status)  # USE THE HELPER FUNCTION
                events.append({
                    "id": a.id,
                    "title": title,
                    "start": a.start_time.isoformat(),
                    "end": a.end_time.isoformat(),
                    "color": color
                })
            except Exception as e:
                print(f"Error processing appointment {a.id}: {e}")
                continue

        for a in dependent_appointments:
            try:
                patient_name = a.dependent_patient.full_name if a.dependent_patient else "Unknown Patient"
                title = f"{patient_name} ({a.status})"
                color = get_event_color(a.status)  # USE THE HELPER FUNCTION
                events.append({
                    "id": a.id,
                    "title": title,
                    "start": a.start_time.isoformat(),
                    "end": a.end_time.isoformat(),
                    "color": color
                })
            except Exception as e:
                print(f"Error processing dependent appointment {a.id}: {e}")
                continue
    
    return JsonResponse(events, safe=False)

@login_required
def staff_day_appointments(request):
    if request.user.role != "staff":
        return JsonResponse([], safe=False)

    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse([], safe=False)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Normal appointments
    appointments = Appointment.objects.filter(
        start_time__date=date_obj
    ).select_related("patient", "doctor")

    # Dependent appointments
    dependent_appointments = DependentAppointment.objects.filter(
        start_time__date=date_obj
    ).select_related("dependent_patient", "doctor")

    data = []

    for a in appointments:
        patient_name = a.patient.get_full_name()
        doctor_name = a.doctor.user.get_full_name() if a.doctor else "Unassigned"
        data.append({
            'id': a.id,
            'patient_name': patient_name,
            'doctor_name': doctor_name,
            'start_time': a.start_time.strftime("%I:%M %p"),
            'end_time': a.end_time.strftime("%I:%M %p"),
            'status': a.status
        })

    for a in dependent_appointments:
        patient_name = a.dependent_patient.full_name
        doctor_name = a.doctor.user.get_full_name() if a.doctor else "Unassigned"
        data.append({
            'id': a.id,
            'patient_name': patient_name,
            'doctor_name': doctor_name,
            'start_time': a.start_time.strftime("%I:%M %p"),
            'end_time': a.end_time.strftime("%I:%M %p"),
            'status': a.status
        })

    # Sort by start time
    data.sort(key=lambda x: x['start_time'])

    return JsonResponse(data, safe=False)

@login_required
def staff_appointment_details(request, pk):
    if request.user.role != "staff":
        return HttpResponseForbidden("You are not authorized to view this appointment.")

    appointment = get_object_or_404(Appointment, pk=pk)

    return render(
        request,
        "calendar/partials/staff_appointment_details.html",
        {"appointment": appointment}
    )

@login_required
def staff_appointments(request):
    if request.user.role != "staff":
        return redirect("home")

    today = date.today()

    # Regular patient appointments
    appointments = Appointment.objects.select_related("patient", "doctor").order_by("-start_time")
    
    # Dependent patient appointments
    dependent_appointments = DependentAppointment.objects.select_related("dependent_patient", "doctor").order_by("-start_time")

    # Counts
    total_today = appointments.filter(start_time__date=today).count() + dependent_appointments.filter(start_time__date=today).count()
    confirmed_count = appointments.filter(status="approved").count() + dependent_appointments.filter(status="approved").count()
    pending_count = appointments.filter(status="pending").count() + dependent_appointments.filter(status="pending").count()
    completed_count = CompletedAppointment.objects.count()  # includes only Appointment; adjust if needed

    context = {
        "appointments": appointments,
        "dependent_appointments": dependent_appointments,
        "total_today": total_today,
        "confirmed_count": confirmed_count,
        "pending_count": pending_count,
        "completed_count": completed_count,
    }

    return render(request, "staffs/appointments.html", context)

#! NOT USE
@login_required
def approve_appointment(request, pk):
    if request.user.role != "staff":
        return JsonResponse({"error": "Forbidden"}, status=403)
    
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    appointment = get_object_or_404(Appointment, pk=pk)
    appointment.status = "approved"
    appointment.save()

    return JsonResponse({
        "id": appointment.id,
        "status": appointment.status,
        "status_class": "bg-success text-white"  
    })
#! NOT USE
@login_required
def reject_appointment(request, pk):
    if request.user.role != "staff":
        return JsonResponse({"error": "Forbidden"}, status=403)
    
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    appointment = get_object_or_404(Appointment, pk=pk)
    appointment.status = "rejected"
    appointment.save()

    return JsonResponse({
        "id": appointment.id,
        "status": appointment.status,
        "status_class": "bg-danger text-white"
    })

@login_required
def update_appointment_status(request, pk, action):
    if request.user.role == "patient":
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    appointment_type = request.POST.get("appointment_type", "self")
    
    try:
        if appointment_type == "dependent":
            appointment = DependentAppointment.objects.get(pk=pk)
            model_name = "DependentAppointment"
            user_for_log = appointment.dependent_patient.guardian
        else:
            appointment = Appointment.objects.get(pk=pk)
            model_name = "Appointment"
            user_for_log = appointment.patient
    except (Appointment.DoesNotExist, DependentAppointment.DoesNotExist):
        return JsonResponse({"error": "Appointment not found"}, status=404)

    # Update status
    old_status = appointment.status
    if action == "approve":
        appointment.status = "approved"
    elif action == "reject":
        appointment.status = "rejected"
    elif action == "complete":
        appointment.status = "completed"
        if appointment_type == "self":
            CompletedAppointment.objects.get_or_create(appointment=appointment)
    elif action == "no_show":
        appointment.status = "no_show"
    else:
        return JsonResponse({"error": "Invalid action"}, status=400)

    appointment.save()

    # Log activity
    ActivityLog.objects.create(
        user=request.user,  # who performed the action
        action_type="update",
        model_name=model_name,
        object_id=str(appointment.id),
        related_object_repr=str(appointment),
        description=f"Status changed from {old_status} to {appointment.status}"
    )

    return JsonResponse({
        "id": appointment.id,
        "status": appointment.status
    })

@login_required
def reschedule_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)

    if request.user.role == "staff":
        pass
    elif request.user.role == "doctor":
        if appointment.doctor != getattr(request.user, "doctor_info", None):
            messages.error(request, "Unauthorized")
            return redirect("doctor_appointments")
    else:
        messages.error(request, "Unauthorized")
        return redirect("home")

    if request.method == "POST":
        new_start = request.POST.get("start")
        new_end = request.POST.get("end")

        if not new_start or not new_end:
            messages.error(request, "Start and end times are required.")
            return render(request, "calendar/partials/reschedule_appointment.html", {
                "appointment": appointment
            })

        try:
            new_start_dt = parse_datetime(new_start)
            new_end_dt = parse_datetime(new_end)
        except:
            messages.error(request, "Invalid date/time format.")
            return render(request, "calendar/partials/reschedule_appointment.html", {
                "appointment": appointment
            })

        if new_start_dt >= new_end_dt:
            messages.error(request, "End time must be after start time.")
            return render(request, "calendar/partials/reschedule_appointment.html", {
                "appointment": appointment
            })

        # Check for conflicting approved appointments
        conflict = Appointment.objects.filter(
            doctor=appointment.doctor,
            start_time__lt=new_end_dt,
            end_time__gt=new_start_dt,
            status="approved"
        ).exclude(pk=appointment.pk).exists()

        if conflict:
            messages.error(request, "This time slot is already booked.")
            return render(request, "calendar/partials/reschedule_appointment.html", {
                "appointment": appointment
            })

        # ============ NEW: Check if the new time is within doctor's availability ============
        doctor = appointment.doctor
        new_date = new_start_dt.date()
        new_start_time = new_start_dt.time()
        new_end_time = new_end_dt.time()
        weekday = new_start_dt.weekday()
        
        # Get day name for error message
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_name = day_names[weekday]

        # Check for custom availability first
        custom_avail = doctor.custom_availabilities.filter(date=new_date).first()
        
        if custom_avail:
            # Check if new time falls within custom availability
            if not (new_start_time >= custom_avail.start_time and new_end_time <= custom_avail.end_time):
                messages.error(request, f"The selected time is outside Dr. {doctor.user.get_full_name()}'s availability on {new_date.strftime('%B %d, %Y')}.")
                return render(request, "calendar/partials/reschedule_appointment.html", {
                    "appointment": appointment
                })
        else:
            # Check regular weekly availability
            regular_avail = doctor.availabilities.filter(weekday=weekday).first()
            
            if not regular_avail:
                messages.error(request, f"Dr. {doctor.user.get_full_name()} is not available on {day_name}s ({new_date.strftime('%B %d, %Y')}).")
                return render(request, "calendar/partials/reschedule_appointment.html", {
                    "appointment": appointment
                })
            
            # Check if new time falls within regular availability
            if not (new_start_time >= regular_avail.start_time and new_end_time <= regular_avail.end_time):
                messages.error(request, f"The selected time is outside Dr. {doctor.user.get_full_name()}'s availability hours ({regular_avail.start_time.strftime('%I:%M %p')} - {regular_avail.end_time.strftime('%I:%M %p')}) on {day_name}s.")
                return render(request, "calendar/partials/reschedule_appointment.html", {
                    "appointment": appointment
                })

        # ============ END: Availability check ============

        old_start, old_end = appointment.start_time, appointment.end_time
        appointment.start_time = new_start_dt
        appointment.end_time = new_end_dt
        appointment.status = "pending"
        appointment.save()

        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type="update",
            model_name="Appointment",
            object_id=str(appointment.id),
            related_object_repr=str(appointment),
            description=f"Rescheduled from {old_start}–{old_end} to {new_start_dt}–{new_end_dt}"
        )

        messages.success(request, "Appointment rescheduled successfully!")

        if request.user.role == "staff":
            return redirect("appointments")
        elif request.user.role == "doctor":
            return redirect("doctor_appointments")

    return render(request, "calendar/partials/reschedule_appointment.html", {
        "appointment": appointment
    })
  
@login_required
def cancel_appointment(request, pk):
    """Allow patient to cancel their own appointment request"""
    if request.user.role != "patient":
        messages.error(request, "Only patients can cancel appointments.")
        return redirect("home")
    
    try:
        # Try to find self appointment
        appointment = Appointment.objects.get(pk=pk, patient=request.user)
        is_dependent = False
    except Appointment.DoesNotExist:
        # Try to find dependent appointment
        try:
            appointment = DependentAppointment.objects.get(
                pk=pk, 
                dependent_patient__guardian=request.user
            )
            is_dependent = True
        except DependentAppointment.DoesNotExist:
            messages.error(request, "Appointment not found.")
            return redirect("patient_appointments")
    
    # Allow cancellation only for pending or approved appointments
    if appointment.status not in ['pending', 'approved']:
        messages.error(request, f"Cannot cancel a {appointment.status} appointment.")
        return redirect("patient_appointments")
    
    if request.method == "POST":
        old_status = appointment.status
        appointment.status = "rejected"  # Mark as rejected/cancelled
        appointment.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type="update",
            model_name="DependentAppointment" if is_dependent else "Appointment",
            object_id=str(appointment.id),
            related_object_repr=str(appointment),
            description=f"Cancelled appointment (was {old_status})"
        )
        
        messages.success(request, "Your appointment has been cancelled successfully.")
        return redirect("patient_appointments")
    
    return render(request, "calendar/cancel_appointment.html", {
        "appointment": appointment,
        "is_dependent": is_dependent
    })
  
@login_required
def patient_appointments(request):
    if request.user.role != "patient":
        return redirect("home")

    # Own appointments
    own_appointments = Appointment.objects.filter(patient=request.user)

    # Dependent appointments
    dependents = DependentPatient.objects.filter(guardian=request.user)
    dependent_appointments = DependentAppointment.objects.filter(
        dependent_patient__in=dependents
    )

    # Combine both querysets into a single list, sorted by start_time
    appointments = sorted(
        chain(own_appointments, dependent_appointments),
        key=lambda a: a.start_time
    )

    return render(request, "patients/appointments.html", {
        "appointments": appointments
    })


@login_required
@doctor_approved_required
def doctor_calendar(request):
    """Render doctor calendar page"""
    doctor = request.user.doctor_info
    return render(request, "calendar/doctor_calendar.html", {"doctor": doctor})


@login_required
@doctor_approved_required
def doctor_calendar_events(request):
    """Return all appointments for the doctor as JSON for calendar"""
    try:
        doctor = request.user.doctor_info
        events = []

        def get_event_color(status):
            """Return calendar event color based on appointment status"""
            colors = {
                'pending': '#ffc107',        # yellow
                'approved': '#28a745',       # green
                'completed': '#6c757d',      # gray
                'rejected': '#dc3545',       # red
                'no_show': '#17a2b8',        # blue/info
            }
            return colors.get(status, '#ffc107')

        # Self appointments
        appointments = Appointment.objects.filter(
            doctor=doctor
        ).select_related("patient")
        
        for a in appointments:
            try:
                patient_name = a.patient.get_full_name() if a.patient else "Unknown Patient"
                color = get_event_color(a.status)  # Use helper function
                events.append({
                    "id": f"self-{a.id}",
                    "title": f"{patient_name} ({a.status})",
                    "start": a.start_time.isoformat(),
                    "end": a.end_time.isoformat(),
                    "color": color
                })
            except Exception as e:
                print(f"Error processing appointment {a.id}: {e}")
                continue

        # Dependent appointments
        dependent_appointments = DependentAppointment.objects.filter(
            doctor=doctor
        ).select_related("dependent_patient")
        
        for a in dependent_appointments:
            try:
                patient_name = a.dependent_patient.full_name if a.dependent_patient else "Unknown Patient"
                color = get_event_color(a.status)  # Use helper function
                events.append({
                    "id": f"dep-{a.id}",
                    "title": f"{patient_name} ({a.status})",
                    "start": a.start_time.isoformat(),
                    "end": a.end_time.isoformat(),
                    "color": color
                })
            except Exception as e:
                print(f"Error processing dependent appointment {a.id}: {e}")
                continue

        return JsonResponse(events, safe=False)

    except Exception as e:
        print(f"Error in doctor_calendar_events: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse([], safe=False)

@login_required
@doctor_approved_required
def doctor_day_appointments(request):
    """Return appointments for a given date"""
    try:
        doctor = request.user.doctor_info
        date_str = request.GET.get("date")
        
        if not date_str:
            return JsonResponse([], safe=False)

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse([], safe=False)

        data = []

        # Self appointments
        appointments = Appointment.objects.filter(
            doctor=doctor,
            start_time__date=date_obj
        ).select_related("patient")
        
        for a in appointments:
            try:
                patient_name = a.patient.get_full_name() if a.patient else "Unknown"
                status_class = "status-confirmed" if a.status == "approved" else "status-pending" if a.status == "pending" else "status-cancelled"
                
                data.append({
                    "id": f"self-{a.id}",
                    "patient_name": patient_name,
                    "start_time": a.start_time.strftime("%I:%M %p"),
                    "end_time": a.end_time.strftime("%I:%M %p"),
                    "status": a.status,
                    "status_class": status_class
                })
            except Exception as e:
                print(f"Error processing appointment {a.id}: {e}")
                continue

        # Dependent appointments
        dependent_appointments = DependentAppointment.objects.filter(
            doctor=doctor,
            start_time__date=date_obj
        ).select_related("dependent_patient")
        
        for a in dependent_appointments:
            try:
                patient_name = a.dependent_patient.full_name if a.dependent_patient else "Unknown"
                status_class = "status-confirmed" if a.status == "approved" else "status-pending" if a.status == "pending" else "status-cancelled"
                
                data.append({
                    "id": f"dep-{a.id}",
                    "patient_name": patient_name,
                    "start_time": a.start_time.strftime("%I:%M %p"),
                    "end_time": a.end_time.strftime("%I:%M %p"),
                    "status": a.status,
                    "status_class": status_class
                })
            except Exception as e:
                print(f"Error processing dependent appointment {a.id}: {e}")
                continue

        # Sort by start time
        data.sort(key=lambda x: x['start_time'])
        return JsonResponse(data, safe=False)

    except Exception as e:
        print(f"Error in doctor_day_appointments: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse([], safe=False)

def get_status_class(status, for_calendar=False):
    """Return CSS color code for status"""
    mapping = {
        'approved': '#28a745',  # green
        'pending': '#ffc107',   # yellow
        'completed': '#6c757d', # gray
        'rejected': '#dc3545'   # red
    }
    if for_calendar:
        return mapping.get(status, '#ffc107')  # fallback yellow
    else:
        # bootstrap classes for lists
        bootstrap_mapping = {
            'approved': 'bg-success text-white',
            'pending': 'bg-warning text-dark',
            'completed': 'bg-secondary text-white',
            'rejected': 'bg-danger text-white'
        }
        return bootstrap_mapping.get(status, 'bg-warning text-dark')


@login_required
@doctor_approved_required
def doctor_appointments(request):
    if request.user.role != "doctor":
        return redirect("home")

    doctor = request.user.doctor_info
    
    # Get all appointments for this doctor
    own_appointments = Appointment.objects.filter(doctor=doctor).select_related("patient")
    dependent_appointments = DependentAppointment.objects.filter(doctor=doctor).select_related("dependent_patient")

    # Add appointment_type to each appointment for template differentiation
    for a in own_appointments:
        a.appointment_type = "self"
    
    for da in dependent_appointments:
        da.appointment_type = "dependent"

    # Combine and sort by start_time
    appointments = sorted(
        list(own_appointments) + list(dependent_appointments),
        key=lambda a: a.start_time,
        reverse=True
    )

    return render(request, "doctors/appointments.html", {
        "appointments": appointments,
        "own_appointments": own_appointments,
        "dependent_appointments": dependent_appointments
    })

@login_required
@doctor_approved_required
def update_doctor_appointment_status(request, pk, action):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)
    
    appointment = get_object_or_404(Appointment, pk=pk, doctor=request.user.doctor_info)
    
    if action == "approve":
        appointment.status = "approved"
    elif action == "reject":
        appointment.status = "rejected"
    elif action == "complete":
        appointment.status = "completed"
        CompletedAppointment.objects.get_or_create(appointment=appointment)
    elif action == "no_show":  # NEW
        appointment.status = "no_show"
    else:
        return JsonResponse({"error": "Invalid action"}, status=400)
    
    appointment.save()
    return JsonResponse({
        "id": appointment.id,
        "status": appointment.status,
        "status_class": get_status_class(appointment.status)
    })

def get_status_class(status):
    """Return CSS color code for status"""
    mapping = {
        'approved': 'bg-success text-white',
        'pending': 'bg-warning text-dark',
        'completed': 'bg-secondary text-white',
        'rejected': 'bg-danger text-white',
        'no_show': 'bg-info text-white',  # NEW - using info/blue color
    }
    return mapping.get(status, 'bg-warning text-dark')

@login_required
def add_medical_record(request, patient_type, pk):
    if request.user.role not in ['staff', 'doctor']:
        messages.error(request, "Access denied")
        return redirect('home')

    # Select patient or dependent
    if patient_type == 'self':
        patient = get_object_or_404(PatientInfo, pk=pk)
    elif patient_type == 'dependent':
        patient = get_object_or_404(DependentPatient, pk=pk)
    else:
        messages.error(request, "Invalid patient type")
        return redirect('patient_list')

    if request.method == 'POST':
        record_form = MedicalRecordForm(request.POST)
        prescription_formset = PrescriptionFormSet(request.POST)

        if record_form.is_valid() and prescription_formset.is_valid():
            # Save medical record
            record = record_form.save(commit=False)
            # AUTO-ASSIGN LOGGED-IN USER
            record.created_by = request.user
            
            if patient_type == 'self':
                record.patient = patient
            else:
                record.dependent_patient = patient
            record.save()

            # Save prescriptions
            prescription_formset.instance = record
            for prescription in prescription_formset.save(commit=False):
                # AUTO-ASSIGN LOGGED-IN USER
                prescription.created_by = request.user
                prescription.save()

            # Log activity for medical record
            ActivityLog.objects.create(
                user=request.user,
                action_type="create",
                model_name="MedicalRecord",
                object_id=str(record.id),
                related_object_repr=str(record)
            )

            # Log activity for prescriptions
            for prescription in record.prescriptions.all():
                ActivityLog.objects.create(
                    user=request.user,
                    action_type="create",
                    model_name="Prescription",
                    object_id=str(prescription.id),
                    related_object_repr=str(prescription)
                )

            messages.success(request, "Medical record added successfully")
            if request.user.role == 'doctor':
                return redirect('doctor_patient_list')
            else:
                return redirect('patient_list')
    else:
        record_form = MedicalRecordForm()
        prescription_formset = PrescriptionFormSet()

    return render(request, 'medical_records/add_medical_record.html', {
        'record_form': record_form,
        'prescription_formset': prescription_formset,
        'patient': patient,
        'patient_type': patient_type
    })

@login_required
def edit_medical_record(request, pk):
    if request.user.role not in ['staff', 'doctor']:
        messages.error(request, "Access denied")
        return redirect('home')

    record = get_object_or_404(MedicalRecord, pk=pk)

    # Determine patient type
    if record.patient:
        patient = record.patient
        patient_type = 'self'
    elif record.dependent_patient:
        patient = record.dependent_patient
        patient_type = 'dependent'
    else:
        messages.error(request, "Medical record has no associated patient")
        return redirect('home')

    if request.method == 'POST':
        record_form = MedicalRecordForm(request.POST, instance=record)
        prescription_formset = PrescriptionFormSet(request.POST, instance=record)

        if record_form.is_valid() and prescription_formset.is_valid():
            record_form.save()
            
            # Save prescriptions and assign created_by if new
            for prescription in prescription_formset.save(commit=False):
                if not prescription.created_by:
                    prescription.created_by = request.user
                prescription.save()

            # Log activity for update
            ActivityLog.objects.create(
                user=request.user,
                action_type="update",
                model_name="MedicalRecord",
                object_id=str(record.id),
                related_object_repr=str(record)
            )

            for prescription in record.prescriptions.all():
                ActivityLog.objects.create(
                    user=request.user,
                    action_type="update",
                    model_name="Prescription",
                    object_id=str(prescription.id),
                    related_object_repr=str(prescription)
                )

            messages.success(request, "Medical record updated successfully")
            return redirect('view_medical_record', pk=record.pk)
    else:
        record_form = MedicalRecordForm(instance=record)
        prescription_formset = PrescriptionFormSet(instance=record)

    return render(request, 'medical_records/edit_medical_record.html', {
        'record_form': record_form,
        'prescription_formset': prescription_formset,
        'patient': patient,
        'patient_type': patient_type,
        'record': record
    })

@login_required
def view_medical_record(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk)
    prescriptions = record.prescriptions.all()  # get all prescriptions for display
    return render(request, 'medical_records/medical_record_detail.html', {
        'record': record,
        'prescriptions': prescriptions
    })

#! Not use
@login_required
def rate_doctor(request, doctor_id):
    # Only patients can rate
    if request.user.role != 'patient':
        messages.error(request, "Only patients can rate doctors.")
        return redirect('home')

    doctor = get_object_or_404(DoctorInfo, pk=doctor_id)
    patient = get_object_or_404(PatientInfo, user=request.user)

    # Check if patient already rated
    rating_instance = DoctorRating.objects.filter(patient=patient, doctor=doctor).first()

    if request.method == 'POST':
        form = DoctorRatingForm(request.POST, instance=rating_instance)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.patient = patient
            rating.doctor = doctor
            rating.save()
            messages.success(request, "Your rating has been saved!")
            return redirect('view_doctors')  # or doctor detail page
    else:
        form = DoctorRatingForm(instance=rating_instance)

    return render(request, 'doctors/rate_doctor.html', {
        'form': form,
        'doctor': doctor
    })
    
@login_required
def rate_doctor_page(request, doctor_id):
    doctor = get_object_or_404(DoctorInfo, id=doctor_id, is_approved=True)
    return render(request, "doctors/rate_doctor.html", {"doctor": doctor})

@login_required
def submit_doctor_rating(request, doctor_id):
    if request.user.role != 'patient':
        messages.error(request, "Only patients can rate doctors.")
        return redirect('home')

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("view_doctors")

    rating_value = request.POST.get("rating")
    review_text = request.POST.get("comment", "")

    if not rating_value:
        messages.error(request, "Rating is required.")
        return redirect("rate_doctor", doctor_id=doctor_id)

    doctor = get_object_or_404(DoctorInfo, id=doctor_id, is_approved=True)
    patient = get_object_or_404(PatientInfo, user=request.user)

    # Check if patient already rated
    rating_instance = DoctorRating.objects.filter(patient=patient, doctor=doctor).first()

    if rating_instance:
        old_rating = rating_instance.rating
        rating_instance.rating = rating_value
        rating_instance.review = review_text
        rating_instance.save()

        # Log update
        ActivityLog.objects.create(
            user=request.user,
            action_type="update",
            model_name="DoctorRating",
            object_id=str(rating_instance.id),
            related_object_repr=f"{patient.patient_id} → {doctor.user.get_full_name()}",
            description=f"Updated rating from {old_rating} to {rating_value}"
        )
    else:
        rating_instance = DoctorRating.objects.create(
            patient=patient,
            doctor=doctor,
            rating=rating_value,
            review=review_text
        )

        # Log create
        ActivityLog.objects.create(
            user=request.user,
            action_type="create",
            model_name="DoctorRating",
            object_id=str(rating_instance.id),
            related_object_repr=f"{patient.patient_id} → {doctor.user.get_full_name()}",
            description=f"Rated {rating_value} stars"
        )

    messages.success(request, "Your rating has been submitted successfully!")
    return redirect("view_doctors")

@login_required
def delete_patient_vitals(request, pk, patient_type='self'):
    """Delete patient vitals record"""
    if request.user.role not in ['staff', 'patient']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Get vitals
    if patient_type == 'self':
        vitals = get_object_or_404(PatientVitals, pk=pk)
        patient = vitals.patient
        
        # Permission check
        if request.user.role == 'patient' and patient.user != request.user:
            messages.error(request, "Access denied.")
            return redirect('medical_records')
    else:
        vitals = get_object_or_404(DependentPatientVitals, pk=pk)
        patient = vitals.dependent_patient
        
        # Permission check
        if request.user.role == 'patient' and patient.guardian != request.user:
            messages.error(request, "Access denied.")
            return redirect('medical_records')
    
    if request.method == 'POST':
        vitals_id = vitals.id
        vitals_repr = f"Vitals recorded at {vitals.recorded_at.strftime('%Y-%m-%d %H:%M')}"
        
        vitals.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='delete',
            model_name=vitals.__class__.__name__,
            object_id=str(vitals_id),
            related_object_repr=vitals_repr
        )
        
        messages.success(request, "Vitals record deleted successfully.")
        return redirect('vital_history', patient_type=patient_type, pk=patient.pk)
    
    return render(request, 'medical_records/confirm_delete.html', {
        'record_type': 'Vitals',
        'record': vitals,
        'patient_type': patient_type,
        'patient': patient
    })

@login_required
def delete_patient_allergy(request, pk, patient_type='self'):
    """Delete patient allergy record"""
    if request.user.role not in ['staff', 'patient']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    if patient_type == 'self':
        allergy = get_object_or_404(PatientAllergy, pk=pk)
        patient = allergy.patient
        
        if request.user.role == 'patient' and patient.user != request.user:
            messages.error(request, "Access denied.")
            return redirect('medical_records')
    else:
        allergy = get_object_or_404(DependentPatientAllergy, pk=pk)
        patient = allergy.dependent_patient
        
        if request.user.role == 'patient' and patient.guardian != request.user:
            messages.error(request, "Access denied.")
            return redirect('medical_records')
    
    if request.method == 'POST':
        allergy_name = allergy.allergy_name
        allergy_id = allergy.id
        
        allergy.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='delete',
            model_name=allergy.__class__.__name__,
            object_id=str(allergy_id),
            related_object_repr=f"Allergy: {allergy_name}"
        )
        
        messages.success(request, "Allergy deleted successfully.")
        if request.user.role == 'patient':
            return redirect('medical_records')
        else:
            return redirect('patient_list')
    
    return render(request, 'medical_records/confirm_delete.html', {
        'record_type': 'Allergy',
        'record': allergy,
        'patient_type': patient_type,
        'patient': patient
    })


@login_required
def delete_patient_medication(request, pk, patient_type='self'):
    """Delete patient medication record"""
    if request.user.role not in ['staff', 'patient']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    if patient_type == 'self':
        medication = get_object_or_404(PatientMedication, pk=pk)
        patient = medication.patient
        
        if request.user.role == 'patient' and patient.user != request.user:
            messages.error(request, "Access denied.")
            return redirect('medical_records')
    else:
        medication = get_object_or_404(DependentPatientMedication, pk=pk)
        patient = medication.dependent_patient
        
        if request.user.role == 'patient' and patient.guardian != request.user:
            messages.error(request, "Access denied.")
            return redirect('medical_records')
    
    if request.method == 'POST':
        med_name = medication.medication_name
        med_id = medication.id
        
        medication.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='delete',
            model_name=medication.__class__.__name__,
            object_id=str(med_id),
            related_object_repr=f"Medication: {med_name}"
        )
        
        messages.success(request, "Medication deleted successfully.")
        return redirect('medication_history', patient_type=patient_type, pk=patient.pk)
    
    return render(request, 'medical_records/confirm_delete.html', {
        'record_type': 'Medication',
        'record': medication,
        'patient_type': patient_type,
        'patient': patient
    })


@login_required
def delete_medical_record(request, pk):
    """Delete a complete medical record"""
    if request.user.role not in ['staff', 'doctor']:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    medical_record = get_object_or_404(MedicalRecord, pk=pk)
    
    # Determine patient for redirect
    if medical_record.patient:
        patient = medical_record.patient
        patient_type = 'self'
    elif medical_record.dependent_patient:
        patient = medical_record.dependent_patient
        patient_type = 'dependent'
    else:
        messages.error(request, "Medical record has no associated patient.")
        return redirect('patient_list')
    
    if request.method == 'POST':
        record_id = medical_record.id
        record_repr = f"Medical Record: {medical_record.reason_for_visit}"
        
        # Delete prescriptions first (they cascade)
        prescriptions = medical_record.prescriptions.all()
        for prescription in prescriptions:
            # Log each prescription deletion
            ActivityLog.objects.create(
                user=request.user,
                action_type='delete',
                model_name='Prescription',
                object_id=str(prescription.id),
                related_object_repr=f"Prescription: {prescription.medication_name}"
            )
        
        medical_record.delete()
        
        # Log activity for medical record
        ActivityLog.objects.create(
            user=request.user,
            action_type='delete',
            model_name='MedicalRecord',
            object_id=str(record_id),
            related_object_repr=record_repr
        )
        
        messages.success(request, "Medical record deleted successfully.")
        if request.user.role == 'doctor':
            return redirect('doctor_patient_list')
        else:
            return redirect('patient_list')
    
    return render(request, 'medical_records/confirm_delete.html', {
        'record_type': 'Medical Record',
        'record': medical_record,
        'patient_type': patient_type,
        'patient': patient
    })

@login_required
def manager_users_list(request):
    """View and manage all users (manager only)"""
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    # Get filter parameters
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    
    # Base queryset - exclude patients
    users = User.objects.exclude(role='patient').select_related(
        'doctor_info', 'doctorprofile', 'staffprofile', 'managerprofile'
    ).order_by('-date_joined')
    
    # Apply role filter
    if role_filter != 'all':
        users = users.filter(role=role_filter)
    
    # Apply search
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Apply status filter for doctors
    if status_filter != 'all' and role_filter in ['doctor', 'all']:
        if status_filter == 'pending':
            users = users.filter(role='doctor', doctor_info__is_approved=False, doctor_info__is_rejected=False)
        elif status_filter == 'approved':
            users = users.filter(role='doctor', doctor_info__is_approved=True)
        elif status_filter == 'rejected':
            users = users.filter(role='doctor', doctor_info__is_rejected=True)
    
    # Get counts for statistics
    total_doctors = User.objects.filter(role='doctor').count()
    total_staff = User.objects.filter(role='staff').count()
    total_managers = User.objects.filter(role='manager').count()
    pending_doctors = User.objects.filter(
        role='doctor',
        doctor_info__is_approved=False,
        doctor_info__is_rejected=False
    ).count()
    
    # Prepare user data with additional info
    user_list = []
    for user in users:
        user_data = {
            'user': user,
            'profile': None,
            'status': None,
            'additional_info': {}
        }
        
        if user.role == 'doctor':
            user_data['profile'] = getattr(user, 'doctor_info', None)
            if user_data['profile']:
                if user_data['profile'].is_approved:
                    user_data['status'] = 'approved'
                elif user_data['profile'].is_rejected:
                    user_data['status'] = 'rejected'
                else:
                    user_data['status'] = 'pending'
                user_data['additional_info']['specialization'] = user_data['profile'].specialization
                user_data['additional_info']['license'] = user_data['profile'].license_number
        elif user.role == 'staff':
            user_data['profile'] = getattr(user, 'staffprofile', None)
            user_data['status'] = 'active'
            if user_data['profile']:
                user_data['additional_info']['staff_id'] = user_data['profile'].staff_id
        elif user.role == 'manager':
            user_data['profile'] = getattr(user, 'managerprofile', None)
            user_data['status'] = 'active'
            if user_data['profile']:
                user_data['additional_info']['manager_id'] = user_data['profile'].manager_id
        
        user_list.append(user_data)
    
    context = {
        'user_list': user_list,
        'role_filter': role_filter,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_doctors': total_doctors,
        'total_staff': total_staff,
        'total_managers': total_managers,
        'pending_doctors': pending_doctors,
    }
    
    return render(request, "managers/users_list.html", context)


@login_required
def manager_user_details(request, user_id):
    """View detailed information about a user"""
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    user = get_object_or_404(User, id=user_id)
    
    # Get role-specific profile
    profile = None
    additional_data = {}
    
    if user.role == 'doctor':
        profile = getattr(user, 'doctor_info', None)
        if profile:
            additional_data = {
                'specialization': profile.specialization,
                'license_number': profile.license_number,
                'years_experience': profile.years_experience,
                'bio': profile.bio,
                'qualifications': profile.qualifications,
                'is_approved': profile.is_approved,
                'is_rejected': profile.is_rejected,
                'approved_at': profile.approved_at,
            }
    elif user.role == 'staff':
        profile = getattr(user, 'staffprofile', None)
        if profile:
            additional_data = {
                'staff_id': profile.staff_id,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
            }
    elif user.role == 'manager':
        profile = getattr(user, 'managerprofile', None)
        if profile:
            additional_data = {
                'manager_id': profile.manager_id,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
            }
    
    # Get activity logs for this user
    recent_activities = ActivityLog.objects.filter(user=user).order_by('-timestamp')[:10]
    
    context = {
        'viewed_user': user,
        'profile': profile,
        'additional_data': additional_data,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'managers/user_details.html', context)


@login_required
def manager_deactivate_user(request, user_id):
    """Deactivate a user account (manager only)"""
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent self-deactivation
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('manager_users_list')
    
    # Prevent deactivating patients
    if user.role == 'patient':
        messages.error(request, "Patient accounts cannot be deactivated from this interface.")
        return redirect('manager_users_list')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        user.is_active = False
        user.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='update',
            model_name='User',
            object_id=str(user.id),
            related_object_repr=user.get_full_name() or user.username,
            description=f"Deactivated user account. Reason: {reason}"
        )
        
        messages.success(request, f"User {user.get_full_name() or user.username} has been deactivated.")
        return redirect('manager_users_list')
    
    return render(request, 'managers/confirm_deactivate_user.html', {'viewed_user': user})


@login_required
def manager_activate_user(request, user_id):
    """Reactivate a user account (manager only)"""
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    user = get_object_or_404(User, id=user_id)
    
    if user.is_active:
        messages.info(request, "User is already active.")
        return redirect('manager_users_list')
    
    user.is_active = True
    user.save()
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action_type='update',
        model_name='User',
        object_id=str(user.id),
        related_object_repr=user.get_full_name() or user.username,
        description="Reactivated user account"
    )
    
    messages.success(request, f"User {user.get_full_name() or user.username} has been reactivated.")
    return redirect('manager_users_list')


@login_required
def manager_change_user_role(request, user_id):
    """Change a user's role (manager only)"""
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent changing own role
    if user == request.user:
        messages.error(request, "You cannot change your own role.")
        return redirect('manager_users_list')
    
    # Prevent changing patient roles
    if user.role == 'patient':
        messages.error(request, "Patient roles cannot be changed from this interface.")
        return redirect('manager_users_list')
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        
        if new_role not in ['doctor', 'staff', 'manager']:
            messages.error(request, "Invalid role selected.")
            return redirect('manager_users_list')
        
        old_role = user.role
        user.role = new_role
        user.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action_type='update',
            model_name='User',
            object_id=str(user.id),
            related_object_repr=user.get_full_name() or user.username,
            description=f"Changed role from {old_role} to {new_role}"
        )
        
        messages.success(request, f"User role changed from {old_role} to {new_role}.")
        return redirect('manager_users_list')
    
    return render(request, 'managers/change_user_role.html', {'viewed_user': user})

@login_required
def appointment_recommendations(request):
    """Show intelligent appointment recommendations for patient"""
    if request.user.role != "patient":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    # Get doctor_id from query params
    doctor_id = request.GET.get('doctor')
    
    if not doctor_id:
        messages.error(request, "Please select a doctor first.")
        return redirect("patient_calendar")
    
    doctor = get_object_or_404(DoctorInfo, id=doctor_id, is_approved=True)
    
    # Get patient info
    try:
        patient = PatientInfo.objects.get(user=request.user)
        patient_type = 'self'
    except PatientInfo.DoesNotExist:
        messages.error(request, "Please complete your profile first.")
        return redirect("edit_my_patient_info")
    
    # Get recommendations
    recommendations = get_appointment_recommendations(patient, doctor, patient_type)
    
    # Format recommendations for display
    formatted_slots = []
    for item in recommendations['recommended_times'][:10]:  # Top 10
        slot = item['slot']
        formatted_slots.append({
            'datetime': slot['datetime'],
            'date': slot['date'].strftime('%A, %B %d, %Y'),
            'time': slot['datetime'].strftime('%I:%M %p'),
            'score': item['score'],
            'reasons': item['reasons'],
            'start_iso': slot['datetime'].isoformat(),
            'end_iso': (slot['datetime'] + timedelta(minutes=30)).isoformat()
        })
    
    # Get urgency level
    urgency_score = recommendations['urgency_score']
    if urgency_score >= 75:
        urgency_level = 'high'
        urgency_label = 'High Priority'
        urgency_color = '#ef4444'
    elif urgency_score >= 50:
        urgency_level = 'medium'
        urgency_label = 'Moderate Priority'
        urgency_color = '#f59e0b'
    else:
        urgency_level = 'low'
        urgency_label = 'Low Priority'
        urgency_color = '#10b981'
    
    context = {
        'doctor': doctor,
        'patient': patient,
        'recommendations': formatted_slots,
        'urgency_score': urgency_score,
        'urgency_level': urgency_level,
        'urgency_label': urgency_label,
        'urgency_color': urgency_color,
        'reasoning': recommendations['reasoning'],
    }
    
    return render(request, 'calendar/appointment_recommendations.html', context)

@login_required
def manager_dashboard(request):
    """Manager dashboard with comprehensive analytics"""
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    ninety_days_ago = today - timedelta(days=90)
    
    # === OVERVIEW METRICS ===
    # Users
    total_doctors = User.objects.filter(role='doctor').count()
    active_doctors = DoctorInfo.objects.filter(is_approved=True).count()
    pending_doctors = DoctorInfo.objects.filter(is_approved=False, is_rejected=False).count()
    total_staff = User.objects.filter(role='staff').count()
    
    # Patient counts
    total_self_patients = User.objects.filter(role='patient').count()
    total_dependents = DependentPatient.objects.count()
    total_patients = total_self_patients + total_dependents 
    
    # Appointments
    total_appointments = Appointment.objects.count() + DependentAppointment.objects.count()
    pending_appointments = (
        Appointment.objects.filter(status='pending').count() +
        DependentAppointment.objects.filter(status='pending').count()
    )
    completed_appointments = (
        Appointment.objects.filter(status='completed').count() +
        DependentAppointment.objects.filter(status='completed').count()
    )
    
    # Today's appointments
    today_appointments = (
        Appointment.objects.filter(start_time__date=today).count() +
        DependentAppointment.objects.filter(start_time__date=today).count()
    )
    
    # Medical records
    total_medical_records = MedicalRecord.objects.count()
    records_this_month = MedicalRecord.objects.filter(
        created_at__gte=today.replace(day=1)
    ).count()
    
    # === APPOINTMENT TRENDS (Last 30 days) ===
    appointment_trends = []
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        count = (
            Appointment.objects.filter(start_time__date=date).count() +
            DependentAppointment.objects.filter(start_time__date=date).count()
        )
        appointment_trends.append({
            'date': date.strftime('%b %d'),
            'count': count
        })
    
    # === APPOINTMENT STATUS BREAKDOWN ===
    status_data = {}
    for status in ['pending', 'approved', 'completed', 'rejected', 'no_show']:
        count = (
            Appointment.objects.filter(status=status).count() +
            DependentAppointment.objects.filter(status=status).count()
        )
        status_data[status] = count
    
    # === DOCTOR PERFORMANCE ===
    doctor_performance = []
    doctors = DoctorInfo.objects.filter(is_approved=True).select_related('user', 'specialization')
    
    for doctor in doctors[:10]:  # Top 10
        appt_count = (
            Appointment.objects.filter(doctor=doctor).count() +
            DependentAppointment.objects.filter(doctor=doctor).count()
        )
        completed = (
            Appointment.objects.filter(doctor=doctor, status='completed').count() +
            DependentAppointment.objects.filter(doctor=doctor, status='completed').count()
        )
        avg_rating = DoctorRating.objects.filter(doctor=doctor).aggregate(
            avg=Avg('rating')
        )['avg'] or 0
        
        doctor_performance.append({
            'name': doctor.user.get_full_name(),
            'specialization': doctor.specialization.name if doctor.specialization else 'General',
            'appointments': appt_count,
            'completed': completed,
            'rating': round(avg_rating, 1)
        })
    
    # Sort by appointments
    doctor_performance.sort(key=lambda x: x['appointments'], reverse=True)
    
    # === SPECIALIZATION DISTRIBUTION ===
    specialization_data = []
    specializations = Specialization.objects.annotate(
        doctor_count=Count('doctors', filter=Q(doctors__is_approved=True))
    ).filter(doctor_count__gt=0)
    
    for spec in specializations:
        specialization_data.append({
            'name': spec.name,
            'count': spec.doctor_count
        })
    
    # === PATIENT GROWTH (Last 6 months) ===
    patient_growth = []
    for i in range(6, 0, -1):
        month = today - timedelta(days=30*i)
        month_start = month.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        count = User.objects.filter(
            role='patient',
            date_joined__gte=month_start,
            date_joined__lte=month_end
        ).count()
        
        patient_growth.append({
            'month': month.strftime('%b'),
            'count': count
        })
    
    # === RECENT ACTIVITY ===
    recent_activities = ActivityLog.objects.select_related('user').order_by('-timestamp')[:15]
    
    # === TOP RATED DOCTORS ===
    top_rated_doctors = []
    doctors_with_ratings = DoctorInfo.objects.filter(
        is_approved=True,
        ratings__isnull=False
    ).annotate(
        avg_rating=Avg('ratings__rating'),
        rating_count=Count('ratings')
    ).filter(rating_count__gte=3).order_by('-avg_rating')[:5]
    
    for doctor in doctors_with_ratings:
        top_rated_doctors.append({
            'name': doctor.user.get_full_name(),
            'specialization': doctor.specialization.name if doctor.specialization else 'General',
            'rating': round(doctor.avg_rating, 1),
            'count': doctor.rating_count
        })
    
    # === BUSIEST HOURS ===
    busiest_hours = []
    for hour in range(8, 18):  # 8 AM to 6 PM
        count = (
            Appointment.objects.filter(
                start_time__hour=hour,
                start_time__gte=thirty_days_ago
            ).count() +
            DependentAppointment.objects.filter(
                start_time__hour=hour,
                start_time__gte=thirty_days_ago
            ).count()
        )
        busiest_hours.append({
            'hour': f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}",
            'count': count
        })
    
    # === APPOINTMENT COMPLETION RATE ===
    total_past_appointments = (
        Appointment.objects.filter(start_time__lt=timezone.now()).count() +
        DependentAppointment.objects.filter(start_time__lt=timezone.now()).count()
    )
    
    completion_rate = 0
    if total_past_appointments > 0:
        completion_rate = round((completed_appointments / total_past_appointments) * 100, 1)
    
    context = {
        # Overview
        'total_doctors': total_doctors,
        'active_doctors': active_doctors,
        'pending_doctors': pending_doctors,
        'total_staff': total_staff,
        'total_patients': total_patients, 
        'total_dependents': total_dependents,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'completed_appointments': completed_appointments,
        'today_appointments': today_appointments,
        'total_medical_records': total_medical_records,
        'records_this_month': records_this_month,
        'completion_rate': completion_rate,
        
        # Charts data
        'appointment_trends': json.dumps(appointment_trends),
        'status_data': json.dumps(status_data),
        'specialization_data': json.dumps(specialization_data),
        'patient_growth': json.dumps(patient_growth),
        'busiest_hours': json.dumps(busiest_hours),
        
        # Tables
        'doctor_performance': doctor_performance,
        'top_rated_doctors': top_rated_doctors,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'managers/dashboard.html', context)


@login_required
def manager_reports(request):
    """Comprehensive reporting system"""
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    # Get filter parameters
    report_type = request.GET.get('type', 'appointments')
    date_range = request.GET.get('range', '30')  # days
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Calculate date range
    today = timezone.now().date()
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            start = today - timedelta(days=int(date_range))
            end = today
    else:
        start = today - timedelta(days=int(date_range))
        end = today
    
    report_data = {}
    
    if report_type == 'appointments':
        report_data = generate_appointments_report(start, end)
    elif report_type == 'doctors':
        report_data = generate_doctors_report(start, end)
    elif report_type == 'patients':
        report_data = generate_patients_report(start, end)
    elif report_type == 'revenue':
        report_data = generate_revenue_report(start, end)
    
    context = {
        'report_type': report_type,
        'date_range': date_range,
        'start_date': start.strftime('%Y-%m-%d'),
        'end_date': end.strftime('%Y-%m-%d'),
        'report_data': report_data,
    }
    
    return render(request, 'managers/reports.html', context)


def generate_appointments_report(start_date, end_date):
    """Generate detailed appointments report"""
    appointments = Appointment.objects.filter(
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    )
    dependent_appointments = DependentAppointment.objects.filter(
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    )
    
    total = appointments.count() + dependent_appointments.count()
    
    # Status breakdown
    status_breakdown = {
        'pending': appointments.filter(status='pending').count() + 
                   dependent_appointments.filter(status='pending').count(),
        'approved': appointments.filter(status='approved').count() + 
                    dependent_appointments.filter(status='approved').count(),
        'completed': appointments.filter(status='completed').count() + 
                     dependent_appointments.filter(status='completed').count(),
        'rejected': appointments.filter(status='rejected').count() + 
                    dependent_appointments.filter(status='rejected').count(),
        'no_show': appointments.filter(status='no_show').count() + 
                   dependent_appointments.filter(status='no_show').count(),
    }
    
    # Daily breakdown
    daily_breakdown = []
    current = start_date
    while current <= end_date:
        count = (
            appointments.filter(start_time__date=current).count() +
            dependent_appointments.filter(start_time__date=current).count()
        )
        daily_breakdown.append({
            'date': current.strftime('%Y-%m-%d'),
            'count': count
        })
        current += timedelta(days=1)
    
    # Top doctors by appointments
    top_doctors = []
    doctors = DoctorInfo.objects.filter(is_approved=True)
    for doctor in doctors:
        count = (
            appointments.filter(doctor=doctor).count() +
            dependent_appointments.filter(doctor=doctor).count()
        )
        if count > 0:
            top_doctors.append({
                'name': doctor.user.get_full_name(),
                'count': count
            })
    top_doctors.sort(key=lambda x: x['count'], reverse=True)
    top_doctors = top_doctors[:10]
    
    return {
        'total': total,
        'status_breakdown': status_breakdown,
        'daily_breakdown': daily_breakdown,
        'top_doctors': top_doctors,
    }


def generate_doctors_report(start_date, end_date):
    """Generate doctors performance report"""
    doctors = DoctorInfo.objects.filter(is_approved=True).select_related('user', 'specialization')
    
    doctor_stats = []
    for doctor in doctors:
        appointments = Appointment.objects.filter(
            doctor=doctor,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).count() + DependentAppointment.objects.filter(
            doctor=doctor,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).count()
        
        completed = Appointment.objects.filter(
            doctor=doctor,
            status='completed',
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).count() + DependentAppointment.objects.filter(
            doctor=doctor,
            status='completed',
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).count()
        
        avg_rating = DoctorRating.objects.filter(doctor=doctor).aggregate(
            avg=Avg('rating')
        )['avg'] or 0
        
        doctor_stats.append({
            'name': doctor.user.get_full_name(),
            'specialization': doctor.specialization.name if doctor.specialization else 'General',
            'appointments': appointments,
            'completed': completed,
            'rating': round(avg_rating, 1),
            'completion_rate': round((completed / appointments * 100) if appointments > 0 else 0, 1)
        })
    
    doctor_stats.sort(key=lambda x: x['appointments'], reverse=True)
    
    return {
        'total_doctors': len(doctor_stats),
        'doctor_stats': doctor_stats,
    }


def generate_patients_report(start_date, end_date):
    """Generate patients statistics report"""

    # New patient accounts created in date range
    new_patients = User.objects.filter(
        role='patient',
        date_joined__date__gte=start_date,
        date_joined__date__lte=end_date
    ).count()

    # Total patient accounts (self profiles)
    total_self_patients = User.objects.filter(role='patient').count()
    
    # Total dependents
    total_dependents = DependentPatient.objects.count()
    
    # FIXED: Total patients = self patients + dependents
    total_patients = total_self_patients + total_dependents

    # ✅ SAFE age distribution keys
    age_groups = {
        'age_0_18': 0,
        'age_19_35': 0,
        'age_36_50': 0,
        'age_51_65': 0,
        'age_65_plus': 0
    }

    # Count ages from self patients
    patients = PatientInfo.objects.all()
    for patient in patients:
        age = patient.age or 0

        if age <= 18:
            age_groups['age_0_18'] += 1
        elif age <= 35:
            age_groups['age_19_35'] += 1
        elif age <= 50:
            age_groups['age_36_50'] += 1
        elif age <= 65:
            age_groups['age_51_65'] += 1
        else:
            age_groups['age_65_plus'] += 1
    
    # Count ages from dependents
    dependents = DependentPatient.objects.all()
    for dependent in dependents:
        age = dependent.age or 0

        if age <= 18:
            age_groups['age_0_18'] += 1
        elif age <= 35:
            age_groups['age_19_35'] += 1
        elif age <= 50:
            age_groups['age_36_50'] += 1
        elif age <= 65:
            age_groups['age_51_65'] += 1
        else:
            age_groups['age_65_plus'] += 1

    # Gender distribution from both self patients and dependents
    gender_dist = {
        'male': PatientInfo.objects.filter(gender='M').count() +
                DependentPatient.objects.filter(gender='M').count(),
        'female': PatientInfo.objects.filter(gender='F').count() +
                  DependentPatient.objects.filter(gender='F').count(),
    }

    return {
        'new_patients': new_patients,  # New patient accounts only
        'total_patients': total_patients,  # FIXED: Self + Dependents
        'total_self_patients': total_self_patients,  # Just for reference
        'total_dependents': total_dependents,
        'age_distribution': age_groups,
        'gender_distribution': gender_dist,
    }

def generate_revenue_report(start_date, end_date):
    """Generate revenue projections (placeholder for future implementation)"""
    # This is a placeholder for future revenue tracking
    completed_appointments = (
        Appointment.objects.filter(
            status='completed',
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).count() +
        DependentAppointment.objects.filter(
            status='completed',
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        ).count()
    )
    
    # Assuming $50 per appointment (this should come from a pricing model)
    estimated_revenue = completed_appointments * 50
    
    return {
        'completed_appointments': completed_appointments,
        'estimated_revenue': estimated_revenue,
        'note': 'Revenue tracking is a placeholder. Implement actual pricing model.'
    }

@login_required
def export_report(request):
    """Handle report export requests"""
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")
    
    # Get parameters
    report_type = request.GET.get('type', 'appointments')
    export_format = request.GET.get('format', 'pdf')  # 'pdf' or 'csv'
    date_range = request.GET.get('range', '30')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Calculate date range
    today = timezone.now().date()
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            start = today - timedelta(days=int(date_range))
            end = today
    else:
        start = today - timedelta(days=int(date_range))
        end = today
    
    # Format dates for filenames
    start_str = start.strftime('%Y-%m-%d')
    end_str = end.strftime('%Y-%m-%d')
    
    # Generate report data
    if report_type == 'appointments':
        report_data = generate_appointments_report(start, end)
        if export_format == 'csv':
            return ReportExporter.export_appointments_csv(report_data, start_str, end_str)
        else:
            return ReportExporter.export_appointments_pdf(report_data, start_str, end_str)
    
    elif report_type == 'doctors':
        report_data = generate_doctors_report(start, end)
        if export_format == 'csv':
            return ReportExporter.export_doctors_csv(report_data, start_str, end_str)
        else:
            return ReportExporter.export_doctors_pdf(report_data, start_str, end_str)
    
    elif report_type == 'patients':
        report_data = generate_patients_report(start, end)
        if export_format == 'csv':
            return ReportExporter.export_patients_csv(report_data, start_str, end_str)
        else:
            return ReportExporter.export_patients_pdf(report_data, start_str, end_str)
    
    elif report_type == 'revenue':
        # Revenue export is simpler, create inline
        report_data = generate_revenue_report(start, end)
        
        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="revenue_report_{start_str}_to_{end_str}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Revenue Report'])
            writer.writerow([f'Period: {start_str} to {end_str}'])
            writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}'])
            writer.writerow([])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Completed Appointments', report_data['completed_appointments']])
            writer.writerow(['Estimated Revenue', f"${report_data['estimated_revenue']}"])
            writer.writerow([])
            writer.writerow(['Note', report_data['note']])
            
            return response
        else:
            # Simple PDF for revenue
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph("Revenue Report", styles['Title']))
            elements.append(Spacer(1, 0.3*inch))
            
            data = [
                ['Report Period:', f'{start_str} to {end_str}'],
                ['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M')],
                ['', ''],
                ['Completed Appointments:', str(report_data['completed_appointments'])],
                ['Estimated Revenue:', f"${report_data['estimated_revenue']}"],
            ]
            
            table = Table(data, colWidths=[2.5*inch, 3*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph(f"<i>Note: {report_data['note']}</i>", styles['Normal']))
            
            doc.build(elements)
            pdf = buffer.getvalue()
            buffer.close()
            
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="revenue_report_{start_str}_to_{end_str}.pdf"'
            response.write(pdf)
            
            return response
    
    messages.error(request, "Invalid report type.")
    return redirect('manager_reports')