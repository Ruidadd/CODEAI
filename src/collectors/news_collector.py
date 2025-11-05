"""
News Collector
Collects news articles from various sources (RSS feeds, APIs)
"""
import feedparser
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import time
import re


class NewsCollector:
    """Collects news articles from RSS feeds and news APIs"""

    def __init__(self, logger=None):
        """
        Initialize the news collector

        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def collect_from_rss(self, source_name, rss_url, stock_symbols=None, max_articles=20):
        """
        Collect articles from an RSS feed

        Args:
            source_name (str): Name of the news source
            rss_url (str): URL of the RSS feed
            stock_symbols (list): List of stock symbols to filter for
            max_articles (int): Maximum number of articles to collect

        Returns:
            list: List of article dictionaries
        """
        articles = []

        try:
            if self.logger:
                self.logger.info(f"Fetching RSS feed from {source_name}: {rss_url}")

            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if feed.bozo:
                if self.logger:
                    self.logger.warning(f"RSS feed parsing warning for {source_name}: {feed.bozo_exception}")

            # Process entries
            for entry in feed.entries[:max_articles]:
                article = self._parse_rss_entry(entry, source_name, stock_symbols)
                if article:
                    articles.append(article)

            if self.logger:
                self.logger.info(f"Collected {len(articles)} articles from {source_name}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error collecting from {source_name}: {str(e)}")

        return articles

    def _parse_rss_entry(self, entry, source_name, stock_symbols=None):
        """
        Parse a single RSS feed entry

        Args:
            entry: RSS feed entry
            source_name (str): Name of the news source
            stock_symbols (list): List of stock symbols to filter for

        Returns:
            dict: Parsed article data or None if filtered out
        """
        try:
            # Extract basic information
            title = entry.get('title', '').strip()
            description = entry.get('summary', entry.get('description', '')).strip()
            link = entry.get('link', '')

            # Extract published date
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            if published:
                pub_date = datetime(*published[:6])
            else:
                pub_date = datetime.now()

            # Clean HTML from description
            if description:
                soup = BeautifulSoup(description, 'html.parser')
                description = soup.get_text().strip()

            # Combine title and description for full text
            full_text = f"{title}. {description}"

            # Filter by stock symbols if provided
            if stock_symbols:
                found_symbols = self._find_stock_symbols(full_text, stock_symbols)
                if not found_symbols:
                    return None
            else:
                found_symbols = []

            return {
                'title': title,
                'description': description,
                'full_text': full_text,
                'url': link,
                'source': source_name,
                'published_date': pub_date,
                'collected_date': datetime.now(),
                'stock_symbols': found_symbols
            }

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error parsing RSS entry: {str(e)}")
            return None

    def _find_stock_symbols(self, text, stock_symbols):
        """
        Find stock symbols mentioned in text

        Args:
            text (str): Text to search
            stock_symbols (list): List of stock symbols to look for

        Returns:
            list: List of found stock symbols
        """
        found = []
        text_upper = text.upper()

        for symbol in stock_symbols:
            # Look for symbol as whole word or with $ prefix
            pattern = r'\b' + re.escape(symbol) + r'\b|\$' + re.escape(symbol) + r'\b'
            if re.search(pattern, text_upper):
                found.append(symbol)

        return found

    def collect_from_sources(self, sources, stock_symbols=None, max_articles_per_source=20):
        """
        Collect articles from multiple sources

        Args:
            sources (list): List of source dictionaries with 'name' and 'url'
            stock_symbols (list): List of stock symbols to filter for
            max_articles_per_source (int): Maximum articles per source

        Returns:
            list: List of all collected articles
        """
        all_articles = []

        for source in sources:
            name = source.get('name')
            url = source.get('url')

            if not name or not url:
                continue

            articles = self.collect_from_rss(
                name,
                url,
                stock_symbols,
                max_articles_per_source
            )
            all_articles.extend(articles)

            # Be nice to servers
            time.sleep(1)

        if self.logger:
            self.logger.info(f"Total articles collected: {len(all_articles)}")

        return all_articles

    def search_news_api(self, api_key, query, language='en', page_size=20):
        """
        Search for news using News API (requires API key)

        Args:
            api_key (str): News API key
            query (str): Search query
            language (str): Language code
            page_size (int): Number of articles to retrieve

        Returns:
            list: List of article dictionaries
        """
        if not api_key:
            if self.logger:
                self.logger.warning("News API key not provided, skipping API search")
            return []

        try:
            from newsapi import NewsApiClient

            newsapi = NewsApiClient(api_key=api_key)
            response = newsapi.get_everything(
                q=query,
                language=language,
                sort_by='publishedAt',
                page_size=page_size
            )

            articles = []
            for article_data in response.get('articles', []):
                article = {
                    'title': article_data.get('title', ''),
                    'description': article_data.get('description', ''),
                    'full_text': f"{article_data.get('title', '')}. {article_data.get('description', '')}",
                    'url': article_data.get('url', ''),
                    'source': article_data.get('source', {}).get('name', 'Unknown'),
                    'published_date': datetime.fromisoformat(article_data.get('publishedAt', '').replace('Z', '+00:00')),
                    'collected_date': datetime.now(),
                    'stock_symbols': []
                }
                articles.append(article)

            if self.logger:
                self.logger.info(f"Collected {len(articles)} articles from News API")

            return articles

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error searching News API: {str(e)}")
            return []
