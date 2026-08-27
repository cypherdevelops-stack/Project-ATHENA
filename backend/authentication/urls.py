from django.urls import path

from . import views

app_name = 'authentication'

urlpatterns = [
    path('session', views.session_view, name='session'),
    path('login', views.login_view, name='login'),
    path('signup', views.signup_view, name='signup'),
    path('logout', views.logout_view, name='logout'),
    path('password-reset', views.password_reset_view, name='password-reset'),
]
