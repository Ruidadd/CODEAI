"""
Configuration Loader
Handles loading and parsing of configuration files
"""
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv


class ConfigLoader:
    """Loads and manages application configuration"""

    def __init__(self, config_path='config/config.yaml'):
        """
        Initialize the configuration loader

        Args:
            config_path (str): Path to the YAML configuration file
        """
        self.config_path = config_path
        self.config = None
        self._load_env()
        self._load_config()

    def _load_env(self):
        """Load environment variables from .env file"""
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)

    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing configuration file: {e}")

    def get(self, key, default=None):
        """
        Get a configuration value by key (supports nested keys with dot notation)

        Args:
            key (str): Configuration key (e.g., 'data_collection.stock_symbols')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def get_env(self, key, default=None):
        """
        Get an environment variable

        Args:
            key (str): Environment variable name
            default: Default value if not found

        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)

    def get_stock_symbols(self):
        """Get list of stock symbols to track"""
        return self.get('data_collection.stock_symbols', [])

    def get_news_sources(self):
        """Get list of enabled news sources"""
        sources = self.get('data_collection.news_sources', [])
        return [s for s in sources if s.get('enabled', True)]

    def get_collection_interval(self):
        """Get data collection interval in minutes"""
        return self.get('data_collection.collection_interval', 60)

    def get_storage_config(self):
        """Get storage configuration"""
        return self.get('storage', {})

    def get_sentiment_config(self):
        """Get sentiment analysis configuration"""
        return self.get('sentiment_analysis', {})

    def get_visualization_config(self):
        """Get visualization configuration"""
        return self.get('visualization', {})
