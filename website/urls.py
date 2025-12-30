from django.urls import path
from . import views, views_archive

urlpatterns = [
    path("", views.home, name="home"),
    path("logout/", views.logout_user, name="logout"),
    path('account/settings/', views.account_settings, name='account_settings'),

    path('medical-records/', views.medical_records, name='medical_records'),
    path('patients/', views.patient_list, name='patient_list'),
    path('ajax/patient/<str:pk>/', views.patient_details_ajax, name='patient_details_ajax'),
    path("patient/edit/", views.edit_my_patient_info, name="edit_my_patient_info"),
    
    path("dependent/add/", views.add_dependent, name="add_dependent"),
    path("dependent/<str:pk>/edit/", views.edit_dependent, name="edit_dependent"),
        
    path("vitals/<str:patient_type>/<str:pk>/add/", views.add_patient_vitals, name="add_patient_vitals"),
    path('patients/<str:patient_type>/<str:pk>/vitals/', views.vital_history, name='vital_history'),

    path("allergy/<str:patient_type>/<str:pk>/add/", views.add_patient_allergy, name="add_patient_allergy"),
    path("medication/<str:patient_type>/<str:pk>/add/", views.add_patient_medication, name="add_patient_medication"),
    path("patients/<str:patient_type>/<str:pk>/medications/", views.medication_history, name="medication_history"),

    path("doctor/edit-info/", views.doctor_edit_info, name="doctor_edit_info"),
    path('doctors/rate/<int:doctor_id>/', views.rate_doctor_page, name='rate_doctor_page'),
    path('doctors/rate/<int:doctor_id>/submit/', views.submit_doctor_rating, name='submit_doctor_rating'),
    
    path("manager/specialization/add/", views.manager_add_specialization, name="manager_add_specialization"),
    path("manager/", views.manager_doctor_list, name="manager_users"),
    path("manager/doctors/approve/<int:doctor_id>/", views.manager_approve_doctor, name="manager_approve_doctor"),
    path("manager/doctor/<int:doctor_id>/reject/", views.manager_reject_doctor, name="manager_reject_doctor"),

    path("manager/users/", views.manager_users_list, name="manager_users_list"),
    path("manager/user/<int:user_id>/", views.manager_user_details, name="manager_user_details"),
    path("manager/user/<int:user_id>/deactivate/", views.manager_deactivate_user, name="manager_deactivate_user"),
    path("manager/user/<int:user_id>/activate/", views.manager_activate_user, name="manager_activate_user"),
    path("manager/user/<int:user_id>/change-role/", views.manager_change_user_role, name="manager_change_user_role"),
    
    path('doctors/', views.view_doctors, name='view_doctors'),
    path("doctor/schedule/", views.doctor_schedule, name="doctor_schedule"),
    path("doctor/schedule/delete/<int:pk>/", views.delete_availability, name="delete_availability"),
    path("doctor/custom-schedule/", views.doctor_custom_schedule, name="doctor_custom_schedule"),
    path("doctor/custom-schedule/delete/<int:pk>/", views.delete_custom_availability, name="delete_custom_availability"),

    # Doctor patient list
    path("doctor/patients/", views.doctor_patient_list, name="doctor_patient_list"),

    path("staff-calendar/", views.staff_appointment_calendar, name="staff_calendar"),
    path("patient-calendar/", views.patient_appointment_calendar, name="patient_calendar"),
    
    path("calendar/availability/", views.doctor_daily_availability, name="doctor_daily_availability"),
    path("calendar/available-days/", views.doctor_available_days, name="doctor_available_days"),
    path("calendar/events/", views.calendar_events, name="calendar_events"),
    path("calendar/book", views.book_appointment, name="book_schedule"),
    path('calendar/day-appointments/', views.staff_day_appointments, name='staff_day_appointments'),
    
    path("doctor/calendar/", views.doctor_calendar, name="doctor_calendar"),
    path("doctor/calendar/events/", views.doctor_calendar_events, name="doctor_calendar_events"),
    path("doctor/calendar/day-appointments/", views.doctor_day_appointments, name="doctor_day_appointments"),
    path("doctor/appointments/", views.doctor_appointments, name="doctor_appointments"),
    path("doctor/appointments/<int:pk>/update_status/<str:action>/",views.update_doctor_appointment_status, name="update_doctor_appointment_status"),
    

    path("staff/appointments/pending/", views.staff_appointments, name="appointments"),
    
    path('appointments/<int:pk>/update_status/<str:action>/', views.update_appointment_status, name='update_status'),
    path("appointment/<int:pk>/reschedule/", views.reschedule_appointment, name="reschedule_appointment"),
    path('appointment/<int:pk>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    
    path('my-appointments/', views.patient_appointments, name='patient_appointments'),

    # urls.py
    path('add-medical-record/<str:patient_type>/<str:pk>/', views.add_medical_record, name='add_medical_record'),
    path('medical-record/edit/<int:pk>/', views.edit_medical_record, name='edit_medical_record'),
    path('medical-record/<int:pk>/', views.view_medical_record, name='view_medical_record'),
    
    # ! Merged to update appointment status
    # path('appointments/<int:pk>/approve/', views.approve_appointment, name='approve_appointment'),
    # path('appointments/<int:pk>/reject/', views.reject_appointment, name='reject_appointment'),

     # ! Currently not used...Cannot view appointment details yet.
    # path('appointments/<int:pk>/details/', views.appointment_details, name='appointment_details'),
    # path('appointments/<int:pk>/staff-details/', views.staff_appointment_details, name='staff_appointment_details'),
    # path('appointments/<int:pk>/staff-details/', views.staff_appointment_details, name='staff_appointment_details'),

    # Archive/Delete URLs
    path('patient/<str:pk>/archive/', views_archive.archive_patient, name='archive_patient'),
    path('patient/<str:pk>/delete/', views_archive.delete_patient, name='delete_patient'),
    path('dependent/<str:pk>/archive/', views_archive.archive_dependent, name='archive_dependent'),
    path('doctor/<int:doctor_id>/archive/', views_archive.archive_doctor, name='archive_doctor'),
    path('appointment/<int:pk>/delete/', views_archive.delete_appointment, name='delete_appointment'),
    
    # Archive Lists
    path('archived/patients/', views_archive.archived_patients_list, name='archived_patients'),
    path('archived/doctors/', views_archive.archived_doctors_list, name='archived_doctors'),
    path('archived/appointments/', views_archive.archived_appointments_list, name='archived_appointments'),
    path('deleted/records/', views_archive.deleted_records_list, name='deleted_records'),
    
    # AJAX
    path('ajax/archived-patient/<int:pk>/', views_archive.archived_patient_details_ajax, name='archived_patient_details_ajax'),

    # Delete small records
    path("vitals/<str:patient_type>/<int:pk>/delete/", views.delete_patient_vitals, name="delete_patient_vitals"),
    path("allergy/<str:patient_type>/<int:pk>/delete/", views.delete_patient_allergy, name="delete_patient_allergy"),
    path("medication/<str:patient_type>/<int:pk>/delete/", views.delete_patient_medication, name="delete_patient_medication"),
    path("medical-record/<int:pk>/delete/", views.delete_medical_record, name="delete_medical_record"),

    path('appointment-recommendations/', views.appointment_recommendations, name='appointment_recommendations'),
]
