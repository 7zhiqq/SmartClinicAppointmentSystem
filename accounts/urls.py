from django.urls import path
from . import views

urlpatterns = [
    path("invite/create/", views.create_invite, name="create_invite"),
    path("register/invite/<uuid:token>/", views.register_invite, name="register_invite"),

    path('register/patient/', views.register_patient, name='register_patient'),
]
