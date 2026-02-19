"""URL configuration for reporting app."""

from django.urls import path

from .views import ReportCreateView

app_name = "reporting"

urlpatterns = [
    path("new/", ReportCreateView.as_view(), name="report_new"),
]
