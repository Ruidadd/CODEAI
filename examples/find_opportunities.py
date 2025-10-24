"""
Find best trading opportunities script
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_stock_agent import StockAnalyzerAgent
from loguru import logger


def main():
    """Find best trading opportunities"""
    parser = argparse.ArgumentParser(description="Find Best Trading Opportunities")
    parser.add_argument(
        "--top", type=int, default=5, help="Number of opportunities to find (default: 5)"
    )
    parser.add_argument(
        "--market", type=str, default="A", help="Market type (default: A)"
    )
    parser.add_argument(
        "--no-ai", action="store_true", help="Skip AI analysis (technical only)"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Finding Top {args.top} Trading Opportunities")
    print(f"{'='*60}\n")

    agent = StockAnalyzerAgent()

    opportunities = agent.find_best_opportunities(
        market=args.market, top_n=args.top, analyze_with_ai=not args.no_ai
    )

    if not opportunities:
        print("No opportunities found.")
        return

    print(f"Found {len(opportunities)} opportunities:\n")

    for i, opp in enumerate(opportunities, 1):
        print(f"\n{'='*60}")
        print(f"Opportunity #{i}")
        print(f"{'='*60}")

        if args.no_ai:
            # Technical analysis only
            print(f"Stock Code: {opp['stock_code']}")
            print(f"Date: {opp['analysis_date']}")
            print(f"Price: {opp['latest_price']:.2f}")
            print(f"Change: {opp['pct_change']:.2f}%")
            print(f"Amplitude: {opp['amplitude']:.2f}%")
            print(f"Volume Ratio: {opp['volume_ratio']:.2f}")

            vp_signal = opp["volume_price_signal"]
            print(f"\nSignal: {vp_signal['signal']}")
            print(f"Strength: {vp_signal['strength']}")
        else:
            # AI analysis
            report = agent.generate_trading_report(opp)
            print(report)


if __name__ == "__main__":
    main()
