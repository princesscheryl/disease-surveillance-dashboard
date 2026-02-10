from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Alert
from .models import AlertEscalation
from .models import AlertNote
from .models import AlertStatus
from .serializers import AlertEscalationSerializer
from .serializers import AlertNoteSerializer
from .serializers import AlertSerializer
from .serializers import AlertStatusSerializer
from .services import evaluate_trend_and_generate_alert


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

    @action(detail=False, methods=["post"])
    def evaluate(self, request):
        """
        Evaluate a trend metric and generate an alert if threshold is exceeded.

        This endpoint triggers the CUSUM-based alert evaluation for a specific
        trend metric. It calls the evaluation service which computes CUSUM
        and creates an alert if the threshold is exceeded.

        Expected payload:
        {
            "trend_metric_id": <integer>
        }

        Returns:
        - 201 Created: Alert was generated
        - 200 OK: No alert generated (below threshold)
        - 400 Bad Request: Invalid trend_metric_id or missing parameter
        - 404 Not Found: TrendMetric not found
        """
        trend_metric_id = request.data.get("trend_metric_id")

        if not trend_metric_id:
            return Response(
                {"error": "trend_metric_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            trend_metric_id = int(trend_metric_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "trend_metric_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        alert_created, new_alert, cusum_value = evaluate_trend_and_generate_alert(
            trend_metric_id,
        )

        if not alert_created:
            return Response(
                {
                    "message": "No alert generated",
                    "cusum_value": cusum_value,
                    "threshold": 5.0,
                },
                status=status.HTTP_200_OK,
            )

        serializer = AlertSerializer(new_alert, context={"request": request})
        return Response(
            {
                "message": "Alert generated",
                "alert": serializer.data,
                "cusum_value": cusum_value,
            },
            status=status.HTTP_201_CREATED,
        )


class AlertNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for AlertNote model."""

    queryset = AlertNote.objects.select_related("alert", "noted_by")
    serializer_class = AlertNoteSerializer
    filterset_fields = ["alert", "noted_by"]
    search_fields = ["note_text"]


class AlertEscalationViewSet(viewsets.ModelViewSet):
    """ViewSet for AlertEscalation model."""

    queryset = AlertEscalation.objects.select_related(
        "alert", "escalated_from_role", "escalated_to_role",
    )
    serializer_class = AlertEscalationSerializer
    filterset_fields = [
        "alert",
        "escalated_from_role",
        "escalated_to_role",
    ]
    search_fields = ["escalation_reason"]

