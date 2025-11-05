"""
Data Storage
Handles storing and retrieving sentiment analysis data
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd


class DataStorage:
    """Manages data storage for sentiment analysis"""

    def __init__(self, storage_type='sqlite', db_path='data/sentiment.db',
                 json_path='data/sentiment_data.json', logger=None):
        """
        Initialize data storage

        Args:
            storage_type (str): 'sqlite' or 'json'
            db_path (str): Path to SQLite database
            json_path (str): Path to JSON file
            logger: Logger instance
        """
        self.storage_type = storage_type.lower()
        self.db_path = db_path
        self.json_path = json_path
        self.logger = logger

        if self.storage_type == 'sqlite':
            self._init_sqlite()
        elif self.storage_type == 'json':
            self._init_json()
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")

    def _init_sqlite(self):
        """Initialize SQLite database"""
        # Create directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                full_text TEXT,
                url TEXT UNIQUE,
                source TEXT,
                published_date TIMESTAMP,
                collected_date TIMESTAMP,
                sentiment TEXT,
                compound_score REAL,
                positive_score REAL,
                negative_score REAL,
                neutral_score REAL,
                analyzer TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS article_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                stock_symbol TEXT,
                FOREIGN KEY (article_id) REFERENCES articles (id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_url ON articles(url)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_published_date ON articles(published_date)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_stock_symbol ON article_stocks(stock_symbol)
        ''')

        conn.commit()
        conn.close()

        if self.logger:
            self.logger.info(f"Initialized SQLite database at {self.db_path}")

    def _init_json(self):
        """Initialize JSON storage"""
        # Create directory if it doesn't exist
        Path(self.json_path).parent.mkdir(parents=True, exist_ok=True)

        if not Path(self.json_path).exists():
            with open(self.json_path, 'w') as f:
                json.dump({'articles': []}, f)

        if self.logger:
            self.logger.info(f"Initialized JSON storage at {self.json_path}")

    def save_articles(self, articles):
        """
        Save analyzed articles

        Args:
            articles (list): List of article dictionaries with sentiment analysis

        Returns:
            int: Number of new articles saved
        """
        if self.storage_type == 'sqlite':
            return self._save_articles_sqlite(articles)
        elif self.storage_type == 'json':
            return self._save_articles_json(articles)

    def _save_articles_sqlite(self, articles):
        """Save articles to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved_count = 0

        for article in articles:
            try:
                sentiment = article.get('sentiment_analysis', {})

                # Insert article
                cursor.execute('''
                    INSERT OR IGNORE INTO articles
                    (title, description, full_text, url, source, published_date,
                     collected_date, sentiment, compound_score, positive_score,
                     negative_score, neutral_score, analyzer)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.get('title'),
                    article.get('description'),
                    article.get('full_text'),
                    article.get('url'),
                    article.get('source'),
                    article.get('published_date'),
                    article.get('collected_date'),
                    sentiment.get('sentiment'),
                    sentiment.get('compound'),
                    sentiment.get('positive'),
                    sentiment.get('negative'),
                    sentiment.get('neutral'),
                    sentiment.get('analyzer')
                ))

                if cursor.rowcount > 0:
                    saved_count += 1
                    article_id = cursor.lastrowid

                    # Insert stock symbols
                    for symbol in article.get('stock_symbols', []):
                        cursor.execute('''
                            INSERT INTO article_stocks (article_id, stock_symbol)
                            VALUES (?, ?)
                        ''', (article_id, symbol))

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error saving article: {str(e)}")

        conn.commit()
        conn.close()

        if self.logger:
            self.logger.info(f"Saved {saved_count} new articles to database")

        return saved_count

    def _save_articles_json(self, articles):
        """Save articles to JSON file"""
        try:
            # Load existing data
            with open(self.json_path, 'r') as f:
                data = json.load(f)

            existing_urls = {a['url'] for a in data['articles']}
            saved_count = 0

            # Add new articles
            for article in articles:
                if article.get('url') not in existing_urls:
                    # Convert datetime objects to strings
                    article_copy = article.copy()
                    if isinstance(article_copy.get('published_date'), datetime):
                        article_copy['published_date'] = article_copy['published_date'].isoformat()
                    if isinstance(article_copy.get('collected_date'), datetime):
                        article_copy['collected_date'] = article_copy['collected_date'].isoformat()

                    data['articles'].append(article_copy)
                    saved_count += 1

            # Save back to file
            with open(self.json_path, 'w') as f:
                json.dump(data, f, indent=2)

            if self.logger:
                self.logger.info(f"Saved {saved_count} new articles to JSON")

            return saved_count

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving articles to JSON: {str(e)}")
            return 0

    def get_articles(self, stock_symbol=None, start_date=None, end_date=None, limit=None):
        """
        Retrieve articles from storage

        Args:
            stock_symbol (str): Filter by stock symbol
            start_date (datetime): Filter by start date
            end_date (datetime): Filter by end date
            limit (int): Maximum number of articles to retrieve

        Returns:
            list: List of article dictionaries
        """
        if self.storage_type == 'sqlite':
            return self._get_articles_sqlite(stock_symbol, start_date, end_date, limit)
        elif self.storage_type == 'json':
            return self._get_articles_json(stock_symbol, start_date, end_date, limit)

    def _get_articles_sqlite(self, stock_symbol=None, start_date=None, end_date=None, limit=None):
        """Retrieve articles from SQLite database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM articles"
        params = []
        conditions = []

        if stock_symbol:
            query = '''
                SELECT DISTINCT a.* FROM articles a
                JOIN article_stocks s ON a.id = s.article_id
                WHERE s.stock_symbol = ?
            '''
            params.append(stock_symbol)

        if start_date:
            conditions.append("published_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("published_date <= ?")
            params.append(end_date)

        if conditions:
            if stock_symbol:
                query += " AND " + " AND ".join(conditions)
            else:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY published_date DESC"

        if limit:
            query += f" LIMIT {limit}"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        articles = []
        for row in rows:
            article = dict(row)
            # Get stock symbols for this article
            cursor2 = conn.execute(
                "SELECT stock_symbol FROM article_stocks WHERE article_id = ?",
                (article['id'],)
            )
            article['stock_symbols'] = [r[0] for r in cursor2.fetchall()]
            articles.append(article)

        conn.close()
        return articles

    def _get_articles_json(self, stock_symbol=None, start_date=None, end_date=None, limit=None):
        """Retrieve articles from JSON file"""
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)

            articles = data['articles']

            # Apply filters
            if stock_symbol:
                articles = [a for a in articles if stock_symbol in a.get('stock_symbols', [])]

            if start_date:
                articles = [a for a in articles
                           if datetime.fromisoformat(a['published_date']) >= start_date]

            if end_date:
                articles = [a for a in articles
                           if datetime.fromisoformat(a['published_date']) <= end_date]

            # Sort by published date
            articles.sort(key=lambda x: x.get('published_date', ''), reverse=True)

            # Apply limit
            if limit:
                articles = articles[:limit]

            return articles

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error retrieving articles from JSON: {str(e)}")
            return []

    def get_sentiment_stats(self, stock_symbol=None, days=7):
        """
        Get sentiment statistics for a time period

        Args:
            stock_symbol (str): Filter by stock symbol
            days (int): Number of days to look back

        Returns:
            dict: Statistics dictionary
        """
        start_date = datetime.now() - timedelta(days=days)
        articles = self.get_articles(stock_symbol, start_date=start_date)

        if not articles:
            return {}

        # Calculate statistics
        total = len(articles)
        positive = sum(1 for a in articles if a.get('sentiment') == 'positive')
        negative = sum(1 for a in articles if a.get('sentiment') == 'negative')
        neutral = sum(1 for a in articles if a.get('sentiment') == 'neutral')

        compound_scores = [a.get('compound_score', 0) for a in articles]
        avg_compound = sum(compound_scores) / len(compound_scores) if compound_scores else 0

        return {
            'stock_symbol': stock_symbol,
            'period_days': days,
            'total_articles': total,
            'positive_count': positive,
            'negative_count': negative,
            'neutral_count': neutral,
            'positive_percentage': (positive / total * 100) if total > 0 else 0,
            'negative_percentage': (negative / total * 100) if total > 0 else 0,
            'neutral_percentage': (neutral / total * 100) if total > 0 else 0,
            'average_compound_score': avg_compound
        }

    def cleanup_old_data(self, days=30):
        """
        Remove data older than specified days

        Args:
            days (int): Number of days to keep

        Returns:
            int: Number of records deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        if self.storage_type == 'sqlite':
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM articles WHERE published_date < ?", (cutoff_date,))
            deleted = cursor.rowcount

            conn.commit()
            conn.close()

            if self.logger:
                self.logger.info(f"Cleaned up {deleted} old articles from database")

            return deleted

        elif self.storage_type == 'json':
            with open(self.json_path, 'r') as f:
                data = json.load(f)

            original_count = len(data['articles'])
            data['articles'] = [
                a for a in data['articles']
                if datetime.fromisoformat(a['published_date']) >= cutoff_date
            ]

            deleted = original_count - len(data['articles'])

            with open(self.json_path, 'w') as f:
                json.dump(data, f, indent=2)

            if self.logger:
                self.logger.info(f"Cleaned up {deleted} old articles from JSON")

            return deleted
