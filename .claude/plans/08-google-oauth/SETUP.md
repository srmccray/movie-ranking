# Google OAuth Setup Guide

This guide walks you through setting up Google OAuth credentials for the "Sign in with Google" feature.

## Prerequisites

- A Google account
- Access to create a project in Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top of the page
3. Click **New Project**
4. Enter a project name (e.g., "Movie Ranking App")
5. Click **Create**
6. Wait for the project to be created, then select it from the project dropdown

## Step 2: Configure the OAuth Consent Screen

Before creating OAuth credentials, you must configure the consent screen:

1. In the left sidebar, navigate to **APIs & Services > OAuth consent screen**
2. Select **External** user type (unless you have a Google Workspace organization)
3. Click **Create**
4. Fill in the required fields:
   - **App name**: Movie Ranking (or your preferred name)
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
5. Click **Save and Continue**
6. On the **Scopes** page, click **Add or Remove Scopes**
7. Add the following scopes:
   - `openid`
   - `email`
   - `profile`
8. Click **Update**, then **Save and Continue**
9. On the **Test users** page, add your email address for testing
10. Click **Save and Continue**, then **Back to Dashboard**

## Step 3: Create OAuth Client ID

1. Navigate to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Select **Web application** as the application type
4. Enter a name (e.g., "Movie Ranking Web Client")
5. Under **Authorized JavaScript origins**, add:
   - Development: `http://localhost:3000`
   - Production: `https://yourdomain.com`
6. Under **Authorized redirect URIs**, add:
   - Development: `http://localhost:8000/api/v1/auth/google/callback/`
   - Production: `https://yourdomain.com/api/v1/auth/google/callback/`
7. Click **Create**
8. Copy the **Client ID** and **Client Secret** from the popup

## Step 4: Configure Environment Variables

Add the credentials to your `.env` file:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Optional: Override redirect URI (defaults to http://localhost:8000/api/v1/auth/google/callback/)
# GOOGLE_REDIRECT_URI=https://yourdomain.com/api/v1/auth/google/callback/
```

## Step 5: Verify Setup

1. Start the application:
   ```bash
   docker compose up -d
   docker compose exec api alembic upgrade head
   cd frontend && npm run dev
   ```

2. Open the login page at http://localhost:3000/login
3. Click "Sign in with Google"
4. You should be redirected to Google's login page
5. After signing in, you should be redirected back and logged in

## Production Considerations

### HTTPS Requirement

Google OAuth requires HTTPS for production redirect URIs. Ensure your production environment:
- Has a valid SSL certificate
- Uses HTTPS for all OAuth-related URLs
- Has the production redirect URI added to Google Cloud Console

### Environment Variables in Production

Never commit secrets to your repository. Use your deployment platform's secrets management:
- **AWS**: Secrets Manager or Parameter Store
- **Heroku**: Config Vars
- **Docker**: Secrets or environment files
- **Kubernetes**: Secrets

### Domain Verification (Optional)

For additional security, you can verify your domain ownership in Google Cloud Console:
1. Navigate to **APIs & Services > Domain verification**
2. Click **Add domain**
3. Follow the verification steps

## Troubleshooting

### "redirect_uri_mismatch" Error

This error occurs when the redirect URI in your request doesn't match any authorized URIs in Google Cloud Console.

**Solution:**
1. Check the exact redirect URI in the error message
2. Add that exact URI to **Authorized redirect URIs** in Google Cloud Console
3. Ensure the trailing slash matches (the app uses trailing slashes)

### "access_denied" Error

This usually means the user cancelled the sign-in process or your app is in testing mode and the user isn't a test user.

**Solution:**
1. Add the user's email to test users in OAuth consent screen
2. Or publish your app (requires Google verification for sensitive scopes)

### "invalid_client" Error

The client ID or secret is incorrect.

**Solution:**
1. Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your `.env` file
2. Ensure there are no extra spaces or quotes
3. Check that you're using the correct project's credentials

### State Validation Failed

The OAuth state parameter didn't match. This could indicate:
- The state expired (5-minute timeout)
- A CSRF attack attempt
- Browser went back/forward during the flow

**Solution:**
1. Try the sign-in process again
2. Ensure cookies are enabled
3. Don't use the browser back button during OAuth

## Security Best Practices

1. **Never expose client secret**: The client secret should only exist on your backend server
2. **Use state parameter**: Always validate the state to prevent CSRF attacks (the app does this automatically)
3. **Verify email**: Only accept users with verified Google emails (the app checks `email_verified` claim)
4. **Use HTTPS in production**: OAuth tokens should always be transmitted over encrypted connections
5. **Rotate secrets**: If you suspect your client secret was compromised, create new credentials in Google Cloud Console

## Related Documentation

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Sign-In for Web](https://developers.google.com/identity/sign-in/web/sign-in)
- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
