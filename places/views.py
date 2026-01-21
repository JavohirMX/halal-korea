from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import (
    Avg,
    Q,
    Value,
    FloatField,
    Count,
    Prefetch,
    IntegerField,
    DecimalField,
)
from django.http import Http404
from django.contrib.auth import get_user_model
from .models import (
    HalalPlace,
    PlaceEditSuggestion,
    PlaceImageSuggestion,
    BusinessHours,
    TimeSlot,
)
from reviews.models import Review
from .forms import HalalPlaceForm, PlaceSuggestionForm, PlaceImageSuggestionForm  # noqa: F401
from .business_hours import (
    parse_business_hours_payload,
    build_existing_hours_data_from_payload,
    BusinessHoursParseError,
    DAY_NAMES,
)
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
from django.db.models.functions import Round, Coalesce
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.http import JsonResponse
from utils.location_manager import get_user_location_context, update_user_location
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string
import json
from datetime import datetime
import logging
import hashlib
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from utils.telegram_notifications import send_new_place_notification
from utils.watermark import apply_watermark_to_uploaded_file
from utils.logging_utils import log_user_action, log_execution, sanitize_sensitive_data
import io
from users.decorators import email_verification_required

User = get_user_model()
logger = logging.getLogger(__name__)



@log_execution(level="info", sample=True)  # Apply sampling for high-volume endpoint
def home(request):
    """Main home page view showing featured places with international user support"""
    try:
        # Log with structured data
        log_user_action(
            logger,
            "home_page_accessed",
            request.user if request.user.is_authenticated else None,
            request,
            extra_data={"is_authenticated": request.user.is_authenticated},
        )

        # Get user location context (includes international user detection)
        location_context = get_user_location_context(request)
        location = location_context["location"]
        is_in_korea = location_context["is_in_korea"]
        user_location = None

        if "lat" in location and "lng" in location and not location.get("is_fallback"):
            user_location = Point(location["lng"], location["lat"], srid=4326)
            logger.debug(
                "User location determined",
                extra={
                    "latitude": location["lat"],
                    "longitude": location["lng"],
                    "is_in_korea": is_in_korea,
                },
            )

        # Get featured places with different logic for Korea vs international users
        # Use cached rating fields for better performance, with fallback to annotation
        featured_places = HalalPlace.objects.filter(status="approved").annotate(
            # Use cached values if available, otherwise calculate from reviews
            average_rating=Coalesce(
                "cached_average_rating",
                Round(Avg("reviews__rating"), 1),
                output_field=DecimalField(max_digits=3, decimal_places=1),
            ),
            reviews_count=Coalesce(
                "cached_reviews_count", Count("reviews"), output_field=IntegerField()
            ),
        )

        # Different sorting logic based on user location
        if is_in_korea and user_location:
            # For Korea users: distance-based recommendations
            featured_places = featured_places.annotate(
                distance=Distance("location", user_location)
            ).order_by("distance")[:6]
            logger.debug(
                "Featured places ordered by distance",
                extra={"sort_method": "distance", "user_type": "korea"},
            )
        else:
            # For international users: popular/highly-rated places
            # Use Coalesce to ensure places with no ratings appear last
            featured_places = featured_places.annotate(
                rating_for_sort=Coalesce(
                    "average_rating", Value(-1.0), output_field=FloatField()
                )
            ).order_by("-rating_for_sort", "-created_at")[:6]
            logger.debug(
                "Featured places ordered by rating",
                extra={"sort_method": "rating", "user_type": "international"},
            )

        logger.info(
            "Home page rendered successfully",
            extra={
                "featured_places_count": featured_places.count(),
                "is_in_korea": is_in_korea,
            },
        )
        return render(
            request,
            "places/home.html",
            {
                "featured_places": featured_places,
                "location_context": location_context,
            },
        )
    except Exception as e:
        logger.error(
            "Error in home view",
            extra={"error_type": type(e).__name__, "error_message": str(e)},
            exc_info=True,
        )
        return render(
            request,
            "places/error.html",
            {"error": "Unable to load home page", "details": str(e)},
        )


def _get_explore_cache_key(
    request, category, search_query, city_filter, sort, page, location_context
):
    """Generate a cache key for explore view based on query parameters and location."""
    is_in_korea = location_context.get("is_in_korea", False)
    location = location_context.get("location", {})
    # Round coordinates to reduce cache fragmentation
    lat = round(location.get("lat", 0), 2) if location.get("lat") else 0
    lng = round(location.get("lng", 0), 2) if location.get("lng") else 0

    cache_parts = [
        "explore",
        category or "",
        search_query or "",
        city_filter or "",
        sort or "distance",
        str(page),
        str(is_in_korea),
        f"{lat},{lng}",
    ]
    cache_string = ":".join(cache_parts)
    return f"explore_{hashlib.md5(cache_string.encode()).hexdigest()}"


