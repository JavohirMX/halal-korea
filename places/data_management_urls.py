"""
URL configuration for data management (import/export).
These URLs are included at root level to avoid conflicts with admin catch-all.
"""

from django.urls import path
from . import data_management_views

app_name = "places_data_management"

urlpatterns = [
    path(
        "",
        data_management_views.data_management_dashboard,
        name="data_management_dashboard",
    ),
    path(
        "export/",
        data_management_views.export_places_view,
        name="export_places",
    ),
    path(
        "import/",
        data_management_views.import_places_view,
        name="import_places",
    ),
    path(
        "import/validate/",
        data_management_views.validate_import_file_ajax,
        name="validate_import_file",
    ),
    path(
        "template/<str:format_type>/",
        data_management_views.import_template_download,
        name="import_template",
    ),
]
