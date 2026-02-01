# Telegram Bot Notifications Setup

This guide explains how to set up Telegram bot notifications for new place submissions in the Halal Korea application.

## Overview

When enabled, the application will automatically send Telegram notifications to a specified chat whenever a user submits a new place for review. The notification includes:

- Place name and category
- Address and description
- Submitter's username
- Contact information (if provided)
- Number of uploaded photos
- Direct link to the admin panel for review

## Setup Instructions

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Start a conversation with BotFather by clicking `/start`
3. Create a new bot by sending `/newbot`
4. Follow the prompts to choose a name and username for your bot
5. BotFather will provide you with a **Bot Token** - save this securely

### 2. Get Chat ID

You can send notifications to either:
- A private chat with the bot
- A group/channel where the bot is added

#### For Private Chat:
1. Start a conversation with your bot
2. Send any message to the bot
3. Open this URL in your browser (replace `YOUR_BOT_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for the `chat` object in the response and note the `id` value

#### For Group/Channel:
1. Add your bot to the group/channel
2. Make the bot an admin (for channels)
3. Send a message mentioning the bot (`@your_bot_username`)
4. Use the same getUpdates URL as above to get the chat ID
5. For channels, the chat ID will start with `-100`

### 3. Configure Environment Variables

Add the following variables to your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_NOTIFICATIONS_ENABLED=True
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Site URL for admin links (update for production)
SITE_URL=http://localhost:8000
```

**Important Notes:**
- Set `TELEGRAM_NOTIFICATIONS_ENABLED=False` to disable notifications
- The `SITE_URL` should be your production domain for proper admin links
- Keep your bot token secure and never commit it to version control

### 4. Test the Setup

1. Restart your Django application after adding the environment variables
2. Submit a test place through the web interface
3. Check your Telegram chat for the notification

## Example Notification

When a place is submitted, you'll receive a message like this:

```
🔔 New Place Submission!

📍 Name: Seoul Halal Restaurant
🏷️ Category: Restaurant
📍 Address: 123 Gangnam-gu, Seoul, South Korea
👤 Submitted by: john_doe
📝 Description: Authentic halal Korean-style restaurant serving...
🌐 Website: https://example.com
📞 Phone: +82-10-1234-5678
📷 Photos: 3 uploaded
🔗 Review: Admin Panel

⏳ Status: Pending Review
```

## Troubleshooting

### Common Issues:

1. **Notifications not being sent:**
   - Check that `TELEGRAM_NOTIFICATIONS_ENABLED=True`
   - Verify your bot token and chat ID are correct
   - Check the application logs for error messages

2. **"Chat not found" error:**
   - Ensure the bot has been started in private chats
   - For groups/channels, ensure the bot is properly added and has necessary permissions

3. **Admin links not working:**
   - Update the `SITE_URL` environment variable to match your domain
   - Ensure the Django admin is properly configured

### Checking Logs:

The application logs notification attempts. Look for messages like:
- `Telegram notification sent successfully`
- `Failed to send Telegram notification: [error details]`

## Security Considerations

- Never expose your bot token in public repositories
- Use environment variables for all sensitive configuration
- Consider using a dedicated bot for notifications rather than a personal bot
- For production, consider implementing rate limiting for notifications

## Customization

The notification format can be customized by modifying the `notify_new_place_submission` method in `utils/telegram_notifications.py`. You can:

- Change the message format and emojis
- Add or remove information fields
- Modify the HTML formatting
- Add custom logic based on place category or other criteria

## Production Considerations

- Set up proper error monitoring for notification failures
- Consider implementing a fallback notification method (email)
- Monitor Telegram API rate limits for high-volume applications
- Use HTTPS for your `SITE_URL` in production 