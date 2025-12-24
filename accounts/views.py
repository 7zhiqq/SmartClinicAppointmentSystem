from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.mail import send_mail
from django.conf import settings
from .forms import RegisterForm
from django.contrib import messages
from .models import (
    Invite,
    User,
    DoctorProfile,
    PatientProfile,
    StaffProfile,
    ManagerProfile,
    Phone,
)

# Manager Creates Invitation
@login_required
def create_invite(request):
    if request.user.role != "manager":
        return HttpResponseForbidden("Only managers can create invites.")

    if request.method == "POST":
        email = request.POST["email"]
        role = request.POST["role"]

        invite = Invite.objects.create(email=email, role=role)

        invite_link = request.build_absolute_uri(
            f"/accounts/register/invite/{invite.token}/"
        )

        # Send email with invite link
        send_mail(
            subject="You're Invited to Join Smart Clinic Platform",
            message=f"""Hello,

            We are excited to invite you to register with our Smart Clinic Platform! By signing up, you'll gain access to your patients' records, appointments, scheduling, and more.

            Getting started is quick and easy:
            1. Click the link below to visit our registration page.
            2. Fill out your details.
            3. Wait for approval.
            4. Start enjoying all the benefits immediately!

            ⏰ IMPORTANT: This link expires in 24 hours. Please register as soon as possible.

            Register here: {invite_link}

            We look forward to welcoming you to our community. If you have any questions, feel free to reach out to us at {settings.DEFAULT_FROM_EMAIL}.

            Best regards,
            WestPoint Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL, 
            recipient_list=[email],
            fail_silently=False
        )

        return render(request, "register/invite_success.html", {
            "invite_link": invite_link,
            "expires_at": invite.expires_at,
        })

    return render(request, "register/create_invite.html")


# Register using Invite Token
def register_invite(request, token):
    # Get the invite
    invite = get_object_or_404(Invite, token=token, used=False)

    # Check if invite has expired
    if invite.is_expired():
        messages.error(
            request, 
            "This invitation link has expired. "
            "Please contact your manager for a new invitation."
        )
        return redirect('home')

    form = RegisterForm(request.POST or None)

    if form.is_valid():
        user = form.save(commit=False)
        user.email = invite.email
        user.role = invite.role
        user.save()

        # Create role-based profile
        if user.role == "doctor":
            DoctorProfile.objects.create(user=user)
        elif user.role == "patient":
            PatientProfile.objects.create(user=user)
        elif user.role == "staff":
            StaffProfile.objects.create(user=user)
        elif user.role == "manager":
            ManagerProfile.objects.create(user=user)

        # Mark invite as used
        invite.used = True
        invite.save()

        messages.success(request, "Registration successful! Please log in.")
        return redirect('home')

    return render(request, "register/register_invite.html", {
        "form": form,
        "invite": invite,
        "time_remaining": f"{invite.time_remaining:.1f}",
    })

# Register Patient (patients can self-register)
def register_patient(request):
    form = RegisterForm(request.POST or None)

    if form.is_valid():
        user = form.save(commit=False)
        user.role = "patient"
        user.save()

        PatientProfile.objects.create(
            user=user,
        )

        return redirect("home")

    return render(request, "register/register_patient.html", {"form": form})
