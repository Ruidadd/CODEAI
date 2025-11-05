#!/usr/bin/env python3
"""
CODEAI - CLI Intelligence Collector

A command-line interface for collecting AI intelligence from YouTube and Twitter,
formatting it for NotebookLM.

Usage:
    python collect_cli.py
    python collect_cli.py --days 7 --max-videos 20
"""

import os
import sys
import json
import re
import yaml
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import argparse

# YouTube & Transcript
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build

# Twitter (now X)
import tweepy

# AI Understanding
import anthropic

# Environment
from dotenv import load_dotenv

# Rich for beautiful CLI output (optional)
try:
    from rich.console import Console
    from rich.progress import track
    from rich import print as rprint
    console = Console()
    USE_RICH = True
except ImportError:
    console = None
    USE_RICH = False
    def rprint(*args, **kwargs):
        print(*args, **kwargs)


# Load environment variables
load_dotenv()

# API Keys
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')


@dataclass
class YouTubeVideo:
    """Represents a YouTube video with intelligence metadata"""
    video_id: str
    url: str
    title: str
    channel: str
    published_at: str
    view_count: int
    like_count: int
    duration: str
    description: str
    has_transcript: bool
    importance_score: Optional[float] = None
    ai_summary: Optional[str] = None
    key_topics: Optional[List[str]] = None

    def to_markdown(self) -> str:
        """Format as NotebookLM-ready markdown"""
        md = f"""# {self.title}

**Channel:** {self.channel}
**Published:** {self.published_at}
**Views:** {self.view_count:,} | **Likes:** {self.like_count:,}
**Duration:** {self.duration}
**URL:** {self.url}

## Description

{self.description}
"""
        if self.ai_summary:
            md += f"\n## AI Summary\n\n{self.ai_summary}\n"

        if self.key_topics:
            md += f"\n## Key Topics\n\n{', '.join(self.key_topics)}\n"

        if self.importance_score:
            md += f"\n## Importance Score: {self.importance_score}/10\n"

        return md


