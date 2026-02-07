from django.contrib import admin

from .models import BaselineMetric
from .models import TrendMetric


@admin.register(BaselineMetric)
class BaselineMetricAdmin(admin.ModelAdmin):
    """Admin interface for BaselineMetric model."""

    list_display = [
        "id",
        "disease",
        "location",
        "period_type",
        "baseline_method",
        "baseline_value",
        "computed_for_start",
        "computed_for_end",
        "computed_at",
    ]
    list_filter = ["period_type", "baseline_method", "computed_at"]
    search_fields = [
        "disease__disease_name",
        "location__district_name",
        "location__area_name",
    ]
    ordering = ["-computed_for_end", "disease_id", "location_id"]
    readonly_fields = ["computed_at"]


@admin.register(TrendMetric)
class TrendMetricAdmin(admin.ModelAdmin):
    """Admin interface for TrendMetric model."""

    list_display = [
        "id",
        "disease",
        "location",
        "period_start",
        "period_end",
        "total_cases",
        "moving_avg",
        "pct_change",
        "computed_at",
    ]
    list_filter = ["computed_at"]
    search_fields = [
        "disease__disease_name",
        "location__district_name",
        "location__area_name",
    ]
    ordering = ["-period_end", "disease_id", "location_id"]
    readonly_fields = ["computed_at"]

