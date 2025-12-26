from django.urls import path
from website import views_archive

urlpatterns = [
    # Patient Archive/Delete
    path('patient/<str:pk>/archive/', views_archive.archive_patient, name='archive_patient'),
    path('patient/<str:pk>/delete/', views_archive.delete_patient, name='delete_patient'),
    path('dependent/<str:pk>/archive/', views_archive.archive_dependent, name='archive_dependent'),
    
    # Doctor Archive
    path('doctor/<int:doctor_id>/archive/', views_archive.archive_doctor, name='archive_doctor'),
    
    # Appointment Archive
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
    
    # Doctor Details
    path('archived/doctor/<int:pk>/details/', views_archive.deleted_doctor_details, name='deleted_doctor_details'),
    
    # AJAX
    path('ajax/archived-patient/<int:pk>/', views_archive.archived_patient_details_ajax, name='archived_patient_details_ajax'),
    path('ajax/archived-doctor/<int:pk>/', views_archive.archived_doctor_details_ajax, name='archived_doctor_details_ajax'),
    path('ajax/deleted-record/<int:pk>/', views_archive.deleted_record_snapshot_ajax, name='deleted_record_snapshot_ajax'),

    path('archived/patient/<int:pk>/records/<str:patient_type>/', 
        views_archive.archived_patient_detailed_records, 
        name='archived_patient_records'),
    path('archived/patient/<int:pk>/records/', 
        views_archive.archived_patient_detailed_records, 
        {'patient_type': 'self'}, 
        name='archived_patient_records_self'),

    path('archived/patient/<int:pk>/restore/confirm/<str:patient_type>/', 
        views_archive.confirm_restore_patient, 
        name='confirm_restore_patient'),
    path('archived/patient/<int:pk>/restore/', 
        views_archive.restore_patient, 
        name='restore_patient'),
    path('archived/patient/<int:pk>/restore/<str:patient_type>/', 
        views_archive.restore_patient, 
        name='restore_patient_type'),
]