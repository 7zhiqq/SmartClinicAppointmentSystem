from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import (
    User,
    Phone,
    DoctorProfile,
    PatientProfile,
    StaffProfile,
    ManagerProfile,
)

# PHONE ADMIN
@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ("user", "number")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "number",
    )

# CUSTOM USER ADMIN
class CustomUserAdmin(UserAdmin):
    model = User

    list_display = (
        "username",
        "email",
        "role",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_active",
    )

    fieldsets = UserAdmin.fieldsets + (
        ("Role Information", {"fields": ("role",)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role Information", {"fields": ("role",)}),
    )


admin.site.register(User, CustomUserAdmin)



# BASE PROFILE ADMIN (REUSABLE)
class BaseProfileAdmin(admin.ModelAdmin):
    def phone_number(self, obj):
        if hasattr(obj.user, "phone"):
            return format_html(
                '<a href="tel:{}">{}</a>',
                obj.user.phone.number,
                obj.user.phone.number,
            )
        return "-"

    phone_number.short_description = "Phone"

    search_fields = (
        "first_name",
        "last_name",
        "user__phone__number",
    )

# DOCTOR PROFILE ADMIN
@admin.register(DoctorProfile)
class DoctorProfileAdmin(BaseProfileAdmin):
    list_display = (
        "doctor_id",
        "first_name",
        "last_name",
        "phone_number",
    )

    search_fields = BaseProfileAdmin.search_fields + (
        "doctor_id",
    )

# PATIENT PROFILE ADMIN
@admin.register(PatientProfile)
class PatientProfileAdmin(BaseProfileAdmin):
    list_display = (
        "patient_id",
        "first_name",
        "last_name",
        "phone_number",
    )

    search_fields = BaseProfileAdmin.search_fields + (
        "patient_id",
    )

# STAFF PROFILE ADMIN
@admin.register(StaffProfile)
class StaffProfileAdmin(BaseProfileAdmin):
    list_display = (
        "staff_id",
        "first_name",
        "last_name",
        "phone_number",
    )

    search_fields = BaseProfileAdmin.search_fields + (
        "staff_id",
    )

# MANAGER PROFILE ADMIN
@admin.register(ManagerProfile)
class ManagerProfileAdmin(BaseProfileAdmin):
    list_display = (
        "manager_id",
        "first_name",
        "last_name",
        "phone_number",
    )

    search_fields = BaseProfileAdmin.search_fields + (
        "manager_id",
    )
