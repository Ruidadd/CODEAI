"""
Configuration management for AI Stock Agent
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for AI Stock Agent"""

    # API Configuration
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "claude-3-5-sonnet-20241022")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))

    # Data Source Configuration
    DATA_SOURCE: str = os.getenv("DATA_SOURCE", "akshare")

    # Technical Indicator Configuration
    MA_PERIODS: list = [5, 10, 20, 60]  # Moving average periods
    VOLUME_MA_PERIOD: int = 5  # Volume moving average period

    # Stock Selection Criteria
    MIN_VOLUME_RATIO: float = 1.5  # Minimum volume ratio vs average
    MIN_AMPLITUDE: float = 3.0  # Minimum amplitude percentage
    MAX_AMPLITUDE: float = 15.0  # Maximum amplitude percentage

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        return True

    @classmethod
    def get_api_key(cls) -> str:
        """Get API key"""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        return cls.ANTHROPIC_API_KEY