@log_execution(level="info", sample=True)  # High-volume endpoint with sampling
def explore(request):
    from .search import build_search_query, parse_proximity_phrase, log_search_query

    # Get filter parameters
    category = request.GET.get("category")
    search_query = request.GET.get("q", "")
    city_filter = request.GET.get("city", "")  # New city filter
    sort = request.GET.get("sort", "distance")  # Default to distance sorting
    page = request.GET.get("page", 1)

    # Get location context early for cache key and smart defaults
    location_context = get_user_location_context(request)

    # Tourist area coordinates for distance-based sorting
    TOURIST_AREAS = {
        "Seoul": {"lat": 37.5665, "lng": 126.9780},
        "Busan": {"lat": 35.1796, "lng": 129.0756},
        "Jeju": {"lat": 33.4996, "lng": 126.5312},
        "Incheon": {"lat": 37.4563, "lng": 126.7052},
        "Gyeonggi": {"lat": 37.4138, "lng": 127.5183},  # Suwon center
        "Daegu": {"lat": 35.8714, "lng": 128.6014},
        "Daejeon": {"lat": 36.3504, "lng": 127.3845},
        "Gwangju": {"lat": 35.1601, "lng": 126.8515},
        "Ulsan": {"lat": 35.5395, "lng": 129.3114},
    }

    # Get user location from context
    location = location_context["location"]
    is_in_korea = location_context["is_in_korea"]
    user_location = None
    if "lat" in location and "lng" in location and not location.get("is_fallback"):
        user_location = Point(location["lng"], location["lat"], srid=4326)

    # Set smart default sort and reference location for international users
    reference_location = None
    if location_context["is_in_korea"] and user_location:
        # Korea users: use their actual location
        reference_location = user_location
        default_sort = "distance"
    elif city_filter and city_filter in TOURIST_AREAS:
        # International users with tourist area selection: use tourist area center
        tourist_coords = TOURIST_AREAS[city_filter]
        reference_location = Point(
            tourist_coords["lng"], tourist_coords["lat"], srid=4326
        )
        default_sort = "distance"  # Distance from selected tourist area
    else:
        # International users: default to Seoul location for distance-based sorting
        seoul_coords = TOURIST_AREAS["Seoul"]
        reference_location = Point(seoul_coords["lng"], seoul_coords["lat"], srid=4326)
        default_sort = "distance"  # Distance from Seoul by default

    # Override sort parameter if it's the old default
    if sort == "distance" and not request.GET.get("sort"):  # Only if not explicitly set
        sort = default_sort

    # Try to get cached response for anonymous users (non-AJAX only)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    cache_key = None
    if not request.user.is_authenticated and not is_ajax:
        cache_key = _get_explore_cache_key(
            request, category, search_query, city_filter, sort, page, location_context
        )
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug(
                "Explore page served from cache", extra={"cache_key": cache_key}
            )
            return cached_response

    # Log explore action with filters
    log_user_action(
        logger,
        "explore_places",
        request.user if request.user.is_authenticated else None,
        request,
        extra_data={
            "category": category,
            "search_query": search_query,
            "city_filter": city_filter,
            "sort": sort,
            "page": page,
            "is_ajax": request.headers.get("X-Requested-With") == "XMLHttpRequest",
        },
    )

    # Location context already fetched for cache key; use existing data
    location = location_context["location"]
    is_in_korea = location_context["is_in_korea"]
    user_location = None

    if "lat" in location and "lng" in location and not location.get("is_fallback"):
        user_location = Point(location["lng"], location["lat"], srid=4326)

    # Parse proximity phrases from search query (e.g., "near Hongdae")
    cleaned_query = search_query
    is_location_only_search = False
    if search_query:
        cleaned_query, proximity_location, is_location_only_search = (
            parse_proximity_phrase(search_query)
        )
        if proximity_location:
            # Use proximity location for distance calculations
            user_location = Point(
                proximity_location[1], proximity_location[0], srid=4326
            )
            # For location-only search, force distance sorting
            if is_location_only_search:
                sort = "distance"
                is_in_korea = True  # Treat as in-Korea for sorting

    # Base queryset
    places = HalalPlace.objects.filter(status="approved")

    # Apply filters
    if category:
        # Treat mosque and prayer_room as the same category for filtering
        if category == "mosque" or category == "prayer_room":
            places = places.filter(Q(category="mosque") | Q(category="prayer_room"))
        else:
            places = places.filter(category=category)

    # Enhanced search with transliteration and synonyms
    # Use slice-based checks instead of .exists() to reduce database queries
    used_fuzzy_search = False
    if cleaned_query:
        words = cleaned_query.split()

        # For multi-word queries, try strict (AND) matching first for better relevance
        if len(words) > 1:
            from .search import build_search_query_strict

            strict_filter = build_search_query_strict(cleaned_query)
            strict_places = places.filter(strict_filter)

            # Use slice check instead of .exists() - single query that also gives results
            strict_sample = list(strict_places[:1])
            if strict_sample:
                # Strict match found - all words present
                places = strict_places
            else:
                # Fall back to OR matching (any word matches)
                q_filter, expanded_queries, synonyms_used = build_search_query(
                    cleaned_query
                )
                filtered_places = places.filter(q_filter)

                filtered_sample = list(filtered_places[:1])
                if filtered_sample:
                    places = filtered_places
                else:
                    # Still no results - try fuzzy matching
                    from .search import search_places_fuzzy

                    try:
                        fuzzy_places = search_places_fuzzy(
                            cleaned_query, places, threshold=0.25
                        )
                        fuzzy_sample = list(fuzzy_places[:1])
                        if fuzzy_sample:
                            places = fuzzy_places
                            used_fuzzy_search = True
                        else:
                            places = filtered_places  # Keep empty result
                    except Exception:
                        places = filtered_places
        else:
            # Single word query - use regular search
            q_filter, expanded_queries, synonyms_used = build_search_query(
                cleaned_query
            )
            filtered_places = places.filter(q_filter)

            filtered_sample = list(filtered_places[:1])
            if not filtered_sample:
                from .search import search_places_fuzzy

                try:
                    fuzzy_places = search_places_fuzzy(
                        cleaned_query, places, threshold=0.3
                    )
                    fuzzy_sample = list(fuzzy_places[:1])
                    if fuzzy_sample:
                        places = fuzzy_places
                        used_fuzzy_search = True
                    else:
                        places = filtered_places
                except Exception:
                    places = filtered_places
            else:
                places = filtered_places

        # Log search for analytics (only for first page)
        # Use paginator.count after pagination to avoid extra count() query
        if page == 1 or page == "1":
            # Defer count until after pagination is set up
            pass  # Will log after pagination

    # Use cached rating fields for better performance, with fallback to annotation
    places = places.annotate(
        average_rating=Coalesce(
            "cached_average_rating",
            Round(Avg("reviews__rating"), 1),
            output_field=DecimalField(max_digits=3, decimal_places=1),
        ),
        reviews_count=Coalesce(
            "cached_reviews_count", Count("reviews"), output_field=IntegerField()
        ),
    )

    # Enhanced sorting logic using reference location
    if reference_location:
        # Distance-based sorting from reference location (user location or tourist area)
        places = places.annotate(distance=Distance("location", reference_location))
        if sort == "rating":
            # Use Coalesce to ensure places with no ratings appear last
            places = places.annotate(
                rating_for_sort=Coalesce(
                    "average_rating", Value(-1.0), output_field=FloatField()
                )
            ).order_by("-rating_for_sort", "name")
        else:  # Default to distance sorting
            places = places.order_by("distance")
    else:
        # Fallback to rating-based sorting if no reference location
        # Use Coalesce to ensure places with no ratings appear last
        places = places.annotate(
            rating_for_sort=Coalesce(
                "average_rating", Value(-1.0), output_field=FloatField()
            )
        ).order_by("-rating_for_sort", "name")

    # Pagination
    paginator = Paginator(places, 20)  # Show 20 places per page

    try:
        paginated_places = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        paginated_places = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        paginated_places = paginator.page(paginator.num_pages)

    # Log search analytics after pagination (use paginator.count to avoid extra query)
    if cleaned_query and (page == 1 or page == "1"):
        log_search_query(
            query=search_query,
            results_count=paginator.count,  # Use paginator's cached count
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            category_filter=category,
        )

    # Check if this is an AJAX request
    if is_ajax:
        places_html = render_to_string(
            "places/partials/place_list.html",
            {
                "places": paginated_places,
                "user_location": user_location,
                "location_context": location_context,
            },
        )

        logger.info(
            "AJAX explore request completed",
            extra={
                "results_count": paginator.count,
                "page_number": paginated_places.number,
                "has_next": paginated_places.has_next(),
                "filters_applied": bool(category or search_query),
            },
        )

        # Return JSON response with HTML and pagination info
        response = JsonResponse(
            {
                "html": places_html,
                "has_next": paginated_places.has_next(),
                "next_page": int(page) + 1 if paginated_places.has_next() else None,
                "total_pages": paginator.num_pages,
            }
        )
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    logger.info(
        "Explore page rendered",
        extra={
            "results_count": paginated_places.paginator.count,
            "page_number": paginated_places.number,
            "total_pages": paginator.num_pages,
            "filters_applied": bool(category or search_query or city_filter),
        },
    )

    response = render(
        request,
        "places/explore.html",
        {
            "places": paginated_places,
            "current_filters": {
                "category": category,
                "search_query": search_query,
                "city": city_filter,  # Include city filter in current filters
                "sort": sort,
            },
            "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
            "user_location": user_location,
            "location_context": location_context,
            "TOURIST_AREAS": TOURIST_AREAS,  # Pass tourist areas coordinates to JavaScript
        },
    )

    # Cache response for anonymous users (5 minutes)
    if cache_key and not request.user.is_authenticated:
        cache.set(cache_key, response, 300)

    return response


