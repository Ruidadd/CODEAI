#!/usr/bin/env python3
"""
特朗普X.com推文分析工具
获取特朗普最近10天的推文，分析评论数和点赞数
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import time


class TrumpXAnalyzer:
    """分析特朗普X.com推文的类"""

    def __init__(self):
        self.username = "realDonaldTrump"
        self.posts = []

    def fetch_posts_mock(self, days: int = 10) -> List[Dict]:
        """
        模拟获取推文数据的函数

        注意：这是一个示例框架。实际使用时需要：
        1. 使用官方Twitter API v2 (需要API密钥)
        2. 使用第三方服务如nitter实例
        3. 使用已授权的数据采集服务

        Args:
            days: 获取最近几天的推文

        Returns:
            推文列表
        """
        # 这里是模拟数据，实际应用需要使用真实的API
        print(f"正在获取 @{self.username} 最近 {days} 天的推文...")

        # 模拟数据结构
        mock_posts = [
            {
                "id": "1234567890",
                "text": "MAKE AMERICA GREAT AGAIN!",
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "likes": 125000,
                "retweets": 45000,
                "replies": 12000,
                "views": 2500000
            },
            {
                "id": "1234567891",
                "text": "The election was rigged. Everyone knows it!",
                "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "likes": 98000,
                "retweets": 35000,
                "replies": 15000,
                "views": 1800000
            },
            {
                "id": "1234567892",
                "text": "Fake News Media at it again!",
                "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
                "likes": 110000,
                "retweets": 40000,
                "replies": 18000,
                "views": 2100000
            },
            {
                "id": "1234567893",
                "text": "America First! Always!",
                "created_at": (datetime.now() - timedelta(days=4)).isoformat(),
                "likes": 135000,
                "retweets": 48000,
                "replies": 11000,
                "views": 2700000
            },
            {
                "id": "1234567894",
                "text": "The radical left is destroying our country!",
                "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
                "likes": 105000,
                "retweets": 38000,
                "replies": 22000,
                "views": 1950000
            },
            {
                "id": "1234567895",
                "text": "We will win in 2024!",
                "created_at": (datetime.now() - timedelta(days=6)).isoformat(),
                "likes": 145000,
                "retweets": 52000,
                "replies": 14000,
                "views": 3000000
            },
            {
                "id": "1234567896",
                "text": "Biden is the worst president in history!",
                "created_at": (datetime.now() - timedelta(days=7)).isoformat(),
                "likes": 118000,
                "retweets": 42000,
                "replies": 19000,
                "views": 2300000
            },
            {
                "id": "1234567897",
                "text": "Thank you to all my supporters! Together we are strong!",
                "created_at": (datetime.now() - timedelta(days=8)).isoformat(),
                "likes": 152000,
                "retweets": 55000,
                "replies": 10000,
                "views": 3200000
            },
            {
                "id": "1234567898",
                "text": "The corrupt DOJ and FBI are targeting me because I'm winning!",
                "created_at": (datetime.now() - timedelta(days=9)).isoformat(),
                "likes": 128000,
                "retweets": 46000,
                "replies": 25000,
                "views": 2600000
            },
            {
                "id": "1234567899",
                "text": "Build the wall! Secure our borders!",
                "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
                "likes": 115000,
                "retweets": 41000,
                "replies": 16000,
                "views": 2200000
            }
        ]

        self.posts = mock_posts
        return mock_posts

    def fetch_posts_nitter(self, days: int = 10) -> List[Dict]:
        """
        使用Nitter实例获取推文（公开数据）

        注意：Nitter是Twitter的开源前端，不需要API密钥
        但需要找到一个可用的Nitter实例
        """
        # 可用的Nitter实例列表（这些可能会变化）
        nitter_instances = [
            "https://nitter.net",
            "https://nitter.it",
            "https://nitter.privacydev.net"
        ]

        # 这里应该实现实际的爬取逻辑
        # 由于Nitter的HTML结构可能变化，这里只是框架
        print("注意：此功能需要实现具体的爬取逻辑")
        return []

    def analyze_posts(self) -> pd.DataFrame:
        """
        分析推文数据

        Returns:
            包含分析结果的DataFrame
        """
        if not self.posts:
            print("没有推文数据，请先获取数据")
            return pd.DataFrame()

        # 创建DataFrame
        df = pd.DataFrame(self.posts)

        # 转换日期
        df['created_at'] = pd.to_datetime(df['created_at'])

        # 添加互动总数
        df['total_engagement'] = df['likes'] + df['retweets'] + df['replies']

        # 计算互动率（相对于浏览量）
        df['engagement_rate'] = (df['total_engagement'] / df['views'] * 100).round(2)

        # 按点赞数排序
        df = df.sort_values('likes', ascending=False)

        return df

    def generate_report(self, df: pd.DataFrame) -> str:
        """
        生成分析报告

        Args:
            df: 推文数据DataFrame

        Returns:
            报告文本
        """
        if df.empty:
            return "没有数据可供分析"

        report = []
        report.append("=" * 80)
        report.append("特朗普X.com推文分析报告")
        report.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"数据范围: 最近10天")
        report.append("=" * 80)
        report.append("")

        # 总体统计
        report.append("## 总体统计")
        report.append(f"- 推文总数: {len(df)}")
        report.append(f"- 总点赞数: {df['likes'].sum():,}")
        report.append(f"- 总转发数: {df['retweets'].sum():,}")
        report.append(f"- 总评论数: {df['replies'].sum():,}")
        report.append(f"- 总浏览量: {df['views'].sum():,}")
        report.append(f"- 平均点赞数: {df['likes'].mean():,.0f}")
        report.append(f"- 平均评论数: {df['replies'].mean():,.0f}")
        report.append(f"- 平均互动率: {df['engagement_rate'].mean():.2f}%")
        report.append("")

        # 按点赞数排名
        report.append("## 按点赞数排名 (Top 5)")
        for idx, row in df.head(5).iterrows():
            report.append(f"\n{idx+1}. 点赞数: {row['likes']:,}")
            report.append(f"   推文: {row['text'][:100]}...")
            report.append(f"   发布时间: {row['created_at'].strftime('%Y-%m-%d %H:%M')}")
            report.append(f"   转发: {row['retweets']:,} | 评论: {row['replies']:,} | 浏览: {row['views']:,}")
            report.append(f"   互动率: {row['engagement_rate']:.2f}%")
        report.append("")

        # 按评论数排名
        df_by_replies = df.sort_values('replies', ascending=False)
        report.append("## 按评论数排名 (Top 5)")
        for idx, row in df_by_replies.head(5).iterrows():
            report.append(f"\n{idx+1}. 评论数: {row['replies']:,}")
            report.append(f"   推文: {row['text'][:100]}...")
            report.append(f"   发布时间: {row['created_at'].strftime('%Y-%m-%d %H:%M')}")
            report.append(f"   点赞: {row['likes']:,} | 转发: {row['retweets']:,}")
        report.append("")

        # 按互动率排名
        df_by_engagement = df.sort_values('engagement_rate', ascending=False)
        report.append("## 按互动率排名 (Top 5)")
        for idx, row in df_by_engagement.head(5).iterrows():
            report.append(f"\n{idx+1}. 互动率: {row['engagement_rate']:.2f}%")
            report.append(f"   推文: {row['text'][:100]}...")
            report.append(f"   总互动: {row['total_engagement']:,}")
        report.append("")

        report.append("=" * 80)
        report.append("报告结束")
        report.append("=" * 80)

        return "\n".join(report)

    def save_data(self, df: pd.DataFrame, filename: str = "trump_posts_data.csv"):
        """保存数据到CSV文件"""
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"数据已保存到: {filename}")

    def save_report(self, report: str, filename: str = "trump_analysis_report.txt"):
        """保存报告到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存到: {filename}")


def main():
    """主函数"""
    print("=" * 80)
    print("特朗普X.com推文分析工具")
    print("=" * 80)
    print()

    # 创建分析器实例
    analyzer = TrumpXAnalyzer()

    # 获取推文数据
    print("步骤 1: 获取推文数据...")
    posts = analyzer.fetch_posts_mock(days=10)
    print(f"✓ 成功获取 {len(posts)} 条推文")
    print()

    # 分析数据
    print("步骤 2: 分析推文数据...")
    df = analyzer.analyze_posts()
    print("✓ 分析完成")
    print()

    # 生成报告
    print("步骤 3: 生成分析报告...")
    report = analyzer.generate_report(df)
    print("✓ 报告生成完成")
    print()

    # 保存数据和报告
    print("步骤 4: 保存结果...")
    analyzer.save_data(df)
    analyzer.save_report(report)
    print("✓ 保存完成")
    print()

    # 打印报告
    print(report)

    print("\n注意事项:")
    print("- 当前使用的是模拟数据")
    print("- 要获取真实数据，请配置Twitter API或使用其他授权的数据源")
    print("- 可以修改 fetch_posts_nitter() 方法来实现实际的数据采集")


if __name__ == "__main__":
    main()
