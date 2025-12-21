from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from datetime import datetime, timedelta, date
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from calendar import monthrange
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt

from .models import (
    PatientInfo,
    DependentPatient,
    DoctorInfo,
    Appointment,
    DoctorAvailability,
    CompletedAppointment,
    CustomDoctorAvailability,
    MedicalRecord
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
    MedicalRecordForm
)

# Authentication
def home(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("home")
        messages.error(request, "Invalid username or password. Please try again...")

    doctor_info = None
    if request.user.is_authenticated and request.user.role == "doctor":
        doctor_info = getattr(request.user, "doctor_info", None)

    return render(request, "home.html", {
        "doctor_info": doctor_info
    })

@login_required
def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")

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
    Always returns JSON with 'html' key, even if patient not found.
    """
    try:
        user_role = getattr(request.user, 'role', None)
        patient = None
        patient_type = None

        # --- Try self patient first ---
        if user_role in ['staff', 'doctor']:
            patient = PatientInfo.objects.filter(pk=pk).first()
            if patient:
                patient_type = 'self'
        else:
            patient = PatientInfo.objects.filter(pk=pk, user=request.user).first()
            if patient:
                patient_type = 'self'

        # --- Try dependent patient ---
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

        # --- Fetch related objects safely ---
        vitals = getattr(patient, 'vitals', None)
        if vitals:
            vitals = vitals.last()  # Get latest vital record

        # Medications
        medications = getattr(patient, 'medications', None) or getattr(patient, 'patientmedication_set', None)
        medications = medications.all() if medications else []

        # Allergies
        allergies = getattr(patient, 'allergies', None) or getattr(patient, 'patientallergy_set', None)
        allergies = allergies.all() if allergies else []

        # Medical history
        if patient_type == 'self':
            medical_history = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')
        elif patient_type == 'dependent':
            medical_history = MedicalRecord.objects.filter(dependent_patient=patient).order_by('-created_at')
        else:
            medical_history = []

        # --- Last appointment ---
        last_schedule = None
        try:
            if patient_type == 'self' and getattr(patient, 'user', None):
                last_appointment = Appointment.objects.filter(
                    patient=patient.user,
                    status='completed'
                ).order_by('-start_time').first()
            elif patient_type == 'dependent':
                last_appointment = Appointment.objects.filter(
                    dependent_patient=patient,
                    status='completed'
                ).order_by('-start_time').first()
            else:
                last_appointment = None

            if last_appointment:
                last_schedule = last_appointment.start_time
        except Exception as e:
            print(f"Error fetching last appointment for patient {pk}: {e}")
            last_schedule = None

        # --- Render partial template ---
        html = render_to_string(
            'patients/partials/patient_details.html',
            {
                "patient": patient,
                "patient_type": patient_type,
                "vitals": vitals,
                "medications": medications,
                "allergies": allergies,
                "medical_history": medical_history,
                "last_schedule": last_schedule,
                "user": request.user,
            },
            request=request
        )

        return JsonResponse({'html': html})

    except Exception as e:
        print(f"AJAX error for patient {pk}: {e}")
        return JsonResponse({'html': f'<p class="muted">Failed to load patient details: {e}</p>'})

@login_required
def doctor_patient_list(request):
    if getattr(request.user, "role", None) != "doctor":
        messages.error(request, "Access denied.")
        return redirect("home")

    doctor = request.user.doctor_info

    # Get users (self patients) who have appointments with this doctor
    user_ids = Appointment.objects.filter(
        doctor=doctor,
        patient__isnull=False
    ).values_list('patient_id', flat=True).distinct()

    # Get dependent patients who have appointments with this doctor
    dependent_ids = Appointment.objects.filter(
        doctor=doctor,
        dependent_patient__isnull=False
    ).values_list('dependent_patient_id', flat=True).distinct()

    patients = []

    # Fetch self patients (linked via User)
    for p in PatientInfo.objects.filter(user_id__in=user_ids).select_related('user'):
        setattr(p, "patient_type", "self")
        patients.append(p)

    # Fetch dependent patients
    for d in DependentPatient.objects.filter(patient_id__in=dependent_ids):
        setattr(d, "patient_type", "dependent")
        patients.append(d)

    # Optional: sort by name
    patients.sort(key=lambda x: x.user.get_full_name() if hasattr(x, 'user') else x.full_name)

    return render(request, "doctors/patient_list.html", {"patients": patients})

# USER PATIENT PROFILE
@login_required
def edit_my_patient_info(request):
    try:
        patient_info = PatientInfo.objects.get(user=request.user)
    except PatientInfo.DoesNotExist:
        # Create an unsaved instance so we don't attempt to save
        # required fields (like birthdate) before the user submits the form.
        patient_info = PatientInfo(user=request.user)

    user_form = UserBasicInfoForm(instance=request.user)
    patient_form = PatientInfoForm(instance=patient_info)

    if request.method == "POST":
        user_form = UserBasicInfoForm(request.POST, instance=request.user)
        patient_form = PatientInfoForm(request.POST, instance=patient_info)

        if user_form.is_valid() and patient_form.is_valid():
            user_form.save()
            patient_form.save()
            messages.success(request, "Profile updated.")
            return redirect("medical_records")

    return render(request, "patients/edit_my_profile.html", {
        "user_form": user_form,
        "patient_form": patient_form,
    })

# DEPENDENT PATIENTS
@login_required
def add_dependent(request):
    if request.method == "POST":
        form = DependentPatientForm(request.POST)
        if form.is_valid():
            dependent = form.save(commit=False)
            dependent.guardian = request.user
            dependent.save()
            messages.success(request, "Dependent patient added successfully.")
            return redirect("medical_records")
    else:
        form = DependentPatientForm()

    return render(request, "patients/add_dependent.html", {"form": form})

@login_required
def edit_dependent(request, pk):
    dependent = get_object_or_404(
        DependentPatient,
        pk=pk,
        guardian=request.user
    )

    if request.method == "POST":
        form = DependentPatientForm(request.POST, instance=dependent)
        if form.is_valid():
            form.save()
            messages.success(request, "Dependent patient updated.")
            return redirect("medical_records")
    else:
        form = DependentPatientForm(instance=dependent)

    return render(request, "patients/edit_dependent.html", {"form": form})

# VITALS
@login_required
def add_patient_vitals(request, patient_type, pk):
    if patient_type == "self":
        patient = get_object_or_404(PatientInfo, pk=pk) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(PatientInfo, pk=pk, user=request.user)
        form_class = PatientVitalsForm
    else:
        patient = get_object_or_404(DependentPatient, pk=pk) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(DependentPatient, pk=pk, guardian=request.user)
        form_class = DependentPatientVitalsForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            vitals = form.save(commit=False)
            if patient_type == "self":
                vitals.patient = patient
            else:
                vitals.dependent_patient = patient
            vitals.save()
            messages.success(request, "Vitals added successfully.")
            return redirect("patient_list" if getattr(request.user, 'role', None) == 'staff' else "medical_records")
    else:
        form = form_class()

    return render(request, "patients/add_vitals.html", {"form": form, "patient": patient})

# ALLERGIES
@login_required
def add_patient_allergy(request, patient_type, pk):
    if patient_type == "self":
        patient = get_object_or_404(PatientInfo, pk=pk) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(PatientInfo, pk=pk, user=request.user)
        form_class = PatientAllergyForm
    else:
        patient = get_object_or_404(DependentPatient, pk=pk) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(DependentPatient, pk=pk, guardian=request.user)
        form_class = DependentPatientAllergyForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            allergy = form.save(commit=False)
            if patient_type == "self":
                allergy.patient = patient
            else:
                allergy.dependent_patient = patient
            allergy.save()
            messages.success(request, "Allergy added successfully.")
            return redirect("patient_list" if getattr(request.user, 'role', None) == 'staff' else "medical_records")
    else:
        form = form_class()

    return render(request, "patients/add_allergy.html", {"form": form, "patient": patient})

# MEDICATIONS
@login_required
def add_patient_medication(request, patient_type, pk):
    if patient_type == "self":
        patient = get_object_or_404(PatientInfo, pk=pk) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(PatientInfo, pk=pk, user=request.user)
        form_class = PatientMedicationForm
    else:
        patient = get_object_or_404(DependentPatient, pk=pk) if getattr(request.user, 'role', None) == 'staff' else get_object_or_404(DependentPatient, pk=pk, guardian=request.user)
        form_class = DependentPatientMedicationForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            medication = form.save(commit=False)
            if patient_type == "self":
                medication.patient = patient
            else:
                medication.dependent_patient = patient
            medication.save()
            messages.success(request, "Medication added successfully.")
            return redirect("patient_list" if getattr(request.user, 'role', None) == 'staff' else "medical_records")
    else:
        form = form_class()

    return render(request, "patients/add_medication.html", {"form": form, "patient": patient})

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
        # Fetch existing profile
        doctor_info = DoctorInfo.objects.get(user=request.user)
    except DoctorInfo.DoesNotExist:
        # Create an UNSAVED instance
        doctor_info = DoctorInfo(user=request.user)

    if request.method == "POST":
        form = DoctorInfoForm(request.POST, request.FILES, instance=doctor_info)
        if form.is_valid():
            form.save()  
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
    return render(request, "managers/users.html", {"doctors": doctors})

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

        messages.success(request, f"{doctor.user.get_full_name()} has been approved.")

        #send email notification
        subject = "Your Doctor Profile Has Been Approved"
        message = f"Hello {doctor.user.get_full_name()},\n\nYour doctor profile has been approved. You can now access all doctor features on the platform.\n\nBest regards,\nThe Team"
        recipient_list = [doctor.user.email]

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

    return redirect("manager_users")

@login_required
def manager_reject_doctor(request, doctor_id):
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")

    doctor = get_object_or_404(DoctorInfo, id=doctor_id)

    if doctor.is_approved:
        messages.warning(
            request,
            f"{doctor.user.get_full_name()} is already approved and cannot be rejected."
        )
    elif doctor.is_rejected:
        messages.info(
            request,
            f"{doctor.user.get_full_name()} has already been rejected."
        )
    else:
        doctor.is_rejected = True
        doctor.rejected_at = timezone.now()
        doctor.save()
        
        # send email
        subject = "Your Doctor Profile Has Been Rejected"
        message = f"Hello {doctor.user.get_full_name()},\n\nWe regret to inform you that your doctor profile has been rejected. Please review your submission and try again.\n\nBest regards,\nThe Team"
        recipient_list = [doctor.user.email]

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)


        messages.success(
            request,
            f"{doctor.user.get_full_name()} has been rejected."
        )

    return redirect("manager_users")

@login_required
def manager_add_specialization(request):
    if request.user.role != "manager":
        messages.error(request, "Access denied.")
        return redirect("home")

    if request.method == "POST":
        form = SpecializationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Specialization added successfully.")
            return redirect("manager_users")
    else:
        form = SpecializationForm()

    return render(request, "managers/add_specialization.html", {
        "form": form
    })


@login_required
def view_doctors(request):
    # Only allow staff or patients
    if request.user.role not in ["staff", "patient"]:
        messages.error(request, "Access denied.")
        return redirect("home")

    # Fetch only approved doctors
    approved_doctors = DoctorInfo.objects.filter(is_approved=True).select_related("user").order_by("user__last_name")

    return render(request, "view_doctors.html", {
        "doctors": approved_doctors
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
        patient_type = request.POST.get("patient_type")

        with transaction.atomic():
            # Lock overlapping approved appointments
            conflict = Appointment.objects.select_for_update().filter(
                doctor=doctor,
                start_time__lt=end,
                end_time__gt=start,
                status="approved"
            ).exists()

            if conflict:
                messages.error(
                    request,
                    "This time slot was just booked. Please choose another."
                )
                return redirect("patient_calendar")

            appointment = Appointment(
                doctor=doctor,
                start_time=start,
                end_time=end,
                status="pending"
            )

            if patient_type == "self":
                appointment.patient = request.user
            else:
                # ✅ Use patient_id, not id
                dependent = get_object_or_404(
                    DependentPatient,
                    patient_id=patient_type,
                    guardian=request.user
                )
                appointment.dependent_patient = dependent

            appointment.save()

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
            availability.save()
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
            custom_avail.save()
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
    messages.success(request, "Custom availability removed.")
    return redirect("doctor_custom_schedule")


@login_required
def doctor_daily_availability(request):
    doctor_id = request.GET.get("doctor_id")
    date_str = request.GET.get("date")  # YYYY-MM-DD

    if not doctor_id or not date_str:
        return JsonResponse({"error": "Invalid request"}, status=400)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    weekday = date_obj.weekday()
    doctor = get_object_or_404(DoctorInfo, id=doctor_id)

    # 1️⃣ Check for custom availability for this date
    custom_availabilities = doctor.custom_availabilities.filter(date=date_obj)
    if custom_availabilities.exists():
        availabilities = custom_availabilities
    else:
        availabilities = doctor.availabilities.filter(weekday=weekday)

    # Get approved appointments on this date
    appointments = Appointment.objects.filter(
        doctor=doctor,
        start_time__date=date_obj,
        status="approved"
    )

    booked_times = {a.start_time.time(): a.end_time.time() for a in appointments}

    slots = []
    SLOT_MINUTES = 30

    for a in availabilities:
        start_time = getattr(a, "start_time", None)
        end_time = getattr(a, "end_time", None)

        if not start_time or not end_time:
            continue

        current = datetime.combine(date_obj, start_time)
        end = datetime.combine(date_obj, end_time)

        while current + timedelta(minutes=SLOT_MINUTES) <= end:
            slot_end = current + timedelta(minutes=SLOT_MINUTES)

            # Check if slot overlaps any booked appointment
            is_booked = any(
                current.time() >= b_start and current.time() < b_end
                for b_start, b_end in booked_times.items()
            )

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

    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
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

        # Approved appointments on this day
        appointments = Appointment.objects.filter(
            doctor=doctor,
            start_time__date=d,
            status="approved"
        )
        booked_times = [(a.start_time.time(), a.end_time.time()) for a in appointments]

        SLOT_MINUTES = 30
        day_has_free_slot = False

        for a in availabilities:
            current = datetime.combine(d, a.start_time)
            end = datetime.combine(d, a.end_time)

            while current + timedelta(minutes=SLOT_MINUTES) <= end:
                slot_end = current + timedelta(minutes=SLOT_MINUTES)

                # Check if slot overlaps with any booked appointment
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

@login_required
def calendar_events(request):
    user = request.user

    if user.role == "staff":
        # Exclude completed from calendar
        appointments = Appointment.objects.exclude(status="completed").select_related(
            "patient", "dependent_patient", "doctor"
        )
    elif user.role == "patient":
        appointments = Appointment.objects.filter(patient=user).select_related("doctor")
    else:
        return JsonResponse([], safe=False)

    events = []
    for a in appointments:
        if a.patient:
            title = f"{a.patient.get_full_name()} ({a.status})"
        elif a.dependent_patient:
            title = f"{a.dependent_patient.full_name} ({a.status})"
        else:
            title = f"Unknown ({a.status})"

        color = (
            "#ffc107" if a.status == "pending" else
            "#28a745" if a.status == "approved" else
            "#6c757d" if a.status == "completed" else
            "#dc3545"
        )

        events.append({
            "id": a.id,
            "title": title,
            "start": a.start_time.isoformat(),
            "end": a.end_time.isoformat(),
            "color": color
        })

    return JsonResponse(events, safe=False)


@login_required
def staff_day_appointments(request):
    if request.user.role != "staff":
        return JsonResponse([], safe=False)

    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse([], safe=False)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

    appointments = Appointment.objects.filter(
        start_time__date=date_obj
    ).select_related("patient", "dependent_patient", "doctor")

    data = []
    for a in appointments:
        patient_name = a.patient.get_full_name() if a.patient else a.dependent_patient.full_name

        if a.status == "completed":
            status_class = 'bg-secondary text-white'  # gray for completed
        elif a.status == 'approved':
            status_class = 'bg-success text-white'
        elif a.status == 'pending':
            status_class = 'bg-warning text-dark'
        else:  # rejected
            status_class = 'bg-danger text-white'

        doctor_name = (
            a.doctor.user.get_full_name()
            if a.doctor and a.doctor.user
            else "Unassigned"
        )

        data.append({
            'id': a.id,
            'patient_name': patient_name,
            'doctor_name': doctor_name,
            'start_time': a.start_time.strftime("%I:%M %p"),
            'end_time': a.end_time.strftime("%I:%M %p"),
            'status': a.status,
            'status_class': status_class
        })

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

    appointments = Appointment.objects.select_related(
        "patient", "dependent_patient", "doctor"
    ).order_by("-start_time")

    total_today = appointments.filter(start_time__date=today).count()
    confirmed_count = appointments.filter(status="approved").count()
    pending_count = appointments.filter(status="pending").count()
    completed_count = CompletedAppointment.objects.count()

    return render(request, "staffs/appointments.html", {
        "appointments": appointments,
        "total_today": total_today,
        "confirmed_count": confirmed_count,
        "pending_count": pending_count,
        "completed_count": completed_count,
    })

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
    if request.user.role != "staff":
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    appointment = get_object_or_404(Appointment, pk=pk)

    if action == "approve":
        appointment.status = "approved"

    elif action == "reject":
        appointment.status = "rejected"

    elif action == "complete":
        appointment.status = "completed"
        CompletedAppointment.objects.get_or_create(appointment=appointment)

    else:
        return JsonResponse({"error": "Invalid action"}, status=400)

    appointment.save()

    return JsonResponse({
        "id": appointment.id,
        "status": appointment.status
    })

@login_required
def reschedule_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)

    # Permission check
    if request.user.role == "staff":
        pass  # staff can reschedule any appointment
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
            return redirect("reschedule_appointment", pk=pk)

        try:
            new_start_dt = parse_datetime(new_start)
            new_end_dt = parse_datetime(new_end)
        except:
            messages.error(request, "Invalid date/time format.")
            return redirect("reschedule_appointment", pk=pk)

        if new_start_dt >= new_end_dt:
            messages.error(request, "End time must be after start time.")
            return redirect("reschedule_appointment", pk=pk)

        # Check conflicts
        conflict = Appointment.objects.filter(
            doctor=appointment.doctor,
            start_time__lt=new_end_dt,
            end_time__gt=new_start_dt,
            status="approved"
        ).exclude(pk=appointment.pk).exists()

        if conflict:
            messages.error(request, "This time slot is already booked.")
            return redirect("reschedule_appointment", pk=pk)

        # Update appointment
        appointment.start_time = new_start_dt
        appointment.end_time = new_end_dt
        appointment.status = "pending"  # reset to pending after reschedule
        appointment.save()

        messages.success(request, "Appointment rescheduled successfully!")

        # Redirect based on user
        if request.user.role == "staff":
            return redirect("appointments")
        elif request.user.role == "doctor":
            return redirect("doctor_appointments")

    # GET request → render reschedule page
    return render(request, "calendar/partials/reschedule_appointment.html", {"appointment": appointment})

@login_required
def patient_appointments(request):
    if request.user.role != "patient":
        return redirect("home")

    own_appointments = Appointment.objects.filter(patient=request.user)

    dependents = DependentPatient.objects.filter(guardian=request.user)
    dependent_appointments = Appointment.objects.filter(dependent_patient__in=dependents)

    appointments = own_appointments.union(dependent_appointments).order_by('start_time')

    return render(request, "patients/appointments.html", {
        "appointments": appointments
    })

@login_required
@doctor_approved_required
def doctor_calendar(request):
    doctor = request.user.doctor_info
    return render(request, "calendar/doctor_calendar.html", {"doctor": doctor})

@login_required
@doctor_approved_required
def doctor_calendar_events(request):
    doctor = request.user.doctor_info
    appointments = Appointment.objects.filter(
        doctor=doctor
    ).select_related("patient", "dependent_patient")

    events = []
    for a in appointments:
        if a.patient:
            title = f"{a.patient.get_full_name()} ({a.status})"
        elif a.dependent_patient:
            title = f"{a.dependent_patient.full_name} ({a.status})"
        else:
            title = f"Unknown ({a.status})"

        color = "#ffc107" if a.status == "pending" else "#28a745" if a.status == "approved" else "#dc3545"

        events.append({
            "id": a.id,
            "title": title,
            "start": a.start_time.isoformat(),
            "end": a.end_time.isoformat(),
            "color": color
        })

    return JsonResponse(events, safe=False)

@login_required
@doctor_approved_required
def doctor_day_appointments(request):
    doctor = request.user.doctor_info
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse([], safe=False)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

    appointments = Appointment.objects.filter(
        doctor=doctor,
        start_time__date=date_obj
    ).select_related("patient", "dependent_patient")

    data = []
    for a in appointments:
        patient_name = a.patient.get_full_name() if a.patient else a.dependent_patient.full_name

        if a.status == "completed":
            status_class = 'bg-secondary text-white'
        elif a.status == 'approved':
            status_class = 'bg-success text-white'
        elif a.status == 'pending':
            status_class = 'bg-warning text-dark'
        else:
            status_class = 'bg-danger text-white'

        data.append({
            'id': a.id,
            'patient_name': patient_name,
            'start_time': a.start_time.strftime("%I:%M %p"),
            'end_time': a.end_time.strftime("%I:%M %p"),
            'status': a.status,
            'status_class': status_class
        })

    return JsonResponse(data, safe=False)

@login_required
@doctor_approved_required
def doctor_appointments(request):
    doctor = request.user.doctor_info
    appointments = Appointment.objects.filter(doctor=doctor).select_related(
        "patient", "dependent_patient"
    ).order_by("start_time")
    
    return render(request, "doctors/appointments.html", {"appointments": appointments})

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
    else:
        return JsonResponse({"error": "Invalid action"}, status=400)
    
    appointment.save()
    return JsonResponse({
        "id": appointment.id,
        "status": appointment.status,
        "status_class": get_status_class(appointment.status)
    })

def get_status_class(status):
    mapping = {
        'approved': 'bg-success text-white',
        'pending': 'bg-warning text-dark',
        'completed': 'bg-secondary text-white',
        'rejected': 'bg-danger text-white'
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
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            if patient_type == 'self':
                record.patient = patient
            else:
                record.dependent_patient = patient
            record.save()
            messages.success(request, "Medical record added successfully")

            # --- Redirect dynamically based on role ---
            if request.user.role == 'doctor':
                return redirect('doctor_patient_list')  # your doctor patient list URL name
            else:  # staff
                return redirect('patient_list')

    else:
        form = MedicalRecordForm()

    return render(request, 'medical_records/add_medical_record.html', {
        'form': form,
        'patient': patient,
        'patient_type': patient_type
    })

@login_required
def edit_medical_record(request, pk):
    # Only staff or doctor can edit
    if request.user.role not in ['staff', 'doctor']:
        messages.error(request, "Access denied")
        return redirect('home')

    # Get the medical record
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
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Medical record updated successfully")
            return redirect('view_medical_record', pk=record.pk)


    else:
        form = MedicalRecordForm(instance=record)

    return render(request, 'medical_records/edit_medical_record.html', {
        'form': form,
        'patient': patient,
        'patient_type': patient_type,
        'record': record
    })


def view_medical_record(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk)
    return render(request, 'medical_records/medical_record_detail.html', {'record': record})