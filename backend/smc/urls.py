from django.urls import path

from . import views

urlpatterns = [
    path('scan', views.scan_view, name='smc-scan'),
]
