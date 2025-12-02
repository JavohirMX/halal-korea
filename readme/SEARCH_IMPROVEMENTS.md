# Search Feature Improvements

This document describes the enhanced search functionality implemented in the Halal Korea application.

## Overview

The search system was upgraded from basic `icontains` queries to a comprehensive search solution featuring:

- **Weighted full-text search** with PostgreSQL
- **Korean↔English transliteration** for cross-language search
- **Fuzzy search** for typo tolerance (e.g., "resturant" → "restaurant")
- **Autocomplete suggestions** with keyboard navigation
- **Recent searches** persistence
- **Synonym expansion** for common terms
- **Proximity phrase parsing** for location-based queries
- **Location-only search** (e.g., searching "Hongdae" shows all places near Hongdae)
- **Search analytics** for monitoring and optimization

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (explore.html)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Search Input │  │ Autocomplete│  │ Recent Searches     │  │
│  │ + Debounce  │  │ Dropdown    │  │ (localStorage)      │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Endpoints                           │
│  /api/search/autocomplete/  - Suggestions                    │
│  /api/search/log/           - Log search queries             │
│  /api/search/recent/        - Get recent searches            │
│  /api/search/recent/clear/  - Clear recent searches          │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Search Service (search.py)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Synonyms    │  │ Proximity   │  │ Transliteration     │  │
│  │ Expansion   │  │ Parsing     │  │ (Korean↔English)    │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ HalalPlace                                           │    │
│  │ - search_vector (SearchVectorField + GIN Index)      │    │
│  │ - name_romanized (Korean → English transliteration)  │    │
│  │ - name_korean (English → Korean transliteration)     │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ SearchQuery (Analytics)                              │    │
│  │ - query, results_count, user, session_key, filters   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Features

### 1. Weighted Full-Text Search

Search results are ranked by field importance:

| Field | Weight | Description |
|-------|--------|-------------|
| `name` | A (highest) | Place name - most important |
| `description` | B | Place description |
| `address` | C | Physical address |

**Implementation:** Uses PostgreSQL `SearchVector` and `SearchRank` with GIN index for fast lookups.

### 2. Korean↔English Transliteration

Enables cross-language search without requiring exact character matches.

**Examples:**
- Search "bibimbap" → finds "비빔밥"
- Search "김치" → finds "kimchi"
- Search "Hongdae" → finds "홍대"

**How it works:**
- `name_romanized`: Stores romanized version of Korean names
- `name_korean`: Stores Korean version of English names
- Auto-populated via Django signals on model save

**Transliteration Mappings:**

```python
# Korean → English (Romanization)
KOREAN_TO_ROMAN = {
    'ㄱ': 'g', 'ㄴ': 'n', 'ㄷ': 'd', 'ㄹ': 'r/l',
    'ㅁ': 'm', 'ㅂ': 'b', 'ㅅ': 's', 'ㅇ': '',
    'ㅈ': 'j', 'ㅊ': 'ch', 'ㅋ': 'k', 'ㅌ': 't',
    'ㅍ': 'p', 'ㅎ': 'h', ...
}

# Common word mappings
COMMON_WORDS = {
    '식당': 'sikdang', '마트': 'mart', '카페': 'cafe',
    '홍대': 'hongdae', '이태원': 'itaewon', ...
}
```

### 3. Autocomplete Suggestions

Real-time search suggestions as users type.

**Features:**
- 300ms debounce to reduce API calls
- Keyboard navigation (↑↓ arrows, Enter, Escape)
- Category badges (restaurant, mosque, etc.)
- Recent searches shown when input is empty

**API Endpoint:** `GET /api/search/autocomplete/?q=<query>&limit=5`

**Response:**
```json
{
  "suggestions": [
    {
      "id": 1,
      "name": "Halal Kitchen",
      "category": "restaurant",
      "category_display": "Restaurant",
      "address": "Itaewon, Seoul"
    }
  ],
  "recent": ["previous search 1", "previous search 2"]
}
```

### 4. Recent Searches

Stores user's search history for quick access.

**Storage:**
- **Session-based:** Server-side for authenticated users
- **localStorage:** Client-side for persistence across sessions

**Limit:** 10 most recent searches

**API Endpoints:**
- `GET /api/search/recent/` - Get recent searches
- `POST /api/search/recent/clear/` - Clear history

### 5. Synonym Expansion

Automatically expands search terms to include common variations.

**Synonym Groups:**

| Search Term | Also Matches |
|-------------|--------------|
| masjid | mosque, prayer room, 모스크 |
| halal | restaurant, food, 할랄 |
| korean food | korean restaurant, 한식 |
| grocery | mart, supermarket, store |
| cafe | coffee, 카페 |

**Example:** Searching "masjid" will find places categorized as "mosque" or "prayer_room".

### 6. Proximity Phrase Parsing

Understands location-based queries like "near Hongdae" or "Itaewon area".

**Supported Patterns:**
- "near [location]"
- "around [location]"
- "[location] area"
- "close to [location]"
- "in [location]"

**Known Locations:**

