import streamlit as st
import requests
from datetime import datetime, timedelta
import os
import json
import re
import html
import pandas as pd
from dashboard.data_loader import load_bitcoin_data
from textblob import TextBlob


def fetch_newsapi_news(api_key, query="bitcoin OR BTC", max_results=10):
    """Fetch news from NewsAPI"""
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "apiKey": api_key,
            "pageSize": max_results,
            "sortBy": "publishedAt",
            "language": "en"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "ok":
            return data.get("articles", [])
        return []
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        return []


def fetch_reddit_posts(subreddit="Bitcoin", limit=10):
    """Fetch posts from Reddit API (no key required)"""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        headers = {
            "User-Agent": "BTC-Dashboard/1.0 (Educational Dashboard; +https://github.com/TrilemmaFoundation/UCI-MDS-F25-Bitcoin)",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }
        params = {"limit": limit}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        # Check for 403 specifically and provide helpful message
        if response.status_code == 403:
            st.warning("⚠️ Reddit API blocked the request. This may be due to rate limiting or IP restrictions. Try again in a few minutes.")
            return []
        
        response.raise_for_status()
        data = response.json()
        
        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            if post.get("score", 0) > 10:  # Only show popular posts
                posts.append({
                    "title": post.get("title", ""),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "url": post.get("url", ""),
                    "permalink": f"https://www.reddit.com{post.get('permalink', '')}",
                    "created_utc": post.get("created_utc", 0),
                    "author": post.get("author", "")
                })
        return posts
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            st.error(f"Error fetching Reddit posts: 403 Forbidden - Reddit is blocking the request. This may be temporary. Error: {str(e)}")
        else:
            st.error(f"Error fetching Reddit posts: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Error fetching Reddit posts: {str(e)}")
        return []


