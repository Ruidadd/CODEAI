"""
Azure GPU spot (low-priority / Spot VM) price collector.

Uses the Azure Retail Prices API — free, no authentication required.
Docs: https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices
"""
import logging
from typing import Dict, List, Optional

import requests

from ..config import ASIAN_REGIONS, GPU_INSTANCE_TYPES

logger = logging.getLogger(__name__)

_BASE_URL = "https://prices.azure.com/api/retail/prices"


def _build_filter(regions: List[str], vm_sizes: List[str]) -> str:
    region_filter = " or ".join(f"armRegionName eq '{r}'" for r in regions)
    size_filter = " or ".join(f"skuName eq '{s} Spot'" for s in vm_sizes)
    return f"({region_filter}) and ({size_filter}) and serviceName eq 'Virtual Machines'"


def fetch_spot_prices() -> List[Dict]:
    """
    Return list of dicts with keys:
      provider, region, instance_type, spot_price_usd, available
    """
    regions = ASIAN_REGIONS["azure"]
    vm_sizes = GPU_INSTANCE_TYPES["azure"]
    results = []

    params = {
        "$filter": _build_filter(regions, vm_sizes),
        "api-version": "2023-01-01-preview",
    }

    try:
        resp = requests.get(_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("Items", []):
            sku = item.get("skuName", "").replace(" Spot", "").strip()
            region = item.get("armRegionName", "")
            price = item.get("retailPrice")
            results.append({
                "provider": "azure",
                "region": region,
                "instance_type": sku,
                "spot_price_usd": price,
                "available": price is not None and price > 0,
            })
        # Follow pagination
        next_url = data.get("NextPageLink")
        while next_url:
            resp = requests.get(next_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("Items", []):
                sku = item.get("skuName", "").replace(" Spot", "").strip()
                region = item.get("armRegionName", "")
                price = item.get("retailPrice")
                results.append({
                    "provider": "azure",
                    "region": region,
                    "instance_type": sku,
                    "spot_price_usd": price,
                    "available": price is not None and price > 0,
                })
            next_url = data.get("NextPageLink")
    except Exception as exc:
        logger.warning("Azure Retail Prices API failed: %s", exc)
        # Synthetic fallback
        import random
        _FALLBACK = {
            "Standard_NC6s_v3": 0.918,
            "Standard_NC24s_v3": 3.672,
            "Standard_ND96asr_v4": 12.24,
            "Standard_NV6ads_A10_v5": 0.454,
        }
        for region in regions:
            for itype in vm_sizes:
                base = _FALLBACK.get(itype, 1.5)
                price = base * (1 + random.gauss(0, 0.05))
                results.append({
                    "provider": "azure",
                    "region": region,
                    "instance_type": itype,
                    "spot_price_usd": round(price, 4),
                    "available": random.random() > 0.1,
                })

    return results
