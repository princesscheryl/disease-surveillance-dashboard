from rest_framework import viewsets

from .models import DuplicateFlag
from .models import Report
from .models import ReportStatus
from .serializers import DuplicateFlagSerializer
from .serializers import ReportSerializer
from .serializers import ReportStatusSerializer


class ReportStatusViewSet(viewsets.ModelViewSet):
    """ViewSet for ReportStatus model."""

    queryset = ReportStatus.objects.all()
    serializer_class = ReportStatusSerializer
    filterset_fields = ["status_name"]
    search_fields = ["status_name", "description"]


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for Report model."""

    queryset = Report.objects.select_related(
        "disease", "location", "reported_by", "status",
    )
    serializer_class = ReportSerializer
    filterset_fields = ["disease", "location", "status", "reported_by", "report_source"]
    search_fields = ["case_notes"]


class DuplicateFlagViewSet(viewsets.ModelViewSet):
    """ViewSet for DuplicateFlag model."""

    queryset = DuplicateFlag.objects.select_related("report", "reviewed_by")
    serializer_class = DuplicateFlagSerializer
    filterset_fields = ["report", "reviewed_by", "review_outcome"]
    search_fields = ["flagged_reason"]

