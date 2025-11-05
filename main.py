#!/usr/bin/env python3
"""
Stock Sentiment Analysis System
Main entry point for the application
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils import ConfigLoader, setup_logger
from src.collectors import NewsCollector
from src.analyzers import SentimentAnalyzer
from src.storage import DataStorage
from src.visualizers import SentimentVisualizer


def collect_and_analyze(config, logger):
    """
    Collect news and perform sentiment analysis

    Args:
        config: ConfigLoader instance
        logger: Logger instance
    """
    logger.info("=" * 50)
    logger.info("Starting sentiment analysis collection")
    logger.info("=" * 50)

    # Initialize components
    collector = NewsCollector(logger=logger)

    sentiment_config = config.get_sentiment_config()
    analyzer = SentimentAnalyzer(
        analyzer_type=sentiment_config.get('analyzer', 'vader'),
        logger=logger
    )

    storage_config = config.get_storage_config()
    storage = DataStorage(
        storage_type=storage_config.get('type', 'sqlite'),
        db_path=storage_config.get('sqlite_path', 'data/sentiment.db'),
        json_path=storage_config.get('json_path', 'data/sentiment_data.json'),
        logger=logger
    )

    # Get configuration
    stock_symbols = config.get_stock_symbols()
    news_sources = config.get_news_sources()
    max_articles = config.get('data_collection.max_articles_per_source', 20)

    logger.info(f"Tracking stocks: {', '.join(stock_symbols)}")
    logger.info(f"Collecting from {len(news_sources)} news sources")

    # Collect articles
    articles = collector.collect_from_sources(
        news_sources,
        stock_symbols=stock_symbols,
        max_articles_per_source=max_articles
    )

    if not articles:
        logger.warning("No articles collected")
        return

    logger.info(f"Collected {len(articles)} relevant articles")

    # Analyze sentiment
    analyzed_articles = analyzer.analyze_articles(articles)

    # Save to storage
    saved_count = storage.save_articles(analyzed_articles)
    logger.info(f"Saved {saved_count} new articles to storage")

    # Display summary
    summary = analyzer.get_sentiment_summary(analyzed_articles)
    logger.info("\n" + "=" * 50)
    logger.info("OVERALL SENTIMENT SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total articles analyzed: {summary['total_articles']}")
    logger.info(f"Positive: {summary['positive_count']} ({summary['positive_percentage']:.1f}%)")
    logger.info(f"Negative: {summary['negative_count']} ({summary['negative_percentage']:.1f}%)")
    logger.info(f"Neutral: {summary['neutral_count']} ({summary['neutral_percentage']:.1f}%)")
    logger.info(f"Average compound score: {summary['average_compound_score']:.3f}")
    logger.info(f"Overall sentiment: {summary['overall_sentiment'].upper()}")

    # Display per-stock summary
    logger.info("\n" + "=" * 50)
    logger.info("PER-STOCK SENTIMENT SUMMARY")
    logger.info("=" * 50)
    for symbol in stock_symbols:
        stock_summary = analyzer.get_stock_sentiment(analyzed_articles, symbol)
        if stock_summary['total_articles'] > 0:
            logger.info(f"\n{symbol}:")
            logger.info(f"  Articles: {stock_summary['total_articles']}")
            logger.info(f"  Positive: {stock_summary['positive_count']} ({stock_summary['positive_percentage']:.1f}%)")
            logger.info(f"  Negative: {stock_summary['negative_count']} ({stock_summary['negative_percentage']:.1f}%)")
            logger.info(f"  Avg Score: {stock_summary['average_compound_score']:.3f}")
            logger.info(f"  Sentiment: {stock_summary['overall_sentiment'].upper()}")

    logger.info("\n" + "=" * 50)
    logger.info("Collection and analysis completed")
    logger.info("=" * 50)


def visualize(config, logger, days=7):
    """
    Generate visualizations

    Args:
        config: ConfigLoader instance
        logger: Logger instance
        days: Number of days to analyze
    """
    logger.info("=" * 50)
    logger.info("Generating visualizations")
    logger.info("=" * 50)

    # Initialize components
    storage_config = config.get_storage_config()
    storage = DataStorage(
        storage_type=storage_config.get('type', 'sqlite'),
        db_path=storage_config.get('sqlite_path', 'data/sentiment.db'),
        json_path=storage_config.get('json_path', 'data/sentiment_data.json'),
        logger=logger
    )

    viz_config = config.get_visualization_config()
    visualizer = SentimentVisualizer(
        output_dir=viz_config.get('output_dir', 'data/charts'),
        logger=logger
    )

    stock_symbols = config.get_stock_symbols()

    # Generate report
    charts = visualizer.generate_report(storage, stock_symbols, days=days)

    logger.info("\nGenerated charts:")
    for name, path in charts.items():
        if path:
            logger.info(f"  {name}: {path}")

    logger.info("\n" + "=" * 50)
    logger.info("Visualization completed")
    logger.info("=" * 50)


def show_stats(config, logger, days=7):
    """
    Show statistics from stored data

    Args:
        config: ConfigLoader instance
        logger: Logger instance
        days: Number of days to analyze
    """
    logger.info("=" * 50)
    logger.info(f"Statistics for last {days} days")
    logger.info("=" * 50)

    # Initialize storage
    storage_config = config.get_storage_config()
    storage = DataStorage(
        storage_type=storage_config.get('type', 'sqlite'),
        db_path=storage_config.get('sqlite_path', 'data/sentiment.db'),
        json_path=storage_config.get('json_path', 'data/sentiment_data.json'),
        logger=logger
    )

    stock_symbols = config.get_stock_symbols()

    for symbol in stock_symbols:
        stats = storage.get_sentiment_stats(symbol, days=days)
        if stats and stats['total_articles'] > 0:
            logger.info(f"\n{symbol}:")
            logger.info(f"  Total articles: {stats['total_articles']}")
            logger.info(f"  Positive: {stats['positive_count']} ({stats['positive_percentage']:.1f}%)")
            logger.info(f"  Negative: {stats['negative_count']} ({stats['negative_percentage']:.1f}%)")
            logger.info(f"  Neutral: {stats['neutral_count']} ({stats['neutral_percentage']:.1f}%)")
            logger.info(f"  Average score: {stats['average_compound_score']:.3f}")
        else:
            logger.info(f"\n{symbol}: No data available")

    logger.info("\n" + "=" * 50)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Stock Sentiment Analysis System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect and analyze news
  python main.py collect

  # Generate visualizations
  python main.py visualize

  # Show statistics
  python main.py stats

  # Show statistics for last 30 days
  python main.py stats --days 30

  # Generate visualizations for last 14 days
  python main.py visualize --days 14
        """
    )

    parser.add_argument(
        'command',
        choices=['collect', 'visualize', 'stats', 'all'],
        help='Command to execute'
    )

    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days for analysis (default: 7)'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = ConfigLoader(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1

    # Setup logger
    log_config = config.get('logging', {})
    logger = setup_logger(
        name='stock_sentiment',
        log_file=log_config.get('file', 'data/sentiment_analysis.log'),
        level=log_config.get('level', 'INFO'),
        console=log_config.get('console', True)
    )

    # Execute command
    try:
        if args.command == 'collect':
            collect_and_analyze(config, logger)
        elif args.command == 'visualize':
            visualize(config, logger, days=args.days)
        elif args.command == 'stats':
            show_stats(config, logger, days=args.days)
        elif args.command == 'all':
            collect_and_analyze(config, logger)
            visualize(config, logger, days=args.days)
            show_stats(config, logger, days=args.days)

        return 0

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
