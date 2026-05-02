"""Flask web dashboard for Alpha Signal."""

import json
import os
from flask import Flask, render_template, jsonify, request
from stock_data import (
    get_all_watched_quotes, get_market_indices,
    get_stock_history, get_stock_fundamentals,
    get_competition_sector_data, get_comparable_companies,
    normalize_ticker,
)
from news_fetcher import get_daily_news_digest, fetch_rss_news, categorize_news
from ai_analyzer import (
    summarize_news, analyze_sentiment, extract_keywords,
    generate_daily_briefing, ai_stock_valuation, compare_stocks_for_competition,
    _call_deepseek,
)
from trend_charts import (
    create_full_chart, create_comparison_chart,
    create_valuation_comparison, create_sector_heatmap,
    create_chan_analysis,
)
from stock_screener import (
    screen_stock, screen_all_candidates, rank_candidates,
    ai_pair_recommendation, TECH_UNIVERSE,
)

app = Flask(__name__)


def get_cached_data():
    """Load cached data from latest_data.json or fetch fresh."""
    if os.path.exists("latest_data.json"):
        try:
            with open("latest_data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# === Page Routes ===

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analysis")
def analysis():
    return render_template("analysis.html")

@app.route("/valuation")
def valuation():
    return render_template("valuation.html")

@app.route("/screener")
def screener():
    return render_template("screener.html")

@app.route("/charts")
def charts():
    return render_template("charts.html")

@app.route("/competition")
def competition():
    return render_template("competition.html")

@app.route("/sigma")
def sigma():
    return render_template("sigma.html")


# === Dashboard API ===

@app.route("/api/dashboard")
def api_dashboard():
    cached = get_cached_data()
    if cached:
        return jsonify(cached)
    stocks = get_all_watched_quotes()
    indices = get_market_indices()
    return jsonify({
        "timestamp": "No cached data - run daily pipeline first",
        "stocks": stocks, "indices": indices,
        "news": {}, "sentiment": {}, "keywords": {},
        "briefing": "Run the daily pipeline (python run_daily.py --preview) to populate data.",
    })

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    try:
        from run_daily import run_daily_pipeline
        run_daily_pipeline(send_email=False, preview_only=False)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/chart/<ticker>")
def api_chart(ticker):
    ticker = normalize_ticker(ticker)
    hist = get_stock_history(ticker, period="3mo")
    if hist.empty:
        return jsonify({"dates": [], "open": [], "high": [], "low": [], "close": []})
    return jsonify({
        "dates": hist.index.strftime("%Y-%m-%d").tolist(),
        "open": hist["Open"].round(2).tolist(),
        "high": hist["High"].round(2).tolist(),
        "low": hist["Low"].round(2).tolist(),
        "close": hist["Close"].round(2).tolist(),
        "volume": hist["Volume"].tolist(),
    })

@app.route("/api/comparables/<sector>")
def api_comparables(sector):
    try:
        return jsonify(get_competition_sector_data(sector))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Technical Chart API ===

@app.route("/api/chart/technical/<ticker>")
def api_chart_technical(ticker):
    """Full technical chart with indicators."""
    ticker = normalize_ticker(ticker)
    period = request.args.get("period", "6mo")
    chart = create_full_chart(ticker, period=period)
    if "error" in chart:
        return jsonify(chart), 404
    return jsonify(chart)

@app.route("/api/chart/chan/<ticker>")
def api_chart_chan(ticker):
    """Chan/market-structure indicator summary."""
    ticker = normalize_ticker(ticker)
    period = request.args.get("period", "1y")
    result = create_chan_analysis(ticker, period=period)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)

@app.route("/api/chart/comparison", methods=["POST"])
def api_chart_comparison():
    """Relative performance comparison chart."""
    data = request.get_json()
    tickers = data.get("tickers", {})
    period = data.get("period", "6mo")
    chart = create_comparison_chart(tickers, period)
    return jsonify(chart)

@app.route("/api/chart/valuation-compare", methods=["POST"])
def api_chart_valuation_compare():
    """Valuation comparison bar charts."""
    data = request.get_json()
    stocks = data.get("stocks", [])
    chart = create_valuation_comparison(stocks)
    return jsonify(chart)

