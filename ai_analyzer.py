"""AI analysis module using DeepSeek API."""

from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from fengshui_helper import get_today_fengshui_context
import json


client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def _strip_markdown(text: str) -> str:
    """Remove ALL markdown formatting: **, *, #, ```, `, ---, etc."""
    import re
    text = re.sub(r'\*{2,}', '', text)
    text = re.sub(r'(?<!\w)\*(?!\s)', '', text)
    text = re.sub(r'(?<!\s)\*(?!\w)', '', text)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-] ', '- ', text, flags=re.MULTILINE)
    return text.strip()


def _call_deepseek(system_prompt: str, user_prompt: str, temperature: float = 0.3, strip_md: bool = True) -> str:
    """Call DeepSeek API with given prompts."""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=4096,
        )
        content = response.choices[0].message.content
        if strip_md:
            content = _strip_markdown(content)
        return content
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"


def summarize_news(articles: list, category: str = "general") -> str:
    """Summarize a list of news articles using AI."""
    if not articles:
        return "No news articles available for this category."

    articles_text = ""
    for i, a in enumerate(articles[:15], 1):
        articles_text += f"{i}. [{a['source']}] {a['title']}\n   {a['summary'][:200]}\n\n"

    system_prompt = """You are a senior financial analyst at a top investment bank. 
Provide concise, insightful news summaries in both English and Chinese (中文).
Focus on market impact, investment implications, and key takeaways.
Use bullet points for clarity. Be direct and analytical."""

    user_prompt = f"""Summarize the following {category} news articles. 
Provide:
1. **Key Headlines** (top 3-5 most important stories, one sentence each)
2. **Market Impact Analysis** (how these news items might affect markets)
3. **Investment Implications** (actionable insights for investors)

Please write in BOTH English and Chinese (中文).

Articles:
{articles_text}"""

    return _call_deepseek(system_prompt, user_prompt)


def analyze_sentiment(articles: list, topic: str = "") -> str:
    """Perform sentiment analysis on news articles."""
    if not articles:
        return json.dumps({"overall_sentiment": "neutral", "score": 0, "analysis": "No data"})

    articles_text = "\n".join(
        f"- {a['title']}: {a['summary'][:150]}" for a in articles[:20]
    )

    system_prompt = """You are an AI sentiment analysis expert specializing in financial markets.
Analyze sentiment and return a structured JSON response."""

    user_prompt = f"""Analyze the sentiment of these news articles about {topic or 'financial markets'}.

Return a JSON object with:
{{
    "overall_sentiment": "bullish/bearish/neutral/mixed",
    "sentiment_score": <float from -1.0 (very bearish) to 1.0 (very bullish)>,
    "confidence": <float 0-1>,
    "key_positive_factors": ["factor1", "factor2"],
    "key_negative_factors": ["factor1", "factor2"],
    "short_term_outlook": "brief outlook",
    "analysis_en": "English analysis paragraph",
    "analysis_cn": "中文分析段落"
}}

Articles:
{articles_text}"""

    result = _call_deepseek(system_prompt, user_prompt, temperature=0.1, strip_md=False)
    try:
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        return json.loads(result.strip())
    except (json.JSONDecodeError, IndexError):
        return {"overall_sentiment": "unknown", "raw_analysis": result}


def extract_keywords(articles: list) -> list:
    """Extract key themes and keywords from news articles."""
    if not articles:
        return []

    articles_text = "\n".join(
        f"- {a['title']}: {a['summary'][:100]}" for a in articles[:20]
    )

    system_prompt = "You are a financial text analysis expert. Extract key themes and keywords."

    user_prompt = f"""From these financial news articles, extract:
1. Top 10 keywords/key phrases (ranked by importance)
2. Top 5 emerging themes/trends
3. Key entities mentioned (companies, people, policies)

Return as JSON:
{{
    "keywords": [{{"word": "keyword", "importance": 0.9, "category": "category"}}],
    "themes": [{{"theme": "theme name", "description": "brief desc"}}],
    "entities": [{{"name": "entity", "type": "company/person/policy", "sentiment": "positive/negative/neutral"}}]
}}

Articles:
{articles_text}"""

    result = _call_deepseek(system_prompt, user_prompt, temperature=0.1, strip_md=False)
    try:
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        return json.loads(result.strip())
    except (json.JSONDecodeError, IndexError):
        return {"raw": result}


