# Contact Form Feature

A comprehensive contact form feature integrated into the Halal Korea website, allowing users to send messages directly through the site with Telegram notifications and rate limiting.

## Features

### ✨ **Core Functionality**
- **Universal Access**: Available to both authenticated and anonymous users
- **Smart Pre-filling**: Authenticated users get name/email pre-filled from their profile
- **Form Fields**: Name, Email, Subject (optional), Message
- **AJAX Submission**: Smooth user experience without page reloads
- **Real-time Validation**: Client-side and server-side validation

### 🛡️ **Security & Rate Limiting**
- **IP-based Rate Limiting**: 
  - 1 message per 5 minutes
  - 3 messages per hour (anonymous users)
  - 5 messages per hour (authenticated users)
- **Form Validation**: 
  - Minimum message length (10 characters)
  - Minimum name length (2 characters)
  - Email format validation
  - Maximum character limits

### 📱 **Telegram Integration**
- **Instant Notifications**: Messages sent to configured Telegram chat
- **Rich Formatting**: Organized message format with user details
- **User Type Detection**: Distinguishes between registered and anonymous users
- **Error Handling**: Graceful fallback if Telegram is unavailable

### 🎨 **Design & UX**
- **Consistent Styling**: Matches existing Tailwind CSS design system
- **Dark Mode Support**: Full dark/light theme compatibility
- **Responsive Design**: Works on all device sizes
- **Loading States**: Visual feedback during form submission
- **Success/Error Messages**: Clear user feedback

## Implementation

### File Structure
```
contact/
├── __init__.py
├── admin.py              # Admin interface for managing messages
├── apps.py               # App configuration
├── forms.py              # Contact form definition
├── models.py             # ContactMessage model
├── rate_limiting.py      # Rate limiting logic
├── tests.py              # Comprehensive test suite
├── urls.py               # URL patterns
├── views.py              # Form submission and AJAX views
├── migrations/
│   └── 0001_initial.py   # Database migration
└── templates/contact/
    ├── form.html         # Contact form template
    ├── section.html      # Complete contact section
    └── rate_limited.html # Rate limit exceeded page
```

### Database Model
The `ContactMessage` model stores:
- User information (name, email, optional user link)
- Message content (subject, message)
- Metadata (IP address, user agent, timestamps)
- Status tracking (read status, response status)

### Integration Points
- **Home Page**: Contact section added before closing content block
- **About Page**: Contact section added after main content
- **Telegram**: Extended existing notification system
- **Admin Panel**: Full management interface with bulk actions

## Configuration

### Required Settings
Ensure these are configured in your `.env` file:

```env
# Telegram notifications (required for contact form notifications)
TELEGRAM_NOTIFICATIONS_ENABLED=True
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Site URL for admin links in notifications
SITE_URL=https://your-domain.com
```

### Rate Limiting
Rate limits are cached-based and can be adjusted in `contact/rate_limiting.py`:
- Anonymous users: 3 submissions per hour, 1 per 5 minutes
- Authenticated users: 5 submissions per hour, 1 per 5 minutes

## Admin Interface

### Features
- **Message Management**: View, read, and respond to messages
- **Filtering**: By read status, response status, date
- **Search**: Across name, email, subject, and message content
- **Bulk Actions**: Mark multiple messages as read/responded
- **User Type Indicators**: Visual distinction between user types
- **Status Tracking**: Clear status indicators

### Admin Actions
- `mark_as_read`: Mark selected messages as read
- `mark_as_responded`: Mark selected messages as responded

## API Endpoints

### `POST /contact/submit/`
Submit a contact form message
- **Rate Limited**: Yes
- **Authentication**: Optional
- **Response**: JSON with success/error status

### `GET /contact/form/`
Get contact form HTML (for AJAX loading)
- **Authentication**: Optional
- **Response**: JSON with form HTML

## Usage Examples

### Anonymous User Flow
1. User visits home or about page
2. Scrolls to contact section
3. Fills out name, email, subject, message
4. Submits form
5. Receives success message
6. Admin gets Telegram notification

### Authenticated User Flow
1. User visits home or about page
2. Scrolls to contact section
3. Name and email pre-filled
4. Fills out subject and message
5. Submits form with linked user account
6. Higher rate limits apply

### Rate Limited Flow
1. User exceeds rate limits
2. Redirected to informative rate limit page
3. Clear explanation of limits and next steps
4. Options to wait or create account for higher limits

## Testing

### Test Coverage
- Model functionality (creation, status tracking)
- Form validation (all field validations)
- Rate limiting logic
- Admin interface
- View responses

### Running Tests
```bash
python manage.py test contact
```

## Telegram Integration

### Notification Format
```
💬 New Contact Message!

👤 Name: John Doe
📧 Email: john@example.com
🆔 User Type: Registered User
🔢 User ID: 123
📋 Subject: Website Question

💬 Message:
I have a question about the halal restaurants...

📧 Please reply to the user's email address
```

### Error Handling
- Graceful degradation if Telegram is unavailable
- Detailed logging for troubleshooting
- Form submission succeeds even if notification fails

## Customization

### Styling
Contact form uses existing Tailwind classes and can be customized by editing:
- `contact/templates/contact/form.html` - Form styling
- `contact/templates/contact/section.html` - Section layout

### Rate Limits
Adjust rate limits in `contact/rate_limiting.py`:
```python
# Check 5-minute limit (1 submission)
if ip_minute_count >= 1:
    # Increase or decrease as needed
```

### Form Fields
Add or modify fields in `contact/forms.py` and update:
- Model (`contact/models.py`)
- Template (`contact/templates/contact/form.html`)
- Validation logic

## Troubleshooting

### Common Issues

#### Form Not Loading
- Check JavaScript console for errors
- Verify AJAX endpoints are accessible
- Ensure CSRF tokens are properly configured

#### Rate Limiting Too Strict
- Clear cache: `python manage.py shell -c "from django.core.cache import cache; cache.clear()"`
- Adjust limits in `rate_limiting.py`

#### Telegram Not Working
- Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- Check bot permissions in target chat
- Review logs for specific error messages

#### Styling Issues
- Verify Tailwind CSS is loaded
- Check for CSS conflicts
- Test in different browsers/devices

## Future Enhancements

### Potential Improvements
- **File Attachments**: Allow users to attach images/documents
- **Message Categories**: Dropdown for message types
- **Auto-Response**: Email confirmation to users
- **Advanced Filtering**: More admin filtering options
- **Analytics**: Track message patterns and response times
- **Multi-language**: Translate form to Korean/Uzbek

### Performance Optimizations
- **Database Indexing**: Add indexes for common queries
- **Caching**: Cache form HTML for better performance
- **Pagination**: For admin interface with many messages

## Conclusion

The contact form feature provides a professional, secure, and user-friendly way for visitors to communicate with the Halal Korea team. It integrates seamlessly with the existing codebase while maintaining high standards for security, usability, and maintainability.
