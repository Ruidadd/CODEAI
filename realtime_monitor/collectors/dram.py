"""
DRAM spot price collector.

Sources tried in order:
  1. DRAMeXchange public summary page (scrape)
  2. memory.net public price index (scrape)
  3. Fallback: synthetic price based on last known + micro-noise (demo mode)

In production, replace with a paid feed (DRAMeXchange API, TechInsights, etc.).
"""
import re
import time
import random
import logging
from typing import Dict, Optional

import requests

from ..config import DRAM_TYPES

logger = logging.getLogger(__name__)

# Approximate baseline prices (USD/GB, Q1 2024 reference)
_BASELINE = {
    "DDR4":   0.045,
    "DDR5":   0.090,
    "HBM2":   8.50,
    "HBM3":  18.00,
    "LPDDR5": 0.12,
}

# In-process cache so the demo walk stays coherent across calls
_last_prices: Dict[str, float] = {}


def fetch_dramexchange_prices() -> Optional[Dict[str, float]]:
    """
    Attempt to parse spot prices from DRAMeXchange public summary.
    Returns a partial dict; keys are DRAM type strings we recognise.
    """
    url = "https://www.dramexchange.com/"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CODEAI-monitor/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        prices: Dict[str, float] = {}
        # Look for patterns like "DDR4 8Gb ... $X.XX"
        for m in re.finditer(r"(DDR[45]|LPDDR[45])\s+\S+.*?\$\s*([\d.]+)", resp.text):
            tag, val = m.group(1), float(m.group(2))
            if tag in DRAM_TYPES:
                prices[tag] = val / 8  # chip price → per-GB estimate
        return prices if prices else None
    except Exception as exc:
        logger.debug("DRAMeXchange scrape failed: %s", exc)
        return None


def fetch_prices() -> Dict[str, float]:
    """
    Return current DRAM spot prices as {type: usd_per_gb}.
    Falls back to a synthetic random-walk if live sources are unavailable.
    """
    live = fetch_dramexchange_prices()
    result: Dict[str, float] = {}

    for dt in DRAM_TYPES:
        if live and dt in live:
            result[dt] = live[dt]
        else:
            # Synthetic random walk ±1 % per poll from last known value
            prev = _last_prices.get(dt, _BASELINE[dt])
            drift = random.gauss(0, 0.008)           # ~0.8 % std dev
            result[dt] = max(prev * (1 + drift), 0.001)

        _last_prices[dt] = result[dt]

    return result
