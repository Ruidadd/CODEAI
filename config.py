import os
from dotenv import load_dotenv

load_dotenv()

# arXiv categories to search
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.MA"]

# How many days back to search
LOOKBACK_DAYS = 7

# How many papers to fetch from arXiv (fetch more, rank down to 20)
MAX_FETCH_RESULTS = 300

# How many papers in the final digest
DIGEST_PAPER_COUNT = 20

# Kimi (Moonshot AI) configuration - OpenAI-compatible API
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
KIMI_BASE_URL = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
KIMI_MODEL = os.environ.get("KIMI_MODEL", "moonshot-v1-32k")

# Email configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")
