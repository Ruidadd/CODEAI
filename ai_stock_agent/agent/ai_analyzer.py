"""
AI-powered stock analyzer using Claude for intelligent trading signals
"""

import json
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
from loguru import logger

from ..utils.config import Config
from ..strategies.stock_selector import StockSelector


class StockAnalyzerAgent:
    """
    AI Agent for analyzing stocks and providing trading signals
    Uses Claude to analyze technical indicators and market data
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize StockAnalyzerAgent

        Args:
            api_key: Anthropic API key (optional, will use from config if not provided)
        """
        self.api_key = api_key or Config.get_api_key()
        self.client = Anthropic(api_key=self.api_key)
        self.model = Config.MODEL_NAME
        self.selector = StockSelector()

        logger.info(f"Initialized StockAnalyzerAgent with model: {self.model}")

    def _prepare_analysis_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """
        Prepare prompt for AI analysis

        Args:
            analysis_data: Stock analysis data

        Returns:
            Formatted prompt string
        """
        indicators = analysis_data.get("indicators", {})
        vp_signal = analysis_data.get("volume_price_signal", {})
        recent_data = analysis_data.get("historical_data", [])

        prompt = f"""你是一位专业的股票分析师，精通技术分析和量价关系分析。请基于以下数据分析这支股票，并给出买卖建议。

股票代码: {analysis_data.get('stock_code', 'N/A')}
分析日期: {analysis_data.get('analysis_date', 'N/A')}

当前价格信息:
- 最新价: {indicators.get('close', 0):.2f}
- 涨跌幅: {indicators.get('pct_change', 0):.2f}%
- 振幅: {indicators.get('amplitude', 0):.2f}%
- 成交量比: {indicators.get('volume_ratio', 0):.2f}

技术指标:
- MA5: {indicators.get('ma5', 0):.2f}
- MA10: {indicators.get('ma10', 0):.2f}
- MA20: {indicators.get('ma20', 0):.2f}
- MA60: {indicators.get('ma60', 0):.2f}
- MACD: {indicators.get('macd', 0):.4f}
- MACD Signal: {indicators.get('macd_signal', 0):.4f}
- MACD Histogram: {indicators.get('macd_hist', 0):.4f}
- RSI(14): {indicators.get('rsi14', 0):.2f}
- 布林带上轨: {indicators.get('bb_upper', 0):.2f}
- 布林带中轨: {indicators.get('bb_middle', 0):.2f}
- 布林带下轨: {indicators.get('bb_lower', 0):.2f}

量价关系分析:
- 量价信号: {vp_signal.get('signal', 'N/A')}
- 信号强度: {vp_signal.get('strength', 'N/A')}
- 量价关系: {vp_signal.get('vp_relation', 'N/A')}
- 成交量突破: {vp_signal.get('volume_breakout', False)}
- 背离情况: {vp_signal.get('divergence', 'N/A')}

近期走势 (最近10天):
{json.dumps(recent_data[-10:], indent=2, ensure_ascii=False)}

请提供以下分析:
1. 技术面综合评价 (分析均线系统、MACD、RSI、布林带等指标)
2. 量价关系评价 (分析成交量与价格的配合情况)
3. 趋势判断 (上升趋势、下降趋势、震荡)
4. 买卖建议 (强烈买入、买入、持有、卖出、强烈卖出)
5. 支撑位和压力位预测
6. 风险提示

请以JSON格式返回分析结果，包含以下字段:
{{
    "technical_rating": "技术面评级(1-10分)",
    "volume_price_rating": "量价关系评级(1-10分)",
    "trend": "趋势判断",
    "signal": "买卖建议",
    "signal_strength": "信号强度(1-10)",
    "support_level": "支撑位",
    "resistance_level": "压力位",
    "risk_level": "风险等级(低/中/高)",
    "analysis": "详细分析文字",
    "key_points": ["关键要点1", "关键要点2", "关键要点3"]
}}
"""

        return prompt

    def analyze_stock(self, stock_code: str, days: int = 60) -> Dict[str, Any]:
        """
        Analyze a stock using AI

        Args:
            stock_code: Stock code
            days: Number of days of historical data

        Returns:
            AI analysis result
        """
        logger.info(f"Starting AI analysis for stock {stock_code}")

        try:
            # Get stock analysis data
            analysis_data = self.selector.analyze_stock_with_history(stock_code, days=days)

            if "error" in analysis_data:
                logger.error(f"Error getting stock data: {analysis_data['error']}")
                return {"error": analysis_data["error"]}

            # Prepare prompt
            prompt = self._prepare_analysis_prompt(analysis_data)

            # Call Claude API
            logger.info("Calling Claude API for analysis")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract AI response
            ai_response = response.content[0].text

            # Try to parse JSON response
            try:
                # Find JSON in response
                json_start = ai_response.find("{")
                json_end = ai_response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = ai_response[json_start:json_end]
                    ai_analysis = json.loads(json_str)
                else:
                    ai_analysis = {"analysis": ai_response}
            except json.JSONDecodeError:
                logger.warning("Could not parse AI response as JSON, using raw text")
                ai_analysis = {"analysis": ai_response}

            # Combine results
            result = {
                "stock_code": stock_code,
                "basic_info": {
                    "date": analysis_data.get("analysis_date", ""),
                    "price": analysis_data.get("latest_price", 0),
                    "pct_change": analysis_data.get("pct_change", 0),
                    "amplitude": analysis_data.get("amplitude", 0),
                    "volume_ratio": analysis_data.get("volume_ratio", 0),
                },
                "technical_indicators": analysis_data.get("indicators", {}),
                "volume_price_signal": analysis_data.get("volume_price_signal", {}),
                "ai_analysis": ai_analysis,
                "raw_ai_response": ai_response,
            }

            logger.info(f"AI analysis completed for {stock_code}")

            return result

        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return {"error": str(e)}

    def batch_analyze_stocks(
        self, stock_codes: List[str], days: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Batch analyze multiple stocks using AI

        Args:
            stock_codes: List of stock codes
            days: Number of days of historical data

        Returns:
            List of AI analysis results
        """
        logger.info(f"Starting batch AI analysis for {len(stock_codes)} stocks")

        results = []
        for i, code in enumerate(stock_codes, 1):
            logger.info(f"Analyzing stock {i}/{len(stock_codes)}: {code}")

            try:
                analysis = self.analyze_stock(code, days=days)
                if "error" not in analysis:
                    results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {code}: {e}")
                continue

        logger.info(f"Batch AI analysis completed: {len(results)} successful")

        return results

    def find_best_opportunities(
        self, market: str = "A", top_n: int = 5, analyze_with_ai: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find best trading opportunities in the market

        Args:
            market: Market type
            top_n: Number of opportunities to return
            analyze_with_ai: Whether to use AI for detailed analysis

        Returns:
            List of best opportunities
        """
        logger.info(f"Finding top {top_n} trading opportunities")

        # Get buy candidates
        candidates = self.selector.get_buy_candidates(market=market, top_n=top_n * 2)

        if not candidates:
            logger.warning("No buy candidates found")
            return []

        # If AI analysis requested, analyze top candidates
        if analyze_with_ai:
            stock_codes = [c["stock_code"] for c in candidates[:top_n]]
            ai_results = self.batch_analyze_stocks(stock_codes)

            # Sort by AI signal strength
            ai_results.sort(
                key=lambda x: x.get("ai_analysis", {}).get("signal_strength", 0),
                reverse=True,
            )

            return ai_results[:top_n]
        else:
            return candidates[:top_n]

    def generate_trading_report(
        self, analysis_result: Dict[str, Any]
    ) -> str:
        """
        Generate a formatted trading report

        Args:
            analysis_result: AI analysis result

        Returns:
            Formatted report string
        """
        basic_info = analysis_result.get("basic_info", {})
        ai_analysis = analysis_result.get("ai_analysis", {})

        report = f"""
{'='*60}
股票分析报告
{'='*60}

股票代码: {analysis_result.get('stock_code', 'N/A')}
分析日期: {basic_info.get('date', 'N/A')}

基本信息:
- 最新价: {basic_info.get('price', 0):.2f}
- 涨跌幅: {basic_info.get('pct_change', 0):.2f}%
- 振幅: {basic_info.get('amplitude', 0):.2f}%
- 量比: {basic_info.get('volume_ratio', 0):.2f}

AI分析结果:
- 技术面评级: {ai_analysis.get('technical_rating', 'N/A')}
- 量价关系评级: {ai_analysis.get('volume_price_rating', 'N/A')}
- 趋势判断: {ai_analysis.get('trend', 'N/A')}
- 交易建议: {ai_analysis.get('signal', 'N/A')}
- 信号强度: {ai_analysis.get('signal_strength', 'N/A')}
- 支撑位: {ai_analysis.get('support_level', 'N/A')}
- 压力位: {ai_analysis.get('resistance_level', 'N/A')}
- 风险等级: {ai_analysis.get('risk_level', 'N/A')}

详细分析:
{ai_analysis.get('analysis', 'N/A')}

关键要点:
"""
        key_points = ai_analysis.get("key_points", [])
        for i, point in enumerate(key_points, 1):
            report += f"{i}. {point}\n"

        report += f"\n{'='*60}\n"

        return report
