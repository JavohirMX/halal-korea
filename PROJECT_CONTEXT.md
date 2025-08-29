# Project Context File - Halal Korea

## Project Summary

### Purpose:
Halal Korea is a comprehensive location-based web application designed to help Muslims and halal food enthusiasts discover verified halal places throughout South Korea. The platform serves both locals and international visitors by providing accurate, up-to-date information about halal restaurants, markets, mosques, and prayer facilities.

### Main Features:
- **🗺️ Interactive Map Integration** - Real-time location-based search with Google Maps JavaScript API
- **📍 Smart Place Discovery** - Automatic location detection with distance-based recommendations
- **⭐ Community-Driven Reviews** - User-generated reviews and 5-star rating system
- **🕌 Prayer Time Calculator** - Accurate Islamic prayer times for any location in Korea with multiple calculation methods
- **👥 User Profile Management** - Personalized favorites, submission history, and settings
- **🌍 Multi-language Support** - English, Korean, and Uzbek with persistent language preferences
- **📱 Responsive Design** - Mobile-first approach with progressive enhancement
- **🔧 Admin Moderation System** - Comprehensive admin tools for content approval and management

### Tech Stack:
- **Backend**: Django 5.1.6 with Python 3.12
- **Database**: PostgreSQL with PostGIS extension for geospatial queries
- **Frontend**: HTML5, Tailwind CSS 3.x, Alpine.js, Vanilla JavaScript
- **Maps**: Google Maps JavaScript API with custom markers
- **Rich Text**: TinyMCE for blog content editing
- **Deployment**: Docker + Gunicorn with Nginx
- **Caching**: Django Local Memory Cache (Redis ready)
- **Logging**: Comprehensive multi-level logging with file rotation

### Architectural Style:
**Monolithic Django MVC Architecture** with:
- **App-based modularization** (places, users, reviews, prayer_times, blog, contact, utils)
- **PostGIS spatial database** for geographic queries
- **RESTful API endpoints** for AJAX interactions
- **Template-based server-side rendering** with progressive enhancement
- **Comprehensive logging system** with structured log files
- **Environment-based configuration** using python-decouple

## Coding Guidelines

### Naming Conventions:
- **Models**: PascalCase (e.g., `HalalPlace`, `ContactMessage`, `PrayerTimeCache`)
- **Views**: snake_case functions (e.g., `home`, `place_detail`, `get_prayer_times_data`)
- **URLs**: kebab-case with underscores (e.g., `submit-place`, `prayer-times`, `set_location`)
- **Templates**: snake_case with hyphens for directories (e.g., `places/place_detail.html`)
- **CSS Classes**: Tailwind utility classes + custom kebab-case (e.g., `glass-effect`, `gradient-bg-hover`)
- **JavaScript**: camelCase (e.g., `toggleTheme`, `findNearestBtn`)

### Folder Structure:
```
halal-korea/
├── config/                 # Django configuration
│   ├── settings.py        # Environment-based settings
│   ├── urls.py           # Root URL routing
│   ├── static_info.py    # Site metadata constants
│   └── middleware.py     # Custom middleware
├── {app_name}/            # Each Django app follows this pattern:
│   ├── models.py         # Database models
│   ├── views.py          # View logic
│   ├── urls.py           # App-specific URLs
│   ├── forms.py          # Form definitions
│   ├── admin.py          # Admin interface
│   ├── apps.py           # App configuration
│   ├── tests.py          # Unit tests
│   ├── templates/        # HTML templates
│   │   └── {app_name}/   # App-specific templates
│   ├── migrations/       # Database migrations
│   └── management/       # Custom management commands
│       └── commands/
├── static/               # Static assets
├── media/                # User uploads
├── locale/              # Translation files
├── logs/                # Application logs
└── readme/              # Technical documentation
```

### Reusable Patterns/Components:

#### **Database Models Pattern:**
```python
class ModelName(models.Model):
    # Core fields first
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Status/category choices with explicit constants
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Relationships
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Timestamps (always include)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
```

