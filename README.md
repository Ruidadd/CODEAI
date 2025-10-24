# AI Stock Agent - AI驱动的股票买卖点提示系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个类似Bloomberg GPT的AI驱动股票分析系统，能够：
- 获取同花顺A股K线数据
- 计算技术指标（均线、MACD、RSI、布林带等）
- 基于量价关系和振幅选股
- 使用Claude AI分析股票并给出买卖建议

## 特性

### 1. 数据获取
- 支持AKShare数据源获取A股K线数据
- 实时行情数据获取
- 股票列表筛选

### 2. 技术指标分析
- **均线系统**: MA5, MA10, MA20, MA60
- **趋势指标**: MACD
- **动量指标**: RSI
- **波动指标**: 布林带
- **成交量指标**: 量比、成交量均线
- **价格指标**: 振幅、涨跌幅

### 3. 量价关系分析
- 价涨量增/价涨量缩
- 价跌量增/价跌量缩
- 成交量突破检测
- 量价背离识别
- OBV指标
- A/D线指标

### 4. 智能选股策略
- 基于量比筛选（默认>1.5）
- 基于振幅筛选（默认3%-15%）
- 趋势方向过滤
- 多指标综合排序

### 5. AI分析Agent
- 使用Claude AI进行深度分析
- 综合评估技术面和量价关系
- 给出具体买卖建议
- 预测支撑位和压力位
- 风险等级评估

## 安装

### 前置要求
- Python 3.8+
- Anthropic API Key

### 安装步骤

1. 克隆仓库
```bash
git clone <repository-url>
cd CODEAI
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

或使用开发模式安装
```bash
pip install -e .
```

3. 配置API密钥

复制`.env.example`为`.env`并填入你的API密钥：
```bash
cp .env.example .env
```

编辑`.env`文件：
```
ANTHROPIC_API_KEY=your_api_key_here
MODEL_NAME=claude-3-5-sonnet-20241022
```

## 快速开始

### 示例1: 运行交互式Demo

```bash
python examples/demo.py
```

这将显示一个交互式菜单，包含以下功能：
1. 获取K线数据
2. 量价选股
3. 技术指标分析
4. AI股票分析
5. 寻找最佳交易机会

### 示例2: 快速分析单只股票

```bash
# 分析平安银行(000001)
python examples/quick_analysis.py 000001

# 分析60天数据
python examples/quick_analysis.py 000001 --days 60

# 仅技术分析（不使用AI）
python examples/quick_analysis.py 000001 --no-ai
```

### 示例3: 寻找交易机会

```bash
# 寻找前5个最佳机会
python examples/find_opportunities.py --top 5

# 寻找前10个机会（不使用AI）
python examples/find_opportunities.py --top 10 --no-ai
```

## 使用指南

### 1. 数据获取模块

```python
from ai_stock_agent import DataFetcher

# 初始化
fetcher = DataFetcher(source="akshare")

# 获取K线数据
df = fetcher.get_stock_kline(
    stock_code="000001",
    period="daily",
    adjust="qfq"  # 前复权
)

# 获取股票列表
stocks = fetcher.get_stock_list(market="A")

# 获取实时行情
quotes = fetcher.get_realtime_quote(["000001", "600036"])
```

### 2. 技术指标计算

```python
from ai_stock_agent import TechnicalIndicators

# 计算所有指标
df = TechnicalIndicators.calculate_all_indicators(df)

# 获取最新指标值
latest = TechnicalIndicators.get_latest_indicators(df)

print(f"MA5: {latest['ma5']}")
print(f"RSI: {latest['rsi14']}")
print(f"MACD: {latest['macd']}")
```

### 3. 量价关系分析

```python
from ai_stock_agent.indicators import VolumePriceAnalyzer

# 量价趋势分析
df = VolumePriceAnalyzer.analyze_volume_price_trend(df)

# 成交量突破检测
df = VolumePriceAnalyzer.identify_volume_breakout(df)

# 获取量价信号
signal = VolumePriceAnalyzer.get_volume_price_signal(df)
print(f"Signal: {signal['signal']}")
print(f"Strength: {signal['strength']}")
```

### 4. 智能选股

```python
from ai_stock_agent import StockSelector

# 初始化选股器
selector = StockSelector(
    min_volume_ratio=1.5,  # 最小量比
    min_amplitude=3.0,      # 最小振幅
    max_amplitude=15.0      # 最大振幅
)

# 选股
selected = selector.select_stocks(
    market="A",
    price_trend="up",  # 上涨趋势
    rank_by="volume_ratio",
    top_n=20
)

# 详细分析单只股票
analysis = selector.analyze_stock_with_history("000001", days=60)
```

### 5. AI分析Agent

```python
from ai_stock_agent import StockAnalyzerAgent

