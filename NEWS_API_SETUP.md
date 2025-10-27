# News & Social Media API Setup Guide

This guide will help you set up the free APIs used in the News & Social section of the BTC Dashboard.

## Free APIs Used

The News & Social section uses three free APIs:

### 1. NewsAPI (Recommended - Most Reliable)
- **What it does**: Fetches latest news articles about Bitcoin
- **Free tier**: 100 requests per day
- **Setup**: Requires API key
- **Get your free key**: https://newsapi.org/register

### 2. Reddit API
- **What it does**: Fetches popular posts from r/Bitcoin, r/CryptoCurrency, etc.
- **Free tier**: Unlimited (no key required)
- **Setup**: No setup needed - works automatically

### 3. CryptoCompare News API
- **What it does**: Fetches crypto-specific news
- **Free tier**: Unlimited
- **Setup**: No setup needed - works automatically

## How to Set Up NewsAPI

### Step 1: Get Your API Key

1. Go to https://newsapi.org/register
2. Sign up for a free account
3. Verify your email
4. Copy your API key from the dashboard

### Step 2: Set the Environment Variable

#### On macOS/Linux:

```bash
export NEWSAPI_KEY="your_api_key_here"
```

To make it permanent, add it to your `~/.zshrc` (for zsh) or `~/.bashrc` (for bash):

```bash
echo 'export NEWSAPI_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

#### On Windows:

```cmd
set NEWSAPI_KEY=your_api_key_here
```

Or use PowerShell:

```powershell
[System.Environment]::SetEnvironmentVariable('NEWSAPI_KEY', 'your_api_key_here', 'User')
```

### Step 3: Restart Your Streamlit App

After setting the environment variable, restart your Streamlit application:

```bash
streamlit run app.py
```

### Step 4: Verify It's Working

1. Navigate to the "News & Social" section in your app
2. Click the "⚙️ API Configuration" expander
3. You should see: "✅ NewsAPI key is configured"

## Rate Limits

**NewsAPI Free Tier:**
- 100 requests per day
- Rate limit per second: 1 request/second

**Reddit API:**
- No rate limits
- Uses public data

**CryptoCompare:**
- No rate limits
- Free tier is unlimited

## Troubleshooting

### Issue: "NewsAPI key not set" warning

**Solution**: Make sure you've set the `NEWSAPI_KEY` environment variable and restarted the app.

### Issue: "Error fetching news" message

**Possible causes**:
1. API key is invalid
2. Rate limit exceeded (100 requests/day)
3. Network connectivity issues

**Solution**: 
- Verify your API key at https://newsapi.org/account
- Wait until the next day for rate limit to reset
- Check your internet connection

### Issue: Reddit posts not showing

**Solution**: This might be due to Reddit's rate limiting or API issues. The section will still work with NewsAPI and CryptoCompare.

## Alternative: Using Without NewsAPI

If you don't want to set up NewsAPI, the app will still work with:
- ✅ Reddit posts (always available)
- ✅ CryptoCompare news (always available)
- ❌ General news articles (requires NewsAPI key)

## Security Notes

1. **Never commit your API key** to version control
2. Keep your API key private
3. If you accidentally commit it, revoke it at newsapi.org and generate a new one

## Next Steps

1. Set up your NewsAPI key following the steps above
2. Navigate to the "News & Social" section
3. Explore news articles and social media discussions
4. Stay informed about Bitcoin market developments!

For questions or issues, check the NewsAPI documentation: https://newsapi.org/docs