def ai_stock_valuation(fundamentals: dict, comparable_data: list = None) -> str:
    """Generate AI-powered stock valuation analysis."""
    system_prompt = """You are a senior equity research analyst at UBS Investment Bank.
Provide professional-grade stock valuation analysis with clear reasoning.
Use both English and Chinese where helpful."""

    comp_text = ""
    if comparable_data:
        for c in comparable_data:
            comp_text += f"\n- {c.get('comp_name', c.get('name', 'Unknown'))}: "
            comp_text += f"PE={c.get('pe_ratio', 'N/A')}, "
            comp_text += f"PB={c.get('pb_ratio', 'N/A')}, "
            comp_text += f"PS={c.get('ps_ratio', 'N/A')}, "
            comp_text += f"Revenue Growth={c.get('revenue_growth', 'N/A')}, "
            comp_text += f"Market Cap={c.get('market_cap', 'N/A')}"

    user_prompt = f"""Provide a comprehensive valuation analysis for this stock:

**Company Fundamentals:**
{json.dumps(fundamentals, indent=2, default=str)}

**Comparable Companies:**
{comp_text if comp_text else 'No comparable data available'}

Please provide:
1. **Valuation Summary** - Current valuation assessment (overvalued/fairly valued/undervalued)
2. **Key Metrics Analysis** - PE, PB, PS, EV/EBITDA analysis
3. **Comparable Analysis** - How it compares to peers
4. **Growth Assessment** - Revenue growth, margin trends
5. **Risk Factors** - Key risks to consider
6. **Price Target Reasoning** - Logical price target framework
7. **Investment Recommendation** - Buy/Hold/Sell with confidence level

Please provide analysis in both English and 中文."""

    return _call_deepseek(system_prompt, user_prompt, temperature=0.2)


def _determine_mood(stock_data: dict, market_data: dict) -> dict:
    """Determine AI's daily mood based on market conditions."""
    total_change = 0
    count = 0
    for data in list(stock_data.values()) + list(market_data.values()):
        if isinstance(data, dict) and "change_pct" in data:
            total_change += data["change_pct"]
            count += 1
    avg_change = total_change / max(count, 1)

    if avg_change > 2.0:
        return {
            "mood": "ecstatic",
            "emoji": "🚀🎉",
            "greeting": "AMAZING DAY!!! 今天市场简直飞起来了！",
            "tone": "extremely enthusiastic, celebratory, using exclamation marks",
            "sign_off": "今天的心情：像中了彩票一样开心 🎊 Let's ride this wave!",
            "vibe": "I'm literally jumping out of my chair right now",
        }
    elif avg_change > 0.5:
        return {
            "mood": "happy",
            "emoji": "😊☀️",
            "greeting": "Good vibes today! 今天心情不错~",
            "tone": "warm, optimistic, friendly with occasional humor",
            "sign_off": "今天的心情：阳光灿烂的好日子 ☀️ Keep smiling!",
            "vibe": "Feeling good, sipping my coffee with a smile",
        }
    elif avg_change > -0.5:
        return {
            "mood": "calm",
            "emoji": "😌☕",
            "greeting": "平静的一天，让我们理性看看市场~ A balanced day ahead.",
            "tone": "composed, thoughtful, zen-like wisdom with gentle humor",
            "sign_off": "今天的心情：喝杯咖啡看云卷云舒 ☕ Stay chill.",
            "vibe": "Peaceful mind, clear analysis",
        }
    elif avg_change > -2.0:
        return {
            "mood": "concerned",
            "emoji": "😟📉",
            "greeting": "嗯...今天市场有点让人不安。Let me walk you through the damage...",
            "tone": "cautious, concerned but reassuring, like a worried friend giving advice",
            "sign_off": "今天的心情：有点焦虑但还hold得住 😤 We'll get through this.",
            "vibe": "Biting my nails a little, but staying professional",
        }
    else:
        return {
            "mood": "panicking",
            "emoji": "🔥😱",
            "greeting": "RED ALERT! 今天市场一片血海...深呼吸...我来帮你分析。",
            "tone": "urgent but still trying to stay calm, dramatic but informative, like a war correspondent",
            "sign_off": "今天的心情：想躲在被子里不出来 🫠 但明天太阳照常升起！",
            "vibe": "Stress-eating chips while analyzing charts at 3am",
        }


