# 股票舆情收集与分析系统

一个功能完善的股票市场舆情收集与情感分析系统，能够自动从多个新闻源收集相关文章，进行情感分析，并生成可视化报告。

## 功能特性

- **多源数据采集**：支持从 RSS 新闻源和新闻 API 收集数据
- **智能过滤**：根据股票代码自动筛选相关新闻
- **情感分析**：使用 VADER 或 TextBlob 进行 NLP 情感分析
- **金融词汇优化**：针对金融市场术语优化的情感分析
- **数据持久化**：支持 SQLite 和 JSON 两种存储方式
- **数据可视化**：自动生成多种图表和统计报告
- **灵活配置**：通过 YAML 文件轻松配置所有参数

## 项目结构

```
CODEAI/
├── main.py                 # 主程序入口
├── requirements.txt        # Python 依赖
├── README.md              # 项目文档
├── .env.example           # 环境变量示例
├── config/
│   └── config.yaml        # 配置文件
├── src/
│   ├── collectors/        # 数据采集模块
│   │   └── news_collector.py
│   ├── analyzers/         # 情感分析模块
│   │   └── sentiment_analyzer.py
│   ├── storage/           # 数据存储模块
│   │   └── data_storage.py
│   ├── visualizers/       # 可视化模块
│   │   └── sentiment_visualizer.py
│   └── utils/             # 工具模块
│       ├── config_loader.py
│       └── logger.py
└── data/                  # 数据存储目录
    ├── sentiment.db       # SQLite 数据库
    ├── sentiment_data.json # JSON 数据文件
    ├── charts/            # 图表输出目录
    └── sentiment_analysis.log # 日志文件
```

## 安装

### 前置要求

- Python 3.8 或更高版本
- pip 包管理器

### 安装步骤

1. 克隆项目：
```bash
git clone <repository-url>
cd CODEAI
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 下载 NLTK 数据（首次运行需要）：
```bash
python -c "import nltk; nltk.download('vader_lexicon'); nltk.download('punkt')"
```

4. （可选）配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，添加 API 密钥等
```

## 配置

编辑 `config/config.yaml` 文件来自定义设置：

### 主要配置项

- **股票代码**：在 `data_collection.stock_symbols` 中添加要跟踪的股票
- **新闻源**：在 `data_collection.news_sources` 中配置 RSS 源
- **采集频率**：设置 `data_collection.collection_interval`（分钟）
- **情感分析器**：选择 'vader' 或 'textblob'
- **存储方式**：选择 'sqlite' 或 'json'

示例配置：
```yaml
data_collection:
  stock_symbols:
    - AAPL
    - GOOGL
    - MSFT
  news_sources:
    - name: "Yahoo Finance"
      url: "https://finance.yahoo.com/news/rssindex"
      enabled: true
```

## 使用方法

### 基本命令

1. **收集和分析新闻**：
```bash
python main.py collect
```

2. **生成可视化报告**：
```bash
python main.py visualize
```

3. **查看统计信息**：
```bash
python main.py stats
```

4. **执行完整流程**（收集、分析、可视化）：
```bash
python main.py all
```

### 高级用法

指定分析时间范围：
```bash
python main.py stats --days 30
python main.py visualize --days 14
```

使用自定义配置文件：
```bash
python main.py collect --config my_config.yaml
```

查看帮助信息：
```bash
python main.py --help
```

## 输出说明

### 1. 控制台输出

运行后会在控制台显示：
- 采集进度和统计
- 整体情感分析摘要
- 每个股票的详细情感分析

### 2. 数据库

所有文章和分析结果保存在：
- SQLite: `data/sentiment.db`
- JSON: `data/sentiment_data.json`

### 3. 可视化图表

生成的图表保存在 `data/charts/` 目录：
- `sentiment_timeline_<stock>.png` - 情感时间线
- `sentiment_distribution_<stock>.png` - 情感分布
- `stock_comparison.png` - 股票对比分析

### 4. 日志文件

详细日志保存在 `data/sentiment_analysis.log`

## 情感分析说明

### VADER 分析器

- **Compound Score 范围**：-1（极度负面）到 +1（极度正面）
- **分类标准**：
  - 正面：> 0.05
  - 负面：< -0.05
  - 中性：-0.05 到 0.05

### 金融词汇增强

系统针对金融市场特有术语进行了优化，包括：
- 牛市/熊市术语（bull, bear, bullish, bearish）
- 价格变动词汇（surge, plunge, rally, crash）
- 财务指标（profit, loss, growth, decline）
- 市场事件（upgrade, downgrade, breakthrough）

## 开发和扩展

### 添加新的数据源

在 `config/config.yaml` 中添加新的 RSS 源：
```yaml
news_sources:
  - name: "新数据源"
    url: "https://example.com/rss"
    enabled: true
```

### 使用 News API

1. 获取 API 密钥：https://newsapi.org
2. 在 `.env` 文件中设置：
```
NEWS_API_KEY=your_api_key_here
```
3. 代码会自动使用 API 进行额外的数据收集

### 自定义分析逻辑

可以扩展 `src/analyzers/sentiment_analyzer.py` 来：
- 添加新的情感分析算法
- 增强金融词汇库
- 实现自定义评分机制

## 定期运行

### 使用 Cron（Linux/Mac）

添加到 crontab：
```bash
# 每小时收集一次数据
0 * * * * cd /path/to/CODEAI && python main.py collect

# 每天生成可视化报告
0 9 * * * cd /path/to/CODEAI && python main.py visualize
```

### 使用任务计划程序（Windows）

创建计划任务，定期执行：
```
python C:\path\to\CODEAI\main.py collect
```

## 性能优化建议

1. **数据清理**：定期清理旧数据
```python
from src.storage import DataStorage
storage = DataStorage()
storage.cleanup_old_data(days=30)  # 保留30天数据
```

2. **批量处理**：增加 `max_articles_per_source` 提高效率

3. **缓存优化**：系统自动去重，避免重复分析

## 故障排除

### 常见问题

1. **RSS 源无法访问**
   - 检查网络连接
   - 验证 RSS URL 是否有效
   - 某些源可能需要 VPN 访问

2. **NLTK 数据错误**
   - 重新下载：`python -c "import nltk; nltk.download('all')"`

3. **可视化图表不显示中文**
   - 安装中文字体并在代码中配置 matplotlib

4. **数据库锁定错误**
   - 确保没有多个实例同时写入数据库
   - 考虑使用 JSON 存储方式

## 示例输出

### 控制台输出示例
```
==================================================
OVERALL SENTIMENT SUMMARY
==================================================
Total articles analyzed: 45
Positive: 18 (40.0%)
Negative: 12 (26.7%)
Neutral: 15 (33.3%)
Average compound score: 0.142
Overall sentiment: POSITIVE

==================================================
PER-STOCK SENTIMENT SUMMARY
==================================================

AAPL:
  Articles: 15
  Positive: 8 (53.3%)
  Negative: 3 (20.0%)
  Avg Score: 0.245
  Sentiment: POSITIVE
```

## 技术栈

- **Python 3.8+**
- **数据采集**：requests, feedparser, beautifulsoup4
- **NLP 分析**：VADER, TextBlob, NLTK
- **数据处理**：pandas, numpy
- **数据存储**：SQLite, SQLAlchemy
- **可视化**：matplotlib, seaborn, plotly

## 许可证

本项目仅供学习和研究使用。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 免责声明

本系统提供的情感分析结果仅供参考，不构成投资建议。投资有风险，决策需谨慎。

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系。

---

**版本**: 1.0.0
**最后更新**: 2025
