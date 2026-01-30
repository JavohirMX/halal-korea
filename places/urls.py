from django.urls import path
from . import views
from . import data_management_views

app_name = "places"

urlpatterns = [
    path("", views.home, name="home"),
    path("explore/", views.explore, name="explore"),
    path("place/<int:pk>/", views.place_detail, name="place_detail"),
    path("submit/", views.submit_place, name="submit_place"),
    path("about/", views.about, name="about"),
    path("donate/", views.donate, name="donate"),
    path("legal/", views.legal, name="legal"),
    path("set-location/", views.set_location, name="set_location"),
    path("api/places/", views.get_places_json, name="places_json"),
    path("api/places/map/", views.get_all_places_for_map, name="places_map_json"),
    # Search API endpoints
    path(
        "api/search/autocomplete/",
        views.search_autocomplete,
        name="search_autocomplete",
    ),
    path("api/search/log/", views.log_search, name="log_search"),
    path("api/search/recent/", views.get_recent_searches, name="recent_searches"),
    path(
        "api/search/recent/clear/",
        views.clear_recent_searches,
        name="clear_recent_searches",
    ),
    # Suggestion URLs
    path(
        "place/<int:pk>/suggest-edit/",
        views.suggest_place_edit,
        name="suggest_place_edit",
    ),
    path("my-contributions/", views.my_contributions, name="my_contributions"),
    # Data management URLs (admin import/export)
    path(
        "admin/data-management/",
        data_management_views.data_management_dashboard,
        name="data_management_dashboard",
    ),
    path(
        "admin/data-management/export/",
        data_management_views.export_places_view,
        name="export_places",
    ),
    path(
        "admin/data-management/import/",
        data_management_views.import_places_view,
        name="import_places",
    ),
    path(
        "admin/data-management/import/validate/",
        data_management_views.validate_import_file_ajax,
        name="validate_import_file",
    ),
    path(
        "admin/data-management/template/<str:format_type>/",
        data_management_views.import_template_download,
        name="import_template",
    ),
]
