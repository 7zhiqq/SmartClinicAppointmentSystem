from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import CustomPasswordResetView

urlpatterns = [
    # Existing invite URLs
    path("invite/create/", views.create_invite, name="create_invite"),
    path("register/invite/<uuid:token>/", views.register_invite, name="register_invite"),
    path('register/patient/', views.register_patient, name='register_patient'),
    
    # UPDATED: Use custom view with debugging
    path(
        "password-reset/",
        CustomPasswordResetView.as_view(),
        name="password_reset"
    ),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]