# 初始化Agent
agent = StockAnalyzerAgent()

# 分析单只股票
result = agent.analyze_stock("000001", days=60)

# 生成报告
report = agent.generate_trading_report(result)
print(report)

# 寻找最佳交易机会
opportunities = agent.find_best_opportunities(
    market="A",
    top_n=5,
    analyze_with_ai=True
)

for opp in opportunities:
    print(f"Stock: {opp['stock_code']}")
    print(f"Signal: {opp['ai_analysis']['signal']}")
    print(f"Strength: {opp['ai_analysis']['signal_strength']}")
```

## 项目结构

```
CODEAI/
├── ai_stock_agent/          # 主包
│   ├── __init__.py
│   ├── data/                # 数据获取模块
│   │   ├── data_fetcher.py  # K线数据获取
│   │   └── ...
│   ├── indicators/          # 技术指标模块
│   │   ├── technical_indicators.py  # 技术指标计算
│   │   └── volume_price.py  # 量价关系分析
│   ├── strategies/          # 策略模块
│   │   └── stock_selector.py  # 选股策略
│   ├── agent/               # AI Agent模块
│   │   └── ai_analyzer.py   # AI分析器
│   └── utils/               # 工具模块
│       └── config.py        # 配置管理
├── examples/                # 示例代码
│   ├── demo.py             # 交互式Demo
│   ├── quick_analysis.py   # 快速分析
│   └── find_opportunities.py  # 寻找机会
├── tests/                   # 测试代码
├── requirements.txt         # 依赖列表
├── setup.py                # 安装配置
├── .env.example            # 环境变量示例
└── README.md               # 本文件
```

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    AI Stock Agent                        │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌─────▼─────┐    ┌─────▼─────┐
   │  Data   │      │Indicators │    │Strategies │
   │ Fetcher │      │Calculator │    │ Selector  │
   └────┬────┘      └─────┬─────┘    └─────┬─────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                    ┌─────▼─────┐
                    │    AI     │
                    │  Analyzer │
                    │  (Claude) │
                    └───────────┘
```

## 选股逻辑

系统使用多重筛选机制：

1. **量比筛选**: 选择成交量活跃的股票（量比>1.5）
2. **振幅筛选**: 过滤波动过大或过小的股票（3%-15%）
3. **趋势筛选**: 选择符合指定趋势的股票
4. **技术指标综合评分**: 基于MA、MACD、RSI等指标
5. **量价关系确认**: 确保量价配合良好
6. **AI深度分析**: Claude分析技术面和市场情绪

## AI分析流程

1. **数据准备**: 获取60天K线和技术指标
2. **量价分析**: 计算量价关系和信号强度
3. **AI推理**:
   - 分析技术指标组合
   - 评估量价配合情况
   - 识别趋势和形态
   - 预测支撑位/压力位
4. **生成建议**:
   - 买卖信号（强烈买入/买入/持有/卖出/强烈卖出）
   - 信号强度（1-10分）
   - 风险等级（低/中/高）

## 注意事项

1. **API限制**: 注意Anthropic API的调用频率限制
2. **数据准确性**: AKShare数据为开源数据，可能存在延迟
3. **投资风险**: 本系统仅供学习研究，不构成投资建议
4. **市场风险**: 股市有风险，投资需谨慎

## 配置选项

在`.env`文件或环境变量中配置：

```bash
# API配置
ANTHROPIC_API_KEY=your_api_key
MODEL_NAME=claude-3-5-sonnet-20241022
MAX_TOKENS=4096
TEMPERATURE=0.7

# 数据源配置
DATA_SOURCE=akshare

# 选股参数（可在代码中覆盖）
MIN_VOLUME_RATIO=1.5
MIN_AMPLITUDE=3.0
MAX_AMPLITUDE=15.0
```

## 常见问题

### Q: 如何获取Anthropic API Key?
A: 访问 https://console.anthropic.com/ 注册账号并创建API密钥

### Q: 支持哪些股票市场?
A: 目前支持中国A股市场，可通过修改数据源扩展到其他市场

### Q: 技术指标的参数可以调整吗?
A: 可以，在`utils/config.py`中修改或在代码中传入自定义参数

### Q: AI分析需要多长时间?
A: 通常单只股票分析需要5-10秒，批量分析会更久

### Q: 数据更新频率如何?
A: AKShare提供的是日K线数据，每日收盘后更新

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 免责声明

本软件仅供学习和研究使用，不构成任何投资建议。使用本软件进行股票交易的任何损失，开发者概不负责。投资有风险，入市需谨慎！

## 联系方式

如有问题或建议，请提交Issue。

---

**Happy Trading! 祝投资顺利！** 🚀📈
