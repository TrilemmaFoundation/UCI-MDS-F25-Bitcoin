import streamlit as st
import requests
from datetime import datetime, timedelta
import os
import json
import re
import pandas as pd
from dashboard.data_loader import load_bitcoin_data


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
        headers = {"User-Agent": "BTC-Dashboard/1.0"}
        params = {"limit": limit}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
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
    
    Args:
        published_date: datetime object of when the news was published
        btc_data: DataFrame with BTC price data (indexed by date)
    
    Returns:
        tuple: (percentage_change, price_before, price_after, price_on_date)
    """
    try:
        # Normalize the published date to remove time component
        article_date = pd.Timestamp(published_date).normalize()
        
        # Find the closest price data point to the article date
        # Look for price data on the article date or nearby
        available_dates = btc_data.index
        
        # Try to find price on the article date
        if article_date in available_dates:
            price_on_date = btc_data.loc[article_date, "PriceUSD"]
        else:
            # Find the closest date to the article date
            closest_idx = available_dates.get_indexer([article_date], method="nearest")[0]
            closest_date = available_dates[closest_idx]
            price_on_date = btc_data.loc[closest_date, "PriceUSD"]
            article_date = closest_date
        
        # Get price 3 days before
        if article_date - timedelta(days=3) in available_dates:
            price_before = btc_data.loc[article_date - timedelta(days=3), "PriceUSD"]
        else:
            # Find the closest date 3 days before
            before_date = article_date - timedelta(days=3)
            closest_idx = available_dates.get_indexer([before_date], method="backfill")[0]
            price_before = btc_data.loc[available_dates[closest_idx], "PriceUSD"]
        
        # Get price 3 days after
        if article_date + timedelta(days=3) in available_dates:
            price_after = btc_data.loc[article_date + timedelta(days=3), "PriceUSD"]
        else:
            # Find the closest date 3 days after
            after_date = article_date + timedelta(days=3)
            closest_idx = available_dates.get_indexer([after_date], method="pad")[0]
            price_after = btc_data.loc[available_dates[closest_idx], "PriceUSD"]
        
        # Calculate percentage change
        if price_before > 0:
            percentage_change = ((price_after - price_before) / price_before) * 100
        else:
            percentage_change = 0.0
        
        return percentage_change, price_before, price_after, price_on_date
    
    except Exception as e:
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


def display_news_article(article, index, price_indicator=None):
    """Display a single news article in a card"""
    with st.container():
        # Title with price impact indicator
        title_col, indicator_col = st.columns([4, 1])
        with title_col:
            st.markdown(f"### {index + 1}. {article.get('title', 'No Title')}")
        with indicator_col:
            if price_indicator:
                arrow, color, pct = price_indicator
                st.markdown(f"#### {arrow} {pct}")
        
        # Meta information
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            source = article.get('source', {}).get('name', 'Unknown Source') if isinstance(article.get('source'), dict) else article.get('source', 'Unknown')
            st.caption(f"📰 {source}")
        with col2:
            published = article.get('publishedAt', '')
            if published:
                try:
                    dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                    st.caption(f"🕐 {dt.strftime('%b %d, %Y')}")
                except:
                    st.caption(f"🕐 {published}")
        with col3:
            if article.get('url'):
                st.caption(f"[📖 Read More →]({article['url']})")
        
        # Description
        if article.get('description'):
            st.markdown(f"*{article.get('description', '')[:200]}...*")
        
        st.markdown("---")


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
        
        2. **Reddit API** - No key required, just uses public data
        
        3. **CryptoCompare** - Free crypto news endpoint
        
        **Instructions:**
        - Set your NewsAPI key as an environment variable: `NEWSAPI_KEY`
        - Restart the app after setting the environment variable
        """)
        
        if os.environ.get("NEWSAPI_KEY"):
            st.success("✅ NewsAPI key is configured")
        else:
            st.warning("⚠️ NewsAPI key not set. Set NEWSAPI_KEY environment variable for news articles.")
    
    # Create tabs for different content sources
    tab1, tab2, tab3 = st.tabs(["📰 Latest News", "💬 Reddit Discussions", "₿ Crypto News"])
    
    # Tab 1: Latest News
    with tab1:
        st.header("Latest News Articles")
        
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
                
                for i, article in enumerate(articles[:10]):
                    # Calculate price impact
                    price_indicator = None
                    if btc_df is not None and article.get('publishedAt'):
                        try:
                            published_date = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                            pct_change, _, _, _ = calculate_price_impact(published_date, btc_df)
                            price_indicator = get_price_indicator(pct_change)
                        except Exception as e:
                            pass  # Skip indicator if calculation fails
                    
                    display_news_article(article, i, price_indicator)
            else:
                st.info("No news articles found. Try adjusting your search query.")
    
    # Tab 2: Reddit Discussions
    with tab2:
        st.header("Popular Bitcoin Discussions on Reddit")
        
        subreddit = st.selectbox(
            "Select Subreddit",
            options=["Bitcoin", "CryptoCurrency", "CryptoMarkets", "wallstreetbets"],
            help="Choose which subreddit to browse"
        )
        
        if st.button("🔄 Refresh Reddit Posts", type="primary"):
            with st.spinner(f"Loading posts from r/{subreddit}..."):
                st.session_state.reddit_posts = fetch_reddit_posts(subreddit, limit=15)
        
        # Fetch on initial load or when subreddit changes
        if "reddit_posts" not in st.session_state or st.session_state.get("current_subreddit") != subreddit:
            with st.spinner(f"Loading posts from r/{subreddit}..."):
                st.session_state.reddit_posts = fetch_reddit_posts(subreddit, limit=15)
                st.session_state.current_subreddit = subreddit
        
        if st.session_state.get("reddit_posts"):
            posts = st.session_state.reddit_posts
            st.success(f"✅ Loaded {len(posts)} popular posts from r/{subreddit}")
            
            for i, post in enumerate(posts[:10]):
                display_reddit_post(post, i)
        else:
            st.info("No Reddit posts found. Try another subreddit.")
    
    # Tab 3: Crypto News
    with tab3:
        st.header("Bitcoin & Crypto Market News")
        
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
            
            for i, article in enumerate(articles[:10]):
                with st.container():
                    # Calculate price impact for crypto news
                    price_indicator = None
                    if btc_df is not None and article.get('published_on'):
                        try:
                            timestamp = int(article.get('published_on', 0))
                            published_date = datetime.fromtimestamp(timestamp)
                            pct_change, _, _, _ = calculate_price_impact(published_date, btc_df)
                            price_indicator = get_price_indicator(pct_change)
                        except Exception as e:
                            pass
                    
                    # Title with price impact indicator
                    title_col, indicator_col = st.columns([4, 1])
                    with title_col:
                        st.markdown(f"### {i + 1}. {article.get('title', 'No Title')}")
                    with indicator_col:
                        if price_indicator:
                            arrow, color, pct = price_indicator
                            st.markdown(f"#### {arrow} {pct}")
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        # Get source name
                        source_name = "Unknown Source"
                        if isinstance(article.get('source_info'), dict):
                            source_name = article['source_info'].get('name', 'Unknown')
                        elif isinstance(article.get('source'), str):
                            source_name = article['source'].title()
                        st.caption(f"📰 {source_name}")
                        
                        # Get and format date
                        if article.get('published_on'):
                            try:
                                timestamp = int(article.get('published_on', 0))
                                dt = datetime.fromtimestamp(timestamp)
                                st.caption(f"🕐 {dt.strftime('%b %d, %Y %I:%M %p')}")
                            except:
                                st.caption(f"🕐 Just now")
                    with col2:
                        if article.get('url'):
                            st.caption(f"[📖 Read More →]({article['url']})")
                    
                    # Show snippet if body exists
                    if article.get('body'):
                        body = article.get('body', '')
                        # Strip HTML tags if any
                        body = re.sub('<[^<]+?>', '', body)
                        st.markdown(f"*{body[:300]}...*" if len(body) > 300 else f"*{body}*")
                    
                    st.markdown("---")
        else:
            st.info("No crypto news found at the moment.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **📊 Data Sources:**
    - NewsAPI.org
    - Reddit.com
    - CryptoCompare.com
    
    **⏰ Last Updated:** Real-time data (refresh to update)
    """)


if __name__ == "__main__":
    main()

