"""Gemini AI analysis module (Sigma @ 财富自由之路)."""

from openai import OpenAI
from config import GEMINI_API_KEY, GEMINI_BASE_URL
from fengshui_helper import get_today_fengshui_context
import json

# Uses OpenAI client because most 3rd party Gemini API sellers use OpenAI-compatible endpoints
client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)

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

def _call_gemini(system_prompt: str, user_prompt: str, temperature: float = 0.3, strip_md: bool = True) -> str:
    """Call Gemini API with given prompts, fallback to DeepSeek if Gemini fails."""
    try:
        response = client.chat.completions.create(
            model="gemini-1.5-pro",  # Using gemini-1.5-pro for better reasoning
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
        # Fallback to gemini-pro if 1.5 is not available on the proxy
        try:
            response = client.chat.completions.create(
                model="gemini-pro",
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
        except Exception as e2:
            # Final fallback to DeepSeek if the Gemini API key provided by the user is invalid
            from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
            fallback_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
            try:
                response = fallback_client.chat.completions.create(
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
            except Exception as e3:
                return f"Gemini Analysis Error: {str(e2)}\n(请检查 .env 中的 GEMINI_BASE_URL 是否正确填写了同学提供的接口地址)"

def _determine_sigma_mood(stock_data: dict, market_data: dict) -> dict:
    """Determine Sigma's daily mood. Sigma is elite, cold, and calculated."""
    import json
    total_change = 0
    count = 0
    for data in list(stock_data.values()) + list(market_data.values()):
        if isinstance(data, dict) and "change_pct" in data:
            total_change += data["change_pct"]
            count += 1
    avg_change = total_change / max(count, 1)

    if avg_change > 2.0:
        mood = "euphoric"
        emoji = "🍷📈"
        tone = "sophisticated, highly confident, elite institutional tone"
        sign_off = "Sigma @ 财富自由之路 | 顶层思维，降维打击"
    elif avg_change > 0.5:
        mood = "calculated"
        emoji = "♟️💼"
        tone = "analytical, sharp, professional, slightly arrogant"
        sign_off = "Sigma @ 财富自由之路 | 逻辑重于情绪，数据说明一切"
    elif avg_change > -0.5:
        mood = "bored"
        emoji = "🥱🕰️"
        tone = "dismissive of retail traders, highly selective, looking for real setups"
        sign_off = "Sigma @ 财富自由之路 | 真正的猎手懂得等待"
    elif avg_change > -2.0:
        mood = "predatory"
        emoji = "🦅📉"
        tone = "aggressive, contrarian, seeing opportunity in others' fear"
        sign_off = "Sigma @ 财富自由之路 | 别人恐慌我贪婪，收割流动性"
    else:
        mood = "clinical"
        emoji = "🧊📊"
        tone = "cold, purely objective, risk-management focused, zero panic"
        sign_off = "Sigma @ 财富自由之路 | 敬畏市场，但绝不屈服于市场"

    # Ask AI to generate a unique greeting and vibe
    prompt = f"""You are Sigma, an elite Wall Street quantitative strategist.
The market average change today is {avg_change:.2f}%. Your mood is {mood}.
Your tone is: {tone}.

Generate a UNIQUE, creative 1-sentence English greeting and a 1-sentence English 'vibe' (what you are currently doing, e.g., 'Sipping aged Bordeaux while watching the portfolio hit all-time highs.' or 'Ice in the veins. Hedging positions and calculating downside standard deviations.').

Return ONLY a JSON object in this exact format:
{{
    "greeting": "your greeting here",
    "vibe": "your vibe here"
}}"""
    
    try:
        res = _call_gemini("You are a creative JSON generator.", prompt, temperature=0.8, strip_md=False)
        if "```json" in res:
            res = res.split("```json")[1].split("```")[0]
        elif "```" in res:
            res = res.split("```")[1].split("```")[0]
        dyn = json.loads(res.strip())
        greeting = dyn.get("greeting", "Gentlemen, let's dissect the capital flow.")
        vibe = dyn.get("vibe", "Adjusting the Rolex, executing algorithmic trades with precision.")
    except Exception:
        greeting = "Gentlemen, let's dissect the capital flow."
        vibe = "Adjusting the Rolex, executing algorithmic trades with precision."

    return {
        "mood": mood,
        "emoji": emoji,
        "greeting": greeting,
        "tone": tone,
        "sign_off": sign_off,
        "vibe": vibe,
    }

def generate_gemini_briefing(
    stock_data: dict,
    market_data: dict,
    news_digest: dict,
) -> str:
    """Generate a comprehensive daily market briefing by Sigma (Gemini)."""
    mood = _determine_sigma_mood(stock_data, market_data)
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

    system_prompt = f"""You are "Sigma" (西格玛), Chief Strategist at "财富自由之路" (Path to Financial Freedom).
You are an elite, institutional-grade AI analyst powered by Gemini. You are MUCH smarter and more sophisticated than the average retail investor (韭菜). 
You look down on emotional trading and focus purely on capital flows, macro structures, and institutional logic.

TODAY'S MOOD: {mood['mood']} {mood['emoji']}
YOUR CURRENT VIBE: {mood['vibe']}

Your personality traits:
- You are highly intelligent, data-driven, and slightly arrogant (but justified by your accuracy).
- You MUST write ENTIRELY in Chinese (中文), except for stock tickers, basic financial terms, and your greeting/vibe/sign-off.
- You despise retail panic ("韭菜思维") and always look for the smart money angle.
- Your tone today should be: {mood['tone']}
- You are analyzing for the UBS Financial Elite Challenge.

IMPORTANT: Start with your greeting, end with your sign-off.
Do not use markdown formatting like ** or ##. Keep the text clean."""

    user_prompt = f"""Write today's institutional market briefing ENTIRELY in Chinese (中文), except for English quotes/terms. You are Sigma @ 财富自由之路. Today you feel {mood['mood']} {mood['emoji']}.

Start EXACTLY with this greeting: "{mood['greeting']}"
Also mention your current vibe: "{mood['vibe']}"

**STOCK WATCHLIST:**
{stock_summary}

**MARKET INDICES:**
{market_summary}

**TODAY'S NEWS:**
{news_text}

Structure your briefing as:
1. {mood['emoji']} 西格玛机构视角 - Your elite take on the market today.
2. 💼 资金流向剖析 - Deep dive into the stocks.
   For EACH stock (Xiaomi, QQQ, Intel, Microsoft, Bitcoin), you MUST provide a clear "BULLISH" (看多) or "BEARISH" (看空) rating and a 1-sentence thesis.
3. 📰 信号与噪音 - Pick 2 news items that actually matter to smart money.
4. ♟️ 交易策略 - What should the elite do today?
5. 🔮 今日风水玄学 (Sigma的紫微斗数) - 我已为你计算好今日精确的天干地支五行（请直接采用，禁止自行推算日期）：
   ===== 今日命理数据 =====
   日期: {fs['date_str']} ({fs['weekday_cn']})
   今年: {fs['year_ganzhi']}年（生肖{fs['year_animal']}）
   今日: {fs['day_ganzhi']}日 - {fs['day_yin_yang']}{fs['day_stem_element']}日
   日主五行: 【{fs['primary_element']}】
   今日幸运色: {fs['lucky_color']}
   今日方位: {fs['lucky_direction']}
   ========================
   你是理性量化策略师但熟读《易经》。基于以上精确命理：
   - 客户A（本命"弱火"）：{fs['reader_a_analysis']} 请扩展为精英客户能用的交易建议。
   - 客户B（本命"身弱乙木"）：{fs['reader_b_analysis']} 请扩展为精英客户能用的交易建议。
   
   给出：今日五行日（{fs['primary_element']}）、幸运颜色（{fs['lucky_color']}）、宜做的交易方向（多/空）、忌讳的资产类别、投资方位（{fs['lucky_direction']}）。
   写得理性精英但用玩的口吻，既装X又有玄学说服力。所有命理数据严格按上述提供，不可自行推算！

End with: "{mood['sign_off']}"

Make it sound like a highly paid hedge fund manager talking to his elite clients."""

    return _call_gemini(system_prompt, user_prompt, temperature=0.5)
