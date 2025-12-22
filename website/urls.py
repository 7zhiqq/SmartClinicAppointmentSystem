from django.urls import path
from . import views

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
    path(
        "patients/<str:patient_type>/<str:pk>/medications/",
        views.medication_history,
        name="medication_history"
    ),

    path("doctor/edit-info/", views.doctor_edit_info, name="doctor_edit_info"),
    
    path("manager/specialization/add/", views.manager_add_specialization, name="manager_add_specialization"),
    path("manager/", views.manager_doctor_list, name="manager_users"),
    path("manager/doctors/approve/<int:doctor_id>/", views.manager_approve_doctor, name="manager_approve_doctor"),
    path("manager/doctor/<int:doctor_id>/reject/", views.manager_reject_doctor, name="manager_reject_doctor"),

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
]
