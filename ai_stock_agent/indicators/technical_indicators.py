"""
Technical indicators calculation module
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from loguru import logger


class TechnicalIndicators:
    """
    Calculate various technical indicators for stock analysis
    """

    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
        """
        Calculate Moving Averages

        Args:
            df: DataFrame with OHLCV data
            periods: List of MA periods

        Returns:
            DataFrame with MA columns added
        """
        df = df.copy()

        for period in periods:
            col_name = f"ma{period}"
            df[col_name] = df["close"].rolling(window=period).mean()

        logger.debug(f"Calculated MA for periods: {periods}")
        return df

    @staticmethod
    def calculate_volume_ma(df: pd.DataFrame, period: int = 5) -> pd.DataFrame:
        """
        Calculate Volume Moving Average

        Args:
            df: DataFrame with volume data
            period: MA period

        Returns:
            DataFrame with volume MA column added
        """
        df = df.copy()
        df[f"volume_ma{period}"] = df["volume"].rolling(window=period).mean()

        logger.debug(f"Calculated volume MA{period}")
        return df

    @staticmethod
    def calculate_amplitude(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate daily amplitude (振幅)
        Amplitude = (High - Low) / Pre_Close * 100

        Args:
            df: DataFrame with OHLC data

        Returns:
            DataFrame with amplitude column
        """
        df = df.copy()

        # If amplitude not already in data, calculate it
        if "amplitude" not in df.columns:
            df["pre_close"] = df["close"].shift(1)
            df["amplitude"] = ((df["high"] - df["low"]) / df["pre_close"] * 100).round(2)

        logger.debug("Calculated amplitude")
        return df

    @staticmethod
    def calculate_volume_ratio(df: pd.DataFrame, period: int = 5) -> pd.DataFrame:
        """
        Calculate volume ratio (量比)
        Volume Ratio = Current Volume / Average Volume

        Args:
            df: DataFrame with volume data
            period: Period for average volume calculation

        Returns:
            DataFrame with volume ratio column
        """
        df = df.copy()

        df[f"volume_ma{period}"] = df["volume"].rolling(window=period).mean()
        df["volume_ratio"] = (df["volume"] / df[f"volume_ma{period}"]).round(2)

        logger.debug(f"Calculated volume ratio with period {period}")
        return df

    @staticmethod
    def calculate_price_change(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate price change and percentage change

        Args:
            df: DataFrame with close price data

        Returns:
            DataFrame with price change columns
        """
        df = df.copy()

        # If not already calculated
        if "pct_change" not in df.columns:
            df["change"] = df["close"] - df["close"].shift(1)
            df["pct_change"] = (df["change"] / df["close"].shift(1) * 100).round(2)

        logger.debug("Calculated price change")
        return df

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> pd.DataFrame:
        """
        Calculate MACD indicator

        Args:
            df: DataFrame with close price data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period

        Returns:
            DataFrame with MACD columns
        """
        df = df.copy()

        # Calculate EMAs
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

        # Calculate MACD line
        df["macd"] = ema_fast - ema_slow

        # Calculate signal line
        df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()

        # Calculate histogram
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        logger.debug(f"Calculated MACD({fast},{slow},{signal})")
        return df

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate RSI (Relative Strength Index)

        Args:
            df: DataFrame with close price data
            period: RSI period

        Returns:
            DataFrame with RSI column
        """
        df = df.copy()

        # Calculate price changes
        delta = df["close"].diff()

        # Separate gains and losses
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # Calculate RS and RSI
        rs = gain / loss
        df[f"rsi{period}"] = 100 - (100 / (1 + rs))

        logger.debug(f"Calculated RSI({period})")
        return df

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame, period: int = 20, std_dev: int = 2
    ) -> pd.DataFrame:
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with close price data
            period: MA period
            std_dev: Number of standard deviations

        Returns:
            DataFrame with Bollinger Bands columns
        """
        df = df.copy()

        # Calculate middle band (SMA)
        df["bb_middle"] = df["close"].rolling(window=period).mean()

        # Calculate standard deviation
        std = df["close"].rolling(window=period).std()

        # Calculate upper and lower bands
        df["bb_upper"] = df["bb_middle"] + (std * std_dev)
        df["bb_lower"] = df["bb_middle"] - (std * std_dev)

        logger.debug(f"Calculated Bollinger Bands({period},{std_dev})")
        return df

    @staticmethod
    def calculate_all_indicators(
        df: pd.DataFrame, ma_periods: List[int] = [5, 10, 20, 60]
    ) -> pd.DataFrame:
        """
        Calculate all technical indicators

        Args:
            df: DataFrame with OHLCV data
            ma_periods: List of MA periods

        Returns:
            DataFrame with all indicators
        """
        logger.info("Calculating all technical indicators")

        df = TechnicalIndicators.calculate_ma(df, ma_periods)
        df = TechnicalIndicators.calculate_volume_ma(df)
        df = TechnicalIndicators.calculate_amplitude(df)
        df = TechnicalIndicators.calculate_volume_ratio(df)
        df = TechnicalIndicators.calculate_price_change(df)
        df = TechnicalIndicators.calculate_macd(df)
        df = TechnicalIndicators.calculate_rsi(df)
        df = TechnicalIndicators.calculate_bollinger_bands(df)

        logger.info("All technical indicators calculated successfully")
        return df

    @staticmethod
    def get_latest_indicators(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get latest indicator values

        Args:
            df: DataFrame with calculated indicators

        Returns:
            Dictionary with latest indicator values
        """
        if df.empty:
            return {}

        latest = df.iloc[-1]

        indicators = {
            "date": latest.get("date", ""),
            "close": latest.get("close", 0),
            "open": latest.get("open", 0),
            "high": latest.get("high", 0),
            "low": latest.get("low", 0),
            "volume": latest.get("volume", 0),
            "pct_change": latest.get("pct_change", 0),
            "amplitude": latest.get("amplitude", 0),
            "volume_ratio": latest.get("volume_ratio", 0),
            "ma5": latest.get("ma5", 0),
            "ma10": latest.get("ma10", 0),
            "ma20": latest.get("ma20", 0),
            "ma60": latest.get("ma60", 0),
            "macd": latest.get("macd", 0),
            "macd_signal": latest.get("macd_signal", 0),
            "macd_hist": latest.get("macd_hist", 0),
            "rsi14": latest.get("rsi14", 0),
            "bb_upper": latest.get("bb_upper", 0),
            "bb_middle": latest.get("bb_middle", 0),
            "bb_lower": latest.get("bb_lower", 0),
        }

        return indicators
