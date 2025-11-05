"""
Sentiment Visualizer
Creates visualizations for sentiment analysis data
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from collections import defaultdict


class SentimentVisualizer:
    """Creates charts and visualizations for sentiment data"""

    def __init__(self, output_dir='data/charts', logger=None):
        """
        Initialize the visualizer

        Args:
            output_dir (str): Directory to save charts
            logger: Logger instance
        """
        self.output_dir = output_dir
        self.logger = logger

        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')

    def plot_sentiment_timeline(self, articles, stock_symbol=None, save=True):
        """
        Plot sentiment over time

        Args:
            articles (list): List of articles
            stock_symbol (str): Stock symbol for title
            save (bool): Whether to save the plot

        Returns:
            str: Path to saved figure (if saved)
        """
        if not articles:
            if self.logger:
                self.logger.warning("No articles to plot")
            return None

        # Prepare data
        dates = []
        compounds = []

        for article in articles:
            pub_date = article.get('published_date')
            if isinstance(pub_date, str):
                pub_date = datetime.fromisoformat(pub_date)

            compound = article.get('compound_score', 0)

            dates.append(pub_date)
            compounds.append(compound)

        # Create DataFrame for easier manipulation
        df = pd.DataFrame({'date': dates, 'compound': compounds})
        df = df.sort_values('date')

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot compound scores
        ax.plot(df['date'], df['compound'], marker='o', linestyle='-',
                linewidth=1, markersize=4, alpha=0.6, label='Compound Score')

        # Add horizontal lines for sentiment thresholds
        ax.axhline(y=0.05, color='green', linestyle='--', alpha=0.3, label='Positive Threshold')
        ax.axhline(y=-0.05, color='red', linestyle='--', alpha=0.3, label='Negative Threshold')
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

        # Add rolling average
        if len(df) >= 3:
            df['rolling_avg'] = df['compound'].rolling(window=min(5, len(df))).mean()
            ax.plot(df['date'], df['rolling_avg'], linewidth=2,
                   color='blue', label='Rolling Average', alpha=0.7)

        # Formatting
        title = f"Sentiment Timeline"
        if stock_symbol:
            title += f" - {stock_symbol}"

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Sentiment Score', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save:
            filename = f"sentiment_timeline_{stock_symbol or 'all'}_{datetime.now().strftime('%Y%m%d')}.png"
            filepath = Path(self.output_dir) / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            if self.logger:
                self.logger.info(f"Saved sentiment timeline to {filepath}")
            plt.close()
            return str(filepath)
        else:
            plt.show()
            return None

    def plot_sentiment_distribution(self, articles, stock_symbol=None, save=True):
        """
        Plot distribution of sentiments

        Args:
            articles (list): List of articles
            stock_symbol (str): Stock symbol for title
            save (bool): Whether to save the plot

        Returns:
            str: Path to saved figure (if saved)
        """
        if not articles:
            if self.logger:
                self.logger.warning("No articles to plot")
            return None

        # Count sentiments
        sentiments = [a.get('sentiment', 'neutral') for a in articles]
        positive = sentiments.count('positive')
        negative = sentiments.count('negative')
        neutral = sentiments.count('neutral')

        # Create plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Pie chart
        sizes = [positive, negative, neutral]
        labels = [f'Positive\n({positive})', f'Negative\n({negative})', f'Neutral\n({neutral})']
        colors = ['#2ecc71', '#e74c3c', '#95a5a6']
        explode = (0.05, 0.05, 0)

        ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
        ax1.axis('equal')

        title = "Sentiment Distribution"
        if stock_symbol:
            title += f" - {stock_symbol}"
        ax1.set_title(title, fontsize=14, fontweight='bold')

        # Bar chart
        categories = ['Positive', 'Negative', 'Neutral']
        counts = [positive, negative, neutral]

        bars = ax2.bar(categories, counts, color=colors, alpha=0.7, edgecolor='black')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold')

        ax2.set_title("Sentiment Counts", fontsize=14, fontweight='bold')
        ax2.set_ylabel('Number of Articles', fontsize=12)
        ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        if save:
            filename = f"sentiment_distribution_{stock_symbol or 'all'}_{datetime.now().strftime('%Y%m%d')}.png"
            filepath = Path(self.output_dir) / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            if self.logger:
                self.logger.info(f"Saved sentiment distribution to {filepath}")
            plt.close()
            return str(filepath)
        else:
            plt.show()
            return None

    def plot_stock_comparison(self, storage, stock_symbols, days=7, save=True):
        """
        Compare sentiment across multiple stocks

        Args:
            storage: DataStorage instance
            stock_symbols (list): List of stock symbols
            days (int): Number of days to analyze
            save (bool): Whether to save the plot

        Returns:
            str: Path to saved figure (if saved)
        """
        if not stock_symbols:
            if self.logger:
                self.logger.warning("No stock symbols provided")
            return None

        # Collect data for each stock
        stock_data = {}
        for symbol in stock_symbols:
            stats = storage.get_sentiment_stats(symbol, days=days)
            if stats:
                stock_data[symbol] = stats

        if not stock_data:
            if self.logger:
                self.logger.warning("No data for stock comparison")
            return None

        # Create plot
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        symbols = list(stock_data.keys())

        # 1. Average compound scores
        avg_scores = [stock_data[s]['average_compound_score'] for s in symbols]
        colors = ['green' if s > 0.05 else 'red' if s < -0.05 else 'gray' for s in avg_scores]

        bars = ax1.bar(symbols, avg_scores, color=colors, alpha=0.7, edgecolor='black')
        ax1.axhline(y=0.05, color='green', linestyle='--', alpha=0.3)
        ax1.axhline(y=-0.05, color='red', linestyle='--', alpha=0.3)
        ax1.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        ax1.set_title('Average Sentiment Score by Stock', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Compound Score', fontsize=10)
        ax1.grid(axis='y', alpha=0.3)

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}',
                    ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)

        # 2. Article counts
        article_counts = [stock_data[s]['total_articles'] for s in symbols]
        ax2.bar(symbols, article_counts, color='steelblue', alpha=0.7, edgecolor='black')
        ax2.set_title('Number of Articles by Stock', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Article Count', fontsize=10)
        ax2.grid(axis='y', alpha=0.3)

        # 3. Sentiment distribution (stacked bar)
        positive_pcts = [stock_data[s]['positive_percentage'] for s in symbols]
        negative_pcts = [stock_data[s]['negative_percentage'] for s in symbols]
        neutral_pcts = [stock_data[s]['neutral_percentage'] for s in symbols]

        x = range(len(symbols))
        ax3.bar(x, positive_pcts, label='Positive', color='#2ecc71', alpha=0.7)
        ax3.bar(x, negative_pcts, bottom=positive_pcts, label='Negative',
               color='#e74c3c', alpha=0.7)
        ax3.bar(x, neutral_pcts,
               bottom=[p+n for p, n in zip(positive_pcts, negative_pcts)],
               label='Neutral', color='#95a5a6', alpha=0.7)

        ax3.set_xticks(x)
        ax3.set_xticklabels(symbols)
        ax3.set_title('Sentiment Distribution by Stock (%)', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Percentage', fontsize=10)
        ax3.legend(loc='best')
        ax3.grid(axis='y', alpha=0.3)

        # 4. Summary table
        ax4.axis('tight')
        ax4.axis('off')

        table_data = []
        for symbol in symbols:
            data = stock_data[symbol]
            table_data.append([
                symbol,
                data['total_articles'],
                f"{data['average_compound_score']:.3f}",
                f"{data['positive_percentage']:.1f}%",
                f"{data['negative_percentage']:.1f}%"
            ])

        table = ax4.table(cellText=table_data,
                         colLabels=['Stock', 'Articles', 'Avg Score', 'Positive', 'Negative'],
                         cellLoc='center',
                         loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)

        # Color code the average scores
        for i, score in enumerate(avg_scores):
            if score > 0.05:
                table[(i+1, 2)].set_facecolor('#d5f4e6')
            elif score < -0.05:
                table[(i+1, 2)].set_facecolor('#fadbd8')

        ax4.set_title('Summary Statistics', fontsize=12, fontweight='bold', pad=20)

        plt.suptitle(f'Stock Sentiment Comparison (Last {days} Days)',
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()

        if save:
            filename = f"stock_comparison_{datetime.now().strftime('%Y%m%d')}.png"
            filepath = Path(self.output_dir) / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            if self.logger:
                self.logger.info(f"Saved stock comparison to {filepath}")
            plt.close()
            return str(filepath)
        else:
            plt.show()
            return None

    def generate_report(self, storage, stock_symbols, days=7):
        """
        Generate a comprehensive visualization report

        Args:
            storage: DataStorage instance
            stock_symbols (list): List of stock symbols
            days (int): Number of days to analyze

        Returns:
            dict: Dictionary of generated chart paths
        """
        charts = {}

        if self.logger:
            self.logger.info("Generating visualization report...")

        # Generate comparison chart
        comparison_path = self.plot_stock_comparison(storage, stock_symbols, days)
        if comparison_path:
            charts['comparison'] = comparison_path

        # Generate individual stock charts
        start_date = datetime.now() - timedelta(days=days)
        for symbol in stock_symbols:
            articles = storage.get_articles(stock_symbol=symbol, start_date=start_date)
            if articles:
                timeline_path = self.plot_sentiment_timeline(articles, symbol)
                dist_path = self.plot_sentiment_distribution(articles, symbol)

                charts[f'{symbol}_timeline'] = timeline_path
                charts[f'{symbol}_distribution'] = dist_path

        if self.logger:
            self.logger.info(f"Generated {len(charts)} visualization charts")

        return charts
