# 特朗普X.com推文分析工具

这是一个用于分析特朗普在X.com(原Twitter)上的推文的Python工具。该工具可以获取最近10天的推文数据，并根据点赞数、评论数和其他互动指标进行分析。

## 功能特性

- 获取特朗普最近10天的推文数据
- 分析推文的互动数据（点赞、转发、评论）
- 计算互动率和互动总数
- 生成详细的分析报告
- 按不同指标排名（点赞数、评论数、互动率）
- 导出数据到CSV格式

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

运行分析脚本：

```bash
python3 trump_x_analysis.py
```

脚本将会：
1. 获取推文数据
2. 分析数据并计算各项指标
3. 生成分析报告
4. 保存数据到 `trump_posts_data.csv`
5. 保存报告到 `trump_analysis_report.txt`

## 输出文件

- `trump_posts_data.csv`: 包含所有推文数据的CSV文件
- `trump_analysis_report.txt`: 详细的分析报告文本文件

## 分析指标

报告包含以下分析：

### 总体统计
- 推文总数
- 总点赞数、转发数、评论数、浏览量
- 平均点赞数和评论数
- 平均互动率

### 排名分析
- 按点赞数排名 (Top 5)
- 按评论数排名 (Top 5)
- 按互动率排名 (Top 5)

## 重要说明

**当前版本使用模拟数据进行演示。**

要获取真实数据，您需要：

1. **使用Twitter API v2**:
   - 注册Twitter开发者账号
   - 获取API密钥和访问令牌
   - 使用官方的tweepy库

2. **使用Nitter实例**:
   - 找到可用的Nitter实例
   - 实现HTML解析逻辑

3. **使用第三方数据服务**:
   - 使用授权的社交媒体数据提供商

## 扩展功能

您可以修改 `TrumpXAnalyzer` 类来添加更多功能：

- 情感分析
- 关键词提取
- 时间趋势分析
- 与其他政治人物的对比分析
- 数据可视化（图表生成）

## 技术栈

- Python 3.x
- pandas: 数据分析
- requests: HTTP请求
- beautifulsoup4: HTML解析（用于Nitter集成）
- python-dateutil: 日期处理

## 许可证

MIT License

## 免责声明

本工具仅用于教育和研究目的。使用时请遵守X.com的服务条款和数据使用政策。