@log_execution(level="info", sample=True)  # High-volume API endpoint with sampling
def get_places_json(request):
    """API endpoint to get places as JSON for map and dynamic loading"""
    from .search import build_search_query, parse_proximity_phrase

    # Get filter parameters
    category = request.GET.get("category")
    search_query = request.GET.get("q", "")
    city_filter = request.GET.get("city", "")  # Add city filter
    sort = request.GET.get("sort", "distance")  # Default to distance sorting
    page = request.GET.get("page", 1)

    # Log API request with parameters
    log_user_action(
        logger,
        "api_get_places_json",
        request.user if request.user.is_authenticated else None,
        request,
        extra_data={
            "category": category,
            "search_query": search_query,
            "city_filter": city_filter,
            "sort": sort,
            "page": page,
        },
    )

    # Get user location
    location = get_user_location_context(request)["location"]
    user_location = None

    if "lat" in location and "lng" in location and not location.get("is_fallback"):
        user_location = Point(location["lng"], location["lat"], srid=4326)

    # Parse proximity phrases from search query (e.g., "near Hongdae")
    cleaned_query = search_query
    is_location_only_search = False
    if search_query:
        cleaned_query, proximity_location, is_location_only_search = (
            parse_proximity_phrase(search_query)
        )
        if proximity_location:
            # Use proximity location for distance calculations
            user_location = Point(
                proximity_location[1], proximity_location[0], srid=4326
            )
            # For location-only search, force distance sorting
            if is_location_only_search:
                sort = "distance"

    # Base queryset
    places = HalalPlace.objects.filter(status="approved")

    # Apply filters
    if category:
        # Treat mosque and prayer_room as the same category for filtering
        if category == "mosque" or category == "prayer_room":
            places = places.filter(Q(category="mosque") | Q(category="prayer_room"))
        else:
            places = places.filter(category=category)

    # Note: City filter is NOT applied to places API - we show ALL places
    # City is only used for distance-based sorting from selected location

    # Enhanced search with transliteration and synonyms
    # Use slice-based checks instead of .exists() to reduce database queries
    if cleaned_query:
        words = cleaned_query.split()

        # For multi-word queries, try strict (AND) matching first
        if len(words) > 1:
            from .search import build_search_query_strict

            strict_filter = build_search_query_strict(cleaned_query)
            strict_places = places.filter(strict_filter)

            strict_sample = list(strict_places[:1])
            if strict_sample:
                places = strict_places
            else:
                # Fall back to OR matching
                q_filter, expanded_queries, synonyms_used = build_search_query(
                    cleaned_query
                )
                filtered_places = places.filter(q_filter)

                filtered_sample = list(filtered_places[:1])
                if filtered_sample:
                    places = filtered_places
                else:
                    # Try fuzzy matching
                    from .search import search_places_fuzzy

                    try:
                        fuzzy_places = search_places_fuzzy(
                            cleaned_query, places, threshold=0.25
                        )
                        fuzzy_sample = list(fuzzy_places[:1])
                        if fuzzy_sample:
                            places = fuzzy_places
                        else:
                            places = filtered_places
                    except Exception:
                        places = filtered_places
        else:
            # Single word query
            q_filter, expanded_queries, synonyms_used = build_search_query(
                cleaned_query
            )
            filtered_places = places.filter(q_filter)

            filtered_sample = list(filtered_places[:1])
            if not filtered_sample:
                from .search import search_places_fuzzy

                try:
                    fuzzy_places = search_places_fuzzy(
                        cleaned_query, places, threshold=0.3
                    )
                    fuzzy_sample = list(fuzzy_places[:1])
                    if fuzzy_sample:
                        places = fuzzy_places
                    else:
                        places = filtered_places
                except Exception:
                    places = filtered_places
            else:
                places = filtered_places

    # Use cached rating fields for better performance
    places = places.annotate(
        average_rating=Coalesce(
            "cached_average_rating",
            Round(Avg("reviews__rating"), 1),
            output_field=DecimalField(max_digits=3, decimal_places=1),
        )
    )

    # Location-based sorting
    if user_location:
        places = places.annotate(distance=Distance("location", user_location))
        if sort == "rating":
            # Use Coalesce to ensure places with no ratings appear last
            places = places.annotate(
                rating_for_sort=Coalesce(
                    "average_rating", Value(-1.0), output_field=FloatField()
                )
            ).order_by("-rating_for_sort", "name")
        else:  # Default to distance sorting
            places = places.order_by("distance")
    else:
        if sort == "rating":
            # Use Coalesce to ensure places with no ratings appear last
            places = places.annotate(
                rating_for_sort=Coalesce(
                    "average_rating", Value(-1.0), output_field=FloatField()
                )
            ).order_by("-rating_for_sort", "name")
        else:  # Default to rating if no location
            # Use Coalesce to ensure places with no ratings appear last
            places = places.annotate(
                rating_for_sort=Coalesce(
                    "average_rating", Value(-1.0), output_field=FloatField()
                )
            ).order_by("-rating_for_sort", "name")

    # Pagination
    paginator = Paginator(places, 20)

    try:
        paginated_places = paginator.page(page)
    except PageNotAnInteger:
        paginated_places = paginator.page(1)
    except EmptyPage:
        paginated_places = paginator.page(paginator.num_pages)

    # Prepare places data for JSON response
    places_data = []
    for place in paginated_places:
        place_data = {
            "id": place.id,
            "name": place.name,
            "category": place.category,
            "address": place.address,
            "description": place.description,
            "average_rating": float(place.average_rating)
            if place.average_rating
            else None,
            "photo_url": place.photo_urls[0] if place.photo_urls else None,
            "location": {
                "lat": float(place.location.y),
                "lng": float(place.location.x),
            },
            "detail_url": request.build_absolute_uri(f"/places/{place.id}/"),
            "google_map_link": place.google_map_link,
            "naver_map_link": place.naver_map_link,
            "kakao_map_link": place.kakao_map_link,
        }

        if hasattr(place, "distance"):
            place_data["distance"] = {
                "m": float(place.distance.m),
                "km": float(place.distance.km),
            }

        places_data.append(place_data)

    logger.info(
        "API get_places_json completed",
        extra={
            "places_returned": len(places_data),
            "total_places": paginated_places.paginator.count,
            "page_number": paginated_places.number,
            "has_next": paginated_places.has_next(),
            "filters_applied": bool(category or search_query or city_filter),
        },
    )

    # Return JSON response
    response = JsonResponse(
        {
            "places": places_data,
            "has_next": paginated_places.has_next(),
            "next_page": int(page) + 1 if paginated_places.has_next() else None,
            "total_pages": paginator.num_pages,
            "current_page": paginated_places.number,
        }
    )
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@log_execution(level="info", sample=True)
def get_all_places_for_map(request):
    """
    Optimized API endpoint to get ALL places for map display.
    Returns minimal data needed for markers (id, name, category, location, rating).
    Supports filtering but no pagination - designed for map clustering.
    """
    from .search import build_search_query, parse_proximity_phrase

    # Get filter parameters
    category = request.GET.get("category")
    search_query = request.GET.get("q", "")

    # Get user location for distance calculation
    location = get_user_location_context(request)["location"]
    user_location = None

    if "lat" in location and "lng" in location and not location.get("is_fallback"):
        user_location = Point(location["lng"], location["lat"], srid=4326)

    # Parse proximity phrases from search query
    cleaned_query = search_query
    if search_query:
        cleaned_query, proximity_location, _ = parse_proximity_phrase(search_query)
        if proximity_location:
            user_location = Point(
                proximity_location[1], proximity_location[0], srid=4326
            )

    # Base queryset - only approved places
    places = HalalPlace.objects.filter(status="approved")

    # Apply category filter
    if category:
        if category == "mosque" or category == "prayer_room":
            places = places.filter(Q(category="mosque") | Q(category="prayer_room"))
        else:
            places = places.filter(category=category)

    # Apply search filter
    if cleaned_query:
        q_filter, _, _ = build_search_query(cleaned_query)
        places = places.filter(q_filter)

    # Annotate with average rating
    places = places.annotate(average_rating=Round(Avg("reviews__rating"), 1))

    # Add distance if user location available
    if user_location:
        places = places.annotate(distance=Distance("location", user_location))

    # Select only necessary fields for performance
    places = places.only("id", "name", "category", "location")

    # Build minimal response data for map markers
    places_data = []
    for place in places:
        place_data = {
            "id": place.id,
            "name": place.name,
            "category": place.category,
            "location": {
                "lat": float(place.location.y),
                "lng": float(place.location.x),
            },
            "average_rating": float(place.average_rating)
            if place.average_rating
            else None,
        }

        if hasattr(place, "distance") and place.distance:
            place_data["distance"] = {
                "m": float(place.distance.m),
                "km": float(place.distance.km),
            }

        places_data.append(place_data)

    logger.info(
        "API get_all_places_for_map completed",
        extra={
            "total_places": len(places_data),
            "filters_applied": bool(category or search_query),
        },
    )

    # Return JSON response with caching (data doesn't change often)
    response = JsonResponse(
        {
            "places": places_data,
            "total_count": len(places_data),
        }
    )
    # Cache for 5 minutes since place data doesn't change frequently
    response["Cache-Control"] = "public, max-age=300"
    return response