| Location | Coordinates |
|----------|-------------|
| Hongdae | 37.5563, 126.9220 |
| Itaewon | 37.5345, 126.9946 |
| Gangnam | 37.4979, 127.0276 |
| Myeongdong | 37.5636, 126.9869 |
| Dongdaemun | 37.5712, 127.0095 |
| Insadong | 37.5743, 126.9856 |
| Sinchon | 37.5597, 126.9390 |
| Apgujeong | 37.5273, 127.0286 |

**Example:** "halal near Hongdae" → Shows halal places sorted by distance from Hongdae station.

### 7. Search Analytics

Tracks search queries for optimization and insights.

**Data Collected:**
- Query text
- Results count
- User (if authenticated)
- Session key
- Category filter
- Timestamp

**Admin Dashboard Features:**
- Popular searches (top 10)
- Zero-result searches (needs content)
- Search trends over time

## Files Structure

```
places/
├── models.py          # HalalPlace search fields, SearchQuery model
├── search.py          # Search service (synonyms, proximity, autocomplete)
├── signals.py         # Auto-update transliterations on save
├── views.py           # API endpoints
├── urls.py            # URL routing
├── admin.py           # SearchQuery admin with analytics
├── templates/
│   └── places/
│       └── explore.html  # Autocomplete UI
└── management/
    └── commands/
        └── populate_search_data.py  # Batch populate search vectors

utils/
└── transliteration.py  # Korean↔English transliteration utility
```

## Database Schema

### HalalPlace (New Fields)

```sql
ALTER TABLE places_halalplace ADD COLUMN name_romanized VARCHAR(255);
ALTER TABLE places_halalplace ADD COLUMN name_korean VARCHAR(255);
ALTER TABLE places_halalplace ADD COLUMN search_vector tsvector;

CREATE INDEX places_halalplace_search_vector_gin 
ON places_halalplace USING GIN (search_vector);
```

### SearchQuery (New Table)

```sql
CREATE TABLE places_searchquery (
    id SERIAL PRIMARY KEY,
    query VARCHAR(255) NOT NULL,
    results_count INTEGER NOT NULL,
    user_id INTEGER REFERENCES auth_user(id),
    session_key VARCHAR(40),
    category_filter VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX places_searchquery_query_idx ON places_searchquery (query);
CREATE INDEX places_searchquery_created_at_idx ON places_searchquery (created_at);
```

## Setup Instructions

### 1. Create and Apply Migration

```bash
python manage.py makemigrations places --name search_improvements
python manage.py migrate
```

### 2. Populate Search Data for Existing Places

```bash
# Populate all places (skips those with existing data)
python manage.py populate_search_data

# Force repopulate all places
python manage.py populate_search_data --force

# Custom batch size for large datasets
python manage.py populate_search_data --batch-size 50
```

### 3. Verify Installation

```bash
# Check search vectors are populated
python manage.py shell
>>> from places.models import HalalPlace
>>> HalalPlace.objects.exclude(search_vector='').count()
```

## API Reference

### Autocomplete

```http
GET /api/search/autocomplete/?q=halal&limit=5
```

**Parameters:**
- `q` (required): Search query (min 2 characters)
- `limit` (optional): Max results (default: 5, max: 10)

**Response:**
```json
{
  "suggestions": [
    {
      "id": 123,
      "name": "Halal Guys",
      "category": "restaurant",
      "category_display": "Restaurant",
      "address": "Itaewon, Seoul"
    }
  ],
  "recent": ["halal food", "mosque"]
}
```

### Log Search

```http
POST /api/search/log/
Content-Type: application/json

{
  "query": "halal restaurant",
  "results_count": 15,
  "category": "restaurant"
}
```

### Get Recent Searches

```http
GET /api/search/recent/
```

**Response:**
```json
{
  "recent_searches": ["halal", "mosque", "korean food"]
}
```

### Clear Recent Searches

```http
POST /api/search/recent/clear/
```

## Performance

### Optimizations

1. **GIN Index** on `search_vector` for fast full-text lookups
2. **Debounced autocomplete** (300ms) reduces API calls
3. **Limit results** in autocomplete to 5-10 items
4. **Session caching** for recent searches

### Expected Latency

| Operation | Target | Notes |
|-----------|--------|-------|
| Autocomplete | <100ms | Cached + indexed |
| Full search | <300ms | With filters and sorting |
| Analytics log | <50ms | Async-friendly |

## Monitoring

### Admin Dashboard

Access at `/admin/places/searchquery/` to view:

- **Total searches** in last 24h/7d/30d
- **Popular searches** - Top 10 most common queries
- **Zero-result searches** - Queries that returned no results (content gap)

### Logging

Search operations are logged at INFO level:

```python
logger.info(f"Search query: {query}, results: {count}")
```

## Troubleshooting

### Search vectors not working

```bash
# Repopulate search vectors
python manage.py populate_search_data --force
```

### Transliteration not working

Check that signals are registered:

```python
# places/apps.py should have:
def ready(self):
    import places.signals
```

### Autocomplete slow

1. Ensure GIN index exists on `search_vector`
2. Check database connection pooling
3. Consider adding Redis caching for frequent queries

## Future Enhancements

- [ ] Fuzzy matching ("halaal" → "halal")
- [ ] Voice search integration
- [ ] Personalized search ranking based on user history
- [ ] Elasticsearch integration for larger scale
- [ ] Search result highlighting
- [ ] "Did you mean?" suggestions for typos
