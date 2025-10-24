"""
Quick analysis script - analyze a specific stock
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_stock_agent import StockAnalyzerAgent
from loguru import logger


def main():
    """Quick stock analysis"""
    parser = argparse.ArgumentParser(description="Quick AI Stock Analysis")
    parser.add_argument("stock_code", type=str, help="Stock code (e.g., 000001)")
    parser.add_argument(
        "--days", type=int, default=60, help="Number of days to analyze (default: 60)"
    )
    parser.add_argument(
        "--no-ai", action="store_true", help="Skip AI analysis (technical only)"
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Quick Stock Analysis: {args.stock_code}")
    print(f"{'='*60}\n")

    if args.no_ai:
        # Technical analysis only
        from ai_stock_agent import StockSelector

        selector = StockSelector()
        analysis = selector.analyze_stock_with_history(args.stock_code, days=args.days)

        if "error" not in analysis:
            print(f"Stock: {analysis['stock_code']}")
            print(f"Date: {analysis['analysis_date']}")
            print(f"Latest Price: {analysis['latest_price']:.2f}")
            print(f"Price Change: {analysis['pct_change']:.2f}%")
            print(f"Amplitude: {analysis['amplitude']:.2f}%")
            print(f"Volume Ratio: {analysis['volume_ratio']:.2f}")

            print("\nVolume-Price Signal:")
            vp_signal = analysis["volume_price_signal"]
            print(f"  Signal: {vp_signal['signal']}")
            print(f"  Strength: {vp_signal['strength']}")
            print(f"  VP Relation: {vp_signal['vp_relation']}")

            print("\nLatest Technical Indicators:")
            indicators = analysis["indicators"]
            print(f"  MA5: {indicators.get('ma5', 0):.2f}")
            print(f"  MA10: {indicators.get('ma10', 0):.2f}")
            print(f"  MA20: {indicators.get('ma20', 0):.2f}")
            print(f"  MA60: {indicators.get('ma60', 0):.2f}")
            print(f"  RSI(14): {indicators.get('rsi14', 0):.2f}")
            print(f"  MACD: {indicators.get('macd', 0):.4f}")
        else:
            print(f"Error: {analysis['error']}")
    else:
        # AI analysis
        agent = StockAnalyzerAgent()

        result = agent.analyze_stock(args.stock_code, days=args.days)

        if "error" not in result:
            report = agent.generate_trading_report(result)
            print(report)
        else:
            print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
