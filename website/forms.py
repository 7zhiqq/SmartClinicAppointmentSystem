from django import forms
from datetime import date
from django.contrib.auth.models import User
from .models import (
    PatientInfo,
    DependentPatient,
    PatientVitals,
    DependentPatientVitals,
    PatientAllergy,
    DependentPatientAllergy,
    PatientMedication,
    DependentPatientMedication,
    DoctorInfo,
    Specialization,
    DoctorAvailability,
    Appointment,
    CustomDoctorAvailability,
    MedicalRecord
)

class UserBasicInfoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

class GeneralSettingsForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Check if username is already taken by another user
        from accounts.models import User
        if User.objects.filter(username=username).exclude(id=self.user_id).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if email is already used by another user
        from accounts.models import User
        if User.objects.filter(email=email).exclude(id=self.user_id).exists():
            raise forms.ValidationError("This email is already in use.")
        return email


class SecuritySettingsForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Current Password",
        required=True
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="New Password",
        required=True,
        min_length=8
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirm New Password",
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError("The passwords do not match.")
        
        return cleaned_data

    def clean_new_password1(self):
        new_password1 = self.cleaned_data.get('new_password1')
        
        if new_password1:
            # Check if it's all numeric
            if new_password1.isdigit():
                raise forms.ValidationError("Password cannot be entirely numeric.")
            
            # Check if password is too similar to common patterns
            common_passwords = ['password', '12345678', 'qwerty', 'admin', 'letmein']
            if new_password1.lower() in common_passwords:
                raise forms.ValidationError("This password is too common. Please choose a stronger password.")
        
        return new_password1


class PatientInfoForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            "type": "tel",
            "class": "form-control",
            "placeholder": "Enter phone number"
        })
    )
    age = forms.IntegerField(
        required=False,
        disabled=True,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )
    
    class Meta:
        model = PatientInfo
        fields = ["gender", "birthdate", "blood_type"]
        widgets = {
            "gender": forms.RadioSelect(),
            "birthdate": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "blood_type": forms.Select(attrs={"class": "form-select"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        birthdate = self.initial.get("birthdate") or getattr(self.instance, "birthdate", None)
        if birthdate:
            today = date.today()
            self.fields["age"].initial = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        
        # Load phone number if it exists
        if self.instance and self.instance.user:
            try:
                phone = self.instance.user.phone
                self.fields["phone"].initial = phone.number
            except:
                pass
    
    def save(self, commit=True):
        instance = super().save(commit=commit)
        
        # Save phone number
        phone_number = self.cleaned_data.get("phone")
        if phone_number and instance.user:
            from accounts.models import Phone
            phone_obj, created = Phone.objects.get_or_create(user=instance.user)
            phone_obj.number = phone_number
            phone_obj.save()
        
        return instance
    
class DependentPatientForm(forms.ModelForm):
    age = forms.IntegerField(required=False, disabled=True, widget=forms.NumberInput(attrs={"class": "form-control"}))
    class Meta:
        model = DependentPatient
        fields = ["first_name", "last_name", "gender", "phone", "birthdate", "blood_type"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "gender": forms.RadioSelect(),
            "phone": forms.TextInput(attrs={"type": "tel", "class": "form-control", "placeholder": "Enter phone number"}),
            "birthdate": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "blood_type": forms.Select(attrs={"class": "form-select"}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        birthdate = self.initial.get("birthdate") or getattr(self.instance, "birthdate", None)
        if birthdate:
            today = date.today()
            self.fields["age"].initial = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
# Vitals
class PatientVitalsForm(forms.ModelForm):
    class Meta:
        model = PatientVitals
        exclude = ("patient",)

class DependentPatientVitalsForm(forms.ModelForm):
    class Meta:
        model = DependentPatientVitals
        exclude = ("dependent_patient",)

# Allergies
class PatientAllergyForm(forms.ModelForm):
    class Meta:
        model = PatientAllergy
        exclude = ("patient",)

class DependentPatientAllergyForm(forms.ModelForm):
    class Meta:
        model = DependentPatientAllergy
        exclude = ("dependent_patient",)

# Medications
class PatientMedicationForm(forms.ModelForm):
    class Meta:
        model = PatientMedication
        exclude = ("patient",)

class DependentPatientMedicationForm(forms.ModelForm):
    class Meta:
        model = DependentPatientMedication
        exclude = ("dependent_patient",)

# Doctor Info Form
class DoctorInfoForm(forms.ModelForm):
    class Meta:
        model = DoctorInfo
        fields = [
            "profile_picture",
            "specialization",
            "license_number",
        ]

        widgets = {
            "specialization": forms.Select(attrs={
                "class": "form-select"
            }),
            "license_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter license number"
            }),
        }
        
class SpecializationForm(forms.ModelForm):
    class Meta:
        model = Specialization
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if Specialization.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("This specialization already exists.")
        return name

class DoctorAvailabilityForm(forms.ModelForm):
    class Meta:
        model = DoctorAvailability
        fields = ["weekday", "start_time", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }
             
class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["doctor", "start_time", "end_time"]

    def clean(self):
        cleaned = super().clean()
        doctor = cleaned.get("doctor")
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")

        if doctor and start and end:
            weekday = start.weekday()

            available = doctor.availabilities.filter(
                weekday=weekday,
                start_time__lte=start.time(),
                end_time__gte=end.time()
            ).exists()

            if not available:
                raise forms.ValidationError(
                    "Selected time is outside the doctor's availability."
                )

        return cleaned
    
class CustomDoctorAvailabilityForm(forms.ModelForm):
    class Meta:
        model = CustomDoctorAvailability
        fields = ['date', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['reason_for_visit', 'symptoms', 'diagnosis', 'prescription']
        widgets = {
            'reason_for_visit': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,         # small initial height
                'placeholder': 'Enter reason for visit...'
            }),
            'symptoms': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Enter symptoms...'
            }),
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Enter diagnosis...'
            }),
            'prescription': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Enter prescription...'
            }),
        }