def search_autocomplete(request):
    """API endpoint for search autocomplete suggestions"""
    from .search import get_autocomplete_suggestions, log_search_query

    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"suggestions": [], "recent": []})

    # Get autocomplete suggestions
    suggestions = get_autocomplete_suggestions(query, limit=6)

    # Get recent searches from session
    recent_searches = request.session.get("recent_searches", [])[:5]

    response = JsonResponse(
        {
            "suggestions": suggestions,
            "recent": recent_searches,
        }
    )
    response["Cache-Control"] = "private, max-age=60"
    return response


def log_search(request):
    """API endpoint to log a search query for analytics"""
    from .search import log_search_query

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()
        results_count = data.get("results_count", 0)
        category = data.get("category")

        if query:
            # Log to analytics
            log_search_query(
                query=query,
                results_count=results_count,
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                category_filter=category,
            )

            # Store in recent searches (session-based)
            recent = request.session.get("recent_searches", [])
            if query not in recent:
                recent.insert(0, query)
                request.session["recent_searches"] = recent[:10]  # Keep last 10

        return JsonResponse({"success": True})
    except Exception as e:
        logger.warning(f"Failed to log search: {e}")
        return JsonResponse({"success": False})


def get_recent_searches(request):
    """API endpoint to get user's recent searches"""
    recent_searches = request.session.get("recent_searches", [])[:8]
    return JsonResponse({"recent": recent_searches})


