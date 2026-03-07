"""URL configuration for dashboard API endpoints."""

from django.urls import path

from .api import dashboard_anomalies
from .api import dashboard_choropleth_data
from .api import dashboard_cases_timeseries
from .api import dashboard_data_quality
from .api import dashboard_detection_metrics
from .api import dashboard_district_summary
from .api import dashboard_evaluate
from .api import dashboard_forecast
from .api import dashboard_map_points
from .api import dashboard_recent_alerts
from .api import dashboard_recent_investigations
from .api import dashboard_situation_overview
from .api import dashboard_summary
from .api import dashboard_top_diseases

app_name = "dashboard_api"

urlpatterns = [
    # Existing endpoints — unchanged
    path("summary/",                dashboard_summary,               name="summary"),
    path("cases-timeseries/",       dashboard_cases_timeseries,      name="cases-timeseries"),
    path("anomalies/",              dashboard_anomalies,             name="anomalies"),
    path("forecast/",               dashboard_forecast,              name="forecast"),
    path("top-diseases/",           dashboard_top_diseases,          name="top-diseases"),
    path("map-points/",             dashboard_map_points,            name="map-points"),
    path("recent-alerts/",          dashboard_recent_alerts,         name="recent-alerts"),
    path("recent-investigations/",  dashboard_recent_investigations, name="recent-investigations"),
    path("evaluate/",               dashboard_evaluate,              name="evaluate"),
    # New epidemiological analytics endpoints
    path("situation-overview/",     dashboard_situation_overview,    name="situation-overview"),
    path("detection-metrics/",      dashboard_detection_metrics,     name="detection-metrics"),
    path("data-quality/",           dashboard_data_quality,          name="data-quality"),
    path("district-summary/",       dashboard_district_summary,      name="district-summary"),
    path("choropleth-data/",        dashboard_choropleth_data,      name="choropleth-data"),
]

