# CODEAI 🧠

> **An intelligence layer for the AI revolution.**

Stop drowning in AI content. Start understanding what matters.

---

## The Problem

Every day:
- 📺 Dozens of AI YouTube videos drop
- 🐦 Hundreds of AI tweets and threads spiral
- 📄 Papers, demos, debates, breakthroughs
- 😵 The signal-to-noise ratio is brutal

**You need more than a feed reader. You need an intelligence analyst.**

## The Solution

CODEAI is your AI-powered curator that:

1. **Collects** - Monitors YouTube channels, searches, and Twitter accounts you care about
2. **Understands** - Uses Claude AI to analyze content and rank by importance
3. **Packages** - Formats everything perfectly for NotebookLM
4. **Delivers** - You get AI-generated audio overviews (podcasts) of what actually matters

```
YouTube + Twitter → CODEAI → NotebookLM → Your Daily AI Intelligence Briefing 🎧
```

## Why This Architecture?

**We don't compete with NotebookLM. We feed it perfectly.**

NotebookLM is *insanely good* at:
- Understanding documents
- Creating connections
- Generating audio overviews (AI podcasts)

CODEAI is *insanely good* at:
- Finding important AI content
- Extracting and structuring it
- Ranking by relevance

Together? **Magic.**

## Quick Start

### 1. Install

```bash
# Clone the repo
git clone https://github.com/yourusername/CODEAI.git
cd CODEAI

# Install dependencies
pip install -r requirements.txt

# Set up your API keys
cp .env.example .env
# Edit .env with your keys
```

### 2. Get API Keys

You need three keys (all have free tiers):

| Service | Purpose | Get It |
|---------|---------|--------|
| **YouTube Data API** | Video search & metadata | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| **Twitter API** | Tweet collection | [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) |
| **Anthropic Claude** | AI understanding & ranking | [Anthropic Console](https://console.anthropic.com/) |

### 3. Run the Notebook

```bash
jupyter notebook ai_intelligence_collector.ipynb
```

**Configure your sources:**
- Add YouTube channels you trust
- Add Twitter accounts to monitor
- Set search terms for topics you care about

**Run all cells** → Get NotebookLM-ready sources in minutes.

### 4. Upload to NotebookLM

1. Go to [NotebookLM](https://notebooklm.google.com)
2. Create a new notebook
3. Upload the generated files from `notebooklm_sources/batch_*/`
4. Click **"Generate Audio Overview"**
5. Listen to your personalized AI news podcast 🎧

## What Makes This Different?

### It's Opinionated
Not a generic scraper. It understands **importance**. Claude analyzes each piece of content and ranks it (1-10). You see what matters.

### It's Integrated
Built specifically for NotebookLM's workflow. The output format is optimized for maximum understanding and audio overview quality.

### It's Elegant
Clean architecture. Readable code. Every function does one thing well. It's not just working code—it's *craft*.

### It's Yours
Fully customizable. Add sources. Change rankings. Fork it. Make it your own intelligence system.

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Intelligence Sources                     │
│  YouTube Channels | Search Terms | Twitter       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         Content Collectors                       │
│  - YouTube Data API                              │
│  - YouTube Transcript API                        │
│  - Twitter API v2                                │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         AI Understanding Layer                   │
│  Claude 3.5 Sonnet:                              │
│  - Importance scoring (1-10)                     │
│  - Key insights extraction                       │
│  - Topic identification                          │
│  - Content summarization                         │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         NotebookLM Formatters                    │
│  - Markdown documents                            │
│  - YouTube URL lists                             │
│  - Twitter thread compilations                   │
│  - Master index & README                         │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         Export Package                           │
│  Ready to upload to NotebookLM                   │
└─────────────────────────────────────────────────┘
```

## Use Cases

### Daily Intelligence Brief
Run every morning. Get a digest of overnight AI developments as an audio podcast.

### Research Assistant
Tracking a specific topic? Configure custom search terms and get deep analysis.

### Competitive Intelligence
Monitor what AI companies and researchers are saying. Stay ahead.

### Learning & Education
Perfect for students, educators, or anyone trying to keep up with AI's rapid pace.

## Customization

The notebook is highly configurable. Key variables:

```python
# YouTube
YOUTUBE_CHANNELS = ['channel_id_1', 'channel_id_2', ...]
YOUTUBE_SEARCH_TERMS = ['GPT-5', 'Claude 3.5', ...]

# Twitter
TWITTER_ACCOUNTS = ['AnthropicAI', 'OpenAI', ...]
TWITTER_HASHTAGS = ['#AI', '#LLM', ...]

# Time window
DAYS_TO_LOOK_BACK = 7
```

## Automation

Want this to run automatically?

### GitHub Actions (Recommended)
```yaml
# .github/workflows/collect.yml
name: Daily AI Intelligence
on:
  schedule:
    - cron: '0 8 * * *'  # 8 AM daily
jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt
      - run: python collect_cli.py
      # Upload artifacts or commit results
```

### Cron (Linux/Mac)
```bash
# Run at 8 AM daily
0 8 * * * cd /path/to/CODEAI && python collect_cli.py
```

## Roadmap

- [x] YouTube video collection
- [x] Twitter content collection
- [x] Claude AI analysis
- [x] NotebookLM-optimized export
- [ ] CLI tool for automation
- [ ] Web dashboard
- [ ] Real-time monitoring
- [ ] Trend detection
- [ ] Email/Slack notifications
- [ ] NotebookLM Enterprise API integration
- [ ] Podcast RSS feed generation

## Philosophy

This project follows a few principles:

**1. Simplicity First**
Do one thing exceptionally well. Collect AI intelligence and feed it to NotebookLM.

**2. Leverage Giants**
Don't rebuild what exists. NotebookLM is amazing—use it.

**3. Quality Over Quantity**
Better to surface 5 important things than 500 mediocre ones.

**4. Craft Over Code**
Every line should feel inevitable. Every abstraction should feel natural.

**5. Open & Extendable**
Your intelligence system should be yours. Fork it. Change it. Make it better.

## Contributing

This is a trial project, but contributions are welcome:

- 🐛 Report bugs
- 💡 Suggest features
- 🔧 Submit PRs
- 📝 Improve docs

## License

MIT - Use it however you want.

## Credits

Built with:
- [Anthropic Claude](https://www.anthropic.com/) - AI understanding
- [NotebookLM](https://notebooklm.google.com/) - Intelligence synthesis
- [YouTube Data API](https://developers.google.com/youtube/v3) - Video metadata
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - Transcripts
- [Tweepy](https://www.tweepy.org/) - Twitter integration

---

**"The people who are crazy enough to think they can change the world are the ones who do."**

Let's stay ahead of the AI revolution. Together.
