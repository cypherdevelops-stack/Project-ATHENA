from django.urls import path

from . import views

app_name = 'authentication'

urlpatterns = [
    path('session', views.session_view, name='session'),
    path('login', views.login_view, name='login'),
    path('signup', views.signup_view, name='signup'),
    path('logout', views.logout_view, name='logout'),
    path('send-verification-code', views.send_verification_code_view, name='send-verification-code'),
    path('verify-email', views.verify_email_view, name='verify-email'),
    path('password-reset', views.password_reset_view, name='password-reset'),
    path('password-reset/verify', views.verify_password_reset_link_view, name='password-reset-verify'),
    path('password-reset/complete', views.complete_password_reset_view, name='password-reset-complete'),
]