#### **View Structure Pattern:**
```python
def view_name(request):
    """Descriptive docstring explaining view purpose"""
    try:
        logger.info(f"View accessed by user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
        
        # Get data
        queryset = Model.objects.filter(status='approved').select_related('user')
        
        # Handle pagination if needed
        paginator = Paginator(queryset, 10)
        page = request.GET.get('page', 1)
        
        context = {
            'objects': paginator.get_page(page),
            'page_title': 'Page Title',
        }
        
        return render(request, 'app/template.html', context)
        
    except Exception as e:
        logger.error(f"Error in view_name: {str(e)}", exc_info=True)
        messages.error(request, 'An error occurred')
        return redirect('fallback_url')
```

#### **Form Handling Pattern:**
```python
@login_required
@email_verification_required
def form_view(request):
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = request.user
            instance.save()
            messages.success(request, 'Success message')
            return redirect('success_url')
    else:
        form = FormClass()
    
    return render(request, 'template.html', {'form': form})
```

### Software Engineering Best Practices:

#### **1. DRY (Don't Repeat Yourself)**
- **Utils Module**: Common functionality in `utils/` (logging, location management, notifications)
- **Template Inheritance**: All templates extend `places/base.html`
- **Reusable Components**: Consistent HTML patterns for cards, forms, buttons
- **Model Mixins**: Common fields like `created_at`, `updated_at` in base patterns
- **Form Validation**: Shared validation logic in form classes

**Example - DRY Template Pattern:**
```html
<!-- places/partials/place_card.html -->
<div class="glass-card rounded-lg overflow-hidden">
    <!-- Reusable place card content -->
</div>

<!-- Usage in multiple templates -->
{% include 'places/partials/place_card.html' with place=place %}
```

#### **2. SOLID Principles**

**Single Responsibility Principle (SRP):**
- **Models**: Each model handles one entity (`HalalPlace`, `Review`, `User`)
- **Views**: Each view handles one specific action or page
- **Utils**: Separate modules for distinct concerns (location, logging, notifications)

**Open/Closed Principle (OCP):**
- **Extensible Models**: Use abstract base classes and mixins
- **Configurable Settings**: Environment-based configuration allows extension
- **Plugin Architecture**: Apps can be easily added/removed

**Liskov Substitution Principle (LSP):**
- **User Model**: Custom user extends AbstractUser properly
- **Form Inheritance**: Form classes properly inherit Django's base forms
- **Manager Classes**: Custom managers follow Django patterns

**Interface Segregation Principle (ISP):**
- **Focused Decorators**: `@login_required`, `@email_verification_required`
- **Specific Permissions**: Granular permission checks per view
- **API Endpoints**: Each endpoint serves a specific purpose

**Dependency Inversion Principle (DIP):**
- **Settings Configuration**: Depend on abstractions (environment variables)
- **Database Abstraction**: Use Django ORM instead of raw SQL
- **Service Layer**: External APIs abstracted through utility functions

#### **3. Clean Code Principles**

**Meaningful Names:**
```python
# Good: Descriptive and clear
def get_places_within_radius(user_location, radius_km):
    return HalalPlace.objects.filter(
        location__distance_lte=(user_location, Distance(km=radius_km))
    )

# Avoid: Unclear abbreviations
def get_plcs(loc, r):
    pass
```

**Small Functions:**
```python
# Good: Single purpose, small function
def calculate_place_rating(place):
    """Calculate average rating for a place."""
    return place.reviews.aggregate(Avg('rating'))['rating__avg'] or 0

def format_rating_display(rating):
    """Format rating for display."""
    return round(rating, 1) if rating else 'No ratings'
```

**Function Arguments (Limit to 3):**
```python
# Good: Use keyword arguments or data classes
def create_place_notification(place, user, action_type='created'):
    pass

# Better: Use a data structure
@dataclass
class PlaceNotificationData:
    place: HalalPlace
    user: User
    action_type: str = 'created'
```

#### **4. Architectural Best Practices**

**Separation of Concerns:**
- **Models**: Data structure and business logic only
- **Views**: Request handling and response preparation
- **Templates**: Presentation logic only
- **Forms**: Validation and data cleaning
- **Utils**: Shared business logic and external integrations

**Database Best Practices:**
```python
# Always use select_related for foreign keys
places = HalalPlace.objects.select_related('submitted_by').filter(status='approved')

# Use prefetch_related for many-to-many and reverse foreign keys
places = HalalPlace.objects.prefetch_related('reviews__user').all()

# Database indexes on frequently queried fields
class HalalPlace(models.Model):
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    location = models.PointField(spatial_index=True)
```

