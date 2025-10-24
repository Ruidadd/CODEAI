"""
Stock selection strategy module based on technical indicators
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from loguru import logger

from ..data.data_fetcher import DataFetcher
from ..indicators.technical_indicators import TechnicalIndicators
from ..indicators.volume_price import VolumePriceAnalyzer


class StockSelector:
    """
    Select stocks based on volume-price relationship and technical indicators
    """

    def __init__(
        self,
        min_volume_ratio: float = 1.5,
        min_amplitude: float = 3.0,
        max_amplitude: float = 15.0,
    ):
        """
        Initialize StockSelector

        Args:
            min_volume_ratio: Minimum volume ratio threshold
            min_amplitude: Minimum amplitude threshold (%)
            max_amplitude: Maximum amplitude threshold (%)
        """
        self.min_volume_ratio = min_volume_ratio
        self.min_amplitude = min_amplitude
        self.max_amplitude = max_amplitude
        self.data_fetcher = DataFetcher()

        logger.info(
            f"Initialized StockSelector with volume_ratio>={min_volume_ratio}, "
            f"amplitude: {min_amplitude}-{max_amplitude}%"
        )

    def filter_by_volume_amplitude(self, stocks_df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter stocks by volume ratio and amplitude

        Args:
            stocks_df: DataFrame with stock data

        Returns:
            Filtered DataFrame
        """
        filtered = stocks_df.copy()

        # Calculate volume ratio if not present
        if "volume_ratio" not in filtered.columns:
            # Use a simple heuristic: compare with average
            avg_volume = filtered["volume"].mean()
            filtered["volume_ratio"] = filtered["volume"] / avg_volume

        # Filter by volume ratio
        filtered = filtered[filtered["volume_ratio"] >= self.min_volume_ratio]

        # Filter by amplitude
        filtered = filtered[
            (filtered["amplitude"] >= self.min_amplitude)
            & (filtered["amplitude"] <= self.max_amplitude)
        ]

        logger.info(
            f"Filtered {len(filtered)} stocks from {len(stocks_df)} "
            f"based on volume and amplitude criteria"
        )

        return filtered

    def filter_by_price_trend(
        self, stocks_df: pd.DataFrame, trend: str = "up"
    ) -> pd.DataFrame:
        """
        Filter stocks by price trend

        Args:
            stocks_df: DataFrame with stock data
            trend: 'up' or 'down'

        Returns:
            Filtered DataFrame
        """
        filtered = stocks_df.copy()

        if trend == "up":
            filtered = filtered[filtered["pct_change"] > 0]
        elif trend == "down":
            filtered = filtered[filtered["pct_change"] < 0]

        logger.info(f"Filtered {len(filtered)} stocks with {trend} trend")

        return filtered

    def rank_stocks(
        self, stocks_df: pd.DataFrame, by: str = "volume_ratio", top_n: int = 20
    ) -> pd.DataFrame:
        """
        Rank and select top N stocks

        Args:
            stocks_df: DataFrame with stock data
            by: Column to rank by
            top_n: Number of top stocks to return

        Returns:
            Top N stocks DataFrame
        """
        if by not in stocks_df.columns:
            logger.warning(f"Column '{by}' not found, returning unsorted results")
            return stocks_df.head(top_n)

        ranked = stocks_df.sort_values(by=by, ascending=False).head(top_n)

        logger.info(f"Selected top {len(ranked)} stocks ranked by {by}")

        return ranked

    def select_stocks(
        self,
        market: str = "A",
        price_trend: Optional[str] = "up",
        rank_by: str = "volume_ratio",
        top_n: int = 20,
    ) -> pd.DataFrame:
        """
        Select stocks based on multiple criteria

        Args:
            market: Market type
            price_trend: Price trend filter ('up', 'down', or None)
            rank_by: Column to rank by
            top_n: Number of stocks to return

        Returns:
            Selected stocks DataFrame
        """
        logger.info(f"Starting stock selection for {market} market")

        # Get all stocks
        all_stocks = self.data_fetcher.get_stock_list(market=market)

        # Filter by volume and amplitude
        filtered = self.filter_by_volume_amplitude(all_stocks)

        # Filter by price trend if specified
        if price_trend:
            filtered = self.filter_by_price_trend(filtered, trend=price_trend)

        # Rank and select top N
        selected = self.rank_stocks(filtered, by=rank_by, top_n=top_n)

        logger.info(f"Stock selection completed: {len(selected)} stocks selected")

        return selected

    def analyze_stock_with_history(
        self, stock_code: str, days: int = 60
    ) -> Dict[str, Any]:
        """
        Analyze a stock with historical data and technical indicators

        Args:
            stock_code: Stock code
            days: Number of days of historical data

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing stock {stock_code} with {days} days history")

        try:
            # Fetch historical data
            from datetime import datetime, timedelta

            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            df = self.data_fetcher.get_stock_kline(
                stock_code=stock_code, start_date=start_date, end_date=end_date
            )

            if df.empty:
                logger.warning(f"No data found for stock {stock_code}")
                return {"error": "No data found"}

            # Calculate technical indicators
            df = TechnicalIndicators.calculate_all_indicators(df)

            # Volume-price analysis
            df = VolumePriceAnalyzer.analyze_volume_price_trend(df)
            df = VolumePriceAnalyzer.identify_volume_breakout(df)
            df = VolumePriceAnalyzer.analyze_price_volume_divergence(df)
            df = VolumePriceAnalyzer.calculate_obv(df)

            # Get latest indicators
            latest_indicators = TechnicalIndicators.get_latest_indicators(df)

            # Get volume-price signal
            vp_signal = VolumePriceAnalyzer.get_volume_price_signal(df)

            # Compile analysis result
            analysis = {
                "stock_code": stock_code,
                "analysis_date": latest_indicators.get("date", ""),
                "latest_price": latest_indicators.get("close", 0),
                "pct_change": latest_indicators.get("pct_change", 0),
                "amplitude": latest_indicators.get("amplitude", 0),
                "volume_ratio": latest_indicators.get("volume_ratio", 0),
                "indicators": latest_indicators,
                "volume_price_signal": vp_signal,
                "historical_data": df.tail(10).to_dict("records"),  # Last 10 days
                "full_dataframe": df,  # For further analysis
            }

            logger.info(f"Analysis completed for {stock_code}")

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing stock {stock_code}: {e}")
            return {"error": str(e)}

    def batch_analyze_stocks(
        self, stock_codes: List[str], days: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Batch analyze multiple stocks

        Args:
            stock_codes: List of stock codes
            days: Number of days of historical data

        Returns:
            List of analysis results
        """
        logger.info(f"Batch analyzing {len(stock_codes)} stocks")

        results = []
        for code in stock_codes:
            try:
                analysis = self.analyze_stock_with_history(code, days=days)
                if "error" not in analysis:
                    results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {code}: {e}")
                continue

        logger.info(f"Batch analysis completed: {len(results)} successful")

        return results

    def get_buy_candidates(
        self, market: str = "A", top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top buy candidates with detailed analysis

        Args:
            market: Market type
            top_n: Number of candidates to return

        Returns:
            List of buy candidates with analysis
        """
        logger.info(f"Finding top {top_n} buy candidates")

        # Select stocks
        selected_stocks = self.select_stocks(
            market=market, price_trend="up", rank_by="volume_ratio", top_n=top_n * 2
        )

        # Analyze each stock
        candidates = []
        for _, stock in selected_stocks.iterrows():
            code = stock["code"]
            analysis = self.analyze_stock_with_history(code, days=60)

            if "error" not in analysis:
                # Check if it's a strong buy signal
                vp_signal = analysis.get("volume_price_signal", {})
                if vp_signal.get("signal") in ["buy", "strong_buy"]:
                    candidates.append(analysis)

                    if len(candidates) >= top_n:
                        break

        logger.info(f"Found {len(candidates)} buy candidates")

        return candidates
