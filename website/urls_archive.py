from django.urls import path
from website import views_archive

urlpatterns = [
    # Patient Archive/Delete
    path('patient/<str:pk>/archive/', views_archive.archive_patient, name='archive_patient'),
    path('patient/<str:pk>/delete/', views_archive.delete_patient, name='delete_patient'),
    path('dependent/<str:pk>/archive/', views_archive.archive_dependent, name='archive_dependent'),
    
    # Doctor Archive
    path('doctor/<int:doctor_id>/archive/', views_archive.archive_doctor, name='archive_doctor'),
    
    # Appointment Archive (NEW)
    path('appointment/<int:pk>/archive/', views_archive.archive_appointment_view, name='archive_appointment'),
    path('appointment/dependent/<int:pk>/archive/', views_archive.archive_dependent_appointment_view, name='archive_dependent_appointment'),
    path('appointments/bulk-archive/', views_archive.bulk_archive_appointments, name='bulk_archive_appointments'),
    path('appointment/archived/<int:pk>/restore/', views_archive.restore_archived_appointment, name='restore_archived_appointment'),
    
    # Appointment Delete 
    path('appointment/<int:pk>/delete/', views_archive.delete_appointment, name='delete_appointment'),
    
    # Archive Lists
    path('archived/patients/', views_archive.archived_patients_list, name='archived_patients'),
    path('archived/doctors/', views_archive.archived_doctors_list, name='archived_doctors'),
    path('archived/appointments/', views_archive.archived_appointments_list, name='archived_appointments'),
    path('deleted/records/', views_archive.deleted_records_list, name='deleted_records'),
    
    # AJAX
    path('ajax/archived-patient/<int:pk>/', views_archive.archived_patient_details_ajax, name='archived_patient_details_ajax'),
]