class IntelligenceCollector:
    """Main collector class"""

    def __init__(self, days_back: int = 7, max_videos: int = 20, config_path: str = 'config.yml'):
        self.days_back = days_back
        self.max_videos = max_videos

        # Initialize API clients
        self.youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) if YOUTUBE_API_KEY else None
        self.twitter_client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN) if TWITTER_BEARER_TOKEN else None
        self.claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

        # Load configuration from file or use defaults
        self.load_config(config_path)

    def load_config(self, config_path: str):
        """Load configuration from YAML file or use defaults"""
        config_file = Path(config_path)

        # Default configuration
        default_config = {
            'youtube': {
                'channels': [
                    '@TwoMinutePapers',
                    '@YannicKilcher',
                    '@AIExplained-Official',
                    '@sequoiacapital',
                    '@a16z',
                ],
                'search_terms': [
                    'GPT-5',
                    'Claude 3.5',
                    'OpenAI news',
                    'AI breakthrough',
                    'Sequoia AI',
                    'a16z AI',
                ],
            },
            'twitter': {
                'accounts': [
                    'AnthropicAI',
                    'OpenAI',
                    'karpathy',
                    'sequoia',
                    'a16z',
                    'pmarca',
                ],
            },
        }

        # Try to load from file
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    rprint(f"[green]✓[/green] Loaded config from {config_path}")
            except Exception as e:
                rprint(f"[yellow]⚠ Could not load config file: {e}[/yellow]")
                rprint(f"[yellow]  Using default configuration[/yellow]")
                config = default_config
        else:
            rprint(f"[yellow]⚠ Config file not found: {config_path}[/yellow]")
            rprint(f"[yellow]  Using default configuration[/yellow]")
            config = default_config

        # Extract configuration
        youtube_config = config.get('youtube', {})
        twitter_config = config.get('twitter', {})

        self.youtube_channel_handles = youtube_config.get('channels', [])
        self.youtube_search_terms = youtube_config.get('search_terms', [])
        self.twitter_accounts = twitter_config.get('accounts', [])

        # Convert handles to channel IDs (or keep as handles for search)
        self.youtube_channels = []
        for handle in self.youtube_channel_handles:
            # If it starts with @, it's a handle - we'll search by channel name
            # If it starts with UC, it's already a channel ID
            if handle.startswith('UC'):
                self.youtube_channels.append(handle)
            else:
                # For handles, we'll search by name instead
                # Remove @ if present
                clean_handle = handle.lstrip('@')
                self.youtube_search_terms.append(clean_handle)

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
            r'youtube\.com\/embed\/([^&\n?#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return url if len(url) == 11 else None

    def get_video_details(self, video_id: str) -> Optional[YouTubeVideo]:
        """Fetch detailed information about a YouTube video"""
        if not self.youtube:
            return None

        try:
            response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            ).execute()

            if not response['items']:
                return None

            video = response['items'][0]
            snippet = video['snippet']
            stats = video['statistics']

            # Check if transcript available
            has_transcript = False
            try:
                YouTubeTranscriptApi.get_transcript(video_id)
                has_transcript = True
            except:
                pass

            return YouTubeVideo(
                video_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                title=snippet['title'],
                channel=snippet['channelTitle'],
                published_at=snippet['publishedAt'],
                view_count=int(stats.get('viewCount', 0)),
                like_count=int(stats.get('likeCount', 0)),
                duration=video['contentDetails']['duration'],
                description=snippet['description'],
                has_transcript=has_transcript,
            )
        except Exception as e:
            rprint(f"[red]Error fetching video {video_id}: {e}[/red]")
            return None

    def search_youtube_videos(self, query: str, max_results: int = 10) -> List[YouTubeVideo]:
        """Search YouTube for videos matching query"""
        if not self.youtube:
            return []

        try:
            published_after = (datetime.now() - timedelta(days=self.days_back)).isoformat() + 'Z'

            response = self.youtube.search().list(
                part='id',
                q=query,
                type='video',
                publishedAfter=published_after,
                maxResults=max_results,
                order='relevance',
                relevanceLanguage='en',
            ).execute()

            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                video = self.get_video_details(video_id)
                if video:
                    videos.append(video)

            return videos
        except Exception as e:
            rprint(f"[red]Error searching YouTube for '{query}': {e}[/red]")
            return []

    def get_channel_latest_videos(self, channel_id: str, max_results: int = 10) -> List[YouTubeVideo]:
        """Get latest videos from a channel"""
        if not self.youtube:
            return []

        try:
            published_after = (datetime.now() - timedelta(days=self.days_back)).isoformat() + 'Z'

            response = self.youtube.search().list(
                part='id',
                channelId=channel_id,
                type='video',
                publishedAfter=published_after,
                maxResults=max_results,
                order='date',
            ).execute()

            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                video = self.get_video_details(video_id)
                if video:
                    videos.append(video)

            return videos
        except Exception as e:
            rprint(f"[red]Error fetching channel {channel_id}: {e}[/red]")
            return []

    def analyze_video_importance(self, video: YouTubeVideo) -> YouTubeVideo:
        """Use Claude to analyze video importance and extract insights"""
        if not self.claude_client:
            return video

        try:
            prompt = f"""Analyze this YouTube video about AI and provide:
1. Importance score (1-10) - how significant is this for someone tracking AI developments?
2. Brief summary (2-3 sentences)
3. Key topics (3-5 keywords)

Title: {video.title}
Channel: {video.channel}
Description: {video.description}
Views: {video.view_count:,}
Likes: {video.like_count:,}

Respond in JSON format:
{{
  "importance_score": 8.5,
  "summary": "...",
  "key_topics": ["topic1", "topic2", "topic3"]
}}"""

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            content = response.content[0].text
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                analysis = json.loads(json_match.group())
                video.importance_score = analysis.get('importance_score')
                video.ai_summary = analysis.get('summary')
                video.key_topics = analysis.get('key_topics', [])
        except Exception as e:
            rprint(f"[yellow]Could not analyze video {video.video_id}: {e}[/yellow]")

        return video

    def collect_all_videos(self) -> List[YouTubeVideo]:
        """Collect videos from all configured sources"""
        all_videos = []

        if self.youtube:
            # Collect from channels
            rprint("\n[cyan]Collecting from YouTube channels...[/cyan]")
            for channel_id in self.youtube_channels:
                rprint(f"  Fetching {channel_id}...")
                videos = self.get_channel_latest_videos(channel_id, max_results=5)
                all_videos.extend(videos)
                rprint(f"  Found {len(videos)} videos")

            # Search YouTube
            rprint("\n[cyan]Searching YouTube...[/cyan]")
            for term in self.youtube_search_terms:
                rprint(f"  Searching: {term}")
                videos = self.search_youtube_videos(term, max_results=5)
                all_videos.extend(videos)
                rprint(f"  Found {len(videos)} videos")

        # Deduplicate
        seen_ids = set()
        unique_videos = []
        for video in all_videos:
            if video.video_id not in seen_ids:
                seen_ids.add(video.video_id)
                unique_videos.append(video)

        return unique_videos

    def analyze_videos(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """Analyze videos with Claude"""
        if not self.claude_client:
            return videos

        rprint("\n[cyan]Analyzing videos with Claude...[/cyan]")

        analyzed = []
        videos_to_analyze = videos[:min(self.max_videos, len(videos))]

        iterator = track(videos_to_analyze, description="Analyzing...") if USE_RICH else videos_to_analyze

        for video in iterator:
            if not USE_RICH:
                rprint(f"  Analyzing: {video.title[:50]}...")
            analyzed_video = self.analyze_video_importance(video)
            analyzed.append(analyzed_video)

        # Sort by importance
        analyzed.sort(key=lambda v: v.importance_score or 0, reverse=True)

        return analyzed

    def export_for_notebooklm(self, videos: List[YouTubeVideo]) -> Path:
        """Export videos in NotebookLM-ready format"""
        # Create export directory
        export_dir = Path('notebooklm_sources')
        export_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_dir = export_dir / f'batch_{timestamp}'
        batch_dir.mkdir(exist_ok=True)

        rprint(f"\n[cyan]Exporting to: {batch_dir}[/cyan]")

        # Export videos
        if videos:
            videos_dir = batch_dir / 'youtube_videos'
            videos_dir.mkdir(exist_ok=True)

            for video in videos:
                safe_title = re.sub(r'[^\w\s-]', '', video.title)[:50]
                filename = f"{safe_title}.md"
                filepath = videos_dir / filename

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(video.to_markdown())

            # Create URL list
            urls_file = batch_dir / 'youtube_urls.txt'
            with open(urls_file, 'w') as f:
                f.write("# Important AI Videos (Last 7 Days)\n\n")
                for video in videos:
                    f.write(f"{video.url}\n")

            rprint(f"[green]Exported {len(videos)} videos[/green]")

        # Create master index
        index_file = batch_dir / 'README.md'
        with open(index_file, 'w') as f:
            f.write(f"""# AI Intelligence Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Time Period:** Last {self.days_back} days

## Summary

- **YouTube Videos:** {len(videos)}

## How to Use with NotebookLM

1. Go to [NotebookLM](https://notebooklm.google.com)
2. Create a new notebook
3. Upload `youtube_urls.txt` directly
4. Generate Audio Overview
5. Listen to your AI intelligence briefing! 🎧

## Top Videos

""")

            for i, video in enumerate(videos[:10], 1):
                score = f" [{video.importance_score:.1f}/10]" if video.importance_score else ""
                f.write(f"{i}.{score} [{video.title}]({video.url})\n")
                if video.ai_summary:
                    f.write(f"   - {video.ai_summary}\n")

        return batch_dir

    def run(self):
        """Run the full collection pipeline"""
        rprint("\n[bold cyan]🧠 CODEAI Intelligence Collector[/bold cyan]\n")

        # Check API keys
        rprint("[cyan]Checking API configuration...[/cyan]")
        rprint(f"  YouTube: [{'green']✓[/green]' if self.youtube else 'red']✗ (set YOUTUBE_API_KEY)[/red]'}")
        rprint(f"  Twitter: [{'green']✓[/green]' if self.twitter_client else 'yellow']⚠ (set TWITTER_BEARER_TOKEN)[/yellow]'}")
        rprint(f"  Claude:  [{'green']✓[/green]' if self.claude_client else 'yellow']⚠ (set ANTHROPIC_API_KEY)[/yellow]'}")

        if not self.youtube:
            rprint("\n[red]Error: YouTube API key is required![/red]")
            rprint("Set YOUTUBE_API_KEY in your .env file")
            sys.exit(1)

        # Collect
        videos = self.collect_all_videos()
        rprint(f"\n[green]Collected {len(videos)} unique videos[/green]")

        if not videos:
            rprint("[yellow]No videos found. Try adjusting your search terms or time window.[/yellow]")
            return

        # Analyze
        if self.claude_client:
            videos = self.analyze_videos(videos)

            rprint("\n[bold cyan]🏆 Top 5 Most Important Videos:[/bold cyan]")
            for i, video in enumerate(videos[:5], 1):
                score = video.importance_score or 0
                rprint(f"  {i}. [{score:.1f}/10] {video.title}")

        # Export
        batch_dir = self.export_for_notebooklm(videos)

        rprint(f"\n[bold green]✅ Collection complete![/bold green]")
        rprint(f"\n[cyan]Next steps:[/cyan]")
        rprint(f"  1. Open: {batch_dir}")
        rprint(f"  2. Go to: https://notebooklm.google.com")
        rprint(f"  3. Upload the files")
        rprint(f"  4. Generate Audio Overview")
        rprint(f"  5. Listen to your AI intelligence briefing! 🎧\n")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='CODEAI - AI Intelligence Collector for NotebookLM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python collect_cli.py
  python collect_cli.py --days 7 --max-videos 20
  python collect_cli.py --days 3 --max-videos 10

For more information: https://github.com/yourusername/CODEAI
        """
    )

    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to look back (default: 7)'
    )

    parser.add_argument(
        '--max-videos',
        type=int,
        default=20,
        help='Maximum number of videos to analyze with AI (default: 20)'
    )

    args = parser.parse_args()

    # Run collector
    collector = IntelligenceCollector(
        days_back=args.days,
        max_videos=args.max_videos
    )
    collector.run()


if __name__ == '__main__':
    main()
