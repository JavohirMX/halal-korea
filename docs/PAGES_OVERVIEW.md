# Halal Korea - Pages Overview

**Document Version:** 1.0  
**Last Updated:** November 20, 2025  
**Purpose:** Comprehensive listing of all pages and endpoints organized by importance

---

## Table of Contents

- [Critical Pages (Core Functionality)](#critical-pages-core-functionality)
- [High Priority Pages (User Engagement)](#high-priority-pages-user-engagement)
- [Content & Information Pages](#content--information-pages)
- [User Management & Settings](#user-management--settings)
- [Community Features](#community-features)
- [Content Organization](#content-organization)
- [API & AJAX Endpoints](#api--ajax-endpoints)
- [Internationalization](#internationalization)
- [Admin & Monitoring](#admin--monitoring)
- [Utility & Error Pages](#utility--error-pages)
- [Summary Statistics](#summary-statistics)

---

## Critical Pages (Core Functionality)

### 1. Home Page
- **URL:** `/`
- **View:** `places.views.home`
- **Template:** `places/home.html`
- **Description:** Landing page with featured halal places
- **Features:**
  - Distance-based recommendations for Korea users
  - Rating-based recommendations for international users
  - Featured places carousel
  - Location detection integration
  - Primary entry point for all users

### 2. Explore/Search
- **URL:** `/explore/`
- **View:** `places.views.explore`
- **Template:** `places/explore.html`
- **Description:** Main discovery interface with advanced filtering
- **Features:**
  - Category filtering (Restaurant, Market, Mosque, Prayer Room)
  - City and distance-based search
  - Keyword search
  - Sort options (distance, rating, newest)
  - Pagination support
  - Map view integration
  - AJAX-based filtering

### 3. Place Detail
- **URL:** `/place/<int:pk>/`
- **View:** `places.views.place_detail`
- **Template:** `places/place_detail.html`
- **Description:** Individual place information page
- **Features:**
  - Complete place information
  - Reviews and ratings display
  - Photo gallery
  - Map integration (Google, Kakao, Naver)
  - Contact information
  - Direction links
  - Review submission form
  - Edit suggestion option

### 4. Prayer Times
- **URL:** `/prayer/`
- **View:** `prayer_times.views.prayer_times`
- **Template:** `prayer_times/prayer_times.html`
- **Description:** Real-time Islamic prayer times calculator
- **Features:**
  - Location-based calculations
  - Multiple calculation methods (Muslim World League, etc.)
  - Asr calculation options (Hanafi/Standard)
  - Auto-detection of user location
  - Manual location input
  - 23-hour caching system
  - Essential for Muslim users

---

## High Priority Pages (User Engagement)

### 5. User Registration
- **URL:** `/users/register/`
- **View:** `users.views.register_view`
- **Template:** `users/register.html`
- **Description:** Account creation page
- **Features:**
  - Email verification system
  - Password strength validation
  - Rate limiting protection
  - Gateway to authenticated features
  - Social auth integration (allauth)

### 6. User Login
- **URL:** `/users/login/`
- **View:** `users.views.login_view`
- **Template:** `users/login.html`
- **Description:** Authentication portal
- **Features:**
  - Credential-based login
  - Social login integration (Google, Facebook, etc.)
  - Remember me functionality
  - Password reset link
  - Rate limiting protection

### 7. User Profile
- **URL:** `/users/profile/` or `/users/profile/<str:username>/`
- **View:** `users.views.profile`
- **Template:** `users/profile.html`
- **Description:** Personal dashboard and public profile
- **Features:**
  - Personal information display
  - Favorites management
  - Submission history
  - Reviews history
  - Public/private view modes
  - Edit profile option

### 8. Submit New Place
- **URL:** `/submit/`
- **View:** `places.views.submit_place`
- **Template:** `places/submit_place.html`
- **Description:** Community-driven content creation
- **Features:**
  - Form with location picker
  - Photo upload with automatic watermarking
  - Map integration for location selection
  - Category selection
  - Multiple map links support
  - Requires email verification
  - Telegram notification to admins

### 9. Add Review
- **URL:** `/reviews/add/<int:place_id>/`
- **View:** `reviews.views.add_review`
- **Description:** Rating and review submission
- **Features:**
  - 1-5 star rating system
  - Text review
  - Authentication required
  - One review per user per place
  - User engagement feature

---

## Content & Information Pages

### 10. Blog Home
- **URL:** `/blog/`
- **View:** `blog.views.blog_home`
- **Template:** `blog/home.html`
- **Description:** Articles and guides listing
- **Features:**
  - Published posts listing
  - Pagination
  - Category filtering
  - Search functionality
  - Archive links
  - Content marketing platform

### 11. Blog Post Detail
- **URL:** `/blog/<slug:slug>/`
- **View:** `blog.views.post_detail`
- **Template:** `blog/post_detail.html`
- **Description:** Individual article pages
- **Features:**
  - TinyMCE rich content display
  - Featured image
  - Category and tags
  - Related posts
  - Share functionality
  - View count tracking

### 12. About Page
- **URL:** `/about/`
- **View:** `places.views.about`
- **Template:** `places/about.html`
- **Description:** Project information page
- **Features:**
  - Mission and values
  - Team information
  - Contact form integration
  - Project statistics
  - How it works guide

### 13. Donate Page
- **URL:** `/donate/`
- **View:** `places.views.donate`
- **Template:** `places/donate.html`
- **Description:** Support the platform
- **Features:**
  - Donation information
  - Funding goals
  - Transparency reporting
  - Payment integration options

### 14. Legal/Terms
- **URL:** `/legal/`
- **View:** `places.views.legal`
- **Template:** `places/legal.html`
- **Description:** Legal documentation
- **Features:**
  - Terms of service
  - Privacy policy
  - Data collection notice
  - User rights
  - Legal compliance

---

## User Management & Settings

### 15. Edit Profile
- **URL:** `/users/profile/edit/`
- **View:** `users.views.edit_profile`
- **Template:** `users/edit_profile.html`
- **Description:** Update user information
- **Features:**
  - Profile photo upload
  - Personal information update
  - Bio/description editing
  - Language preferences
  - Privacy settings

### 16. My Contributions
- **URL:** `/my-contributions/`
- **View:** `places.views.my_contributions`
- **Template:** `places/my_contributions.html`
- **Description:** User's submission dashboard
- **Features:**
  - View submitted places
  - Track submission status (pending/approved/rejected)
  - View edit suggestions
  - Track suggestion status
  - Statistics overview

### 17. Password Reset Request
- **URL:** `/users/password-reset/`
- **View:** `users.views.password_reset_request`
- **Template:** `users/password_reset.html`
- **Description:** Account recovery initiation
- **Features:**
  - Email-based reset system
  - Rate limiting protection
  - Token generation
  - Security verification

### 18. Password Reset Confirm
- **URL:** `/users/password-reset/<uidb64>/<token>/`
- **View:** `users.views.password_reset_confirm`
- **Template:** `users/password_reset_confirm.html`
- **Description:** Complete password reset
- **Features:**
  - Token validation
  - New password setting
  - Password strength validation
  - Auto-login after reset

### 19. Account Activation
- **URL:** `/users/activate/<uidb64>/<token>/`
- **View:** `users.views.activate_account`
- **Template:** `users/activation.html`
- **Description:** Email verification completion
- **Features:**
  - Token validation
  - Account enablement
  - Welcome message
  - Auto-redirect to login

### 20. Resend Activation Email
- **URL:** `/users/resend-activation/`
- **View:** `users.views.resend_activation_email`
- **Template:** `users/resend_activation.html`
- **Description:** Re-request verification email
- **Features:**
  - Email resend
  - Rate limiting
  - Token regeneration

---

## Community Features

### 21. Suggest Place Edit
- **URL:** `/place/<int:pk>/suggest-edit/`
- **View:** `places.views.suggest_place_edit`
- **Template:** `places/suggest_edit.html`
- **Description:** Community-driven place updates
- **Features:**
  - Field-specific suggestions
  - Image addition suggestions
  - Reason/explanation required
  - Admin review workflow
  - Authentication required

### 22. Contact Form Submission
- **URL:** `/contact/submit/`
- **View:** `contact.views.submit_contact_form`
- **Description:** User support and feedback
- **Features:**
  - AJAX submission
  - Rate limiting protection
  - Telegram notification integration
  - Available to authenticated and anonymous users
  - Multiple submission contexts (home, about)

### 23. Edit Review
- **URL:** `/reviews/edit/<int:review_id>/`
- **View:** `reviews.views.edit_review`
- **Description:** Modify existing review
- **Features:**
  - Owner-only access
  - Rating update
  - Review text update
  - Timestamp update

### 24. Delete Review
- **URL:** `/reviews/delete/<int:review_id>/`
- **View:** `reviews.views.delete_review`
- **Description:** Remove own review
- **Features:**
  - Owner-only access
  - Confirmation required
  - Soft delete option

### 25. Toggle Favorite
- **URL:** `/users/favorite/toggle/<int:place_id>/` or `/users/toggle-favorite/<int:place_id>/`
- **View:** `users.views.toggle_favorite`
- **Description:** AJAX endpoint for favorites
- **Features:**
  - Add/remove from favorites
  - JSON response
  - Authentication required
  - Quick bookmark functionality

---

## Content Organization

### 26. Blog Search
- **URL:** `/blog/search/`
- **View:** `blog.views.search_posts`
- **Template:** `blog/search.html`
- **Description:** Search articles by keyword
- **Features:**
  - Full-text search
  - Title and content search
  - Pagination
  - Result count

### 27. Blog Archive
- **URL:** `/blog/archive/`, `/blog/archive/<int:year>/`, `/blog/archive/<int:year>/<int:month>/`
- **View:** `blog.views.archive_posts`
- **Template:** `blog/archive.html`
- **Description:** Browse posts by date
- **Features:**
  - Year-based filtering
  - Month-based filtering
  - Chronological listing
  - Archive navigation

### 28. Blog Category Filter
- **URL:** `/blog/category/<slug:slug>/`
- **View:** `blog.views.category_posts`
- **Template:** `blog/category.html`
- **Description:** Filter posts by category
- **Features:**
  - Category-based filtering
  - Category description
  - Post count
  - Pagination

### 29. Blog Tag Filter
- **URL:** `/blog/tag/<slug:slug>/`
- **View:** `blog.views.tag_posts`
- **Template:** `blog/tag.html`
- **Description:** Filter posts by tags
- **Features:**
  - Tag-based filtering
  - Related tags
  - Post count
  - Pagination

---

## API & AJAX Endpoints

### 30. Places JSON API
- **URL:** `/api/places/`
- **View:** `places.views.get_places_json`
- **Response:** JSON
- **Description:** JSON data for map markers
- **Features:**
  - Filter support (category, city, search)
  - Distance calculations
  - Rating aggregation
  - GeoJSON compatible
  - Used by explore map view

### 31. Prayer Times Data API
- **URL:** `/prayer/get-prayer-times/`
- **View:** `prayer_times.views.get_prayer_times_data`
- **Response:** JSON
- **Description:** Real-time prayer times calculation
- **Features:**
  - Location-based calculations
  - Method selection
  - Asr calculation option
  - Date parameter support
  - Cached results (23 hours)

### 32. Get Location from Coordinates
- **URL:** `/prayer/get-location/`
- **View:** `prayer_times.views.get_location_from_coords`
- **Response:** JSON
- **Description:** Reverse geocoding
- **Features:**
  - Lat/lng to city name
  - Google Maps API integration
  - Error handling

### 33. Set User Location
- **URL:** `/set-location/`
- **View:** `places.views.set_location`
- **Response:** JSON
- **Description:** Save user location preference
- **Features:**
  - Session-based storage
  - Lat/lng persistence
  - Used for distance calculations

### 34. Update Prayer Location
- **URL:** `/prayer/update-location/`
- **View:** `prayer_times.views.update_location`
- **Response:** JSON
- **Description:** Update prayer times location
- **Features:**
  - Location update
  - Session storage
  - Immediate recalculation

### 35. Clear Prayer Location
- **URL:** `/prayer/clear-location/`
- **View:** `prayer_times.views.clear_location`
- **Response:** JSON
- **Description:** Remove saved location
- **Features:**
  - Session clearing
  - Reset to default

### 36. Update Prayer Settings
- **URL:** `/prayer/update-settings/`
- **View:** `prayer_times.views.update_prayer_settings`
- **Response:** JSON
- **Description:** Update calculation preferences
- **Features:**
  - Calculation method selection
  - Asr method selection
  - Session persistence

---

## Internationalization

### 37. Set Language (Form-based)
- **URL:** `/i18n/setlang/`
- **View:** `utils.language_views.set_language`
- **Description:** Change interface language (form POST)
- **Features:**
  - Language switching (EN, KO, UZ)
  - Persistent preferences for authenticated users
  - Session-based for anonymous users
  - Redirect to referrer

### 38. Set Language (AJAX)
- **URL:** `/i18n/setlang-ajax/`
- **View:** `utils.language_views.set_language_ajax`
- **Response:** JSON
- **Description:** Change language via AJAX
- **Features:**
  - JSON response
  - Same persistence as form-based
  - No page reload required

### 39. Get Language Preferences
- **URL:** `/i18n/preferences/`
- **View:** `utils.language_views.get_user_language_preferences`
- **Response:** JSON
- **Description:** Retrieve user language settings
- **Features:**
  - Current language
  - Available languages
  - User preference status

### 40. Django i18n
- **URL:** `/i18n/`
- **Description:** Django's built-in i18n URLs
- **Features:**
  - JavaScript catalog
  - Translation utilities

---

## Admin & Monitoring

### 41. Django Admin Panel
- **URL:** `/admin/`
- **Description:** Main admin interface
- **Features:**
  - Content moderation (places, reviews, blogs)
  - User management
  - Database administration
  - Model CRUD operations
  - Custom admin actions

### 42. Main Monitoring Dashboard
- **URL:** `/admin/monitoring/`
- **View:** `utils.admin_views.monitoring_dashboard`
- **Description:** Overview dashboard
- **Features:**
  - System health metrics
  - Quick stats
  - Recent activity
  - Alert notifications

### 43. Performance Dashboard
- **URL:** `/admin/monitoring/performance/`
- **View:** `utils.admin_views.performance_dashboard`
- **Description:** Performance metrics
- **Features:**
  - Response time tracking
  - Database query analysis
  - Cache hit rates
  - Resource usage

### 44. Security Dashboard
- **URL:** `/admin/monitoring/security/`
- **View:** `utils.admin_views.security_dashboard`
- **Description:** Security monitoring
- **Features:**
  - Failed login attempts
  - Rate limit violations
  - Suspicious activity
  - Security logs

### 45. Content Operations Dashboard
- **URL:** `/admin/monitoring/content/`
- **View:** `utils.admin_views.content_operations_dashboard`
- **Description:** Content management overview
- **Features:**
  - Pending submissions
  - Review queue
  - Suggestion management
  - Content statistics

### 46. Analytics Dashboard
- **URL:** `/admin/monitoring/analytics/`
- **View:** `utils.admin_views.analytics_dashboard`
- **Description:** Usage analytics
- **Features:**
  - User activity
  - Popular places
  - Search trends
  - Conversion metrics

### 47. Monitoring Metrics API
- **URL:** `/admin/monitoring/api/metrics/`
- **View:** `utils.admin_views.api_metrics`
- **Response:** JSON
- **Description:** Real-time metrics endpoint

### 48. Monitoring Stats API
- **URL:** `/admin/monitoring/api/stats/`
- **View:** `utils.admin_views.api_stats`
- **Response:** JSON
- **Description:** Statistical data endpoint

### 49. Monitoring Performance API
- **URL:** `/admin/monitoring/api/performance/`
- **View:** `utils.admin_views.api_performance`
- **Response:** JSON
- **Description:** Performance data endpoint

### 50. Translation Management (Rosetta)
- **URL:** `/rosetta/`
- **Description:** i18n string management
- **Features:**
  - Edit translation strings
  - Multi-language support
  - PO file management
  - Admin-only access

---

## Utility & Error Pages

### 51. User Rate Limited
- **URL:** `/users/rate-limited/`
- **View:** `users.views.rate_limited_view`
- **Template:** `users/rate_limited.html`
- **Description:** Rate limit notification for user actions
- **Features:**
  - Explanation of rate limiting
  - Time remaining display
  - Security information

### 52. Contact Rate Limited
- **URL:** `/contact/rate-limited/`
- **View:** `contact.views.rate_limited_view`
- **Template:** `contact/rate_limited.html`
- **Description:** Rate limit notification for contact form
- **Features:**
  - Spam prevention notice
  - Retry information

### 53. Logout
- **URL:** `/users/logout/`
- **View:** `users.views.logout_view`
- **Description:** Session termination
- **Features:**
  - Session clearing
  - Redirect to home
  - Confirmation message

### 54. 404 Error Page
- **Handler:** `places.views.handler404`
- **Template:** `404.html`
- **Description:** User-friendly not found page
- **Features:**
  - Custom error message
  - Navigation links
  - Search suggestions

### 55. Sitemap
- **URL:** `/sitemap.xml`
- **View:** `django.contrib.sitemaps.views.sitemap`
- **Response:** XML
- **Description:** Search engine sitemap
- **Features:**
  - All public places
  - All published blog posts
  - Static pages
  - SEO optimization

### 56. Robots.txt
- **URL:** `/robots.txt`
- **Template:** `robots.txt`
- **Response:** Plain text
- **Description:** Crawler instructions
- **Features:**
  - Sitemap reference
  - Crawl rules
  - Disallow patterns

### 57. TinyMCE Image Upload
- **URL:** `/tinymce/upload/`
- **View:** `blog.upload_views.tinymce_upload_view`
- **Response:** JSON
- **Description:** Image upload for blog editor
- **Features:**
  - Admin-only access
  - Image processing
  - URL return

### 58. TinyMCE URLs
- **URL:** `/tinymce/`
- **Description:** TinyMCE editor resources
- **Features:**
  - Editor JavaScript
  - Plugins
  - Configurations

### 59. Social Authentication (Allauth)
- **URL:** `/accounts/`
- **Description:** Social auth endpoints
- **Features:**
  - Google login/signup
  - Facebook login/signup
  - OAuth callbacks
  - Account connections

### 60. Contact Form HTML (AJAX)
- **URL:** `/contact/form/`
- **View:** `contact.views.get_contact_form_html`
- **Response:** HTML
- **Description:** Dynamic form loading
- **Features:**
  - CSRF-protected form HTML
  - Modal integration
  - AJAX loading

---

## Summary Statistics

### By Importance Tier

| Tier | Count | Description |
|------|-------|-------------|
| **Critical** | 4 | Core user journey pages |
| **High Priority** | 5 | User engagement & authentication |
| **Content** | 5 | Information architecture |
| **User Management** | 6 | Account management features |
| **Community** | 5 | User-generated content tools |
| **Organization** | 4 | Content discovery & filtering |
| **API/AJAX** | 10 | Backend endpoints |
| **i18n** | 4 | Localization features |
| **Admin** | 10 | Management & monitoring tools |
| **Utility** | 7 | Support & error handling |

**Total Pages/Endpoints:** 60+

### By Access Level

- **Public Access:** ~25 pages (including home, explore, place detail, blog, about, etc.)
- **Authenticated Only:** ~20 pages (profile, submit, reviews, favorites, etc.)
- **Admin Only:** ~10 pages (admin panel, monitoring, rosetta, etc.)
- **API/AJAX:** ~10 endpoints (JSON responses for dynamic features)

### By Function Category

- **Place Discovery:** 8 pages/endpoints
- **User Account:** 11 pages
- **Blog/Content:** 7 pages
- **Prayer Times:** 5 pages/endpoints
- **Reviews:** 3 pages
- **Admin/Monitoring:** 10 pages/endpoints
- **Community Features:** 5 pages
- **i18n:** 4 pages/endpoints
- **Utility/Other:** 7 pages

### Technology Integration

- **Django Views:** 50+ view functions
- **AJAX Endpoints:** 10+ JSON APIs
- **Map Integration:** Google Maps, Kakao, Naver
- **Rich Text Editor:** TinyMCE
- **Social Auth:** Allauth (Google, Facebook)
- **Geospatial:** PostGIS for location queries
- **Caching:** Session-based + 23-hour prayer times cache
- **Notifications:** Telegram integration

---

## Development Notes

### URL Naming Conventions
- **Kebab-case with underscores** for URL patterns
- **Namespaced** by app (`places:home`, `blog:detail`, etc.)
- **RESTful** patterns where applicable
- **Consistent** parameter naming (`pk`, `slug`, `id`)

### Template Organization
- Each app has its own template directory
- Shared templates in root `templates/`
- Allauth templates in `templates/account/` and `templates/socialaccount/`

### Security Features
- **Rate Limiting:** Contact form, user registration, social auth
- **CSRF Protection:** All forms
- **Email Verification:** Required for submissions
- **Permission Decorators:** `@login_required`, `@email_verification_required`
- **Admin Staff Required:** Monitoring dashboards

### Performance Optimizations
- **Caching:** Prayer times (23-hour cache)
- **Pagination:** All list views
- **Select Related:** Optimized queries
- **Distance Annotations:** PostGIS spatial queries
- **AJAX Loading:** Dynamic content loading

### Monitoring & Logging
- **Comprehensive Logging:** All major operations
- **Error Tracking:** Sentry integration ready
- **Performance Metrics:** Custom monitoring dashboard
- **Security Logs:** Failed attempts, rate limits
- **Telegram Notifications:** New submissions, contact messages

---

## Future Expansion Considerations

### Potential New Pages
1. **Advanced Search** - Dedicated advanced filtering page
2. **User Dashboard** - Enhanced personal dashboard
3. **Place Comparison** - Compare multiple places side-by-side
4. **Community Forum** - Discussion boards
5. **Events Calendar** - Halal events and Ramadan timing
6. **Mobile App API** - RESTful API for mobile apps
7. **Restaurant Menus** - Digital menu integration
8. **Booking System** - Reservation capabilities
9. **Loyalty Program** - User rewards system
10. **Nearby Alerts** - Location-based notifications

### API Expansion
- **GraphQL API** for more flexible queries
- **Webhook Integration** for third-party services
- **Export Functions** (CSV, PDF) for places and reviews
- **Batch Operations API** for admin tasks

---

**End of Document**