**Error Handling Strategy:**
```python
def robust_view(request):
    """Example of proper error handling."""
    try:
        # Main logic
        data = process_user_request(request)
        return JsonResponse({'success': True, 'data': data})
    
    except ValidationError as e:
        logger.warning(f"Validation error: {e}", extra={'user_id': request.user.id})
        return JsonResponse({'success': False, 'errors': e.message_dict})
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred'})
```

#### **5. Security Best Practices**

**Input Validation:**
```python
# Always validate and sanitize input
from django.core.validators import validate_email
from django.utils.html import escape

def clean_user_input(data):
    """Clean and validate user input."""
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = escape(value.strip())
        else:
            cleaned[key] = value
    return cleaned
```

**Authorization Patterns:**
```python
# Consistent permission checking
@login_required
@email_verification_required
def edit_place(request, place_id):
    place = get_object_or_404(HalalPlace, id=place_id)
    
    # Check ownership or admin rights
    if place.submitted_by != request.user and not request.user.is_staff:
        logger.warning(f"Unauthorized edit attempt", extra={
            'user_id': request.user.id,
            'place_id': place_id
        })
        return HttpResponseForbidden()
```

#### **6. Performance Best Practices**

**Caching Strategy:**
```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Cache expensive operations
def get_prayer_times_cached(city, date):
    cache_key = f"prayer_times_{city}_{date}"
    times = cache.get(cache_key)
    
    if times is None:
        times = calculate_prayer_times(city, date)
        cache.set(cache_key, times, timeout=23*60*60)  # 23 hours
    
    return times

# Cache entire pages when appropriate
@cache_page(60 * 15)  # 15 minutes
def static_about_page(request):
    return render(request, 'places/about.html')
```

**Database Optimization:**
```python
# Use database functions instead of Python loops
from django.db.models import Count, Avg

# Good: Database aggregation
places_with_stats = HalalPlace.objects.annotate(
    review_count=Count('reviews'),
    avg_rating=Avg('reviews__rating')
).filter(status='approved')

# Avoid: Python loops for aggregation
# for place in places:
#     place.review_count = place.reviews.count()  # N+1 query problem
```

#### **7. Testing Best Practices**

**Test Structure:**
```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

class PlaceViewTests(TestCase):
    def setUp(self):
        """Set up test data once per test method."""
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
    
    def test_place_creation_requires_auth(self):
        """Test that place creation requires authentication."""
        response = self.client.post('/places/submit/', {})
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_valid_place_submission(self):
        """Test successful place submission."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post('/places/submit/', {
            'name': 'Test Restaurant',
            'category': 'restaurant',
            # ... other valid data
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(HalalPlace.objects.filter(name='Test Restaurant').exists())
```

#### **8. Code Documentation Standards**

**Docstring Format:**
```python
def calculate_distance_to_places(user_location, places_queryset, max_distance=None):
    """
    Calculate distances from user location to places.
    
    Args:
        user_location (Point): User's geographic location
        places_queryset (QuerySet): QuerySet of HalalPlace objects
        max_distance (float, optional): Maximum distance in kilometers
    
    Returns:
        QuerySet: Places annotated with distance, ordered by proximity
    
    Raises:
        ValueError: If user_location is not a valid Point object
        
    Example:
        >>> user_loc = Point(126.9780, 37.5665)  # Seoul
        >>> nearby_places = calculate_distance_to_places(user_loc, places, 5.0)
    """
```

#### **9. Logging and Monitoring Best Practices**

**Structured Logging:**
```python
import logging
from utils.logging_utils import log_user_action, sanitize_sensitive_data

logger = logging.getLogger(__name__)

def place_submission_view(request):
    """Handle place submission with comprehensive logging."""
    start_time = time.time()
    
    try:
        # Log user action
        log_user_action(logger, 'place_submission_started', request.user, request)
        
        # Process submission
        place = create_place_from_form(request.POST)
        
        # Log success with timing
        execution_time = time.time() - start_time
        logger.info(
            f"Place submitted successfully",
            extra={
                'user_id': request.user.id,
                'place_id': place.id,
                'execution_time': execution_time,
                'category': place.category
            }
        )
        
    except Exception as e:
        logger.error(
            f"Place submission failed: {str(e)}",
            extra={
                'user_id': request.user.id,
                'form_data': sanitize_sensitive_data(request.POST.dict()),
                'execution_time': time.time() - start_time
            },
            exc_info=True
        )
        raise
```

