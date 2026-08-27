from django.urls import path

from . import views

urlpatterns = [
    path('context', views.context_view, name='market-context'),
]
