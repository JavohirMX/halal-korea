# External Login Setup Guide

This guide explains how to set up OAuth applications for each social provider and configure the necessary environment variables.

## Overview

The Halal Korea application supports external authentication through:
- Google OAuth2
- GitHub OAuth

## Environment Variables

Add these variables to your `.env` file:

```bash
# Google OAuth2
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

## Provider Setup Instructions

### 1. Google OAuth2

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set application type to "Web application"
6. Add authorized redirect URIs:
   - Development: `http://localhost:8000/accounts/google/login/callback/`
   - Production: `https://yourdomain.com/accounts/google/login/callback/`
7. Copy Client ID and Client Secret to your `.env` file

### 2. GitHub OAuth

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in application details:
   - Application name: "Halal Korea"
   - Homepage URL: Your site URL
   - Authorization callback URL:
     - Development: `http://localhost:8000/accounts/github/login/callback/`
     - Production: `https://yourdomain.com/accounts/github/login/callback/`
4. Copy Client ID and Client Secret to your `.env` file


## Testing the Integration

1. Start your development server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to the login page: `http://localhost:8000/users/login/`

3. You should see social login buttons for all configured providers

4. Test each provider by clicking their respective buttons

## Troubleshooting

### Common Issues

1. **Redirect URI Mismatch**: Ensure the callback URLs in your OAuth apps match exactly with your domain
2. **Missing Scopes**: Check that you've requested the necessary permissions (email, profile)
3. **SSL Required**: Some providers require HTTPS in production

### Debug Mode

Enable debug logging to troubleshoot OAuth issues:

```python
# In settings.py
LOGGING['loggers']['allauth'] = {
    'handlers': ['console', 'file'],
    'level': 'DEBUG',
    'propagate': False,
}
```

### Rate Limiting

The existing rate limiting system automatically covers social authentication endpoints. Monitor the logs for any rate limiting issues.

## Security Considerations

1. **Environment Variables**: Never commit OAuth secrets to version control
2. **HTTPS**: Always use HTTPS in production
3. **Callback URLs**: Restrict callback URLs to your actual domains
4. **Token Storage**: OAuth tokens are securely stored in the database
5. **Account Merging**: The system automatically merges accounts by email address

## Account Merging Behavior

- If a user signs up with email `user@example.com` normally, then later tries to login with Google using the same email, the accounts will be automatically merged
- Users can link/unlink social accounts from their profile page
- Email verification is automatically trusted for Google providers
- Profile pictures are automatically imported and stored locally

## Production Deployment

1. Update all OAuth app settings with production URLs
2. Set environment variables on your production server
3. Ensure HTTPS is properly configured
4. Test all providers in production environment
5. Monitor logs for any authentication issues
