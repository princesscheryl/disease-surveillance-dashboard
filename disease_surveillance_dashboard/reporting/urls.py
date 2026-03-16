"""URL configuration for reporting app."""

from django.urls import path

from .views import MySubmissionsView
from .views import ReportCreateView
from .views import ReportUpdateView
from .views import export_my_submissions

app_name = "reporting"

urlpatterns = [
    # Create a new report (draft or submit in one step)
    path("new/", ReportCreateView.as_view(), name="report_new"),

    # Edit an existing DRAFT report — 403 if already SUBMITTED
    path("<int:pk>/edit/", ReportUpdateView.as_view(), name="report_edit"),

    # List the current user's own submissions
    path("my-submissions/", MySubmissionsView.as_view(), name="my_submissions"),
    path("my-submissions/export/", export_my_submissions, name="my_submissions_export"),
]