def fetch_crypto_news():
    """Fetch news from CryptoCompare API (free)"""
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/"
        params = {
            "lang": "EN"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check if we have a successful response
        message = data.get("Message", "").lower()
        if "successfully returned" in message or "success" in message:
            articles = data.get("Data", [])
            if articles and len(articles) > 0:
                # Filter for Bitcoin/crypto related news
                filtered = [
                    article for article in articles[:30]
                    if any(keyword in article.get("title", "").lower() or keyword in article.get("body", "").lower() 
                           for keyword in ["bitcoin", "btc", "crypto", "ethereum", "eth", "blockchain", "cryptocurrency"])
                ]
                # If filtering removes everything, return first 20 articles anyway
                return filtered[:20] if filtered else articles[:20]
            return []
        return []
    except Exception as e:
        st.error(f"Error fetching crypto news: {str(e)}")
        return []


def format_reddit_timestamp(timestamp):
    """Format Reddit timestamp to human-readable"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        diff = now - dt
        
        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            return f"{hours}h ago"
        elif diff.days == 1:
            return "1 day ago"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return dt.strftime("%b %d, %Y")
    except:
        return "Unknown time"


def calculate_price_impact(published_date, btc_data):
    """
    Calculate BTC price impact around a news article's publication date.
    
    For news articles:
    - If article is 3+ days old: Calculate % change from 3 days before to 3 days after
    - If article is recent (< 3 days old or today): Calculate % change from 3 days before to current/latest price
    
    Args:
        published_date: datetime object of when the news was published
        btc_data: DataFrame with BTC price data (indexed by date)
    
    Returns:
        tuple: (percentage_change, price_before, price_after, price_on_date)
    """
    try:
        # Convert to pandas Timestamp and handle timezone-aware dates
        if isinstance(published_date, str):
            # If it's a string, parse it
            article_date = pd.to_datetime(published_date)
        else:
            article_date = pd.Timestamp(published_date)
        
        # Normalize to remove time component and timezone
        if article_date.tz is not None:
            # Convert timezone-aware to naive (UTC) and normalize
            article_date = article_date.tz_convert('UTC').tz_localize(None).normalize()
        else:
            article_date = article_date.normalize()
        
        today = pd.Timestamp.now().normalize()
        
        # Check if we have data
        if btc_data is None or btc_data.empty:
            return None, None, None, None
        
        available_dates = btc_data.index.sort_values()
        
        # Find the closest price data point to the article date (on or before)
        if article_date in available_dates:
            price_on_date = btc_data.loc[article_date, "PriceUSD"]
            article_date_normalized = article_date
        else:
            # Find the closest date on or before the article date
            mask = available_dates <= article_date
            if mask.any():
                article_date_normalized = available_dates[mask].max()
                price_on_date = btc_data.loc[article_date_normalized, "PriceUSD"]
            else:
                # Article is before our data range
                return None, None, None, None
        
        # Calculate target date for 3 days before
        target_before_date = article_date_normalized - timedelta(days=3)
        
        # Find price 3 days before (use closest date on or before)
        mask_before = available_dates <= target_before_date
        if mask_before.any():
            before_date = available_dates[mask_before].max()
            price_before = btc_data.loc[before_date, "PriceUSD"]
        else:
            # Not enough historical data
            return None, None, None, None
        
        # Determine if we can get 3 days after or need to use current price
        target_after_date = article_date_normalized + timedelta(days=3)
        days_since_article = (today - article_date_normalized).days
        
        # If article is recent (< 3 days old), today, or in the future, use current/latest price
        if days_since_article < 3 or article_date_normalized > today:
            # Use the latest available price (current price)
            price_after = btc_data["PriceUSD"].iloc[-1]
        else:
            # Article is old enough (3+ days), try to get price 3 days after
            mask_after = available_dates >= target_after_date
            if mask_after.any():
                after_date = available_dates[mask_after].min()
                price_after = btc_data.loc[after_date, "PriceUSD"]
            else:
                # Fallback to latest available price if we can't get 3 days after
                price_after = btc_data["PriceUSD"].iloc[-1]
        
        # Calculate percentage change
        if price_before > 0 and pd.notna(price_before) and pd.notna(price_after):
            percentage_change = ((price_after - price_before) / price_before) * 100
            return percentage_change, price_before, price_after, price_on_date
        else:
            return None, None, None, None
    
    except Exception as e:
        # Silently return None on error (will show as N/A)
        return None, None, None, None


def get_price_indicator(percentage_change):
    """
    Get the price change indicator based on percentage change.
    
    Args:
        percentage_change: Percentage change in price
    
    Returns:
        tuple: (arrow_emoji, color, formatted_percentage)
    """
    if percentage_change is None:
        return "➡️", "gray", "N/A"
    
    percentage_change = float(percentage_change)
    abs_change = abs(percentage_change)
    
    # Determine threshold for "not affected much" (e.g., < 2%)
    neutral_threshold = 2.0
    
    if percentage_change > neutral_threshold:
        # Green up arrow for significant increase
        return "🟢 ↗️", "green", f"+{percentage_change:.1f}%"
    elif percentage_change < -neutral_threshold:
        # Red down arrow for significant decrease
        return "🔴 ↘️", "red", f"{percentage_change:.1f}%"
    else:
        # Orange sideways arrow for minimal change
        return "🟠 ➡️", "orange", f"{percentage_change:+.1f}%"


def format_time_ago(published_date):
    """Format published date to relative time"""
    try:
        if isinstance(published_date, str):
            dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
        else:
            dt = published_date
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt
        
        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f"{minutes}m ago" if minutes > 0 else "Just now"
            return f"{hours}h ago"
        elif diff.days == 1:
            return "1 day ago"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return dt.strftime("%b %d, %Y")
    except:
        return "Recently"


def analyze_sentiment(text):
    """
    Analyze sentiment of text using TextBlob.
    
    Args:
        text: String text to analyze (title + description/body)
    
    Returns:
        tuple: (sentiment_label, sentiment_score) where sentiment_label is "Positive Sentiment" or "Negative Sentiment"
               and sentiment_score is a float between -1 and 1
    """
    try:
        if not text or not isinstance(text, str):
            return "Neutral Sentiment", 0.0
        
        # Clean the text
        text = re.sub(r'<[^<]+?>', '', text)  # Remove HTML tags
        text = text.strip()
        
        if not text:
            return "Neutral Sentiment", 0.0
        
        # Analyze sentiment
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Classify as positive or negative
        # Threshold: > 0.1 = positive, < -0.1 = negative, else neutral
        if polarity > 0.1:
            return "Positive Sentiment", polarity
        elif polarity < -0.1:
            return "Negative Sentiment", polarity
        else:
            return "Neutral Sentiment", polarity
    except Exception as e:
        # Return neutral on error
        return "Neutral Sentiment", 0.0


def display_news_article(article, index, price_indicator=None, sentiment_label=None):
    """Display a single news article in a professional card"""
    # Get article data and escape HTML
    title = html.escape(article.get('title', 'No Title'))
    source = html.escape(article.get('source', {}).get('name', 'Unknown Source') if isinstance(article.get('source'), dict) else article.get('source', 'Unknown'))
    url = article.get('url', '')
    image_url = article.get('urlToImage', '')
    description = html.escape(article.get('description', ''))
    author = html.escape(article.get('author', '')) if article.get('author') else ''
    published = article.get('publishedAt', '')
    time_ago = format_time_ago(published) if published else "Recently"
    
    # Get price indicator if available
    price_badge = ""
    if price_indicator:
        arrow, color, pct = price_indicator
        price_badge = f'<span style="color: {color}; font-weight: 600;">{html.escape(arrow)} {html.escape(pct)}</span>'
    
    # Get sentiment badge if available
    sentiment_badge = ""
    if sentiment_label:
        if sentiment_label == "Positive Sentiment":
            sentiment_badge = f'<span style="background-color: #2d5a2d; color: #90ee90; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;">✓ {html.escape(sentiment_label)}</span>'
        elif sentiment_label == "Negative Sentiment":
            sentiment_badge = f'<span style="background-color: #5a2d2d; color: #ff6b6b; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;">✗ {html.escape(sentiment_label)}</span>'
        else:
            sentiment_badge = f'<span style="background-color: #3d3d3d; color: #b0b0b0; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;">○ {html.escape(sentiment_label)}</span>'
    
    # Clean description
    if description:
        description = description[:200] + "..." if len(description) > 200 else description
    
    # Author display
    author_text = f" · {author}" if author else ""
    
    # Build card HTML - use single line to avoid formatting issues
    card_html = f'<div class="news-card" style="background-color: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); transition: transform 0.2s, box-shadow 0.2s;"><div style="display: flex; flex-direction: column; gap: 12px;">'
    
    # Image if available
    if image_url:
        card_html += f'<div style="width: 100%; border-radius: 8px; overflow: hidden; margin-bottom: 12px;"><img src="{html.escape(image_url)}" alt="{title}" style="width: 100%; height: 200px; object-fit: cover; display: block;" onerror="this.style.display=\'none\'"></div>'
    
    # Source, price indicator, and sentiment row
    price_badge_html = f'<div style="font-size: 14px;">{price_badge}</div>' if price_badge else ''
    sentiment_badge_html = f'<div style="margin-left: 8px;">{sentiment_badge}</div>' if sentiment_badge else ''
    card_html += f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;"><div style="color: #ffffff; font-size: 14px; font-weight: 600; letter-spacing: 0.5px;">{source}</div><div style="display: flex; align-items: center; gap: 8px;">{price_badge_html}{sentiment_badge_html}</div></div>'
    
    # Title
    card_html += f'<h3 style="color: #ffffff; font-size: 20px; font-weight: 700; line-height: 1.4; margin: 0 0 12px 0;">{title}</h3>'
    
    # Metadata
    card_html += f'<div style="color: #b0b0b0; font-size: 13px; margin-bottom: 12px;">{time_ago}{author_text}</div>'
    
    # Description
    if description:
        card_html += f'<p style="color: #d0d0d0; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">{description}</p>'
    
    # Read more link
    if url:
        card_html += f'<a href="{html.escape(url)}" target="_blank" style="color: #4a9eff; text-decoration: none; font-size: 14px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">Read More →</a>'
    
    card_html += '</div></div>'
    
    st.markdown(card_html, unsafe_allow_html=True)


def display_reddit_post(post, index):
    """Display a single Reddit post"""
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {post.get('title', 'No Title')}")
            st.caption(f"u/{post.get('author', 'unknown')} • {format_reddit_timestamp(post.get('created_utc', 0))}")
        
        with col2:
            st.metric("👍 Upvotes", post.get('score', 0))
            st.caption(f"💬 {post.get('num_comments', 0)} comments")
        
        # URL
        if post.get('url'):
            st.markdown(f"[🔗 View Post →]({post['url']})")
        if post.get('permalink'):
            st.markdown(f"[💬 Discuss on Reddit →]({post['permalink']})")
        
        st.markdown("---")


def main():
    """Main function for News & Social page"""
    st.set_page_config(
        page_title="News & Social - BTC Dashboard",
        layout="wide",
        page_icon="📰",
    )
    
    # Add custom CSS for professional dark theme styling
    st.markdown("""
    <style>
    /* Main background styling */
    .stApp {
        background-color: #0f0f0f;
    }
    
    /* News grid container */
    .news-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 24px;
        margin-top: 20px;
    }
    
    /* Responsive grid for smaller screens */
    @media (max-width: 1200px) {
        .news-grid {
            grid-template-columns: 1fr;
        }
    }
    
    /* Card hover effects */
    .news-card {
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .news-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    }
    
    /* Title styling */
    h1 {
        color: #ffffff !important;
    }
    
    /* Text color adjustments */
    .stMarkdown {
        color: #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📰 News & Social Media Impact")
    st.markdown("Stay informed with the latest news and social media discussions that impact Bitcoin and the broader market.")
    
    # Load BTC data for price impact analysis
    try:
        btc_df = load_bitcoin_data()
        if btc_df is None or btc_df.empty:
            st.warning("⚠️ Unable to load BTC price data. Price impact indicators will not be available.")
            btc_df = None
    except Exception as e:
        st.warning(f"⚠️ Error loading BTC data: {e}")
        btc_df = None
    
    # Configuration section
    with st.expander("⚙️ API Configuration"):
        st.info("""
        **Free APIs Used:**
        
        1. **NewsAPI** - Get your free API key at https://newsapi.org/register
           - Free tier: 100 requests/day
        
        2. **CryptoCompare** - Free crypto news endpoint
        
        **Instructions:**
        - Set your NewsAPI key as an environment variable: `NEWSAPI_KEY`
        - Restart the app after setting the environment variable
        """)
        
        if os.environ.get("NEWSAPI_KEY"):
            st.success("✅ NewsAPI key is configured")
        else:
            st.warning("⚠️ NewsAPI key not set. Set NEWSAPI_KEY environment variable for news articles.")
    
    # Create tabs for different content sources
    tab1, tab2 = st.tabs(["📰 Latest News", "₿ Crypto News"])
    
    # Tab 1: Latest News
    with tab1:
        st.markdown('<h2 style="color: #ffffff; margin-bottom: 24px;">Top Stories</h2>', unsafe_allow_html=True)
        
        newsapi_key = os.environ.get("NEWSAPI_KEY")
        
        if not newsapi_key:
            st.warning("⚠️ Please set your NEWSAPI_KEY environment variable to fetch news articles.")
            st.info("Get your free key at: https://newsapi.org/register")
        else:
            query = st.text_input("Search Query", value="bitcoin OR BTC OR cryptocurrency", 
                                 help="Customize your search query")
            
            if st.button("🔄 Refresh News", type="primary"):
                st.session_state.news_articles = fetch_newsapi_news(newsapi_key, query, max_results=15)
        
            # Fetch on initial load
            if "news_articles" not in st.session_state:
                with st.spinner("Loading news articles..."):
                    st.session_state.news_articles = fetch_newsapi_news(newsapi_key, query, max_results=15)
            
            if st.session_state.get("news_articles"):
                articles = st.session_state.news_articles
                st.success(f"✅ Loaded {len(articles)} articles")
                
                # Calculate price impacts for all articles
                price_changes = []
                if btc_df is not None:
                    for article in articles[:10]:
                        if article.get('publishedAt'):
                            try:
                                # Handle different date formats from NewsAPI
                                pub_date_str = article['publishedAt']
                                # Replace Z with +00:00 for timezone-aware parsing
                                if pub_date_str.endswith('Z'):
                                    pub_date_str = pub_date_str.replace('Z', '+00:00')
                                published_date = datetime.fromisoformat(pub_date_str)
                                pct_change, _, _, _ = calculate_price_impact(published_date, btc_df)
                                price_changes.append(pct_change)
                            except (ValueError, AttributeError, TypeError) as e:
                                # If date parsing fails, try using pd.to_datetime as fallback
                                try:
                                    published_date = pd.to_datetime(article['publishedAt'])
                                    pct_change, _, _, _ = calculate_price_impact(published_date, btc_df)
                                    price_changes.append(pct_change)
                                except Exception:
                                    price_changes.append(None)
                            except Exception as e:
                                price_changes.append(None)
                        else:
                            price_changes.append(None)
                
                # Check if all articles have the same percentage change (likely all recent news)
                # Round to 2 decimal places to avoid floating point precision issues
                rounded_changes = [round(pct, 2) if pct is not None else None for pct in price_changes]
                all_same = False
                if rounded_changes and all(pct is not None for pct in rounded_changes):
                    unique_changes = set(rounded_changes)
                    if len(unique_changes) == 1:
                        # All articles show the same % change - display once at the top
                        all_same = True
                        common_pct = price_changes[0]
                        price_indicator = get_price_indicator(common_pct)
                        arrow, color, pct = price_indicator
                        st.info(f"📊 **BTC Price Impact (Last 3 Days):** {arrow} {pct} - All recent news articles show the same impact as they were published within the last 3 days.")
                
                # Display articles without individual price indicators if all are the same
                show_individual_indicators = not all_same
                
                # Calculate sentiment for all articles
                sentiments = []
                for article in articles[:10]:
                    # Combine title and description for sentiment analysis
                    title = article.get('title', '')
                    description = article.get('description', '')
                    text_for_sentiment = f"{title} {description}".strip()
                    sentiment_label, _ = analyze_sentiment(text_for_sentiment)
                    sentiments.append(sentiment_label)
                
                # Display articles in a 2-column grid
                articles_to_show = articles[:10]
                for i in range(0, len(articles_to_show), 2):
                    cols = st.columns(2)
                    for j, col in enumerate(cols):
                        if i + j < len(articles_to_show):
                            article = articles_to_show[i + j]
                            # Only show individual indicator if not all are the same
                            price_indicator = None
                            if show_individual_indicators and (i + j) < len(price_changes) and price_changes[i + j] is not None:
                                price_indicator = get_price_indicator(price_changes[i + j])
                            
                            # Get sentiment for this article
                            sentiment_label = sentiments[i + j] if (i + j) < len(sentiments) else None
                            
                            with col:
                                display_news_article(article, i + j, price_indicator, sentiment_label)
            else:
                st.info("No news articles found. Try adjusting your search query.")
    
    # Tab 2: Crypto News
    with tab2:
        st.markdown('<h2 style="color: #ffffff; margin-bottom: 24px;">Top Stories</h2>', unsafe_allow_html=True)
        
        if st.button("🔄 Refresh Crypto News", type="primary"):
            with st.spinner("Loading crypto news..."):
                st.session_state.crypto_news = fetch_crypto_news()
        
        # Fetch on initial load
        if "crypto_news" not in st.session_state:
            with st.spinner("Loading crypto news..."):
                st.session_state.crypto_news = fetch_crypto_news()
        
        if st.session_state.get("crypto_news"):
            articles = st.session_state.crypto_news
            st.success(f"✅ Loaded {len(articles)} crypto news articles")
            
            # Calculate price impacts for all crypto news articles
            price_changes = []
            if btc_df is not None:
                for article in articles[:10]:
                    if article.get('published_on'):
                        try:
                            timestamp = int(article.get('published_on', 0))
                            published_date = datetime.fromtimestamp(timestamp)
                            pct_change, _, _, _ = calculate_price_impact(published_date, btc_df)
                            price_changes.append(pct_change)
                        except Exception as e:
                            price_changes.append(None)
                    else:
                        price_changes.append(None)
            
            # Check if all articles have the same percentage change (likely all recent news)
            rounded_changes = [round(pct, 2) if pct is not None else None for pct in price_changes]
            all_same = False
            if rounded_changes and all(pct is not None for pct in rounded_changes):
                unique_changes = set(rounded_changes)
                if len(unique_changes) == 1:
                    # All articles show the same % change - display once at the top
                    all_same = True
                    common_pct = price_changes[0]
                    price_indicator = get_price_indicator(common_pct)
                    arrow, color, pct = price_indicator
                    st.info(f"📊 **BTC Price Impact (Last 3 Days):** {arrow} {pct} - All recent news articles show the same impact as they were published within the last 3 days.")
            
            # Display articles without individual price indicators if all are the same
            show_individual_indicators = not all_same
            
            # Calculate sentiment for all crypto news articles
            sentiments = []
            for article in articles[:10]:
                # Combine title and body for sentiment analysis
                title = article.get('title', '')
                body = article.get('body', '')
                # Strip HTML tags from body for sentiment analysis
                body_clean = re.sub('<[^<]+?>', '', body) if body else ''
                text_for_sentiment = f"{title} {body_clean}".strip()
                sentiment_label, _ = analyze_sentiment(text_for_sentiment)
                sentiments.append(sentiment_label)
            
            # Display articles in a 2-column grid
            articles_to_show = articles[:10]
            for i in range(0, len(articles_to_show), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j < len(articles_to_show):
                        article = articles_to_show[i + j]
                        # Only show individual indicator if not all are the same
                        price_indicator = None
                        if show_individual_indicators and (i + j) < len(price_changes) and price_changes[i + j] is not None:
                            price_indicator = get_price_indicator(price_changes[i + j])
                        
                        # Get sentiment for this article
                        sentiment_label = sentiments[i + j] if (i + j) < len(sentiments) else None
                        
                        with col:
                            # Get article data and escape HTML
                            title = html.escape(article.get('title', 'No Title'))
                            
                            # Get source name
                            source_name = "Unknown Source"
                            if isinstance(article.get('source_info'), dict):
                                source_name = html.escape(article['source_info'].get('name', 'Unknown'))
                            elif isinstance(article.get('source'), str):
                                source_name = html.escape(article['source'].title())
                            
                            url = article.get('url', '')
                            image_url = article.get('imageurl', '')
                            
                            # Get and format date
                            time_ago = "Recently"
                            if article.get('published_on'):
                                try:
                                    timestamp = int(article.get('published_on', 0))
                                    published_date = datetime.fromtimestamp(timestamp)
                                    time_ago = format_time_ago(published_date)
                                except:
                                    time_ago = "Recently"
                            
                            # Get body/description
                            body = ""
                            if article.get('body'):
                                body = article.get('body', '')
                                # Strip HTML tags if any
                                body = re.sub('<[^<]+?>', '', body)
                                body = html.escape(body)
                                body = body[:300] + "..." if len(body) > 300 else body
                            
                            # Get price indicator if available
                            price_badge = ""
                            if price_indicator:
                                arrow, color, pct = price_indicator
                                price_badge = f'<span style="color: {color}; font-weight: 600;">{html.escape(arrow)} {html.escape(pct)}</span>'
                            
                            # Get sentiment badge if available
                            sentiment_badge = ""
                            if sentiment_label:
                                if sentiment_label == "Positive Sentiment":
                                    sentiment_badge = f'<span style="background-color: #2d5a2d; color: #90ee90; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;">✓ {html.escape(sentiment_label)}</span>'
                                elif sentiment_label == "Negative Sentiment":
                                    sentiment_badge = f'<span style="background-color: #5a2d2d; color: #ff6b6b; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;">✗ {html.escape(sentiment_label)}</span>'
                                else:
                                    sentiment_badge = f'<span style="background-color: #3d3d3d; color: #b0b0b0; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;">○ {html.escape(sentiment_label)}</span>'
                            
                            # Build card HTML - use single line to avoid formatting issues
                            card_html = f'<div class="news-card" style="background-color: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); transition: transform 0.2s, box-shadow 0.2s;"><div style="display: flex; flex-direction: column; gap: 12px;">'
                            
                            # Image if available
                            if image_url:
                                card_html += f'<div style="width: 100%; border-radius: 8px; overflow: hidden; margin-bottom: 12px;"><img src="{html.escape(image_url)}" alt="{title}" style="width: 100%; height: 200px; object-fit: cover; display: block;" onerror="this.style.display=\'none\'"></div>'
                            
                            # Source, price indicator, and sentiment row
                            price_badge_html = f'<div style="font-size: 14px;">{price_badge}</div>' if price_badge else ''
                            sentiment_badge_html = f'<div style="margin-left: 8px;">{sentiment_badge}</div>' if sentiment_badge else ''
                            card_html += f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;"><div style="color: #ffffff; font-size: 14px; font-weight: 600; letter-spacing: 0.5px;">{source_name}</div><div style="display: flex; align-items: center; gap: 8px;">{price_badge_html}{sentiment_badge_html}</div></div>'
                            
                            # Title
                            card_html += f'<h3 style="color: #ffffff; font-size: 20px; font-weight: 700; line-height: 1.4; margin: 0 0 12px 0;">{title}</h3>'
                            
                            # Metadata
                            card_html += f'<div style="color: #b0b0b0; font-size: 13px; margin-bottom: 12px;">{time_ago}</div>'
                            
                            # Body/Description
                            if body:
                                card_html += f'<p style="color: #d0d0d0; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">{body}</p>'
                            
                            # Read more link
                            if url:
                                card_html += f'<a href="{html.escape(url)}" target="_blank" style="color: #4a9eff; text-decoration: none; font-size: 14px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">Read More →</a>'
                            
                            card_html += '</div></div>'
                            
                            st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info("No crypto news found at the moment.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **📊 Data Sources:**
    - NewsAPI.org
    - CryptoCompare.com
    
    **⏰ Last Updated:** Real-time data (refresh to update)
    """)


if __name__ == "__main__":
    main()

