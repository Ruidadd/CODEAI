"""
Sentiment Analyzer
Analyzes sentiment of news articles using NLP techniques
"""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import re


class SentimentAnalyzer:
    """Analyzes sentiment of text using VADER or TextBlob"""

    def __init__(self, analyzer_type='vader', logger=None):
        """
        Initialize the sentiment analyzer

        Args:
            analyzer_type (str): 'vader' or 'textblob'
            logger: Logger instance
        """
        self.analyzer_type = analyzer_type.lower()
        self.logger = logger

        if self.analyzer_type == 'vader':
            self.vader = SentimentIntensityAnalyzer()
            self._enhance_vader_lexicon()
        elif self.analyzer_type == 'textblob':
            # TextBlob doesn't require initialization
            pass
        else:
            raise ValueError(f"Unknown analyzer type: {analyzer_type}")

        if self.logger:
            self.logger.info(f"Initialized {analyzer_type.upper()} sentiment analyzer")

    def _enhance_vader_lexicon(self):
        """Enhance VADER lexicon with finance-specific terms"""
        # Add financial/stock market specific terms and their sentiment scores
        financial_terms = {
            'bull': 2.5,
            'bullish': 2.5,
            'bear': -2.5,
            'bearish': -2.5,
            'rally': 2.0,
            'surge': 2.0,
            'soar': 2.5,
            'plunge': -2.5,
            'crash': -3.0,
            'tank': -2.5,
            'tumble': -2.0,
            'slide': -1.5,
            'gain': 1.5,
            'profit': 2.0,
            'loss': -2.0,
            'downturn': -2.0,
            'upturn': 2.0,
            'recovery': 2.0,
            'recession': -2.5,
            'growth': 2.0,
            'decline': -1.5,
            'strong': 1.5,
            'weak': -1.5,
            'beat': 2.0,
            'miss': -2.0,
            'outperform': 2.5,
            'underperform': -2.5,
            'upgrade': 2.0,
            'downgrade': -2.0,
            'breakthrough': 2.5,
            'innovation': 2.0,
            'disruption': 1.5,
            'scandal': -2.5,
            'investigation': -1.5,
            'lawsuit': -2.0,
            'settlement': -1.0,
            'acquisition': 1.5,
            'merger': 1.5,
            'partnership': 1.5,
            'expansion': 2.0,
            'bankruptcy': -3.0,
            'default': -2.5,
            'milestone': 2.0,
            'record-breaking': 2.5,
            'all-time high': 2.5,
            'all-time low': -2.5,
        }

        self.vader.lexicon.update(financial_terms)

    def analyze_text(self, text):
        """
        Analyze sentiment of a text

        Args:
            text (str): Text to analyze

        Returns:
            dict: Sentiment scores and classification
        """
        if not text or not text.strip():
            return self._empty_sentiment()

        if self.analyzer_type == 'vader':
            return self._analyze_vader(text)
        elif self.analyzer_type == 'textblob':
            return self._analyze_textblob(text)

    def _analyze_vader(self, text):
        """
        Analyze sentiment using VADER

        Args:
            text (str): Text to analyze

        Returns:
            dict: Sentiment scores
        """
        scores = self.vader.polarity_scores(text)

        # Classify sentiment
        compound = scores['compound']
        if compound >= 0.05:
            sentiment = 'positive'
        elif compound <= -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return {
            'sentiment': sentiment,
            'compound': compound,
            'positive': scores['pos'],
            'negative': scores['neg'],
            'neutral': scores['neu'],
            'analyzer': 'vader'
        }

    def _analyze_textblob(self, text):
        """
        Analyze sentiment using TextBlob

        Args:
            text (str): Text to analyze

        Returns:
            dict: Sentiment scores
        """
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        # Classify sentiment
        if polarity > 0.05:
            sentiment = 'positive'
        elif polarity < -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return {
            'sentiment': sentiment,
            'compound': polarity,
            'polarity': polarity,
            'subjectivity': subjectivity,
            'analyzer': 'textblob'
        }

    def _empty_sentiment(self):
        """Return empty sentiment result"""
        return {
            'sentiment': 'neutral',
            'compound': 0.0,
            'positive': 0.0,
            'negative': 0.0,
            'neutral': 1.0,
            'analyzer': self.analyzer_type
        }

    def analyze_articles(self, articles):
        """
        Analyze sentiment for a list of articles

        Args:
            articles (list): List of article dictionaries

        Returns:
            list: Articles with added sentiment analysis
        """
        analyzed_articles = []

        for article in articles:
            try:
                text = article.get('full_text', '')
                sentiment = self.analyze_text(text)

                # Add sentiment to article
                article_with_sentiment = article.copy()
                article_with_sentiment['sentiment_analysis'] = sentiment

                analyzed_articles.append(article_with_sentiment)

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error analyzing article: {str(e)}")
                # Add empty sentiment
                article_with_sentiment = article.copy()
                article_with_sentiment['sentiment_analysis'] = self._empty_sentiment()
                analyzed_articles.append(article_with_sentiment)

        if self.logger:
            self.logger.info(f"Analyzed sentiment for {len(analyzed_articles)} articles")

        return analyzed_articles

    def get_sentiment_summary(self, articles):
        """
        Get summary statistics of sentiment analysis

        Args:
            articles (list): List of analyzed articles

        Returns:
            dict: Summary statistics
        """
        if not articles:
            return {}

        sentiments = []
        compounds = []

        for article in articles:
            sentiment_data = article.get('sentiment_analysis', {})
            sentiments.append(sentiment_data.get('sentiment', 'neutral'))
            compounds.append(sentiment_data.get('compound', 0.0))

        # Count sentiments
        positive = sentiments.count('positive')
        negative = sentiments.count('negative')
        neutral = sentiments.count('neutral')
        total = len(sentiments)

        # Calculate average compound score
        avg_compound = sum(compounds) / len(compounds) if compounds else 0.0

        return {
            'total_articles': total,
            'positive_count': positive,
            'negative_count': negative,
            'neutral_count': neutral,
            'positive_percentage': (positive / total * 100) if total > 0 else 0,
            'negative_percentage': (negative / total * 100) if total > 0 else 0,
            'neutral_percentage': (neutral / total * 100) if total > 0 else 0,
            'average_compound_score': avg_compound,
            'overall_sentiment': 'positive' if avg_compound > 0.05 else 'negative' if avg_compound < -0.05 else 'neutral'
        }

    def get_stock_sentiment(self, articles, stock_symbol):
        """
        Get sentiment analysis for a specific stock

        Args:
            articles (list): List of analyzed articles
            stock_symbol (str): Stock symbol to filter for

        Returns:
            dict: Sentiment summary for the stock
        """
        # Filter articles mentioning the stock
        stock_articles = [
            a for a in articles
            if stock_symbol in a.get('stock_symbols', [])
        ]

        summary = self.get_sentiment_summary(stock_articles)
        summary['stock_symbol'] = stock_symbol

        return summary