#### **10. Environment and Configuration Management**

**Configuration Pattern:**
```python
# config/settings.py
from decouple import config, Csv

# Required settings (will raise error if missing)
SECRET_KEY = config('DJANGO_SECRET_KEY')
DB_PASSWORD = config('DB_PASSWORD')

# Optional settings with defaults
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

# Feature flags
TELEGRAM_NOTIFICATIONS_ENABLED = config('TELEGRAM_NOTIFICATIONS_ENABLED', default=False, cast=bool)
```

#### **Implementation Guidelines:**

1. **Code Reviews**: Every PR must demonstrate adherence to these principles
2. **Refactoring**: Regularly refactor to maintain code quality
3. **Documentation**: Update documentation when adding new patterns
4. **Testing**: Write tests that verify both functionality and design principles
5. **Performance**: Profile and optimize based on actual usage patterns
6. **Security**: Regular security audits and dependency updates

## Design Guidelines

### Colors:
**Primary Color Palette:**
- **Primary Green**: `#22c55e` (primary-500) - Main brand color
- **Primary Variants**: 
  - Light: `#4ade80` (primary-400)
  - Dark: `#16a34a` (primary-600)
  - Extra Dark: `#15803d` (primary-700)

**Secondary Colors:**
- **Teal Accent**: `#10b981` (teal-500) - Secondary actions
- **Success**: `#059669` (teal-600)
- **Warning**: `#f59e0b` (yellow-500)
- **Error**: `#dc2626` (red-600)

**Neutral Palette:**
- **Background Light**: `#f9fafb` (gray-50)
- **Background Dark**: `#111827` (gray-900)
- **Text Primary**: `#111827` (gray-900) / `#f9fafb` (white in dark mode)
- **Text Secondary**: `#6b7280` (gray-500)

### Typography:
**Font Stack:**
- **Primary**: Ubuntu (Google Fonts)
- **Fallback**: system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Arial, sans-serif

**Font Weights:**
- Light: 300
- Regular: 400  
- Medium: 500
- Bold: 700

**Text Sizes:**
- **Headings**: 2rem, 1.75rem, 1.5rem, 1.25rem, 1.125rem, 1rem
- **Body**: 1rem (16px)
- **Small**: 0.875rem (14px)
- **Extra Small**: 0.75rem (12px)

### Spacing Scale:
Following Tailwind CSS spacing scale (4px base):
- **xs**: 0.25rem (4px)
- **sm**: 0.5rem (8px)
- **md**: 1rem (16px)
- **lg**: 1.5rem (24px)
- **xl**: 2rem (32px)
- **2xl**: 3rem (48px)

### UI Components and Their Usage:

#### **Glass Effect Cards** (`.glass-card`):
```css
background: rgba(255, 255, 255, 0.7);
backdrop-filter: blur(8px);
border: 1px solid rgba(255, 255, 255, 0.3);
```
**Usage**: Place cards, feature sections, content containers

#### **Gradient Buttons** (`.gradient-bg-hover`):
```css
background-image: linear-gradient(to right, #22c55e, #10b981, #22c55e);
transition: all 0.5s ease;
```
**Usage**: Primary CTAs, submit buttons, important actions

#### **Status Badges**:
- **Pending**: `bg-yellow-100 text-yellow-800`
- **Approved**: `bg-green-100 text-green-800`
- **Rejected**: `bg-red-100 text-red-800`
- **Archived**: `bg-gray-100 text-gray-800`

#### **Icons**:
- **FontAwesome 6.5.1** for all icons
- **Category Icons**: `fa-utensils` (restaurant), `fa-shopping-basket` (market), `fa-mosque` (mosque), `fa-pray` (prayer room)
- **Action Icons**: `fa-heart` (favorite), `fa-map-marker-alt` (location), `fa-star` (rating)

#### **Navigation Pattern**:
- **Fixed navbar** with glass effect
- **Responsive breakpoints**: sm (640px), md (768px), lg (1024px), xl (1280px)
- **Mobile hamburger menu** with slide-down animation

## Example Snippets

### Common Coding Patterns:

#### **Location-Based Queryset**:
```python
# Get places near user location
if user_location:
    places = HalalPlace.objects.filter(
        status='approved'
    ).annotate(
        distance=Distance('location', user_location)
    ).order_by('distance')
else:
    places = HalalPlace.objects.filter(status='approved').order_by('-created_at')
```