def clear_recent_searches(request):
    """API endpoint to clear recent searches"""
    if request.method == "POST":
        request.session["recent_searches"] = []
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Method not allowed"}, status=405)


@log_execution(level="info", sample=True)  # High-volume endpoint with sampling
def place_detail(request, pk):
    # Single optimized query with all annotations and prefetches
    place = (
        HalalPlace.objects.filter(pk=pk, status="approved")
        .annotate(
            average_rating=Round(Avg("reviews__rating"), 1),
            reviews_count=Count("reviews"),
        )
        .prefetch_related(
            Prefetch(
                "reviews",
                queryset=Review.objects.select_related("user").order_by("-created_at"),
            )
        )
        .first()
    )

    if not place:
        raise Http404("Place not found")

    # Check if user has reviewed (use prefetched reviews, no extra query)
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = any(
            review.user_id == request.user.id for review in place.reviews.all()
        )

    # Use reviews_count from annotation instead of .count()
    reviews_count = place.reviews_count

    # Log with pre-computed values (no extra queries)
    log_user_action(
        logger,
        "place_detail_viewed",
        request.user if request.user.is_authenticated else None,
        request,
        extra_data={
            "place_id": place.id,
            "place_name": place.name,
            "place_category": place.category,
            "user_has_reviewed": user_has_reviewed,
            "reviews_count": reviews_count,
        },
    )

    # Get user location context for proper map link styling
    location_context = get_user_location_context(request)

    # Check if place is favorited (optimized single query)
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = request.user.favorite_places.filter(pk=place.pk).exists()

    # Get business hours data for display
    from .business_hours import (
        get_place_status,
        get_today_hours,
        get_weekly_hours,
        get_opening_hours_schema,
    )

    business_hours_status = get_place_status(place)
    today_hours = get_today_hours(place)
    weekly_hours = get_weekly_hours(place)
    opening_hours_schema = get_opening_hours_schema(place)

    return render(
        request,
        "places/place_detail.html",
        {
            "place": place,
            "reviews": place.reviews.all(),  # Already prefetched
            "user_has_reviewed": user_has_reviewed,
            "is_favorited": is_favorited,  # Pass as context variable
            "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
            "location_context": location_context,
            # Business hours context
            "business_hours_status": business_hours_status,
            "today_hours": today_hours,
            "weekly_hours": weekly_hours,
            "opening_hours_schema": opening_hours_schema,
        },
    )


def upload_photo(photo):
    # Generate unique filename
    file_ext = photo.name.split(".")[-1]
    file_ext_lower = file_ext.lower()
    unique_id = uuid.uuid4()
    is_jpeg = file_ext_lower in ["jpg", "jpeg"]
    storage_ext = file_ext_lower if is_jpeg else "png"
    filename = f"places/photos/{unique_id}.{storage_ext}"

    # Ensure stream is at the beginning
    if hasattr(photo, "seek"):
        try:
            photo.seek(0)
        except (OSError, ValueError):
            pass

    # Attempt to apply watermark
    try:
        watermarked_img = apply_watermark_to_uploaded_file(photo)

        img_io = io.BytesIO()
        if file_ext_lower in ["jpg", "jpeg"]:
            watermarked_img = watermarked_img.convert("RGB")
            watermarked_img.save(img_io, format="JPEG", quality=95)
        else:
            # Default to PNG for other formats to preserve transparency when needed
            watermarked_img.save(img_io, format="PNG")

        img_content = ContentFile(img_io.getvalue())
        path = default_storage.save(filename, img_content)
        return path  # Return just the path, not the full URL

    except Exception as e:
        logger.error(
            f"Failed to watermark uploaded photo '{photo.name}': {str(e)}",
            exc_info=True,
        )

        # Reset stream before saving original
        if hasattr(photo, "seek"):
            try:
                photo.seek(0)
            except (OSError, ValueError):
                pass

        # Use original extension when saving fallback to preserve format
        fallback_filename = f"places/photos/{uuid.uuid4()}.{file_ext_lower}"
        path = default_storage.save(fallback_filename, ContentFile(photo.read()))
        return path  # Return just the path, not the full URL


