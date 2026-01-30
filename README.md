# Halal Korea 🇰🇷

**Find Halal Places in Korea** - A comprehensive Django web application for discovering halal restaurants, markets, mosques, and prayer rooms across South Korea.

[![Django](https://img.shields.io/badge/Django-5.1.6-092E20?style=flat-square&logo=django)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python)](https://python.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-15--3.3-4169E1?style=flat-square&logo=postgresql)](https://postgis.net/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](https://docker.com/)
[![Sentry](https://img.shields.io/badge/Sentry-Enabled-362D59?style=flat-square&logo=sentry)](https://sentry.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](#)

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [🏗️ Architecture](#-architecture)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Installation](#-installation)
- [🐳 Docker Deployment](#-docker-deployment)
- [🌍 Environment Configuration](#-environment-configuration)
- [📱 Apps & Modules](#-apps--modules)
- [🗄️ Database Schema](#-database-schema)
- [🔧 Management Commands](#-management-commands)
- [📊 Logging System](#-logging-system)
- [💾 Backup System](#-backup-system)
- [🌐 API Endpoints](#-api-endpoints)
- [🎨 Frontend & UI](#-frontend--ui)
- [🌏 Internationalization](#-internationalization)
- [🔒 Security](#-security)
- [📈 Performance](#-performance)
- [🧪 Testing](#-testing)
- [🤝 Contributing](#-contributing)
- [📞 Support](#-support)

## 🎯 Overview

Halal Korea is a location-based web application designed to help Muslims and halal food enthusiasts discover verified halal places throughout South Korea. The platform combines modern web technologies with geographic information systems to provide accurate, up-to-date information about halal restaurants, markets, mosques, and prayer facilities.

### Key Capabilities

- **🗺️ Interactive Map** - Real-time location-based search with Google Maps integration
- **📍 Smart Discovery** - Automatic location detection and distance-based recommendations
- **⭐ Community Reviews** - User-generated reviews and ratings for places
- **🕌 Prayer Times** - Accurate Islamic prayer times for any location in Korea
- **👥 User Profiles** - Personalized favorites and submission history
- **🌍 Multi-language** - Support for English, Korean, and Uzbek languages
- **📱 Responsive Design** - Mobile-first design with Tailwind CSS
- **📝 Blog System** - Full-featured blog with rich text editing and categories
- **💬 Contact Forms** - Integrated contact system with Telegram notifications
- **� Feedback Widget** - Floating feedback collection with user behavior analytics
- **�🔐 Social Login** - Google and GitHub OAuth integration
- **🖼️ Image Watermarking** - Automatic branding for uploaded images
- **� Admin Monitoring** - Real-time dashboards for performance and security
- **✏️ Community Suggestions** - Edit and image suggestions for existing places
- **🗺️ SEO Sitemaps** - Auto-generated XML sitemaps for search engines

## ✨ Features

### 🏪 Place Management

- **Categories**: Restaurants, Markets, Mosques, Prayer Rooms
- **Verification System**: Admin approval workflow for submitted places
- **Rich Information**: Photos, contact details, map links (Google, Kakao, Naver)
- **Geographic Search**: PostGIS-powered location queries
- **Filtering & Sorting**: By category, distance, rating
- **Community Suggestions**: Users can suggest edits to existing place information
- **Image Contributions**: Users can upload additional images for places
- **Watermarked Images**: Automatic watermark application to protect content

### 🔍 Advanced Search

- **Full-Text Search**: PostgreSQL-powered weighted search (name > description > address)
- **Korean↔English Transliteration**: Search "bibimbap" to find "비빔밥" and vice versa
- **Autocomplete Suggestions**: Real-time suggestions with keyboard navigation
- **Recent Searches**: Session and localStorage-based search history
- **Synonym Expansion**: "masjid" finds mosques, "halal" finds restaurants
- **Proximity Phrases**: "near Hongdae" or "Itaewon area" for location-based search
- **Search Analytics**: Track popular and zero-result queries in admin dashboard
- **GIN Index**: Fast full-text lookups with PostgreSQL GIN indexing

### 👤 User Experience

- **Authentication**: Custom user model with enhanced profiles
- **Social Login**: Google and GitHub OAuth integration
- **Account Merging**: Automatic merging of social accounts by email
- **Profile Pictures**: Support for uploaded and social provider avatars
- **Favorites**: Save and organize preferred places
- **Reviews**: Rate and review visited places (1-5 stars)
- **Submissions**: Submit new places for community verification
- **Language Preferences**: Persistent language selection (EN/KO/UZ)
- **Contribution Tracking**: View personal submission and suggestion history

### 🕰️ Prayer Times

- **Real-time Calculation**: Accurate prayer times for any Korean city
- **Multiple Methods**: Support for different calculation methods (Muslim World League, etc.)
- **Caching System**: Optimized performance with 23-hour cache
- **Asr Options**: Hanafi and Standard calculation methods

### 🔧 Admin Features

- **Content Moderation**: Approve/reject place submissions
- **User Management**: Comprehensive user administration
- **Analytics**: Built-in Django admin with custom logging
- **Backup System**: Automated database backups with Telegram notifications
- **Monitoring Dashboards**: 5 real-time dashboards for system health
  - Main monitoring dashboard with key metrics
  - Performance monitoring (slow queries, response times)
  - Security dashboard (failed logins, suspicious activity)
  - Content operations (pending submissions, moderation queue)
  - Analytics dashboard (user engagement, popular content)
- **Data Import/Export**: Multi-format data management system
  - Export: JSON, CSV, Excel, GeoJSON formats
  - Import: JSON and CSV with validation and duplicate detection
  - Bulk operations from admin list view
  - Dry-run validation before importing
- **Suggestion Management**: Review and approve community edits and images
- **Blog Management**: Full CMS with TinyMCE rich text editor
- **Translation Management**: Rosetta web interface for i18n strings

### 💬 Contact System

- **Contact Form**: Integrated contact forms on home and about pages
- **AJAX Submission**: Smooth form submission without page reload
- **Telegram Integration**: Instant notifications for new contact messages
- **Rate Limiting**: Spam protection with IP and user-based limits (3-5 per hour)
- **Admin Management**: Full contact message management in admin panel
- **Universal Access**: Available to both authenticated and anonymous users
- **Message Tracking**: Read status and response tracking

### 📊 Feedback System

- **Floating Widget**: Non-intrusive feedback widget on all pages
- **5-Star Rating**: Quick rating collection with optional comments
- **User Behavior Tracking**: Time on site/page, scroll depth, pages visited
- **Context Awareness**: Captures page type, URL, language, and device
- **Low Rating Alerts**: Telegram notifications for negative feedback (1-2 stars)
- **Rate Limiting**: IP-based spam protection for feedback submissions
- **Admin Categorization**: Categorize feedback (UI/UX, Bug, Feature Request, etc.)
- **Anonymous Support**: Works for both authenticated and anonymous users

### 📝 Blog & Content Management

- **Rich Text Editor**: TinyMCE integration with image uploads
- **Content Organization**: Categories and tags for organizing posts
- **Publishing Workflow**: Draft → Published → Archived states
- **Multi-language Support**: Per-post language selection
- **Featured Images**: Eye-catching images for blog posts
- **Related Places**: Link blog posts to halal places
- **SEO Optimization**: Automatic slug generation and meta descriptions
- **Author Attribution**: Track post authors and publication dates

### 📊 Admin Monitoring System

- **Real-time Dashboards**: 6 comprehensive monitoring dashboards
  - Main Dashboard: Overview of key system metrics
  - Performance Dashboard: Slow queries, response times, throughput
  - Security Dashboard: Failed logins, suspicious activity, authentication events
  - Content Operations: Pending submissions, moderation queue
  - Analytics Dashboard: User engagement, popular content, trends
  - Logs Dashboard: Real-time log viewing and filtering
- **Request Logging**: Sampled request tracking with performance data
- **Admin Actions Audit**: Complete audit trail of all admin operations
- **Security Event Tracking**: Log authentication failures and suspicious activity
- **Content Moderation Logs**: Track approval/rejection workflows
- **Alert System**: Configurable alert rules with Telegram and email notifications
- **Admin Notifications**: In-app notification system for admins
- **Data Retention**: Automatic cleanup of old monitoring data
- **Jazzmin Admin Theme**: Modern, customizable admin interface with dark mode

## 🏗️ Architecture

### Technology Stack

- **Framework**: Django 5.1.6 with Python 3.12
- **Database**: PostgreSQL 15+ with PostGIS 3.3 extension
- **Caching**: Django Local Memory Cache (Redis-ready)
- **Frontend**: HTML5, Tailwind CSS, Alpine.js, Vanilla JavaScript
- **Maps**: Google Maps JavaScript API with custom markers
- **Rich Text**: TinyMCE 4.1.0 for blog editing
- **Authentication**: Django AllAuth 0.57.0 (Google & GitHub OAuth)
- **Image Processing**: Pillow 11.3.0 with automatic watermarking
- **Translation**: Django Rosetta 0.10.2 for i18n management
- **Error Tracking**: Sentry SDK 2.46.0 for production monitoring
- **Admin Theme**: Django Jazzmin 3.0.1 with Cyborg dark theme
- **Deployment**: Docker + Gunicorn 23.0.0
- **Email**: Brevo (Sendinblue) SMTP for transactional emails
- **DNS/CDN**: Cloudflare for DNS, CDN, and email routing
- **Notifications**: Telegram Bot API integration
- **Logging**: Python JSON Logger 2.0.7 for structured logging

### Project Structure

```
halal-korea/
├── config/                 # Django settings and main configuration
│   ├── settings.py        # Main settings with environment variables
│   ├── urls.py           # Root URL configuration
│   ├── sitemaps.py       # SEO sitemap generation
│   ├── middleware.py     # Custom middleware (admin access)
│   ├── language_middleware.py  # Smart language detection
│   └── static_info.py    # Site metadata and branding
├── places/                # Core app for halal places
│   ├── models.py         # HalalPlace, PlaceEditSuggestion, PlaceImageSuggestion
│   ├── views.py          # Place discovery and submission views
│   ├── forms.py          # Place submission forms
│   ├── management/       # Commands: create_test_data, clear_place_images
│   └── templates/        # HTML templates
├── users/                 # User authentication and profiles
│   ├── models.py         # Custom User model with social auth
│   ├── views.py          # Auth and profile views
│   ├── adapters.py       # Custom AllAuth adapters
│   ├── decorators.py     # email_verification_required decorator
│   └── templates/        # User interface templates
├── reviews/              # Review and rating system
│   ├── models.py         # Review model with rating constraints
│   └── views.py          # Review CRUD operations
├── prayer_times/         # Islamic prayer times feature
│   ├── models.py         # PrayerTimeCache model
│   ├── utils.py          # Prayer calculation utilities
│   └── views.py          # Prayer time API views
├── blog/                 # Blog and content management
│   ├── models.py         # BlogPost, Category, Tag, RelatedPlace
│   ├── views.py          # Blog views and article display
│   ├── upload_views.py   # TinyMCE image upload handler
│   └── templates/        # Blog templates
├── contact/              # Contact form system
│   ├── models.py         # ContactMessage model
│   ├── views.py          # AJAX form submission
│   ├── rate_limiting.py  # Spam protection utilities
│   └── templates/        # Contact form templates
├── feedback/             # Floating feedback widget
│   ├── models.py         # FeedbackResponse with behavior metrics
│   ├── views.py          # AJAX feedback submission
│   └── rate_limiting.py  # Feedback spam protection
├── utils/                # Shared utilities and monitoring
│   ├── models.py         # SystemMetric, RequestLog, AdminAction, SecurityEvent, etc.
│   ├── admin_views.py    # Monitoring dashboard views
│   ├── monitoring_middleware.py  # Request tracking middleware
│   ├── logging_middleware.py    # Request ID injection
│   ├── logging_utils.py         # Custom logging decorators
│   ├── location_manager.py      # Location detection and management
│   ├── watermark.py             # Image watermarking utilities
│   ├── telegram_notifications.py # Telegram bot integration
│   ├── context_processors.py    # Global template context
│   ├── language_utils.py        # Language context processor
│   ├── language_views.py        # Language switching views
│   └── management/              # Custom Django commands
├── static/               # Static assets (CSS, JS, images)
├── media/                # User-uploaded content
├── locale/               # Translation files (ko, uz)
├── logs/                 # Application logs
├── templates/            # Global templates (account, socialaccount)
└── readme/               # Technical documentation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ with PostGIS 3.3+ extension
- Docker & Docker Compose (for containerized deployment)

### 1. Clone Repository

```bash
git clone <repository-url>
cd halal-korea
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### 3. Database Setup

```bash
# Create PostgreSQL database with PostGIS
createdb halal_korea
psql -d halal_korea -c "CREATE EXTENSION postgis;"
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Database Migration

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Run Development Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## ⚙️ Installation

### Development Environment

1. **Virtual Environment Setup**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Database Configuration**

   ```bash
   # Install PostgreSQL and PostGIS
   sudo apt-get install postgresql postgresql-contrib postgis

   # Create database
   sudo -u postgres createdb halal_korea
   sudo -u postgres psql -d halal_korea -c "CREATE EXTENSION postgis;"
   ```

3. **Environment Variables**

   ```env
   # Database
   DB_NAME=halal_korea
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432

   # Django
   DJANGO_SECRET_KEY=your-secret-key-here
   DJANGO_DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1

   # External APIs
   GOOGLE_MAPS_API_KEY=your-google-maps-api-key
   PRAYER_TIMES_API_BASE_URL=https://api.aladhan.com

   # Optional: Backup system
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   TELEGRAM_CHAT_ID=your-telegram-chat-id
   ```

4. **Static Files & Translations**

   ```bash
   python manage.py collectstatic
   python manage.py compilemessages
   ```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start services
docker-compose up --build

# Run in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

### Docker Configuration

The project includes:
- `Dockerfile` - Python 3.12-slim with PostGIS/GDAL dependencies
- `docker-compose.yaml` - Development setup with PostgreSQL/PostGIS

```yaml
# docker-compose.yaml
version: '3.9'
services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
    volumes:
      - .:/app
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db

  db:
    image: postgis/postgis:15-3.3
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      - .env
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### Manual Docker Build

```bash
# Build image
docker build -t halal-korea .

# Run container
docker run -p 8000:8000 --env-file .env halal-korea
```

### Production Deployment

```yaml
# docker-compose.prod.yml
version: '3.9'
services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DJANGO_DEBUG=False
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/var/www/static
      - media_volume:/var/www/media
    depends_on:
      - web

  db:
    image: postgis/postgis:15-3.3
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=halal_korea
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
```

## 🌍 Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key for cryptographic signing | `your-50-character-secret-key` |
| `DB_NAME` | PostgreSQL database name | `halal_korea` |
| `DB_USER` | Database username | `postgres` |
| `DB_PASSWORD` | Database password | `your-secure-password` |
| `DB_HOST` | Database host | `localhost` or `db` |
| `GOOGLE_MAPS_API_KEY` | Google Maps JavaScript API key | `AIza...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF | `https://yourdomain.com` |
| `PRAYER_TIMES_API_BASE_URL` | Base URL for prayer times API | `https://api.aladhan.com` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for backups/notifications | N/A |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications | N/A |
| `TELEGRAM_NOTIFICATIONS_ENABLED` | Enable Telegram notifications | `False` |
| `SITE_URL` | Base URL for admin links in notifications | `http://localhost:8000` |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client ID | N/A |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth client secret | N/A |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | N/A |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth client secret | N/A |
| `SENTRY_DSN` | Sentry DSN for error tracking | N/A |
| `SENTRY_ENVIRONMENT` | Sentry environment name | `production` |
| `SENTRY_TRACES_SAMPLE_RATE` | Sentry traces sample rate | `0.1` |
| `MONITORING_ENABLED` | Enable monitoring system | `True` |
| `MONITORING_SAMPLE_RATE` | Request sampling rate | `0.01` |
| `MONITORING_SLOW_THRESHOLD_MS` | Slow query threshold | `1000` |
| `MONITORING_RETENTION_DAYS` | Days to keep monitoring data | `30` |
| `ALERT_TELEGRAM_ENABLED` | Enable Telegram alerts | `True` |
| `ALERT_EMAIL_ENABLED` | Enable email alerts | `True` |
| `ALERT_EMAIL_RECIPIENTS` | Comma-separated alert emails | N/A |
| `WATERMARK_ENABLED` | Enable image watermarking | `True` |
| `WATERMARK_OPACITY` | Watermark opacity (0.0-1.0) | `0.25` |
| `EMAIL_BACKEND` | Email backend class | Console in dev |
| `EMAIL_HOST` | SMTP server host | `smtp-relay.brevo.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | Brevo SMTP login | N/A |
| `EMAIL_HOST_PASSWORD` | Brevo SMTP key | N/A |

### Email Infrastructure

The project uses a dual-service email setup:

**Sending Emails (Brevo/Sendinblue)**
- Transactional emails (password reset, verification, notifications)
- SMTP relay via `smtp-relay.brevo.com:587`
- Requires Brevo account with SMTP credentials

**Receiving Emails (Cloudflare Email Routing)**
- Cloudflare handles inbound email routing
- Custom domain email addresses (e.g., `contact@halal-korea.com`)
- Forwards to designated mailboxes

```env
# Email Configuration (Production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-brevo-smtp-login
EMAIL_HOST_PASSWORD=your-brevo-smtp-key
DEFAULT_FROM_EMAIL=Halal Korea <noreply@halal-korea.com>
```

## 📱 Apps & Modules

### Places App (`places/`)

**Core functionality for halal place management**

- **Models**: `HalalPlace`, `PlaceEditSuggestion`, `PlaceImageSuggestion` with PostGIS Point field
- **Categories**: Restaurant, Market, Mosque, Prayer Room
- **Status Workflow**: Pending → Approved/Rejected/Archived
- **Features**: Photo uploads, multiple map links, GPS coordinates
- **Community Features**: Users can suggest edits and upload additional images

### Users App (`users/`)

**Authentication and user profile management**

- **Custom User Model**: Extended Django user with favorites, social auth support
- **Language Preferences**: Per-user language settings
- **Profile Management**: Edit profile, manage submissions, profile pictures
- **Authentication Views**: Login, register, logout with custom templates
- **Social Login**: Google and GitHub OAuth integration
- **Account Merging**: Automatic merging of social accounts by email
- **Profile Pictures**: Support for uploaded and social provider avatars

### Reviews App (`reviews/`)

**Community review and rating system**

- **Rating System**: 1-5 star ratings with comments
- **Constraints**: One review per user per place
- **Moderation**: Reviews linked to user profiles
- **Display**: Average ratings calculated on-the-fly

### Prayer Times App (`prayer_times/`)

**Islamic prayer time calculations**

- **Calculation Methods**: Multiple Islamic calculation standards
- **Caching**: Efficient caching with 23-hour expiration
- **Location-based**: Automatic city detection for prayer times
- **API Integration**: External prayer time service integration

### Utils App (`utils/`)

**Shared utilities, monitoring, and helper functions**

- **Monitoring Models**: SystemMetric, RequestLog, AdminAction, SecurityEvent, ContentModerationLog, AdminNotification, AlertRule
- **Admin Dashboards**: 6 comprehensive monitoring dashboards
- **Middleware**: Request tracking, performance monitoring, cache statistics, request ID injection
- **Location Manager**: IP-based location detection with Korea/international detection
- **Logging Utilities**: Custom logging decorators, context enrichment, sampling
- **Watermarking**: Automatic watermark application to uploaded images
- **Telegram Notifications**: Integration for admin alerts and backups
- **Context Processors**: Global template context variables
- **Language Utilities**: Enhanced language switching and preferences
- **Management Commands**: Database backup, monitoring, translation tools

### Blog App (`blog/`)

**Content management system**

- **Models**: BlogPost, Category, Tag, RelatedPlace
- **Rich Text Editing**: TinyMCE integration with image uploads
- **Publishing Workflow**: Draft → Published → Archived
- **Multi-language**: Per-post language selection (en, ko, uz)
- **SEO Fields**: Meta title, meta description, auto-generated slugs
- **Features**: Featured images, excerpts, view count tracking
- **Related Content**: Link blog posts to halal places

### Contact App (`contact/`)

**Contact form system**

- **Models**: ContactMessage with user tracking
- **AJAX Submission**: Smooth form submission without page reload
- **Rate Limiting**: IP and user-based spam protection
- **Telegram Integration**: Instant notifications for new messages
- **Admin Management**: Full contact message management in admin panel

### Feedback App (`feedback/`)

**Floating feedback widget system**

- **Models**: FeedbackResponse with detailed behavior metrics
- **Widget**: Non-intrusive floating feedback button on all pages
- **Behavior Tracking**: Time on site, time on page, scroll depth, pages visited
- **Context Capture**: Page URL, page type, language, device type, browser
- **Rate Limiting**: IP-based spam protection
- **Telegram Alerts**: Notifications for low ratings (1-2 stars)
- **Admin Categorization**: UI/UX, Bug, Feature Request, Positive, Complaint

## 🗄️ Database Schema

### Core Models

#### HalalPlace Model

```python
class HalalPlace(models.Model):
    name = CharField(max_length=255)
    description = TextField()
    category = CharField(choices=CATEGORY_CHOICES)
    location = PointField()  # PostGIS Point field
    address = CharField(max_length=255)
    phone_number = CharField(optional)
    website = URLField(optional)
    google_map_link = URLField(optional)
    kakao_map_link = URLField(optional)
    naver_map_link = URLField(optional)
    photo_urls = JSONField(optional)  # Array of photo URLs
    status = CharField(choices=STATUS_CHOICES)
    submitted_by = ForeignKey(User)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

#### PlaceEditSuggestion Model

```python
class PlaceEditSuggestion(models.Model):
    place = ForeignKey(HalalPlace)
    suggested_by = ForeignKey(User)
    field_name = CharField(max_length=50, choices=EDITABLE_FIELDS)
    current_value = TextField()
    suggested_value = TextField()
    reason = TextField()
    status = CharField(choices=['pending', 'approved', 'rejected'])
    created_at = DateTimeField(auto_now_add=True)
    reviewed_by = ForeignKey(User, optional)
    reviewed_at = DateTimeField(optional)
    admin_notes = TextField(optional)
```

#### PlaceImageSuggestion Model

```python
class PlaceImageSuggestion(models.Model):
    place = ForeignKey(HalalPlace)
    suggested_by = ForeignKey(User)
    original_image = ImageField(upload_to='place_suggestions/originals/')
    image = ImageField(upload_to='place_suggestions/')  # Watermarked
    caption = CharField(max_length=255, optional)
    status = CharField(choices=['pending', 'approved', 'rejected'])
    created_at = DateTimeField(auto_now_add=True)
    reviewed_by = ForeignKey(User, optional)
    reviewed_at = DateTimeField(optional)
```

#### User Model

```python
class User(AbstractUser):
    favorite_places = ManyToManyField(HalalPlace)
    preferred_language = CharField(choices=LANGUAGE_CHOICES)
    email_verified = BooleanField(default=False)
    profile_picture = ImageField(upload_to='users/profile_pictures/', optional)
    social_avatar_url = URLField(optional)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    @property
    def avatar_url(self):
        """Returns profile picture or social avatar URL"""
        return self.profile_picture.url if self.profile_picture else self.social_avatar_url
```

#### Review Model

```python
class Review(models.Model):
    user = ForeignKey(User, CASCADE)
    place = ForeignKey(HalalPlace, CASCADE)
    rating = IntegerField()  # 1-5 stars
    comment = TextField()
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'place']
```

#### PrayerTimeCache Model

```python
class PrayerTimeCache(models.Model):
    city = CharField(max_length=100)
    country = CharField(max_length=100)
    date = DateField()
    prayer_times = JSONField()
    calculation_method = IntegerField()
    asr_method = IntegerField()
    last_updated = DateTimeField(auto_now=True)
```

#### BlogPost Model

```python
class BlogPost(models.Model):
    title = CharField(max_length=200)
    slug = SlugField(unique=True)
    author = ForeignKey(User)
    excerpt = TextField(max_length=500)
    content = HTMLField()  # TinyMCE rich text
    featured_image = ImageField(upload_to='blog/featured_images/', optional)
    category = ForeignKey(Category)
    tags = ManyToManyField(Tag)
    status = CharField(choices=['draft', 'published', 'archived'])
    language = CharField(choices=LANGUAGE_CHOICES)
    meta_title = CharField(max_length=60, optional)  # SEO title
    meta_description = CharField(max_length=160, optional)  # SEO description
    view_count = PositiveIntegerField(default=0)  # Analytics
    published_at = DateTimeField(optional)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

#### ContactMessage Model

```python
class ContactMessage(models.Model):
    user = ForeignKey(User, optional)
    name = CharField(max_length=100)
    email = EmailField()
    subject = CharField(max_length=200, optional)
    message = TextField()
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    created_at = DateTimeField(auto_now_add=True)
    is_read = BooleanField(default=False)
    responded_at = DateTimeField(optional)
```

#### Monitoring Models

```python
class SystemMetric(models.Model):
    """Aggregate metrics by hour/day for system monitoring"""
    timestamp = DateTimeField()
    metric_type = CharField(choices=METRIC_TYPE_CHOICES)
    metric_name = CharField(max_length=100)
    value = FloatField()
    metadata = JSONField(optional)

class RequestLog(models.Model):
    """Sampled request tracking with performance data"""
    path = CharField(max_length=500)
    method = CharField(max_length=10)
    status_code = IntegerField()
    response_time_ms = FloatField()
    ip_hash = CharField(max_length=16)  # Privacy-protected
    user_agent_hash = CharField(max_length=16)
    user = ForeignKey(User, optional)
    db_query_count = IntegerField(default=0)
    cache_hits = IntegerField(default=0)
    timestamp = DateTimeField(auto_now_add=True)

class AdminAction(models.Model):
    """Audit trail for admin operations"""
    admin_user = ForeignKey(User)
    action_type = CharField(choices=ACTION_TYPE_CHOICES)
    content_type = ForeignKey(ContentType)
    object_id = PositiveIntegerField()
    object_repr = CharField(max_length=200)
    changes = JSONField()  # Before/after values
    timestamp = DateTimeField(auto_now_add=True)
    ip_hash = CharField(max_length=16)

class ContentModerationLog(models.Model):
    """Track moderation workflow for content approval/rejection"""
    moderator = ForeignKey(User)
    content_type = CharField(choices=CONTENT_TYPE_CHOICES)
    object_id = PositiveIntegerField()
    action = CharField(choices=['approved', 'rejected', 'archived', 'pending'])
    time_in_queue_hours = FloatField(optional)
    reason = TextField(optional)
    timestamp = DateTimeField(auto_now_add=True)

class SecurityEvent(models.Model):
    """Security incidents and suspicious activity tracking"""
    event_type = CharField(choices=EVENT_TYPE_CHOICES)
    severity = CharField(choices=['low', 'medium', 'high', 'critical'])
    ip_hash = CharField(max_length=16)
    user = ForeignKey(User, optional)
    details = JSONField()
    resolved = BooleanField(default=False)
    timestamp = DateTimeField(auto_now_add=True)

class AdminNotification(models.Model):
    """In-app notifications for admin users"""
    recipient = ForeignKey(User, optional)  # Null = all admins
    title = CharField(max_length=200)
    message = TextField()
    severity = CharField(choices=['info', 'warning', 'error', 'critical'])
    link = CharField(max_length=500, optional)
    read = BooleanField(default=False)
    dismissed = BooleanField(default=False)
    timestamp = DateTimeField(auto_now_add=True)

class AlertRule(models.Model):
    """Configurable alert rules for monitoring"""
    name = CharField(max_length=200, unique=True)
    condition = CharField(choices=CONDITION_CHOICES)
    threshold = FloatField()
    window_minutes = IntegerField(default=10)
    alert_channels = JSONField()  # ['telegram', 'email', 'in_app']
    enabled = BooleanField(default=True)
    cooldown_minutes = IntegerField(default=60)
    last_triggered = DateTimeField(optional)
```

#### FeedbackResponse Model

```python
class FeedbackResponse(models.Model):
    user = ForeignKey(User, optional)
    session_id = CharField(max_length=100)
    rating = IntegerField(choices=1-5)
    comment = TextField(max_length=500, optional)
    page_url = CharField(max_length=500)
    page_type = CharField(choices=PAGE_TYPE_CHOICES)
    page_title = CharField(max_length=200, optional)
    time_on_site = IntegerField()  # Seconds
    time_on_page = IntegerField()  # Seconds
    pages_visited = IntegerField(default=1)
    scroll_depth = IntegerField(optional)  # 0-100%
    language = CharField(max_length=5)
    device_type = CharField(choices=['mobile', 'tablet', 'desktop'])
    browser = CharField(max_length=50, optional)
    screen_resolution = CharField(max_length=20, optional)
    ip_address = GenericIPAddressField()
    user_agent = TextField(optional)
    referrer = CharField(max_length=500, optional)
    admin_category = CharField(choices=CATEGORY_CHOICES, optional)
    admin_notes = TextField(optional)
    created_at = DateTimeField(default=timezone.now)
```

### Relationships

- **Users** can submit multiple **Places**
- **Users** can favorite multiple **Places**
- **Users** can write one **Review** per **Place**
- **Users** can suggest edits via **PlaceEditSuggestion**
- **Users** can upload images via **PlaceImageSuggestion**
- **Users** can author multiple **BlogPosts**
- **Places** can have multiple **Reviews**
- **Places** can have multiple **PlaceEditSuggestions**
- **Places** can have multiple **PlaceImageSuggestions**
- **BlogPosts** can be linked to multiple **Places** via **RelatedPlace**
- **BlogPosts** belong to one **Category** and can have multiple **Tags**
- **Prayer Times** are cached per location and calculation method
- **ContactMessages** can be linked to **Users** (optional)
- **FeedbackResponses** capture user behavior and ratings
- **AdminActions** track all admin operations on content
- **SecurityEvents** log authentication and security-related events
- **ContentModerationLogs** track approval/rejection workflows
- **AlertRules** define configurable monitoring alerts

## 🔧 Management Commands

### Available Commands

#### Database & Backup Commands

```bash
# Create and send backup to Telegram
python manage.py backup_database

# Force backup regardless of changes
python manage.py backup_database --force

# Local backup only (no Telegram)
python manage.py backup_database --local-only

# Test Telegram notifications
python manage.py test_telegram
```

#### Monitoring & Alerts

```bash
# Aggregate monitoring metrics
python manage.py aggregate_metrics

# Check and trigger alert rules
python manage.py check_alerts

# Verify monitoring system health
python manage.py check_monitoring_health

# Send daily digest report
python manage.py send_daily_digest
```

#### Test Data & Debugging

```bash
# Create sample places for development
python manage.py create_test_data

# Create specific number of test places
python manage.py create_test_data --count 50

# Clear all place images
python manage.py clear_place_images

# Test watermark application
python manage.py test_watermark path/to/image.jpg

# Test logging system functionality
python manage.py test_logging
```

#### Translation Management

```bash
# Check translation consistency across languages
python manage.py check_translation_consistency

# Get translation status report
python manage.py translation_status

# Validate translation files
python manage.py validate_translations

# AI-assisted translation helper
python manage.py translation_assistant
```

### Custom Command Examples

Create your own management commands in `app_name/management/commands/`:

```python
from django.core.management.base import BaseCommand
from places.models import HalalPlace

class Command(BaseCommand):
    help = 'Custom command description'
    
    def handle(self, *args, **options):
        # Your command logic here
        self.stdout.write(
            self.style.SUCCESS('Command executed successfully')
        )
```

## 📊 Logging System

### Log Files Structure

```
logs/
├── django.log          # General application logs (10MB, 5 backups)
├── django_errors.log   # Error-level logs only (10MB, 5 backups)
├── security.log        # Security events in JSON format (5MB, 3 backups)
├── api.log            # External API calls (5MB, 3 backups)
└── database.log       # Database operations (5MB, 3 backups)
```

### Logging Features

- **Request ID Tracking**: Unique ID for each request for tracing
- **Context Enrichment**: Automatic user ID, username, hostname injection
- **Structured JSON Logging**: Using python-json-logger for machine-readable logs
- **Log Sampling**: Configurable sampling rates for high-volume endpoints
- **Security Logging**: Separate logger for authentication and security events
- **API Logging**: Track external API calls and latencies

### Logging Levels by Environment

- **Development**: INFO level and above to console and files
- **Production**: WARNING level and above to console, INFO+ to files
- **Security Events**: Always logged to `security.log` in JSON format

### Usage in Code

```python
import logging
from utils.logging_utils import log_user_action, log_execution

# Get logger for your app
logger = logging.getLogger(__name__)

# Use decorator for automatic execution logging with sampling
@log_execution(level='info', sample=True)
def my_view(request):
    pass

# Log user actions with context
log_user_action(
    logger,
    'action_name',
    request.user,
    request,
    extra_data={'key': 'value'}
)

# Security logging
security_logger = logging.getLogger('security')
security_logger.info(f"User {user.username} logged in from {ip_address}")
```

### Log Rotation

- **Automatic rotation** when files reach size limits
- **Backup retention** policy (3-5 backup files per log type)
- **Configurable sample rates** per logger for high-volume endpoints

## 💾 Backup System

### Automated Database Backups

The backup system provides automated PostgreSQL database backups with intelligent change detection and Telegram notifications.

#### Features

- **Change Detection**: Only creates backups when database changes
- **Telegram Integration**: Automatic backup delivery to Telegram channel
- **Compression**: Gzip compression to minimize file size
- **Retention Policy**: Keeps last 3 local backups
- **Error Handling**: Comprehensive error notifications

#### Configuration

```env
# Telegram settings for backup notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Database settings (used for backups)
DB_NAME=halal_korea
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
```

#### Usage

```bash
# Automatic backup (only if changes detected)
python manage.py backup_database

# Force backup regardless of changes
python manage.py backup_database --force

# Create local backup without Telegram
python manage.py backup_database --local-only
```

#### Scheduling Backups

```bash
# Add to crontab for daily backups at 2 AM
0 2 * * * cd /path/to/halal-korea && python manage.py backup_database
```

### API Endpoints

#### Get Places JSON API

```http
GET /api/places/?category=restaurant&lat=37.5665&lng=126.9780&radius=5000
```

**Parameters:**

- `category` (optional): Filter by place category
- `lat`, `lng` (optional): User location for distance calculation
- `radius` (optional): Search radius in meters
- `search` (optional): Text search in name and description

**Response:**

```json
{
  "places": [
    {
      "id": 1,
      "name": "Halal Restaurant Seoul",
      "category": "restaurant",
      "latitude": 37.5665,
      "longitude": 126.9780,
      "address": "123 Seoul Street",
      "rating": 4.5,
      "distance": 245.6,
      "photo_urls": ["url1", "url2"]
    }
  ],
  "count": 25,
  "user_location": {
    "lat": 37.5665,
    "lng": 126.9780
  }
}
```

#### Prayer Times API

```http
POST /prayer/get-prayer-times/
Content-Type: application/json

{
  "city": "Seoul",
  "country": "South Korea",
  "date": "12-03-2024",
  "calculation_method": 3,
  "asr_method": 1
}
```

**Response:**

```json
{
  "success": true,
  "prayer_times": {
    "Fajr": "05:30",
    "Sunrise": "07:15",
    "Dhuhr": "12:45",
    "Asr": "15:30",
    "Maghrib": "18:15",
    "Isha": "19:45"
  },
  "location": {
    "city": "Seoul",
    "country": "South Korea"
  },
  "date": "12-03-2024"
}
```

#### Location API

```http
POST /set-location/
Content-Type: application/json

{
  "lat": 37.5665,
  "lng": 126.9780,
  "city": "Seoul",
  "country": "South Korea"
}
```

#### Search Autocomplete API

```http
GET /places/api/search/autocomplete/?q=halal&limit=5
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

#### Recent Searches API

```http
GET /places/api/search/recent/
```

**Response:**

```json
{
  "recent_searches": ["halal", "mosque", "korean food"]
}
```

#### Monitoring API Endpoints (Admin Only)

```http
GET /admin/monitoring/api/metrics/?type=request_count&hours=24
GET /admin/monitoring/api/stats/?period=today
GET /admin/monitoring/api/performance/?days=7
```

### SEO Endpoints

```http
GET /sitemap.xml          # Auto-generated XML sitemap
GET /robots.txt           # Robots exclusion file
```

### Feedback API

```http
POST /feedback/submit/
Content-Type: application/json

{
  "rating": 4,
  "comment": "Great website!",
  "page_url": "/places/explore/",
  "page_type": "explore",
  "session_id": "abc123",
  "time_on_site": 120,
  "time_on_page": 30,
  "pages_visited": 3,
  "scroll_depth": 75,
  "language": "en",
  "device_type": "desktop"
}
```

## 🎨 Frontend & UI

### Design System

- **Framework**: Tailwind CSS for utility-first styling
- **Color Scheme**: Green primary (#22c55e) with semantic color usage
- **Typography**: Ubuntu font family with system fallbacks
- **Layout**: Mobile-first responsive design
- **Components**: Reusable UI components with consistent styling
- **Dark Mode**: Full dark mode support with automatic theme switching

### Key UI Components

#### Navigation

- Responsive navbar with language selector
- Mobile hamburger menu with smooth animations
- User authentication status indicators
- Admin dashboard links for staff users

#### Place Cards

- Image carousel with Swiper.js integration
- Rating display with star icons
- Distance calculation and display
- Quick action buttons (favorite, directions, suggest edit)
- Lazy loading for performance

#### Map Integration

- Google Maps with custom markers
- Category-specific marker icons
- Info windows with place previews
- Real-time location detection
- Clustering for dense areas

#### Forms

- Multi-step place submission form
- Client-side validation with error messages
- Image upload with preview and watermarking
- Geographic coordinate picker
- AJAX form submissions with loading states

### JavaScript Features

- **Progressive Enhancement**: Works without JavaScript
- **AJAX Forms**: Smooth form submissions with fetch API
- **Real-time Search**: Instant place filtering and search
- **Location Services**: Browser geolocation API integration
- **Map Interactions**: Custom Google Maps JavaScript API integration
- **Alpine.js**: Lightweight reactivity for interactive components
- **Swiper.js**: Touch-enabled image carousels
- **Toastify**: Non-intrusive notification system
- **Dark Mode Toggle**: Persistent theme preferences
- **Infinite Scroll**: Pagination without page reloads (where applicable)
- **Feedback Widget**: Floating feedback button with behavior tracking

### Accessibility

- **WCAG 2.1 AA Compliance**: Semantic HTML and ARIA labels
- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Reader Support**: Proper heading structure and alt text
- **Color Contrast**: Meets accessibility standards
- **Focus Management**: Visible focus indicators

## 🌏 Internationalization

### Supported Languages

- **English** (`en`): Default language
- **Korean** (`ko`): Primary local language
- **Uzbek** (`uz`): Additional community language

### Translation Management

#### Mark Strings for Translation

```python
from django.utils.translation import gettext_lazy as _

# In views
message = _("Welcome to Halal Korea")

# In templates
{% load i18n %}
<h1>{% translate "Find Halal Places" %}</h1>
```

#### Update Translation Files

```bash
# Extract translatable strings
python manage.py makemessages -l ko
python manage.py makemessages -l uz

# Compile translations
python manage.py compilemessages
```

#### Translation Files Location

```
locale/
├── ko/LC_MESSAGES/
│   ├── django.po
│   └── django.mo
└── uz/LC_MESSAGES/
    ├── django.po
    └── django.mo
```

Note: English (`en`) is the source language and does not require translation files.

### Language Switching

- **User Preference**: Stored in user profile
- **Session-based**: For anonymous users
- **URL Parameter**: `?language=ko` for temporary switching
- **Browser Detection**: Automatic language detection from Accept-Language header

## 🔒 Security

### Authentication & Authorization

- **Custom User Model**: Extended Django user with additional fields
- **Password Validation**: Strong password requirements
- **Session Security**: Secure session configuration
- **CSRF Protection**: Cross-site request forgery protection
- **Permission System**: Django's built-in permission framework
- **Email Verification**: Required for content submissions
- **Social Authentication**: OAuth2 with Google and GitHub
- **Account Merging**: Secure merging of social accounts by email
- **Rate Limiting**: Protection against brute force attacks
  - Login attempts: IP and user-based limits
  - Registration: IP-based limits (3 per hour)
  - Password reset: IP and email-based limits
  - Contact form: IP and user-based limits (3-5 per hour)
  - Social auth: Request-based rate limiting

### Data Protection

- **Input Validation**: Server-side validation for all user inputs
- **SQL Injection Prevention**: Django ORM with parameterized queries
- **XSS Protection**: Template auto-escaping and CSP headers
- **File Upload Security**: Validated file types and size limits
- **Environment Variables**: Sensitive data in environment variables
- **Password Hashing**: PBKDF2 algorithm with SHA256
- **IP Hashing**: Privacy-preserving IP address hashing for logs
- **User Agent Hashing**: Hashed user agent strings in logs

### Security Headers

```python
# Security settings in production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

### Security Logging

All security-related events are logged to `logs/security.log` in JSON format:

- User authentication attempts (success/failure)
- Permission denials
- Suspicious activity patterns
- Admin actions (create, update, delete, approve)
- Failed form submissions
- Rate limit violations
- Social authentication events
- Account merging operations
- CSRF failures and invalid tokens

### Monitoring & Alerts

- **Real-time Security Dashboard**: Monitor authentication failures and suspicious activity
- **Automated Alerts**: Configurable alert rules with Telegram and email notifications
- **Audit Trail**: Complete history of admin actions with before/after values
- **Security Event Tracking**: Categorized by severity (low, medium, high, critical)
- **IP-based Tracking**: Hashed IP addresses for privacy-preserving security monitoring
- **Content Moderation Logs**: Track approval/rejection workflows with timing

## 📈 Performance

### Database Optimization

- **PostGIS Indexing**: Spatial indexes for location queries
- **Query Optimization**: Select_related and prefetch_related usage
- **Connection Pooling**: Efficient database connection management
- **Database Constraints**: Proper foreign keys and unique constraints

### Caching Strategy

- **Prayer Time Caching**: 23-hour cache for prayer calculations
- **Session Caching**: Location data cached in user sessions
- **Static File Caching**: Browser caching for static assets
- **QuerySet Caching**: Expensive query results cached

### Frontend Performance

- **Image Optimization**: Responsive images with proper sizing
- **Asset Minification**: Compressed CSS and JavaScript
- **Lazy Loading**: Images loaded on-demand
- **CDN Integration**: Static assets served from CDN (optional)

### Monitoring

- **Application Logs**: Performance logging for slow queries
- **Error Tracking**: Comprehensive error logging and alerting
- **Database Monitoring**: Query performance and index usage
- **Memory Usage**: Memory consumption tracking

## 🧪 Testing

### Test Structure

```
app_name/
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_forms.py
│   └── test_utils.py
```

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test places

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Test Categories

- **Unit Tests**: Model methods and utility functions
- **Integration Tests**: View responses and form processing
- **API Tests**: JSON endpoint functionality
- **Authentication Tests**: User login and permission checks
- **Geographic Tests**: PostGIS location queries
- **Blog Tests**: Blog models, views, TinyMCE uploads, admin
- **Contact Tests**: Contact form and rate limiting
- **Prayer Times Tests**: Cache and API integration

### Test Data

```python
# Use factories for test data
from django.test import TestCase
from places.models import HalalPlace
from users.models import User

class PlaceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_place_creation(self):
        place = HalalPlace.objects.create(
            name='Test Restaurant',
            category='restaurant',
            location=Point(126.9780, 37.5665),
            address='Test Address',
            status='approved',
            submitted_by=self.user
        )
        self.assertEqual(place.name, 'Test Restaurant')
```

## 🤝 Contributing

### Development Workflow

1. **Fork the Repository**

   ```bash
   git clone <your-fork-url>
   cd halal-korea
   git remote add upstream <original-repo-url>
   ```

2. **Create Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Development Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
   ```

4. **Code Standards**
   - Follow PEP 8 style guidelines
   - Write comprehensive docstrings
   - Add tests for new functionality
   - Update documentation as needed

5. **Commit and Push**

   ```bash
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/your-feature-name
   ```

6. **Submit Pull Request**
   - Describe changes in detail
   - Include screenshots for UI changes
   - Reference any related issues
   - Ensure all tests pass

### Code Review Process

- All pull requests require review
- Automated tests must pass
- Code coverage should not decrease
- Documentation updates required for new features
- Follow semantic versioning for releases

### Issue Reporting

- Use issue templates for bug reports and feature requests
- Include detailed reproduction steps
- Provide environment information
- Attach relevant log files or screenshots

## 📞 Support

### Documentation

- **Technical Docs**: `/readme/` directory contains detailed technical documentation:
  - `BACKUP_SYSTEM.md` - Automated database backup system with Telegram integration
  - `BLOG_IMPLEMENTATION.md` - Blog system architecture and features
  - `CONTACT_FORM.md` - Contact form implementation and rate limiting
  - `EXTERNAL_LOGIN_IMPLEMENTATION.md` - Social authentication setup and configuration
  - `EXTERNAL_LOGIN_SETUP.md` - Step-by-step OAuth setup guide
  - `LOGGING_SYSTEM.md` - Comprehensive logging system documentation
  - `LOGGING_ENHANCEMENTS.md` - Advanced logging features and decorators
  - `LOGGING_QUICK_REFERENCE.md` - Quick reference for logging usage
  - `MONITORING_SYSTEM.md` - Admin monitoring dashboards and features
  - `MONITORING_FEATURES_IMPLEMENTED.md` - Detailed monitoring implementation
  - `MONITORING_IMPLEMENTATION_SUMMARY.md` - Quick reference for monitoring
  - `PAGES_OVERVIEW.md` - Complete list of all pages and endpoints
  - `PASSWORD_RESET_IMPLEMENTATION.md` - Password reset flow documentation
  - `SEARCH_IMPROVEMENTS.md` - Advanced search with transliteration, autocomplete, and analytics
  - `TELEGRAM_NOTIFICATIONS.md` - Telegram bot integration guide
  - `TESTING.md` - Testing guidelines and test coverage
  - `TRANSLATION_GUIDELINES.md` - i18n and localization best practices
  - `WATERMARK_FEATURE.md` - Image watermarking system documentation
  - `BASE_HTML_IMPROVEMENTS.md` - Base template enhancements
  - `APP_LOGGING_SUMMARY.md` - Per-app logging configuration
- **API Documentation**: Available in this README
- **Deployment Guides**: Docker and production deployment instructions
- **PROJECT_CONTEXT.md**: Comprehensive project context and coding guidelines

### Community

- **Email**: <contact@halal-korea.com>
- **Issues**: Use GitHub issues for bug reports and feature requests
- **Discussions**: GitHub discussions for questions and community support

### Professional Support

For enterprise deployments and professional support:

- Custom development and integration
- Performance optimization consulting
- Security audits and compliance
- Training and documentation

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Django Community** for the excellent web framework
- **PostGIS** for powerful geographic capabilities
- **OpenStreetMap** for geographic data
- **Prayer Times API** (Aladhan) for accurate Islamic prayer calculations
- **Tailwind CSS** for the utility-first CSS framework
- **Jazzmin** for the modern Django admin theme
- **Sentry** for error tracking and monitoring
- **Contributors** who have helped improve this project

---

**Built with ❤️ for the Muslim community in Korea**

*Last updated: November 2025*