#### **AJAX Response Pattern**:
```python
def ajax_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Process data
            return JsonResponse({'success': True, 'message': 'Success'})
        except Exception as e:
            logger.error(f"AJAX error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
```

#### **Template Internationalization Pattern**:
```html
{% load i18n %}
<h1>{% translate "Find Halal Places in Korea" %}</h1>
<p>{% blocktranslate count places=places.count %}Found {{ places }} place{% plural %}Found {{ places }} places{% endblocktranslate %}</p>
```

### Example Component Usage:

#### **Place Card Component**:
```html
<div class="glass-card rounded-lg overflow-hidden transition-all duration-200 hover:shadow-lg">
    <img src="{{ place.photo_urls.0 }}" alt="{{ place.name }}" class="w-full h-48 object-cover">
    <div class="p-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{{ place.name }}</h3>
        <p class="text-sm text-primary-600 dark:text-primary-400">
            <i class="fas fa-utensils mr-1"></i>{{ place.category|title }}
        </p>
    </div>
</div>
```

#### **Form Input Pattern**:
```html
<input type="text" 
       name="name"
       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
       placeholder="{% translate 'Enter place name' %}">
```

## Future Consistency Rules

### What Must Stay Consistent:

1. **Color Palette**: Primary green (#22c55e) and teal (#10b981) must remain the brand colors
2. **Typography**: Ubuntu font family and the established font weight system
3. **Component Names**: Glass effects, gradient patterns, and status badge classes
4. **Database Patterns**: Always include created_at/updated_at, use explicit STATUS_CHOICES
5. **Logging Structure**: Maintain the established logging patterns and levels
6. **URL Naming**: Keep kebab-case URLs with underscores for complex names
7. **Error Handling**: Always use try-catch in views with proper logging
8. **Template Structure**: Keep the base.html inheritance pattern
9. **API Response Format**: Maintain JsonResponse pattern with success/error structure
10. **Security Decorators**: Always use @login_required and @email_verification_required where needed

### What Can Be Flexible:

1. **Content Organization**: New sections and layouts within the established design system
2. **Additional Colors**: Can add accent colors as long as they complement the primary palette
3. **New Component Variants**: Can create variations of glass-card, gradient-bg patterns
4. **Animation Timing**: Can adjust transition durations while keeping the easing functions
5. **Responsive Breakpoints**: Can add new breakpoints for specific needs
6. **Icon Choices**: Can use different FontAwesome icons while maintaining consistency
7. **Form Layouts**: Can create new form patterns following the established input styling
8. **API Endpoints**: Can add new endpoints following the established response patterns

---

## Clarification Needs

Based on my analysis, here are **5 key areas** where I would need additional clarification to ensure stronger consistency in future work:

### 1. **Design System Evolution**
- **Question**: Are there plans to implement a formal design system (like Storybook) to document and maintain component consistency?
- **Impact**: Would help maintain visual consistency and speed up development of new features
- **Current Gap**: Components are well-designed but not formally documented

### 2. **API Strategy & Standards**
- **Question**: What are the long-term plans for API endpoints? Should we establish OpenAPI/Swagger documentation standards?
- **Impact**: Currently using mixed patterns (some AJAX, some traditional forms) - need clarity on API-first vs. server-rendered approach
- **Current Gap**: No formal API documentation or versioning strategy

### 3. **Performance & Scaling Guidelines**
- **Question**: What are the performance benchmarks and scaling requirements? Should we implement Redis caching, CDN strategies, or database optimization guidelines?
- **Impact**: Current caching is local memory only - need guidelines for production scaling
- **Current Gap**: No formal performance monitoring or optimization standards

### 4. **Internationalization Strategy**
- **Question**: Are there plans to add more languages beyond English, Korean, and Uzbek? What's the process for translation management?
- **Impact**: Need to establish workflows for translators and maintain translation quality
- **Current Gap**: No formal translation workflow or style guide

### 5. **Testing & Quality Assurance Standards**
- **Question**: What testing standards should be implemented? Should we require minimum code coverage, integration tests, or E2E testing?
- **Impact**: Currently minimal testing coverage - need guidelines for test requirements
- **Current Gap**: No established testing patterns or coverage requirements

These clarifications would help establish a more robust foundation for maintaining consistency as the project grows and evolves.