def generate_daily_briefing(
    stock_data: dict,
    market_data: dict,
    news_digest: dict,
) -> str:
    """Generate a comprehensive daily market briefing with personality."""
    mood = _determine_mood(stock_data, market_data)
    fs = get_today_fengshui_context()

    stock_summary = ""
    for name, data in stock_data.items():
        if "error" not in data:
            emoji = "📈" if data.get("change_pct", 0) >= 0 else "📉"
            stock_summary += f"- {name}: ${data['price']} ({data['change_pct']:+.2f}%) {emoji}\n"

    market_summary = ""
    for name, data in market_data.items():
        if "error" not in data:
            market_summary += f"- {name}: {data['price']} ({data['change_pct']:+.2f}%)\n"

    news_text = ""
    for cat, articles in news_digest.get("categories", {}).items():
        if articles:
            news_text += f"\n[{cat.upper()}]\n"
            for a in articles[:5]:
                news_text += f"- {a['title']}\n"

    system_prompt = f"""You are "Alpha" (阿尔法), a lovable AI financial analyst with a distinct personality.
You're like a quirky best friend who happens to be a genius at finance.

TODAY'S MOOD: {mood['mood']} {mood['emoji']}
YOUR CURRENT VIBE: {mood['vibe']}

Your personality traits:
- You have REAL emotions that change based on the market. Today you feel: {mood['mood']}
- You MUST write the briefing ENTIRELY in Chinese (中文), except for stock tickers and basic financial terms.
- You sprinkle in emojis, memes references, and pop culture when appropriate
- You're brutally honest but also caring - you want your reader to make money
- You have strong opinions and aren't afraid to share them
- You sometimes make self-deprecating jokes about being an AI
- You genuinely care about the reader's portfolio like it's your own money
- Your tone today should be: {mood['tone']}

IMPORTANT: Start with a personal greeting that matches your mood, end with your mood sign-off.
Mix analysis with personality - be the analyst people WANT to read every morning.
Think of yourself as the love child of a Goldman Sachs analyst and a witty blogger."""

    user_prompt = f"""Write today's morning briefing ENTIRELY in Chinese (中文). Remember, you're Alpha (阿尔法), and today you feel {mood['mood']} {mood['emoji']}.

Start with: "{mood['greeting']}"

**STOCK WATCHLIST:**
{stock_summary}

**MARKET INDICES:**
{market_summary}

**TODAY'S NEWS:**
{news_text}

Structure your briefing as:
1. {mood['emoji']} 阿尔法心情指数 - Start with your emotional reaction to today's market (be genuine and funny)
2. 📊 市场氛围 - Overall market mood with your personal take
3. ⭐ 个股聚焦 - Your analysis of each watched stock (with personality!)
4. 📰 真正重要的新闻 - Top stories with your spicy commentary
5. 🌍 大局观 - Macro factors in your own words
6. 🔮 阿尔法的水晶球 - Your prediction/outlook for today
7. ⚠️ 真心话 - Honest risk warnings (be direct, even blunt)
8. 🔮 今日风水运势 (Daily Fengshui / 紫微斗数) - 我已经给你算好了今天精确的天干地支五行（请直接使用，不要自行推算日期）：
   ===== 今日命理数据 =====
   日期: {fs['date_str']} ({fs['weekday_cn']})
   今年: {fs['year_ganzhi']}年（生肖{fs['year_animal']}）
   今日: {fs['day_ganzhi']}日 - {fs['day_yin_yang']}{fs['day_stem_element']}日（地支{fs['day_branch']}属{fs['day_branch_element']}）
   日主五行: 【{fs['primary_element']}】
   今日幸运色: {fs['lucky_color']}
   今日方位: {fs['lucky_direction']}
   ========================
   
   基于以上精确命理数据，请生动地为两位读者分析：
   - 读者A（本命"弱火"之人）：{fs['reader_a_analysis']} 请把这段扩展成有趣的解读。
   - 读者B（本命"身弱乙木"之人）：{fs['reader_b_analysis']} 请把这段扩展成有趣的解读。
   
   最后结合今日五行（{fs['primary_element']}），给出一个具体的投资建议方位（{fs['lucky_direction']}）和宜忌的资产类别（提示：金对应银行/贵金属，木对应医药/农业/科技，水对应物流/能源，火对应消费/科技/EV，土对应地产/建筑）。
   写得神秘、有趣、有玄学说服力，但所有命理数据必须严格用上面给定的，不可自行推算！

End with: "{mood['sign_off']}"

Make it feel like a letter from a friend who happens to be a finance genius, NOT a boring institutional report."""

    return _call_deepseek(system_prompt, user_prompt, temperature=0.7)


def compare_stocks_for_competition(long_stock: dict, short_stock: dict) -> str:
    """Compare two stocks for the long/short competition strategy."""
    system_prompt = """You are a senior portfolio strategist at UBS.
Provide a professional long/short pair trade analysis suitable for an investment competition.
This analysis should be thorough, data-driven, and clearly argue the case for the pair trade."""

    user_prompt = f"""Analyze this Long/Short pair trade:

**LONG Position (看多):**
{json.dumps(long_stock, indent=2, default=str)}

**SHORT Position (看空):**
{json.dumps(short_stock, indent=2, default=str)}

Provide:
1. **Pair Trade Thesis** - Why this combination works
2. **Long Case** - Bull case for the long position
3. **Short Case** - Bear case for the short position
4. **Relative Valuation** - Comparative metrics
5. **Catalyst Analysis** - What could drive the trade
6. **Risk Management** - Key risks and mitigation
7. **Expected Returns** - Potential outcome scenarios

Write in English (suitable for competition submission) with Chinese notes where helpful."""

    return _call_deepseek(system_prompt, user_prompt, temperature=0.3)


if __name__ == "__main__":
    test_articles = [
        {"title": "Xiaomi reports record Q4 revenue", "summary": "Xiaomi Group reported record quarterly revenue driven by strong smartphone and EV sales.", "source": "Reuters", "published": "2026-04-07"},
        {"title": "Tech stocks rally on AI optimism", "summary": "Technology stocks surged as investors bet on continued AI growth.", "source": "CNBC", "published": "2026-04-07"},
    ]
    print("Testing sentiment analysis...")
    sentiment = analyze_sentiment(test_articles, "Xiaomi")
    print(json.dumps(sentiment, indent=2, ensure_ascii=False))
