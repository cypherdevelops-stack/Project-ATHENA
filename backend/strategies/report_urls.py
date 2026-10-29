from django.urls import path

from .report_views import strategy_report_pdf_view, strategy_report_view

urlpatterns = [
    path('<slug:strategy_slug>', strategy_report_view, name='strategy-report'),
    path('<slug:strategy_slug>/pdf', strategy_report_pdf_view, name='strategy-report-pdf'),
]