@login_required
@email_verification_required
@log_execution(level="info")  # No sampling - important user action
def submit_place(request):
    """Handle place submission by authenticated users"""
    try:
        if request.method == "POST":
            log_user_action(
                logger,
                "place_submission_attempt",
                request.user,
                request,
                extra_data={"has_files": bool(request.FILES)},
            )

            form = HalalPlaceForm(request.POST, request.FILES)
            hours_payload = request.POST.get("business_hours_json", "")
            existing_hours_data = None
            if hours_payload:
                try:
                    raw_hours_data = json.loads(hours_payload)
                    existing_hours_data = build_existing_hours_data_from_payload(
                        raw_hours_data
                    )
                except json.JSONDecodeError:
                    existing_hours_data = None

            parsed_hours = None
            form_is_valid = form.is_valid()
            if form_is_valid and hours_payload:
                try:
                    parsed_hours = parse_business_hours_payload(hours_payload)
                except BusinessHoursParseError as e:
                    form.add_error(None, str(e))
                    form_is_valid = False

            if form_is_valid and not form.errors:
                place = form.save(commit=False)
                place.status = "pending"
                place.submitted_by = request.user

                # Handle location from latitude and longitude
                latitude = form.cleaned_data.get("latitude")
                longitude = form.cleaned_data.get("longitude")
                if latitude is not None and longitude is not None:
                    place.location = Point(longitude, latitude)
                    logger.debug(f"Place location set: lat={latitude}, lng={longitude}")

                # Handle multiple photos
                photos = request.FILES.getlist("photos")
                if photos:
                    logger.debug(
                        f"Processing {len(photos)} photos for place submission"
                    )
                    photo_urls = []
                    for photo in photos:
                        try:
                            # Update the photo URL to include MEDIA_URL
                            photo_url = upload_photo(photo)
                            if not photo_url.startswith(("http://", "https://")):
                                photo_url = settings.MEDIA_URL + photo_url
                            photo_urls.append(photo_url)
                        except Exception as e:
                            logger.error(f"Error uploading photo: {str(e)}")
                            messages.error(
                                request, f"Error uploading photo: {photo.name}"
                            )
                    place.photo_urls = photo_urls

                place.save()

                if parsed_hours:
                    business_hours = BusinessHours.objects.create(
                        place=place,
                        is_24_hours=parsed_hours["is_24_hours"],
                        notes=parsed_hours["notes"],
                    )
                    if not parsed_hours["is_24_hours"]:
                        for day_str, day_data in parsed_hours["hours"].items():
                            day_num = int(day_str)
                            if day_data == "closed":
                                TimeSlot.objects.create(
                                    business_hours=business_hours,
                                    day_of_week=day_num,
                                    is_closed=True,
                                )
                            else:
                                for slot in day_data:
                                    TimeSlot.objects.create(
                                        business_hours=business_hours,
                                        day_of_week=day_num,
                                        open_time=datetime.strptime(
                                            slot["open"], "%H:%M"
                                        ).time(),
                                        close_time=datetime.strptime(
                                            slot["close"], "%H:%M"
                                        ).time(),
                                    )

                log_user_action(
                    logger,
                    "place_submitted_successfully",
                    request.user,
                    request,
                    extra_data={
                        "place_id": place.id,
                        "place_name": place.name,
                        "place_category": place.category,
                        "photos_count": len(place.photo_urls)
                        if place.photo_urls
                        else 0,
                        "has_website": bool(place.website),
                        "has_phone": bool(place.phone_number),
                    },
                )

                # Send Telegram notification about the new submission
                try:
                    notification_data = {
                        "place_id": place.id,
                        "name": place.name,
                        "category": place.category,
                        "address": place.address,
                        "description": place.description,
                        "submitted_by_username": request.user.username,
                        "website": place.website or "",
                        "phone_number": place.phone_number or "",
                        "photos_count": len(place.photo_urls)
                        if place.photo_urls
                        else 0,
                    }

                    notification_sent = send_new_place_notification(notification_data)
                    if notification_sent:
                        logger.info(
                            f"Telegram notification sent for place submission: {place.name}"
                        )
                    else:
                        logger.debug(
                            f"Telegram notification not sent for place submission: {place.name}"
                        )

                except Exception as e:
                    # Don't fail the submission if notification fails
                    logger.error(
                        f"Error sending Telegram notification for place '{place.name}': {str(e)}"
                    )

                messages.success(
                    request,
                    "Place submitted successfully! It will be reviewed by our team.",
                )
                return redirect("places:explore")
            else:
                log_user_action(
                    logger,
                    "place_submission_validation_failed",
                    request.user,
                    request,
                    extra_data={
                        "form_errors": sanitize_sensitive_data(
                            form.errors.get_json_data()
                        )
                    },
                )
                messages.error(request, "Please correct the errors below.")
        else:
            form = HalalPlaceForm()
            existing_hours_data = None

        return render(
            request,
            "places/submit_place.html",
            {
                "form": form,
                "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
                "day_names": DAY_NAMES,
                "existing_hours_data": json.dumps(existing_hours_data)
                if existing_hours_data
                else "null",
            },
        )
    except Exception as e:
        logger.error(
            "Error in submit_place view",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "user": request.user.username
                if request.user.is_authenticated
                else None,
            },
            exc_info=True,
        )
        messages.error(
            request, "An error occurred while submitting the place. Please try again."
        )
        return redirect("places:home")


def about(request):
    stats = {
        "total_places": HalalPlace.objects.filter(status="approved").count(),
        "total_reviews": Review.objects.count(),
        "total_users": User.objects.count(),
    }
    return render(request, "places/about.html", stats)


def donate(request):
    return render(request, "places/donate.html")


def legal(request):
    """Combined legal page with Privacy Policy, Terms of Service, and Cookie Policy"""
    return render(request, "places/legal.html")


