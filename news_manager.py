import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import threading
import time
import re
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Accept': 'application/xml,application/json' # RSS is XML, but we handle both
}

def safe_request(url, method='GET', params=None, json_data=None, timeout=12, retries=2):
    """Fetch with retries and institutional headers."""
    import time
    from requests.exceptions import SSLError, ConnectionError, Timeout, RequestException
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.request(method, url, params=params, json=json_data, headers=HEADERS, timeout=timeout, verify=True)
            r.raise_for_status()
            return r
        except (SSLError, ConnectionError, Timeout) as e:
            # Network/SSL errors - retry with exponential backoff
            last_err = e
            if attempt < retries - 1:
                time.sleep(1 + attempt * 1.5)
            continue
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1 + attempt)
            continue
    raise last_err

class NewsManager:
    def __init__(self):
        self.news_feed = []
        self.sentiment_score = 0
        self.sentiment_label = "NEUTRAL"
        self.btc_price_history = []  # List of (timestamp, price)
        self.volatility_warning = None
        self.news_warning = None
        self.lock = threading.Lock()
        
        # Keywords for simple sentiment analysis
        self.positive_keywords = {
            'bull', 'bullish', 'surge', 'soar', 'jump', 'gain', 'rally', 
            'adoption', 'approve', 'etf', 'partnership', 'launch', 'listing',
            'record', 'high', 'moon', 'breakout', 'support', 'buy', 'growth',
            'upgrade', 'whitelist', 'fundraise', 'investment', 'expanded'
        }
        self.negative_keywords = {
            'bear', 'bearish', 'crash', 'dump', 'drop', 'fall', 'loss', 
            'ban', 'hack', 'exploit', 'lawsuit', 'fraud', 'scam', 'drain',
            'collapse', 'insolvency', 'delist', 'regulatory', 'warn', 'sell', 
            'resistance', 'liquidat', 'bankrupt', 'closure', 'fine', 'penalty'
        }
    
    def fetch_news(self):
        """Fetch news from CoinTelegraph RSS and analyze sentiment"""
        try:
            # CoinTelegraph RSS Feed (Reliable & Free)
            url = "https://cointelegraph.com/rss"
            response = safe_request(url)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                
                new_feed = []
                total_sentiment = 0
                count = 0
                
                # Get last 10 news items
                for item in items[:10]:
                    title = item.find('title').text
                    pub_date_str = item.find('pubDate').text
                    link = item.find('link').text
                    
                    # Parse PubDate (Standard RSS format: Wed, 02 Oct 2002 15:00:00 +0200)
                    # We keep it simple string for UI or parse if needed for strict time check
                    
                    # Sentiment Analysis
                    title_lower = title.lower()
                    score = 0
                    
                    # Count matches
                    pos_matches = sum(1 for word in self.positive_keywords if word in title_lower)
                    neg_matches = sum(1 for word in self.negative_keywords if word in title_lower)
                    
                    if pos_matches > neg_matches:
                        score = 1
                        sentiment = "POSITIVE"
                    elif neg_matches > pos_matches:
                        score = -1
                        sentiment = "NEGATIVE"
                    else:
                        score = 0
                        sentiment = "NEUTRAL"
                        
                    total_sentiment += score
                    count += 1
                    
                    new_feed.append({
                        'title': title,
                        'pub_date': pub_date_str,
                        'link': link,
                        'sentiment': sentiment,
                        'score': score
                    })

                with self.lock:
                    self.news_feed = new_feed
                    
                    # Determine overall sentiment
                    avg_score = total_sentiment / count if count > 0 else 0
                    self.sentiment_score = avg_score
                    
                    if avg_score > 0.2:
                        self.sentiment_label = "BULLISH 🚀"
                    elif avg_score < -0.2:
                        self.sentiment_label = "BEARISH 🐻"
                    else:
                        self.sentiment_label = "NEUTRAL 😐"
                        
                    # Check for "Breaking News" or very recent major news (simple heuristic logic)
                    # Implementation detail: For now, just having the feed is the first step.
                    # Warnings will be generated if sentiment is extreme.
                    if abs(avg_score) >= 0.5:
                        self.news_warning = f"EXTREME MARKET SENTIMENT: {self.sentiment_label}"
                    else:
                        self.news_warning = None
                        
        except Exception as e:
            # Silently handle news fetch errors to avoid terminal clutter
            pass

    def check_btc_volatility(self):
        """Check BTC price movement for sudden volatility"""
        try:
            # Binance API for Price (Fast & Free)
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = safe_request(url, timeout=6)
            
            if response.status_code == 200:
                data = response.json()
                price = float(data['price'])
                now = datetime.now()
                
                with self.lock:
                    # Add current price to history
                    self.btc_price_history.append((now, price))
                    
                    # Clean up old history (keep last 5 minutes)
                    cutoff = now - timedelta(minutes=5)
                    self.btc_price_history = [p for p in self.btc_price_history if p[0] > cutoff]
                    
                    if len(self.btc_price_history) < 2:
                        return
                    
                    # 1. Immediate "Flash" Volatility (within last 30-60 seconds)
                    # Find price 30 seconds ago
                    price_30s_ago = None
                    target_time = now - timedelta(seconds=30)
                    
                    for t, p in self.btc_price_history:
                        if t >= target_time:
                            price_30s_ago = p
                            break
                    
                    if price_30s_ago:
                        change_pct = ((price - price_30s_ago) / price_30s_ago) * 100
                        result_str = f"{change_pct:+.2f}%"
                        
                        # Threshold: 0.5% move in 30 seconds is HUGE for BTC
                        # Let's set a realistic "Sudden Movement" threshold
                        threshold = 0.3 
                        
                        if change_pct >= threshold:
                            self.volatility_warning = f"⚠️ HIGH VOLATILITY: BTC SURGING (+{change_pct:.2f}% in 30s)"
                        elif change_pct <= -threshold:
                            self.volatility_warning = f"⚠️ HIGH VOLATILITY: BTC DUMPING ({change_pct:.2f}% in 30s)"
                        else:
                            self.volatility_warning = None
                            
        except Exception as e:
            # Silently handle volatility check errors
            pass

    def get_market_status(self):
        """Get the current aggregated market status"""
        with self.lock:
            return {
                'sentiment': self.sentiment_label,
                'sentiment_score': self.sentiment_score,
                'news_feed': self.news_feed[:5], # Send top 5
                'volatility_warning': self.volatility_warning,
                'news_warning': self.news_warning
            }

# Global instance
news_manager = NewsManager()
