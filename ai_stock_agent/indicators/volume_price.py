"""
Volume-Price relationship analysis module
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from loguru import logger


class VolumePriceAnalyzer:
    """
    Analyze volume-price relationships for trading signals
    """

    @staticmethod
    def analyze_volume_price_trend(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Analyze volume-price trend relationship

        Args:
            df: DataFrame with OHLCV data
            window: Window for trend analysis

        Returns:
            DataFrame with volume-price analysis columns
        """
        df = df.copy()

        # Price trend
        df["price_trend"] = df["close"].diff(window)

        # Volume trend
        df["volume_trend"] = df["volume"].diff(window)

        # Volume-price relationship
        df["vp_relation"] = np.where(
            (df["price_trend"] > 0) & (df["volume_trend"] > 0),
            "price_up_volume_up",  # 价涨量增 (bullish)
            np.where(
                (df["price_trend"] > 0) & (df["volume_trend"] < 0),
                "price_up_volume_down",  # 价涨量缩 (weak bullish)
                np.where(
                    (df["price_trend"] < 0) & (df["volume_trend"] > 0),
                    "price_down_volume_up",  # 价跌量增 (bearish)
                    np.where(
                        (df["price_trend"] < 0) & (df["volume_trend"] < 0),
                        "price_down_volume_down",  # 价跌量缩 (weak bearish)
                        "neutral",
                    ),
                ),
            ),
        )

        logger.debug(f"Analyzed volume-price trend with window={window}")
        return df

    @staticmethod
    def identify_volume_breakout(df: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
        """
        Identify volume breakouts

        Args:
            df: DataFrame with volume data
            threshold: Volume ratio threshold for breakout

        Returns:
            DataFrame with breakout signals
        """
        df = df.copy()

        # Calculate volume moving average
        df["volume_ma20"] = df["volume"].rolling(window=20).mean()

        # Volume ratio
        df["volume_ratio"] = df["volume"] / df["volume_ma20"]

        # Breakout signal
        df["volume_breakout"] = df["volume_ratio"] > threshold

        logger.debug(f"Identified volume breakouts with threshold={threshold}")
        return df

    @staticmethod
    def analyze_price_volume_divergence(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
        """
        Analyze price-volume divergence

        Args:
            df: DataFrame with OHLCV data
            window: Window for divergence analysis

        Returns:
            DataFrame with divergence signals
        """
        df = df.copy()

        # Price momentum
        df["price_momentum"] = df["close"].pct_change(window)

        # Volume momentum
        df["volume_momentum"] = df["volume"].pct_change(window)

        # Divergence detection
        df["divergence"] = np.where(
            (df["price_momentum"] > 0) & (df["volume_momentum"] < -0.2),
            "bearish_divergence",  # Price up but volume down significantly
            np.where(
                (df["price_momentum"] < 0) & (df["volume_momentum"] > 0.2),
                "bullish_divergence",  # Price down but volume up significantly
                "no_divergence",
            ),
        )

        logger.debug(f"Analyzed price-volume divergence with window={window}")
        return df

    @staticmethod
    def calculate_accumulation_distribution(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Accumulation/Distribution indicator

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with A/D indicator
        """
        df = df.copy()

        # Money Flow Multiplier
        mf_multiplier = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (
            df["high"] - df["low"]
        )

        # Money Flow Volume
        mf_volume = mf_multiplier * df["volume"]

        # Accumulation/Distribution Line
        df["ad_line"] = mf_volume.cumsum()

        logger.debug("Calculated Accumulation/Distribution indicator")
        return df

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate On-Balance Volume (OBV)

        Args:
            df: DataFrame with close price and volume data

        Returns:
            DataFrame with OBV indicator
        """
        df = df.copy()

        # Price change direction
        price_change = df["close"].diff()

        # OBV calculation
        obv = []
        obv_value = 0

        for i in range(len(df)):
            if i == 0:
                obv.append(df["volume"].iloc[i])
            else:
                if price_change.iloc[i] > 0:
                    obv_value += df["volume"].iloc[i]
                elif price_change.iloc[i] < 0:
                    obv_value -= df["volume"].iloc[i]

                obv.append(obv_value)

        df["obv"] = obv

        logger.debug("Calculated OBV")
        return df

    @staticmethod
    def get_volume_price_signal(df: pd.DataFrame) -> Dict[str, str]:
        """
        Get comprehensive volume-price signal

        Args:
            df: DataFrame with volume-price analysis

        Returns:
            Dictionary with signal interpretation
        """
        if df.empty or len(df) < 2:
            return {"signal": "insufficient_data", "strength": "none"}

        latest = df.iloc[-1]

        # Get latest volume-price relationship
        vp_relation = latest.get("vp_relation", "neutral")

        # Get volume breakout status
        volume_breakout = latest.get("volume_breakout", False)

        # Get divergence status
        divergence = latest.get("divergence", "no_divergence")

        # Determine signal
        if vp_relation == "price_up_volume_up" and volume_breakout:
            signal = "strong_buy"
            strength = "strong"
        elif vp_relation == "price_up_volume_up":
            signal = "buy"
            strength = "medium"
        elif vp_relation == "price_down_volume_down":
            signal = "hold"
            strength = "weak"
        elif vp_relation == "price_down_volume_up":
            signal = "sell"
            strength = "medium"
        elif divergence == "bearish_divergence":
            signal = "sell"
            strength = "medium"
        elif divergence == "bullish_divergence":
            signal = "buy"
            strength = "medium"
        else:
            signal = "neutral"
            strength = "weak"

        return {
            "signal": signal,
            "strength": strength,
            "vp_relation": vp_relation,
            "volume_breakout": volume_breakout,
            "divergence": divergence,
        }
