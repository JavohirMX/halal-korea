"""
Advanced Search Service for Halal Places

Provides full-text search with:
- Weighted field ranking (name > description > address)
- Korean ↔ English transliteration support
- Synonym expansion
- Proximity phrase parsing ("near Hongdae", "in Gangnam")
- Search analytics tracking
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector, TrigramSimilarity
)
from django.db.models import Q, F, Value, FloatField
from django.db.models.functions import Coalesce, Greatest
from django.core.cache import cache

from .models import HalalPlace, SearchQuery as SearchQueryModel
from utils.transliteration import expand_search_query, has_korean, romanize_korean

logger = logging.getLogger(__name__)


# Synonym mappings for search expansion
SYNONYMS = {
    # Prayer-related
    'masjid': ['mosque', 'prayer room', 'musalla', '모스크', '마스지드'],
    'mosque': ['masjid', 'prayer room', 'musalla', '모스크'],
    'prayer room': ['musalla', 'prayer space', 'mosque', '기도실'],
    'musalla': ['prayer room', 'mosque', 'masjid'],
    
    # Food-related
    'restaurant': ['food', 'eatery', 'dining', '레스토랑', '식당'],
    'halal food': ['halal restaurant', 'muslim food', '할랄 음식'],
    'kebab': ['kebap', 'kabab', 'kabob', '케밥'],
    'shawarma': ['shawerma', 'shwarma', '샤와르마'],
    'biryani': ['biriyani', 'briyani', '비리야니'],
    
    # Market-related
    'market': ['grocery', 'store', 'shop', 'supermarket', '마켓', '슈퍼'],
    'grocery': ['market', 'store', 'supermarket'],
    'halal market': ['halal grocery', 'halal store', 'muslim store'],
    
    # Common misspellings
    'resturant': ['restaurant'],
    'restraunt': ['restaurant'],
    'mosk': ['mosque'],
    
    # Korean area synonyms
    '이태원': ['itaewon'],
    '홍대': ['hongdae', 'hongik'],
    '강남': ['gangnam'],
    '명동': ['myeongdong'],
    '신촌': ['sinchon'],
}

# Proximity phrase patterns with their associated locations
# These are fallback defaults - the database ProximityLocation model takes precedence
DEFAULT_PROXIMITY_LOCATIONS = {
    'itaewon': (37.5345, 126.9946),
    'hongdae': (37.5563, 126.9237),
    'gangnam': (37.4979, 127.0276),
    'myeongdong': (37.5636, 126.9869),
    'sinchon': (37.5550, 126.9368),
    'jongno': (37.5704, 126.9922),
    'dongdaemun': (37.5711, 127.0095),
    'insadong': (37.5741, 126.9870),
    'apgujeong': (37.5270, 127.0286),
    'yeouido': (37.5217, 126.9243),
    'mapo': (37.5537, 126.9536),
    'yongsan': (37.5299, 126.9648),
    'seoul station': (37.5547, 126.9707),
    '이태원': (37.5345, 126.9946),
    '홍대': (37.5563, 126.9237),
    '강남': (37.4979, 127.0276),
    '명동': (37.5636, 126.9869),
    '신촌': (37.5550, 126.9368),
    '종로': (37.5704, 126.9922),
    '동대문': (37.5711, 127.0095),
    '인사동': (37.5741, 126.9870),
    '압구정': (37.5270, 127.0286),
    '여의도': (37.5217, 126.9243),
    '마포': (37.5537, 126.9536),
    '용산': (37.5299, 126.9648),
}


def get_proximity_locations():
    """
    Get proximity locations from database, with fallback to defaults.
    Results are cached for performance.
    """
    try:
        from .models import ProximityLocation
        db_locations = ProximityLocation.get_locations_dict()
        if db_locations:
            return db_locations
    except Exception:
        pass  # Database not ready or model doesn't exist yet
    
    return DEFAULT_PROXIMITY_LOCATIONS

# Proximity phrase patterns
PROXIMITY_PATTERNS = [
    r'near\s+(.+)',
    r'in\s+(.+)',
    r'around\s+(.+)',
    r'at\s+(.+)',
    r'(.+)\s+근처',
    r'(.+)\s+주변',
    r'(.+)에서',
]


@dataclass
class SearchResult:
    """Container for search results with metadata"""
    places: List[HalalPlace]
    total_count: int
    query_expanded: List[str]
    proximity_location: Optional[Tuple[float, float]]
    synonyms_used: List[str]


def get_synonyms(term: str) -> List[str]:
    """Get synonym expansions for a search term"""
    term_lower = term.lower().strip()
    synonyms = set()
    
    # Direct match
    if term_lower in SYNONYMS:
        synonyms.update(SYNONYMS[term_lower])
    
    # Check if any synonym key contains this term
    for key, values in SYNONYMS.items():
        if term_lower in key or key in term_lower:
            synonyms.update(values)
            synonyms.add(key)
        for v in values:
            if term_lower == v.lower():
                synonyms.add(key)
                synonyms.update(values)
    
    synonyms.discard(term_lower)
    return list(synonyms)


def fuzzy_match_location(query: str, locations: dict, threshold: float = 0.6) -> Optional[str]:
    """
    Find best fuzzy match for a location name.
    
    Args:
        query: User's input (potentially misspelled)
        locations: Dict of location names to coordinates
        threshold: Minimum similarity (0-1)
    
    Returns:
        Best matching location name or None
    """
    from difflib import SequenceMatcher
    
    query_lower = query.lower().strip()
    best_match = None
    best_score = threshold
    
    for loc_name in locations.keys():
        # Direct similarity
        score = SequenceMatcher(None, query_lower, loc_name.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = loc_name
        
        # Also check if query is a substring with minor typos
        # e.g., "itewon" should match "itaewon"
        if len(query_lower) >= 4 and len(loc_name) >= 4:
            # Check starting characters match
            if query_lower[:2] == loc_name[:2].lower():
                # Boost score for same prefix
                score = SequenceMatcher(None, query_lower, loc_name.lower()).ratio() + 0.1
                if score > best_score:
                    best_score = score
                    best_match = loc_name
    
    return best_match


def parse_proximity_phrase(query: str) -> Tuple[str, Optional[Tuple[float, float]], bool]:
    """
    Parse proximity phrases from search query.
    
    Returns:
        Tuple of (cleaned_query, location_coords or None, is_location_only_search)
    """
    query_lower = query.lower().strip()
    proximity_locations = get_proximity_locations()
    
    # First check if the entire query is just a location name (exact match)
    if query_lower in proximity_locations:
        # Location-only search: return empty query but mark it as location search
        return '', proximity_locations[query_lower], True
    
    # Try romanized version for location-only search
    romanized = romanize_korean(query).lower()
    if romanized in proximity_locations:
        return '', proximity_locations[romanized], True
    
    # Try fuzzy match for location-only search (handles typos like "itewon" -> "itaewon")
    fuzzy_match = fuzzy_match_location(query_lower, proximity_locations)
    if fuzzy_match:
        return '', proximity_locations[fuzzy_match], True
    
    # Now check for proximity phrases
    for pattern in PROXIMITY_PATTERNS:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            location_name = match.group(1).strip()
            
            # Check if this is a known location (exact)
            if location_name in proximity_locations:
                # Remove the proximity phrase from query
                cleaned = re.sub(pattern, '', query, flags=re.IGNORECASE).strip()
                return cleaned, proximity_locations[location_name], False
            
            # Try romanized version
            romanized = romanize_korean(location_name).lower()
            if romanized in proximity_locations:
                cleaned = re.sub(pattern, '', query, flags=re.IGNORECASE).strip()
                return cleaned, proximity_locations[romanized], False
            
            # Try fuzzy match for location in phrase
            fuzzy_match = fuzzy_match_location(location_name, proximity_locations)
            if fuzzy_match:
                cleaned = re.sub(pattern, '', query, flags=re.IGNORECASE).strip()
                return cleaned, proximity_locations[fuzzy_match], False
    
    return query, None, False


def build_search_query(query: str, fuzzy: bool = True) -> Tuple[Q, List[str], List[str]]:
    """
    Build a comprehensive Django Q object for search.
    
    Args:
        query: The search query string
        fuzzy: Whether to include fuzzy matching for typos (default True)
    
    Returns:
        Tuple of (Q object, expanded_queries, synonyms_used)
    """
    expanded_queries = expand_search_query(query)
    synonyms_used = []
    
    # Get synonyms for the original query terms
    words = query.lower().split()
    for term in words:
        term_synonyms = get_synonyms(term)
        synonyms_used.extend(term_synonyms)
        expanded_queries.extend(term_synonyms)
    
    # Remove duplicates while preserving order
    expanded_queries = list(dict.fromkeys(expanded_queries))
    synonyms_used = list(dict.fromkeys(synonyms_used))
    
    # Build Q objects using OR strategy (matches any term)
    q_objects = Q()
    
    for q in expanded_queries:
        q_objects |= (
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(address__icontains=q) |
            Q(name_romanized__icontains=q) |
            Q(name_korean__icontains=q)
        )
    
    return q_objects, expanded_queries, synonyms_used


def build_search_query_strict(query: str) -> Q:
    """
    Build a strict search query where ALL words must match (AND logic).
    Useful for multi-word queries to get more relevant results.
    
    Args:
        query: The search query string
    
    Returns:
        Q object requiring all words to match
    """
    words = query.lower().split()
    
    if len(words) <= 1:
        # Single word, use regular search
        q_filter, _, _ = build_search_query(query)
        return q_filter
    
    # For multi-word: require each word to appear somewhere
    q_all = Q()
    for word in words:
        word_q = (
            Q(name__icontains=word) |
            Q(description__icontains=word) |
            Q(address__icontains=word) |
            Q(name_romanized__icontains=word) |
            Q(name_korean__icontains=word)
        )
        if q_all:
            q_all &= word_q  # AND logic
        else:
            q_all = word_q
    
    return q_all


def search_places_fuzzy(query: str, queryset=None, threshold: float = 0.3):
    """
    Add fuzzy matching to a queryset using trigram similarity.
    
    This catches typos like "resturant" -> "restaurant"
    Handles multi-word queries by matching any word.
    
    Args:
        query: Search query
        queryset: Base queryset to filter (defaults to approved places)
        threshold: Minimum similarity score (0-1, default 0.3)
    
    Returns:
        Queryset annotated with similarity scores
    """
    if queryset is None:
        queryset = HalalPlace.objects.filter(status='approved')
    
    words = query.lower().split()
    
    if len(words) == 1:
        # Single word: simple trigram similarity
        queryset = queryset.annotate(
            name_similarity=TrigramSimilarity('name', query),
            address_similarity=TrigramSimilarity('address', query),
        ).annotate(
            max_similarity=Greatest('name_similarity', 'address_similarity')
        ).filter(
            max_similarity__gte=threshold
        )
    else:
        # Multi-word: match if ANY word has good similarity
        # This helps with queries like "halal korean resturant"
        from django.db.models import Case, When, FloatField as ModelFloatField
        
        # Build similarity for each word and take the best match
        similarity_annotations = {}
        for i, word in enumerate(words[:5]):  # Limit to 5 words for performance
            if len(word) >= 3:  # Only fuzzy match words with 3+ chars
                similarity_annotations[f'word_{i}_name_sim'] = TrigramSimilarity('name', word)
                similarity_annotations[f'word_{i}_addr_sim'] = TrigramSimilarity('address', word)
        
        if similarity_annotations:
            queryset = queryset.annotate(**similarity_annotations)
            
            # Calculate max similarity across all word matches
            sim_fields = list(similarity_annotations.keys())
            queryset = queryset.annotate(
                max_similarity=Greatest(*sim_fields)
            ).filter(
                max_similarity__gte=threshold
            )
        else:
            # All words too short, try full phrase match
            queryset = queryset.annotate(
                name_similarity=TrigramSimilarity('name', query),
                max_similarity=F('name_similarity')
            ).filter(
                max_similarity__gte=threshold
            )
    
    return queryset.order_by('-max_similarity')


def search_places(
    query: str,
    category: Optional[str] = None,
    user_location: Optional[Point] = None,
    sort: str = 'relevance',
    limit: int = 50,
    use_full_text: bool = True,
) -> SearchResult:
    """
    Perform an advanced search for halal places.
    
    Args:
        query: Search query string
        category: Optional category filter
        user_location: Optional user location for distance sorting
        sort: Sort order ('relevance', 'distance', 'rating')
        limit: Maximum results to return
        use_full_text: Whether to use PostgreSQL full-text search
        
    Returns:
        SearchResult with places and metadata
    """
    # Parse proximity phrases
    cleaned_query, proximity_location, is_location_only = parse_proximity_phrase(query)
    
    # If proximity location found, use it for distance calculations
    if proximity_location and not user_location:
        user_location = Point(proximity_location[1], proximity_location[0], srid=4326)
    
    # Build search query with expansions
    q_filter, expanded_queries, synonyms_used = build_search_query(cleaned_query or query)
    
    # Base queryset
    places = HalalPlace.objects.filter(status='approved')
    
    # Apply category filter
    if category:
        if category in ('mosque', 'prayer_room'):
            places = places.filter(Q(category='mosque') | Q(category='prayer_room'))
        else:
            places = places.filter(category=category)
    
    # Apply search filter
    if cleaned_query or query:
        if use_full_text and hasattr(places.first() if places.exists() else None, 'search_vector'):
            # Use full-text search if available
            search_query = SearchQuery(query, config='simple')
            places = places.filter(q_filter | Q(search_vector=search_query))
            
            # Add search rank for relevance scoring
            places = places.annotate(
                search_rank=SearchRank(F('search_vector'), search_query)
            )
        else:
            # Fallback to Q-based search
            places = places.filter(q_filter)
            places = places.annotate(search_rank=Value(0.0, output_field=FloatField()))
    else:
        places = places.annotate(search_rank=Value(0.0, output_field=FloatField()))
    
    # Add distance annotation if user location available
    if user_location:
        places = places.annotate(distance=Distance('location', user_location))
    
    # Add rating annotations
    from django.db.models import Avg, Count
    from django.db.models.functions import Round
    
    places = places.annotate(
        average_rating=Round(Avg('reviews__rating'), 1),
        reviews_count=Count('reviews'),
        rating_for_sort=Coalesce('average_rating', Value(-1.0), output_field=FloatField())
    )
    
    # Apply sorting
    if sort == 'distance' and user_location:
        places = places.order_by('distance')
    elif sort == 'rating':
        places = places.order_by('-rating_for_sort', 'name')
    else:  # relevance
        if cleaned_query or query:
            places = places.order_by('-search_rank', '-rating_for_sort', 'name')
        elif user_location:
            places = places.order_by('distance')
        else:
            places = places.order_by('-rating_for_sort', 'name')
    
    # Get total count before limiting
    total_count = places.count()
    
    # Apply limit
    places = places[:limit]
    
    return SearchResult(
        places=list(places),
        total_count=total_count,
        query_expanded=expanded_queries,
        proximity_location=proximity_location,
        synonyms_used=synonyms_used,
    )


def get_autocomplete_suggestions(
    query: str,
    limit: int = 8,
) -> List[Dict]:
    """
    Get autocomplete suggestions for a partial query.
    
    Args:
        query: Partial search query
        limit: Maximum suggestions to return
        
    Returns:
        List of suggestion dicts with 'name', 'category', 'id'
    """
    if not query or len(query) < 2:
        return []
    
    # Cache key for autocomplete - sanitize to avoid memcached issues
    # Replace spaces and special chars, use hash for consistency
    import hashlib
    safe_query = re.sub(r'[^a-zA-Z0-9가-힣]', '_', query.lower()[:30])
    query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:8]
    cache_key = f'autocomplete_{safe_query}_{query_hash}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Expand query with transliterations
    query_variations = expand_search_query(query)
    
    # Build Q filter for prefix matching
    q_filter = Q()
    for q in query_variations:
        q_filter |= (
            Q(name__istartswith=q) |
            Q(name_romanized__istartswith=q) |
            Q(name_korean__istartswith=q)
        )
    
    # Also do contains matching but prioritize prefix
    q_contains = Q()
    for q in query_variations:
        q_contains |= (
            Q(name__icontains=q) |
            Q(name_romanized__icontains=q) |
            Q(name_korean__icontains=q)
        )
    
    # Get prefix matches first
    prefix_matches = (
        HalalPlace.objects
        .filter(status='approved')
        .filter(q_filter)
        .values('id', 'name', 'category', 'address')
        [:limit]
    )
    
    suggestions = list(prefix_matches)
    
    # If we don't have enough, add contains matches
    if len(suggestions) < limit:
        existing_ids = {s['id'] for s in suggestions}
        remaining = limit - len(suggestions)
        
        contains_matches = (
            HalalPlace.objects
            .filter(status='approved')
            .filter(q_contains)
            .exclude(id__in=existing_ids)
            .values('id', 'name', 'category', 'address')
            [:remaining]
        )
        
        suggestions.extend(contains_matches)
    
    # Format results
    result = [
        {
            'id': s['id'],
            'name': s['name'],
            'category': s['category'],
            'address': s['address'][:50] if s['address'] else '',
        }
        for s in suggestions
    ]
    
    # Cache for 60 seconds
    cache.set(cache_key, result, 60)
    
    return result


def log_search_query(
    query: str,
    results_count: int,
    user=None,
    session_key: Optional[str] = None,
    category_filter: Optional[str] = None,
):
    """Log a search query for analytics"""
    try:
        SearchQueryModel.objects.create(
            query=query[:255],
            user=user if user and user.is_authenticated else None,
            session_key=session_key,
            results_count=results_count,
            category_filter=category_filter,
        )
    except Exception as e:
        logger.warning(f"Failed to log search query: {e}")


def get_popular_searches(limit: int = 10) -> List[Dict]:
    """Get most popular recent searches"""
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    # Last 7 days
    since = timezone.now() - timedelta(days=7)
    
    popular = (
        SearchQueryModel.objects
        .filter(created_at__gte=since, results_count__gt=0)
        .values('query')
        .annotate(count=Count('id'))
        .order_by('-count')
        [:limit]
    )
    
    return list(popular)


def get_zero_result_searches(limit: int = 20) -> List[Dict]:
    """Get searches that returned no results (for improving data)"""
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    # Last 30 days
    since = timezone.now() - timedelta(days=30)
    
    zero_results = (
        SearchQueryModel.objects
        .filter(created_at__gte=since, results_count=0)
        .values('query')
        .annotate(count=Count('id'))
        .order_by('-count')
        [:limit]
    )
    
    return list(zero_results)
