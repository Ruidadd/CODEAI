"""监控系统配置"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 数据库
BASE_DIR = Path(__file__).parent.parent
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "price_monitor.db"))

# 监控参数
DEFAULT_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL", "60"))
PRICE_CHANGE_ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "5.0"))  # 涨跌幅 %

# 请求设置
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY", "1.5"))  # 请求间隔，防封

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 数据源配置
SOURCES = {
    "szlcsc": {
        "name": "立创商城",
        "base_url": "https://so.szlcsc.com",
        "search_url": "https://so.szlcsc.com/global.html?k={keyword}",
        "api_url": "https://so.szlcsc.com/s?q={keyword}&pageSize=10&pageIndex=1&hy=IC",
        "enabled": True,
    },
    "allchips": {
        "name": "Allchips芯片网",
        "base_url": "https://www.allchips.com",
        "search_url": "https://www.allchips.com/search?q={keyword}",
        "enabled": True,
    },
    "icsmart": {
        "name": "华强北网(ICSMART)",
        "base_url": "https://www.icsmart.cn",
        "search_url": "https://www.icsmart.cn/search?keyword={keyword}",
        "enabled": True,
    },
    "ickey": {
        "name": "云汉芯城",
        "base_url": "https://www.ickey.cn",
        "search_url": "https://www.ickey.cn/search-products-{keyword}.html",
        "enabled": True,
    },
    "52ic": {
        "name": "52元器件网",
        "base_url": "https://www.52ic.com",
        "search_url": "https://www.52ic.com/icsearch/index.html?key={keyword}",
        "enabled": True,
    },
}

# 默认监控元器件列表
DEFAULT_COMPONENTS = [
    # MCU
    "STM32F103C8T6",
    "ESP32-WROOM-32",
    "GD32F103C8T6",
    # 常用IC
    "NE555",
    "LM358",
    "SN74HC595",
    "AMS1117-3.3",
    # 存储
    "W25Q64JVSIQ",
    "AT24C02",
    # MOSFET
    "AO3400",
    "IRF540N",
]