@log_execution(level="info", sample=True)  # High-volume API with sampling
def set_location(request):
    """API endpoint to set user location"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        lat = data.get("latitude")
        lng = data.get("longitude")
        city = data.get("city")
        country = data.get("country")

        if not (lat and lng) and not city:
            logger.warning(
                "Location update failed - missing data",
                extra={"has_lat_lng": bool(lat and lng), "has_city": bool(city)},
            )
            return JsonResponse({"error": "Missing location data"}, status=400)

        # Prepare location data
        location_data = {}
        if lat and lng:
            location_data["lat"] = lat
            location_data["lng"] = lng
        if city:
            location_data["city"] = city
        if country:
            location_data["country"] = country

        # Log location update
        log_user_action(
            logger,
            "user_location_updated",
            request.user if request.user.is_authenticated else None,
            request,
            extra_data={
                "has_coordinates": bool(lat and lng),
                "city": city,
                "country": country,
            },
        )

        # Update location in session
        location = update_user_location(request, location_data)  # noqa: F841

        return JsonResponse({"success": True})
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in set_location", extra={"error": str(e)}, exc_info=True
        )
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(
            "Error in set_location",
            extra={"error_type": type(e).__name__, "error": str(e)},
            exc_info=True,
        )
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@email_verification_required
@log_execution(level="info")  # No sampling - important user action
def suggest_place_edit(request, pk):
    """Display form for suggesting edits to a place"""
    place = get_object_or_404(HalalPlace, pk=pk, status="approved")
    existing_hours_data = None

    if request.method == "POST":
        log_user_action(
            logger,
            "place_edit_suggestion_attempt",
            request.user,
            request,
            extra_data={
                "place_id": place.id,
                "place_name": place.name,
                "has_files": bool(request.FILES),
            },
        )

        form = PlaceSuggestionForm(place=place, data=request.POST, files=request.FILES)
        hours_payload = request.POST.get("business_hours_json", "")
        suggest_hours = request.POST.get("suggest_business_hours") == "true"
        if hours_payload:
            try:
                raw_hours_data = json.loads(hours_payload)
                existing_hours_data = build_existing_hours_data_from_payload(
                    raw_hours_data
                )
            except json.JSONDecodeError:
                existing_hours_data = None

        if form.is_valid():
            parsed_hours = None
            if suggest_hours and hours_payload:
                try:
                    parsed_hours = parse_business_hours_payload(hours_payload)
                except BusinessHoursParseError as e:
                    form.add_error(None, str(e))

            if not form.errors:
                return _process_place_suggestions(request, form, place, parsed_hours)
    else:
        form = PlaceSuggestionForm(place=place)

    # Check if place has business hours
    has_business_hours = (
        hasattr(place, "business_hours") and place.business_hours is not None
    )

    # Prepare business hours data for pre-population
    if existing_hours_data is None and has_business_hours:
        bh = place.business_hours
        existing_hours_data = {
            "is_24_hours": bh.is_24_hours,
            "notes": bh.notes or "",
            "slots": {},
        }
        for slot in bh.time_slots.all():
            day_key = str(slot.day_of_week)
            if day_key not in existing_hours_data["slots"]:
                existing_hours_data["slots"][day_key] = []
            existing_hours_data["slots"][day_key].append(
                {
                    "is_closed": slot.is_closed,
                    "open": slot.open_time.strftime("%H:%M") if slot.open_time else "",
                    "close": slot.close_time.strftime("%H:%M")
                    if slot.close_time
                    else "",
                }
            )

    context = {
        "place": place,
        "form": form,
        "page_title": f"Suggest edits for {place.name}",
        "has_business_hours": has_business_hours,
        "day_names": DAY_NAMES,
        "existing_hours_data": json.dumps(existing_hours_data)
        if existing_hours_data
        else "null",
    }
    return render(request, "places/suggest_edit.html", context)


def _process_place_suggestions(request, form, place, parsed_hours_data=None):
    """Process the suggestion form and create suggestion objects"""
    try:
        # Get field suggestions
        field_suggestions = form.get_field_suggestions()

        # Create field edit suggestions
        created_suggestions = []
        for suggestion_data in field_suggestions:
            suggestion = PlaceEditSuggestion.objects.create(
                place=place,
                suggested_by=request.user,
                field_name=suggestion_data["field_name"],
                current_value=suggestion_data["current_value"],
                suggested_value=suggestion_data["suggested_value"],
                reason=suggestion_data["reason"],
            )
            created_suggestions.append(suggestion)

        # Handle multiple image uploads
        # Django handles multiple files when the HTML input has multiple attribute
        images = request.FILES.getlist("images")  # Get all uploaded images
        created_image_suggestions = []

        for image in images:
            # Validate image
            if image and _is_valid_image(image):
                image_suggestion = PlaceImageSuggestion.objects.create(
                    place=place,
                    suggested_by=request.user,
                    image=image,
                    caption=form.cleaned_data.get(
                        "reason", ""
                    ),  # Use reason as default caption
                )
                created_image_suggestions.append(image_suggestion)

        # Handle business hours suggestion
        created_hours_suggestion = None
        if parsed_hours_data:
            try:
                from .models import BusinessHoursSuggestion

                created_hours_suggestion = BusinessHoursSuggestion.objects.create(
                    place=place,
                    suggested_by=request.user,
                    suggested_hours=parsed_hours_data.get("hours", {}),
                    is_24_hours=parsed_hours_data.get("is_24_hours", False),
                    suggested_notes=parsed_hours_data.get("notes", ""),
                    reason=form.cleaned_data.get("reason", "Business hours update"),
                )

                logger.info(
                    f"Business hours suggestion created for place {place.id} by user {request.user.username}"
                )
            except Exception as e:
                logger.error(f"Error creating hours suggestion: {e}", exc_info=True)

        # Log successful suggestion submission
        total_suggestions = (
            len(created_suggestions)
            + len(created_image_suggestions)
            + (1 if created_hours_suggestion else 0)
        )

        # Check if at least one suggestion was created
        if total_suggestions == 0:
            messages.warning(
                request,
                "Please suggest at least one change, upload an image, or update business hours.",
            )
            return redirect("places:suggest_place_edit", pk=place.pk)

        log_user_action(
            logger,
            "place_edit_suggestion_submitted",
            request.user,
            request,
            extra_data={
                "place_id": place.id,
                "place_name": place.name,
                "field_suggestions_count": len(created_suggestions),
                "image_suggestions_count": len(created_image_suggestions),
                "hours_suggestion": created_hours_suggestion is not None,
                "total_suggestions": total_suggestions,
            },
        )

        # Send notification if any suggestions were created
        if created_suggestions or created_image_suggestions or created_hours_suggestion:
            _send_suggestion_notification(
                place,
                request.user,
                created_suggestions,
                created_image_suggestions,
                created_hours_suggestion,
            )

        # Success message
        messages.success(
            request,
            f"Thank you! Your {total_suggestions} suggestion(s) have been submitted for review.",
        )

        return redirect("places:place_detail", pk=place.pk)

    except Exception as e:
        logger.error(
            "Error processing place suggestions",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "place_id": place.id,
                "user": request.user.username,
            },
            exc_info=True,
        )
        messages.error(
            request, "There was an error processing your suggestions. Please try again."
        )
        return redirect("places:suggest_place_edit", pk=place.pk)


def _is_valid_image(image):
    """Validate uploaded image file"""
    try:
        # Check file size (max 5MB)
        if image.size > 5 * 1024 * 1024:
            return False

        # Check file type
        allowed_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/webp",
        ]
        if image.content_type not in allowed_types:
            return False

        return True
    except Exception:
        return False


def _send_suggestion_notification(
    place, user, field_suggestions, image_suggestions, hours_suggestion=None
):
    """Send Telegram notification for new suggestions"""
    try:
        # Prepare notification message
        total_suggestions = (
            len(field_suggestions)
            + len(image_suggestions)
            + (1 if hours_suggestion else 0)
        )

        message = (
            "<b>🔔 New Place Edit Suggestions</b>\n\n"
            f"<b>Place:</b> {place.name}\n"
            f"<b>Submitted by:</b> {user.username}\n"
            f"<b>Total suggestions:</b> {total_suggestions}\n\n"
        )

        if field_suggestions:
            message += f"<b>Field edits:</b> {len(field_suggestions)}\n"
            for suggestion in field_suggestions[:3]:  # Show first 3
                message += f" • {suggestion.get_field_name_display()}\n"
            if len(field_suggestions) > 3:
                message += f" • ... and {len(field_suggestions) - 3} more\n"

        if image_suggestions:
            message += f"<b>Images:</b> {len(image_suggestions)}\n"

        if hours_suggestion:
            message += "<b>Business Hours:</b> Updated\n"

        message += "\nPlease review in <a href='https://halal-korea.com/admin/places/'>admin panel</a>."

        # Send notification (reuse existing notification system)
        from utils.telegram_notifications import send_telegram_notification

        send_telegram_notification(message)

    except Exception as e:
        logger.error(f"Error sending suggestion notification: {e}")


@login_required
def my_contributions(request):
    """View user's contributions including submitted places and suggestions"""
    # Get user's submitted places
    submitted_places = HalalPlace.objects.filter(submitted_by=request.user).order_by(
        "-created_at"
    )

    # Get user's field suggestions
    field_suggestions = (
        PlaceEditSuggestion.objects.filter(suggested_by=request.user)
        .select_related("place")
        .order_by("-created_at")
    )

    # Get user's image suggestions
    image_suggestions = (
        PlaceImageSuggestion.objects.filter(suggested_by=request.user)
        .select_related("place")
        .order_by("-created_at")
    )

    # Pagination for submitted places
    places_paginator = Paginator(submitted_places, 9)  # 9 for nice grid layout
    places_page = request.GET.get("places_page", 1)
    try:
        submitted_places_page = places_paginator.page(places_page)
    except (PageNotAnInteger, EmptyPage):
        submitted_places_page = places_paginator.page(1)

    # Pagination for field suggestions
    field_paginator = Paginator(field_suggestions, 10)
    field_page = request.GET.get("field_page", 1)
    try:
        field_suggestions_page = field_paginator.page(field_page)
    except (PageNotAnInteger, EmptyPage):
        field_suggestions_page = field_paginator.page(1)

    # Pagination for image suggestions
    image_paginator = Paginator(image_suggestions, 12)  # 12 for nice grid layout
    image_page = request.GET.get("image_page", 1)
    try:
        image_suggestions_page = image_paginator.page(image_page)
    except (PageNotAnInteger, EmptyPage):
        image_suggestions_page = image_paginator.page(1)

    # Get summary statistics
    total_submitted = submitted_places.count()
    total_field_suggestions = field_suggestions.count()
    total_image_suggestions = image_suggestions.count()

    # Count approved suggestions
    approved_field_suggestions = field_suggestions.filter(status="approved").count()
    approved_image_suggestions = image_suggestions.filter(status="approved").count()
    approved_places = submitted_places.filter(status="approved").count()

    context = {
        "submitted_places": submitted_places_page,
        "field_suggestions": field_suggestions_page,
        "image_suggestions": image_suggestions_page,
        "page_title": "My Contributions",
        # Summary stats
        "stats": {
            "total_submitted": total_submitted,
            "total_field_suggestions": total_field_suggestions,
            "total_image_suggestions": total_image_suggestions,
            "approved_field_suggestions": approved_field_suggestions,
            "approved_image_suggestions": approved_image_suggestions,
            "approved_places": approved_places,
        },
    }
    return render(request, "places/my_contributions.html", context)


def handler404(request, exception):
    try:
        return render(request, "places/404.html", status=404)
    except Exception as e:
        print(e)
        # Fallback to a simple 404 response if template rendering fails
        from django.http import HttpResponseNotFound

        return HttpResponseNotFound("<h1>Page not found 404</h1>")
