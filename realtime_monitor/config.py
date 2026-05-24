"""
Monitoring configuration: sources, thresholds, and schedules.
"""
from dataclasses import dataclass, field
from typing import Dict, List

# Asian cloud regions to monitor
ASIAN_REGIONS = {
    "aws": [
        "ap-northeast-1",   # Tokyo
        "ap-northeast-2",   # Seoul
        "ap-southeast-1",   # Singapore
        "ap-southeast-2",   # Sydney
        "ap-south-1",       # Mumbai
    ],
    "azure": [
        "japaneast",
        "koreacentral",
        "southeastasia",
        "eastasia",
        "centralindia",
    ],
    "gcp": [
        "asia-northeast1",  # Tokyo
        "asia-northeast3",  # Seoul
        "asia-southeast1",  # Singapore
        "asia-south1",      # Mumbai
    ],
}

# GPU instance types to track
GPU_INSTANCE_TYPES = {
    "aws": ["p3.2xlarge", "p3.8xlarge", "p4d.24xlarge", "g4dn.xlarge", "g4dn.12xlarge", "g5.xlarge", "g5.12xlarge"],
    "azure": ["Standard_NC6s_v3", "Standard_NC24s_v3", "Standard_ND96asr_v4", "Standard_NV6ads_A10_v5"],
    "gcp": ["n1-standard-8-nvidia-tesla-v100", "a2-highgpu-1g", "a2-highgpu-8g"],
}

# DRAM types to track
DRAM_TYPES = ["DDR4", "DDR5", "HBM2", "HBM3", "LPDDR5"]

# Alert thresholds (percent change triggers alert)
ALERT_THRESHOLDS = {
    "dram_price_change_pct": 5.0,        # DRAM price change > 5%
    "gpu_price_change_pct": 10.0,        # GPU price change > 10%
    "gpu_availability_drop_pct": 20.0,   # Availability drop > 20%
    "gpu_utilization_fee_change_pct": 15.0,
}

# Polling intervals (seconds)
POLL_INTERVALS = {
    "dram": 3600,          # hourly
    "gpu_cloud": 300,      # every 5 minutes
    "gpu_availability": 180,  # every 3 minutes
}

DB_PATH = "monitor_data.db"


@dataclass
class AlertConfig:
    webhook_url: str = ""
    email: str = ""
    log_to_console: bool = True
