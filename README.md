# Weekly AI Papers Digest / 每周 AI 论文精选

每周一自动从 arXiv 抓取最新 AI/ML 论文，通过 Kimi 大模型智能筛选 Top 20 并生成结构化摘要，邮件推送。

每篇论文包含：
- **问题 (Problem)** — 论文要解决什么问题
- **解决方案 (Solution)** — 提出了什么方法
- **创新之处 (Innovation)** — 与现有工作相比的新颖之处

## Architecture

```
arXiv API → fetcher.py → ranker.py (Kimi LLM) → summarizer.py (Kimi LLM) → emailer.py (SMTP)
                                                                                    ↓
                                                                              Email Digest
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your actual keys
```

**Required variables:**

| Variable | Description |
|---|---|
| `KIMI_API_KEY` | Moonshot AI (Kimi) API key |
| `KIMI_BASE_URL` | API base URL (default: `https://api.moonshot.cn/v1`) |
| `KIMI_MODEL` | Model ID (default: `moonshot-v1-32k`) |
| `SMTP_SERVER` | SMTP server (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (e.g., `465`) |
| `SMTP_USERNAME` | SMTP login username |
| `SMTP_PASSWORD` | SMTP password (Gmail: use App Password) |
| `EMAIL_FROM` | Sender email address |
| `EMAIL_TO` | Recipient email(s), comma-separated |

### 3. Run locally

```bash
python main.py
```

### 4. GitHub Actions (automated weekly)

Add the above variables as **GitHub Secrets** in your repo settings, then the workflow will automatically run every Monday at 16:00 Beijing Time.

You can also trigger it manually via **Actions → Weekly AI Papers Digest → Run workflow**.

## Coverage

- **Categories**: `cs.AI`, `cs.CL`, `cs.LG`, `cs.MA`
- **Time window**: Past 7 days
- **Output**: Top 20 papers ranked by importance
