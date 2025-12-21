from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.mail import send_mail
from django.conf import settings
from .forms import RegisterForm
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

        # * Send email with invite link
        # TODO: Make better email content and template
        send_mail(
            subject="Your Registration Invite",
            message=f"Click to register: {invite_link}",
            from_email=settings.DEFAULT_FROM_EMAIL, 
            recipient_list=[email],
            fail_silently=False
        )

        return render(request, "register/invite_success.html", {
            "invite_link": invite_link
        }) # TODO: Instead of having a different success page, show the link on the same page. 

    return render(request, "register/create_invite.html")


# Register using Invite Token
def register_invite(request, token):
    invite = get_object_or_404(Invite, token=token, used=False)

    form = RegisterForm(request.POST or None)

    if form.is_valid():
        user = form.save(commit=False)
        user.email = invite.email
        user.role = invite.role
        user.save()

        Phone.objects.create(
            user=user,
            number=form.cleaned_data["phone"]
        )

        # Create role-based profile
        if user.role == "doctor":
            DoctorProfile.objects.create(
                user=user,
            )

        elif user.role == "patient":
            PatientProfile.objects.create(
                user=user,
            )

        elif user.role == "staff":
            StaffProfile.objects.create(
                user=user,
            )

        elif user.role == "manager":
            ManagerProfile.objects.create(
                user=user,
            )

        invite.used = True
        invite.save()

        return redirect("home")

    return render(request, "register/register_invite.html", {
        "form": form,
        "invite": invite,
    })


# Register Patient (patients can self-register)
def register_patient(request):
    form = RegisterForm(request.POST or None)

    if form.is_valid():
        user = form.save(commit=False)
        user.role = "patient"
        user.save()

        Phone.objects.create(
            user=user,
            number=form.cleaned_data["phone"]
        )

        PatientProfile.objects.create(
            user=user,
        )

        return redirect("home")

    return render(request, "register/register_patient.html", {"form": form})
