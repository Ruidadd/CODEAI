from setuptools import setup, find_packages

setup(
    name="huaqiangbei-monitor",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "sqlalchemy>=2.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "tenacity>=8.2.0",
        "schedule>=1.2.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "monitor=huaqiangbei_monitor.cli:main",
        ],
    },
    python_requires=">=3.10",
)
