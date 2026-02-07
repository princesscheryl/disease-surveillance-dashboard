from rest_framework import viewsets

from .models import Alert
from .models import AlertEscalation
from .models import AlertNote
from .models import AlertStatus
from .serializers import AlertEscalationSerializer
from .serializers import AlertNoteSerializer
from .serializers import AlertSerializer
from .serializers import AlertStatusSerializer


class AlertStatusViewSet(viewsets.ModelViewSet):
    """ViewSet for AlertStatus model."""

    queryset = AlertStatus.objects.all()
    serializer_class = AlertStatusSerializer
    filterset_fields = ["status_name"]
    search_fields = ["status_name", "description"]


class AlertViewSet(viewsets.ModelViewSet):
    """ViewSet for Alert model."""

    queryset = Alert.objects.select_related("disease", "location", "status")
    serializer_class = AlertSerializer
    filterset_fields = ["disease", "location", "status", "severity_level"]
    search_fields = [
        "disease__disease_name",
        "location__district_name",
        "location__area_name",
        "threshold_rule",
    ]


class AlertNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for AlertNote model."""

    queryset = AlertNote.objects.select_related("alert", "noted_by")
    serializer_class = AlertNoteSerializer
    filterset_fields = ["alert", "noted_by"]
    search_fields = ["note_text"]


class AlertEscalationViewSet(viewsets.ModelViewSet):
    """ViewSet for AlertEscalation model."""

    queryset = AlertEscalation.objects.select_related(
        "alert", "escalated_from_role", "escalated_to_role"
    )
    serializer_class = AlertEscalationSerializer
    filterset_fields = [
        "alert",
        "escalated_from_role",
        "escalated_to_role",
    ]
    search_fields = ["escalation_reason"]

