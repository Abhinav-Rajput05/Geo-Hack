"""
News Ingestion Service - RSS and API Integration
"""
import feedparser
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from app.config import settings


class NewsIngestor:
    """Service for ingesting news from multiple sources"""
    
    def __init__(self):
        self.rss_feeds = settings.rss_feeds
        self.newsapi_key = settings.news_api_key
    
    async def ingest_from_rss(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Ingest news from RSS feeds"""
        articles = []
        
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                source_name = feed.feed.get('title', 'Unknown')
                
                for entry in feed.entries[:limit]:
                    article = self._parse_rss_entry(entry, source_name)
                    if article:
                        articles.append(article)
                        
            except Exception as e:
                print(f"Error parsing RSS feed {feed_url}: {e}")
        
        return articles
    
    def _parse_rss_entry(self, entry: Any, source_name: str) -> Optional[Dict[str, Any]]:
        """Parse RSS entry to article format"""
        try:
            # Parse published date
            published_at = None
            if hasattr(entry, 'published'):
                try:
                    published_at = date_parser.parse(entry.published).isoformat()
                except:
                    published_at = datetime.utcnow().isoformat()
            
            # Extract categories/tags
            categories = []
            if hasattr(entry, 'tags'):
                categories = [tag.term for tag in entry.tags]
            elif hasattr(entry, 'categories'):
                categories = list(entry.categories)
            
            # Get summary (strip HTML)
            summary = ''
            if hasattr(entry, 'summary'):
                summary = self._strip_html(entry.summary)
            elif hasattr(entry, 'description'):
                summary = self._strip_html(entry.description)
            
            # Get title
            title = getattr(entry, 'title', 'Untitled')
            
            return {
                'title': title,
                'summary': summary[:500],  # Limit summary length
                'url': getattr(entry, 'link', ''),
                'source': source_name,
                'published_at': published_at,
                'categories': categories,
                'ingested_at': datetime.utcnow().isoformat(),
                'status': 'pending',  # pending, processed, error
            }
        except Exception as e:
            print(f"Error parsing RSS entry: {e}")
            return None
    
    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from text"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html)
    
    async def ingest_from_newsapi(
        self, 
        query: str = None,
        language: str = 'en',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Ingest news from NewsAPI"""
        if not self.newsapi_key:
            return []
        
        articles = []
        
        try:
            # Top headlines endpoint
            if query is None:
                url = "https://newsapi.org/v2/top-headlines"
                params = {
                    'apiKey': self.newsapi_key,
                    'language': language,
                    'pageSize': limit,
                }
            else:
                url = "https://newsapi.org/v2/everything"
                params = {
                    'apiKey': self.newsapi_key,
                    'q': query,
                    'language': language,
                    'pageSize': limit,
                    'sortBy': 'publishedAt',
                }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'ok':
                for article in data.get('articles', []):
                    parsed = self._parse_newsapi_article(article)
                    if parsed:
                        articles.append(parsed)
                        
        except Exception as e:
            print(f"Error fetching from NewsAPI: {e}")
        
        return articles
    
    def _parse_newsapi_article(self, article: Dict) -> Optional[Dict[str, Any]]:
        """Parse NewsAPI article"""
        try:
            published_at = None
            if article.get('publishedAt'):
                try:
                    published_at = date_parser.parse(article['publishedAt']).isoformat()
                except:
                    published_at = datetime.utcnow().isoformat()
            
            source = article.get('source', {}).get('name', 'Unknown')
            
            # Get description
            description = article.get('description') or ''
            if description:
                description = self._strip_html(description)[:500]
            
            # Get content
            content = article.get('content') or ''
            if content:
                content = self._strip_html(content)
            
            return {
                'title': article.get('title', 'Untitled'),
                'summary': description,
                'content': content,
                'url': article.get('url', ''),
                'image_url': article.get('urlToImage'),
                'source': source,
                'author': article.get('author'),
                'published_at': published_at,
                'categories': self._infer_categories(article.get('title', '')),
                'ingested_at': datetime.utcnow().isoformat(),
                'status': 'pending',
            }
        except Exception as e:
            print(f"Error parsing NewsAPI article: {e}")
            return None
    
    def _infer_categories(self, title: str) -> List[str]:
        """Infer categories from article title"""
        title_lower = title.lower()
        categories = []
        
        category_keywords = {
            'Politics': ['election', 'government', 'president', 'parliament', 'minister', 'vote'],
            'Economics': ['economy', 'market', 'trade', 'gdp', 'inflation', 'recession', 'stock'],
            'Technology': ['tech', 'ai', 'software', 'digital', 'cyber', 'startup', 'app'],
            'Defense': ['military', 'army', 'war', 'soldiers', 'defense', 'nato', 'missile'],
            'Climate': ['climate', 'weather', 'disaster', 'flood', 'earthquake', 'temperature'],
            'Health': ['health', 'virus', 'pandemic', 'vaccine', 'disease', 'hospital'],
            'Energy': ['oil', 'gas', 'energy', 'solar', 'wind', 'power', 'electricity'],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in title_lower for kw in keywords):
                categories.append(category)
        
        return categories if categories else ['General']
    
    async def ingest_all(self, limit_per_source: int = 50) -> Dict[str, Any]:
        """Ingest from all configured sources"""
        all_articles = []
        
        # RSS feeds
        rss_articles = await self.ingest_from_rss(limit=limit_per_source)
        all_articles.extend(rss_articles)
        
        # NewsAPI
        newsapi_articles = await self.ingest_from_newsapi(limit=limit_per_source)
        all_articles.extend(newsapi_articles)
        
        # Remove duplicates based on URL
        unique_articles = self._deduplicate(all_articles)
        
        return {
            'total_articles': len(all_articles),
            'unique_articles': len(unique_articles),
            'articles': unique_articles[:limit_per_source * 3],  # Limit total
            'sources': list(set(a['source'] for a in unique_articles)),
            'ingested_at': datetime.utcnow().isoformat(),
        }
    
    def _deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on URL"""
        seen_urls = set()
        unique = []
        
        for article in articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(article)
        
        return unique


# Singleton instance
news_ingestor = NewsIngestor()