@app.route("/api/chart/heatmap", methods=["POST"])
def api_chart_heatmap():
    """Metrics heatmap."""
    data = request.get_json()
    stocks = data.get("stocks", [])
    chart = create_sector_heatmap(stocks)
    return jsonify(chart)


# === Stock Screener API ===

@app.route("/api/screener/<direction>")
def api_screener(direction):
    """Run full stock screening pipeline."""
    if direction not in ("short", "long"):
        return jsonify({"error": "Direction must be 'short' or 'long'"}), 400

    xiaomi = get_stock_fundamentals("1810.HK")
    candidates = screen_all_candidates()
    ranked = rank_candidates(candidates, xiaomi, direction)
    recommendation = ai_pair_recommendation(xiaomi, ranked[:8], direction)

    result = {
        "direction": direction,
        "xiaomi": xiaomi,
        "total_screened": len(candidates),
        "top_candidates": ranked[:15],
        "ai_recommendation": recommendation,
    }

    with open(f"screening_{direction}_latest.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    return jsonify(result)


# === AI API ===

@app.route("/api/ai/sentiment")
def api_ai_sentiment():
    articles = fetch_rss_news(max_per_feed=10)
    categories = categorize_news(articles)
    sentiment = {}
    for topic in ["xiaomi", "qqq_intel", "macro", "tech"]:
        topic_articles = categories.get(topic, [])
        if topic_articles:
            sentiment[topic] = analyze_sentiment(topic_articles, topic)
    return jsonify(sentiment)

@app.route("/api/ai/keywords")
def api_ai_keywords():
    articles = fetch_rss_news(max_per_feed=10)
    return jsonify(extract_keywords(articles[:30]))

@app.route("/api/ai/cluster")
def api_ai_cluster():
    articles = fetch_rss_news(max_per_feed=10)
    articles_text = "\n".join(
        f"- [{a['source']}] {a['title']}: {a['summary'][:150]}"
        for a in articles[:25]
    )
    result = _call_deepseek(
        "You are a news analysis expert. Group news articles into thematic clusters.",
        f"""Cluster these news articles into 4-6 thematic groups.
For each cluster: Cluster Name, Key Theme, Articles, Market Implication.
Write in both English and Chinese.

Articles:
{articles_text}""",
        temperature=0.3,
    )
    return jsonify({"result": result})

@app.route("/api/ai/query", methods=["POST"])
def api_ai_query():
    data = request.get_json()
    query = data.get("query", "")
    if not query:
        return jsonify({"result": "Please provide a query."}), 400
    cached = get_cached_data()
    context = ""
    if cached:
        for name, d in cached.get("stocks", {}).items():
            if isinstance(d, dict) and "error" not in d:
                context += f"{name}: ${d.get('price', 'N/A')} ({d.get('change_pct', 0):+.2f}%)\n"
    result = _call_deepseek(
        "You are a senior financial analyst. Be direct and data-driven. Use English and Chinese.",
        f"Current market data:\n{context}\n\nQuestion: {query}",
        temperature=0.3,
    )
    return jsonify({"result": result})

@app.route("/api/ai/valuation/<ticker>")
def api_ai_valuation(ticker):
    ticker = normalize_ticker(ticker)
    fundamentals = get_stock_fundamentals(ticker)
    comparables = get_comparable_companies(ticker)
    result = ai_stock_valuation(fundamentals, comparables)
    return jsonify({"result": result, "fundamentals": fundamentals})

@app.route("/api/ai/long-case/<ticker>")
def api_ai_long_case(ticker):
    ticker = normalize_ticker(ticker)
    fundamentals = get_stock_fundamentals(ticker)
    result = _call_deepseek(
        "You are a senior equity analyst at UBS. Write a compelling bull case.",
        f"""Write a detailed LONG (buy) investment case for this stock.
Include: growth drivers, competitive advantages, catalysts, valuation support, risk mitigation.
English for competition, with Chinese insights.

Fundamentals:
{json.dumps(fundamentals, indent=2, default=str)}""",
        temperature=0.3,
    )
    return jsonify({"result": result})

@app.route("/api/ai/short-case/<ticker>")
def api_ai_short_case(ticker):
    ticker = normalize_ticker(ticker)
    fundamentals = get_stock_fundamentals(ticker)
    result = _call_deepseek(
        "You are a senior equity analyst at UBS. Write a compelling bear case.",
        f"""Write a detailed SHORT (sell) investment case for this stock.
Include: structural weaknesses, competitive threats, valuation concerns, catalysts for decline.
English for competition, with Chinese insights.

Fundamentals:
{json.dumps(fundamentals, indent=2, default=str)}""",
        temperature=0.3,
    )
    return jsonify({"result": result})

@app.route("/api/ai/pair-analysis/<long_ticker>/<short_ticker>")
def api_ai_pair_analysis(long_ticker, short_ticker):
    long_ticker = normalize_ticker(long_ticker)
    short_ticker = normalize_ticker(short_ticker)
    long_data = get_stock_fundamentals(long_ticker)
    short_data = get_stock_fundamentals(short_ticker)
    result = compare_stocks_for_competition(long_data, short_data)
    return jsonify({"result": result})

@app.route("/api/ai/technical/<ticker>")
def api_ai_technical(ticker):
    """AI-powered technical analysis for a stock."""
    ticker = normalize_ticker(ticker)
    hist = get_stock_history(ticker, period="6mo")
    if hist.empty:
        return jsonify({"result": "No data available"})

    latest = hist.iloc[-1]
    ma20 = hist["Close"].rolling(20).mean().iloc[-1]
    ma60 = hist["Close"].rolling(60).mean().iloc[-1] if len(hist) > 60 else None
    rsi_delta = hist["Close"].diff()
    gain = rsi_delta.clip(lower=0).rolling(14).mean().iloc[-1]
    loss = (-rsi_delta).clip(lower=0).rolling(14).mean().iloc[-1]
    rsi = 100 - (100 / (1 + gain / loss)) if loss != 0 else 50

    month_ret = (hist["Close"].iloc[-1] / hist["Close"].iloc[-22] - 1) * 100 if len(hist) > 22 else 0
    three_mo_ret = (hist["Close"].iloc[-1] / hist["Close"].iloc[-66] - 1) * 100 if len(hist) > 66 else 0

    tech_data = f"""
Ticker: {ticker}
Latest Close: {latest['Close']:.2f}
MA20: {ma20:.2f}
MA60: {ma60:.2f if ma60 else 'N/A'}
RSI(14): {rsi:.1f}
1M Return: {month_ret:.2f}%
3M Return: {three_mo_ret:.2f}%
Volume (latest): {latest['Volume']:,.0f}
Price vs MA20: {'Above' if latest['Close'] > ma20 else 'Below'} ({((latest['Close']/ma20)-1)*100:.1f}%)
"""
    result = _call_deepseek(
        "You are a top technical analyst. Provide actionable analysis with English and Chinese.",
        f"""Provide technical analysis for this stock:
{tech_data}

Include:
1. Trend Analysis (uptrend/downtrend/sideways)
2. Key Support & Resistance levels
3. RSI interpretation
4. MA crossover signals
5. Volume analysis
6. Short-term trading outlook
7. Key risk levels

Be specific with price levels and actionable.""",
        temperature=0.2,
    )
    return jsonify({"result": result})

@app.route("/api/ai/reflection")
def api_ai_reflection():
    advantages = _call_deepseek(
        "You are an AI research analyst writing about AI capabilities in finance.",
        """Describe AI advantages in stock analysis for a UBS competition.
Cover: speed, sentiment analysis, pattern recognition, automated screening, systematic framework.
English with Chinese key points.""",
        temperature=0.3,
    )
    limitations = _call_deepseek(
        "You are an AI research analyst writing about AI limitations in finance.",
        """Describe AI limitations in stock analysis and where human judgment is essential.
Cover: hallucination risks, real-time judgment, management assessment, historical bias, nuanced knowledge.
English with Chinese key points. Be honest.""",
        temperature=0.3,
    )
    return jsonify({"advantages": advantages, "limitations": limitations})


@app.route("/health")
def health():
    """Health check endpoint for keep-alive pings."""
    return jsonify({"status": "ok", "timestamp": __import__("datetime").datetime.now().isoformat()})


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  ALPHA SIGNAL - Web Dashboard")
    print("  http://localhost:5000")
    print("  Pages: / /analysis /valuation /screener /charts /competition")
    print("=" * 60 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
