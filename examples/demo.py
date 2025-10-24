"""
Demo script for AI Stock Agent
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_stock_agent import StockAnalyzerAgent, DataFetcher, StockSelector
from loguru import logger


def demo_data_fetching():
    """Demo: Fetch stock K-line data"""
    print("\n" + "=" * 60)
    print("Demo 1: Fetching Stock K-line Data")
    print("=" * 60)

    # Initialize data fetcher
    fetcher = DataFetcher(source="akshare")

    # Fetch data for Ping An Bank (平安银行 000001)
    stock_code = "000001"
    print(f"\nFetching K-line data for stock {stock_code}...")

    df = fetcher.get_stock_kline(stock_code=stock_code, adjust="qfq")

    print(f"\nFetched {len(df)} records")
    print("\nLatest 5 days:")
    print(df[["date", "open", "high", "low", "close", "volume", "amplitude"]].tail())


def demo_stock_selection():
    """Demo: Select stocks based on volume and amplitude"""
    print("\n" + "=" * 60)
    print("Demo 2: Stock Selection Based on Volume-Price")
    print("=" * 60)

    # Initialize selector
    selector = StockSelector(
        min_volume_ratio=1.5, min_amplitude=3.0, max_amplitude=15.0
    )

    # Select stocks
    print("\nSelecting stocks with high volume ratio and suitable amplitude...")

    selected = selector.select_stocks(market="A", price_trend="up", top_n=10)

    print(f"\nSelected {len(selected)} stocks:")
    print(
        selected[
            ["code", "name", "price", "pct_change", "amplitude", "volume_ratio"]
        ].head(10)
    )


def demo_technical_analysis():
    """Demo: Technical indicator analysis"""
    print("\n" + "=" * 60)
    print("Demo 3: Technical Indicator Analysis")
    print("=" * 60)

    # Initialize selector
    selector = StockSelector()

    # Analyze a specific stock
    stock_code = "000001"
    print(f"\nAnalyzing stock {stock_code} with technical indicators...")

    analysis = selector.analyze_stock_with_history(stock_code, days=60)

    if "error" not in analysis:
        print(f"\nStock: {analysis['stock_code']}")
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
        print(f"  RSI(14): {indicators.get('rsi14', 0):.2f}")
        print(f"  MACD: {indicators.get('macd', 0):.4f}")


def demo_ai_analysis():
    """Demo: AI-powered stock analysis"""
    print("\n" + "=" * 60)
    print("Demo 4: AI-Powered Stock Analysis")
    print("=" * 60)

    # Check if API key is set
    from ai_stock_agent.utils.config import Config

    if not Config.ANTHROPIC_API_KEY:
        print("\nError: ANTHROPIC_API_KEY not set in environment")
        print("Please set it in .env file or environment variable")
        return

    # Initialize AI agent
    agent = StockAnalyzerAgent()

    # Analyze a stock
    stock_code = "000001"
    print(f"\nAnalyzing stock {stock_code} with AI...")

    result = agent.analyze_stock(stock_code, days=60)

    if "error" not in result:
        # Generate and print report
        report = agent.generate_trading_report(result)
        print(report)
    else:
        print(f"Error: {result['error']}")


def demo_find_opportunities():
    """Demo: Find best trading opportunities"""
    print("\n" + "=" * 60)
    print("Demo 5: Finding Best Trading Opportunities")
    print("=" * 60)

    # Check if API key is set
    from ai_stock_agent.utils.config import Config

    if not Config.ANTHROPIC_API_KEY:
        print("\nError: ANTHROPIC_API_KEY not set in environment")
        print("Please set it in .env file or environment variable")
        return

    # Initialize AI agent
    agent = StockAnalyzerAgent()

    # Find opportunities
    print("\nSearching for best trading opportunities...")

    opportunities = agent.find_best_opportunities(market="A", top_n=3, analyze_with_ai=True)

    print(f"\nFound {len(opportunities)} opportunities:")

    for i, opp in enumerate(opportunities, 1):
        print(f"\n--- Opportunity {i} ---")
        basic = opp.get("basic_info", {})
        ai = opp.get("ai_analysis", {})

        print(f"Stock Code: {opp['stock_code']}")
        print(f"Price: {basic.get('price', 0):.2f}")
        print(f"Change: {basic.get('pct_change', 0):.2f}%")
        print(f"Signal: {ai.get('signal', 'N/A')}")
        print(f"Signal Strength: {ai.get('signal_strength', 'N/A')}")
        print(f"Risk Level: {ai.get('risk_level', 'N/A')}")


def main():
    """Main demo function"""
    logger.info("Starting AI Stock Agent Demo")

    while True:
        print("\n" + "=" * 60)
        print("AI Stock Agent Demo Menu")
        print("=" * 60)
        print("1. Fetch K-line Data")
        print("2. Stock Selection (Volume-Price)")
        print("3. Technical Analysis")
        print("4. AI Stock Analysis (requires API key)")
        print("5. Find Best Opportunities (requires API key)")
        print("6. Run All Demos")
        print("0. Exit")
        print("=" * 60)

        choice = input("\nEnter your choice (0-6): ").strip()

        if choice == "1":
            demo_data_fetching()
        elif choice == "2":
            demo_stock_selection()
        elif choice == "3":
            demo_technical_analysis()
        elif choice == "4":
            demo_ai_analysis()
        elif choice == "5":
            demo_find_opportunities()
        elif choice == "6":
            demo_data_fetching()
            demo_stock_selection()
            demo_technical_analysis()
            demo_ai_analysis()
            demo_find_opportunities()
        elif choice == "0":
            print("\nExiting demo. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please try again.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
