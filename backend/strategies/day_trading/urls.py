from django.urls import path

from . import views

urlpatterns = [
    path('state', views.state_view, name='day-trading-state'),
]
