"""Email service for sending daily financial briefings."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from zoneinfo import ZoneInfo
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER, SMTP_SERVER, SMTP_PORT
from jinja2 import Template

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
LOCAL_TZ = ZoneInfo("Asia/Shanghai")
BLOCKED_EMAIL_RECEIVERS = {"dc22712@umac.mo"}

EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #0a0a0f;
    color: #e0e0e0;
    margin: 0;
    padding: 0;
  }
  .container {
    max-width: 700px;
    margin: 0 auto;
    background: #12121a;
    border: 1px solid #1e1e2e;
  }
  .header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    padding: 30px;
    text-align: center;
    border-bottom: 2px solid #e63946;
  }
  .header h1 {
    color: #ffffff;
    margin: 0;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 2px;
  }
  .header .subtitle {
    color: #a0a0b0;
    font-size: 13px;
    margin-top: 8px;
    letter-spacing: 1px;
  }
  .header .date {
    color: #e63946;
    font-size: 14px;
    margin-top: 5px;
    font-weight: 600;
  }
  .section {
    padding: 20px 30px;
    border-bottom: 1px solid #1e1e2e;
  }
  .section-title {
    color: #e63946;
    font-size: 16px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px;
    padding-bottom: 8px;
    border-bottom: 1px solid #2a2a3a;
  }
  .stock-card {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 10px;
    border-left: 3px solid #2a2a3a;
  }
  .stock-card.up { border-left-color: #00d26a; }
  .stock-card.down { border-left-color: #e63946; }
  .stock-name {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
  }
  .stock-ticker {
    color: #707090;
    font-size: 12px;
    margin-left: 8px;
  }
  .stock-price {
    font-size: 22px;
    font-weight: 700;
    margin: 5px 0;
  }
  .price-up { color: #00d26a; }
  .price-down { color: #e63946; }
  .stock-details {
    color: #8888a0;
    font-size: 12px;
    margin-top: 5px;
  }
  .index-row {
    display: inline-block;
    width: 48%;
    padding: 8px;
    margin: 2px 0;
    background: #1a1a2e;
    border-radius: 6px;
    font-size: 13px;
  }
  .news-item {
    padding: 10px 0;
    border-bottom: 1px solid #1a1a2e;
  }
  .news-title {
    color: #c0c0d0;
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
  }
  .news-title:hover { color: #e63946; }
  .news-source {
    color: #606080;
    font-size: 11px;
    margin-top: 3px;
  }
  .news-keywords {
    margin-top: 4px;
  }
  .keyword-tag {
    display: inline-block;
    background: #2a2a3e;
    color: #a0a0c0;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    margin: 2px;
  }
  .sentiment-bar {
    height: 8px;
    border-radius: 4px;
    background: #2a2a3a;
    margin: 10px 0;
    overflow: hidden;
  }
  .sentiment-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s;
  }
  .sentiment-bullish { background: linear-gradient(90deg, #00d26a, #00ff88); }
  .sentiment-bearish { background: linear-gradient(90deg, #e63946, #ff6b6b); }
  .sentiment-neutral { background: linear-gradient(90deg, #ffd60a, #ffed4a); }
  .ai-briefing {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 20px;
    line-height: 1.7;
    color: #c0c0d0;
    font-size: 14px;
    white-space: pre-wrap;
  }
  .footer {
    text-align: center;
    padding: 20px;
    color: #505070;
    font-size: 11px;
    background: #0a0a0f;
  }
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge-bull { background: #0a2e1a; color: #00d26a; }
  .badge-bear { background: #2e0a0f; color: #e63946; }
  .badge-neutral { background: #2e2a0a; color: #ffd60a; }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
  }
  th, td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #1e1e2e;
    font-size: 13px;
  }
  th {
    color: #8888a0;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
  }
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>{{ ai_name|upper }} SIGNAL</h1>
    <div class="subtitle">{% if ai_name == 'Sigma' %}Elite Institutional Intelligence | 财富自由之路{% else %}Your AI Bestie for Markets | 你的AI金融小伙伴{% endif %}</div>
    <div class="date">{{ date }}</div>
    {% if mood %}
    <div style="margin-top:12px;font-size:28px;">{{ mood.emoji }}</div>
    <div style="color:#c0c0d0;font-size:13px;margin-top:4px;font-style:italic;">"{{ mood.vibe }}"</div>
    <div style="margin-top:8px;">
      <span style="background:{% if mood.mood in ['ecstatic', 'euphoric'] %}#0a3e1a{% elif mood.mood in ['happy', 'calculated'] %}#1a2e1a{% elif mood.mood in ['calm', 'bored'] %}#1a1a2e{% elif mood.mood in ['concerned', 'predatory'] %}#2e2a0a{% else %}#2e0a0f{% endif %};
        color:{% if mood.mood in ['ecstatic', 'euphoric'] %}#00ff88{% elif mood.mood in ['happy', 'calculated'] %}#00d26a{% elif mood.mood in ['calm', 'bored'] %}#4361ee{% elif mood.mood in ['concerned', 'predatory'] %}#ffd60a{% else %}#e63946{% endif %};
        padding:4px 16px;border-radius:20px;font-size:12px;font-weight:700;letter-spacing:1px;">
        MOOD: {{ mood.mood|upper }}
      </span>
    </div>
    {% endif %}
  </div>

  <!-- Stock Watchlist -->
  <div class="section">
    <div class="section-title">📊 Stock Watchlist / 关注股票</div>
    {% for name, data in stocks.items() %}
    {% if 'error' not in data %}
    <div class="stock-card {{ 'up' if data.change_pct >= 0 else 'down' }}">
      <span class="stock-name">{{ name }}</span>
      <span class="stock-ticker">{{ data.ticker }}</span>
      <div class="stock-price {{ 'price-up' if data.change_pct >= 0 else 'price-down' }}">
        {{ data.price }}
        <span style="font-size:14px;">
          {{ '%+.2f'|format(data.change) }} ({{ '%+.2f'|format(data.change_pct) }}%)
        </span>
      </div>
      <div class="stock-details">
        Open: {{ data.open }} | High: {{ data.high }} | Low: {{ data.low }} | Vol: {{ "{:,}".format(data.volume) }}
      </div>
    </div>
    {% endif %}
    {% endfor %}
  </div>

  <!-- Market Indices -->
  <div class="section">
    <div class="section-title">🌍 Market Indices / 市场指数</div>
    <table>
      <tr>
        <th>Index</th>
        <th>Price</th>
        <th>Change</th>
      </tr>
      {% for name, data in indices.items() %}
      {% if 'error' not in data %}
      <tr>
        <td style="color:#fff;">{{ name }}</td>
        <td>{{ data.price }}</td>
        <td class="{{ 'price-up' if data.change_pct >= 0 else 'price-down' }}">
          {{ '%+.2f'|format(data.change_pct) }}%
        </td>
      </tr>
      {% endif %}
      {% endfor %}
    </table>
  </div>

  <!-- Sentiment Analysis -->
  {% if sentiment %}
  <div class="section">
    <div class="section-title">🧠 AI Sentiment Analysis / AI情绪分析</div>
    {% for topic, s in sentiment.items() %}
    <div style="margin-bottom:15px;">
      <strong style="color:#fff;">{{ topic }}</strong>
      {% if s.overall_sentiment is defined %}
      <span class="badge {{ 'badge-bull' if s.overall_sentiment == 'bullish' else ('badge-bear' if s.overall_sentiment == 'bearish' else 'badge-neutral') }}">
        {{ s.overall_sentiment|upper }}
      </span>
      {% endif %}
      {% if s.sentiment_score is defined %}
      <div class="sentiment-bar">
        <div class="sentiment-fill {{ 'sentiment-bullish' if s.sentiment_score > 0 else ('sentiment-bearish' if s.sentiment_score < 0 else 'sentiment-neutral') }}"
             style="width:{{ ((s.sentiment_score + 1) / 2 * 100)|int }}%"></div>
      </div>
      {% endif %}
      {% if s.analysis_cn is defined %}
      <div style="color:#8888a0;font-size:13px;">{{ s.analysis_cn }}</div>
      {% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- News Highlights -->
  {% for cat, articles in news.items() %}
  {% if articles %}
  <div class="section">
    <div class="section-title">
      {% if cat == 'xiaomi' %}🔷 Xiaomi News / 小米新闻
      {% elif cat == 'macro' %}🌐 Macro & Geopolitical / 宏观地缘
      {% elif cat == 'qqq_intel' %}💻 QQQ & Intel
      {% elif cat == 'tech' %}⚡ Tech Sector / 科技板块
      {% elif cat == 'market' %}📈 Market News / 市场动态
      {% else %}📰 {{ cat|title }}
      {% endif %}
    </div>
    {% for article in articles[:5] %}
    <div class="news-item">
      <a href="{{ article.link }}" class="news-title" style="color:#c0c0d0;">{{ article.title }}</a>
      <div class="news-source">{{ article.source }} · {{ article.published }}</div>
      {% if article.matched_keywords is defined %}
      <div class="news-keywords">
        {% for kw in article.matched_keywords[:4] %}
        <span class="keyword-tag">{{ kw }}</span>
        {% endfor %}
      </div>
      {% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}
  {% endfor %}

  <!-- AI Briefing -->
  {% if briefing %}
  <div class="section">
    <div class="section-title">🤖 AI Morning Briefing / AI晨报</div>
    <div class="ai-briefing">{{ briefing }}</div>
  </div>
  {% endif %}

  <!-- Keywords & Themes -->
  {% if keywords %}
  <div class="section">
    <div class="section-title">🔑 Key Themes / 关键主题</div>
    {% if keywords.keywords is defined %}
    <div style="margin-bottom:10px;">
      {% for kw in keywords.keywords[:10] %}
      <span class="keyword-tag" style="font-size:12px;padding:4px 12px;">{{ kw.word }}</span>
      {% endfor %}
    </div>
    {% endif %}
    {% if keywords.themes is defined %}
    {% for theme in keywords.themes[:5] %}
    <div style="color:#a0a0c0;font-size:13px;margin:5px 0;">
      <strong style="color:#fff;">{{ theme.theme }}</strong> - {{ theme.description }}
    </div>
    {% endfor %}
    {% endif %}
  </div>
  {% endif %}

  <!-- Footer -->
  <div class="footer">
    <p>{{ ai_name|upper }} SIGNAL | AI-Powered Financial Intelligence</p>
    <p>Generated by {% if ai_name == 'Sigma' %}Gemini AI{% else %}DeepSeek AI{% endif %} · {{ date }}</p>
    <p style="color:#404060;">UBS Financial Elite Challenge 2026</p>
  </div>
</div>
</body>
</html>
"""


def render_email(data: dict) -> str:
    """Render the email HTML template with data."""
    template = Template(EMAIL_TEMPLATE)
    return template.render(**data)


def _get_all_receivers(receiver: str = None) -> list:
    """Parse comma-separated receiver list."""
    raw = receiver or EMAIL_RECEIVER or ""
    addrs = [
        a.strip()
        for a in raw.split(",")
        if a.strip() and a.strip().lower() not in BLOCKED_EMAIL_RECEIVERS
    ]
    return addrs if addrs else []


def send_email_resend(subject: str, html_content: str, receiver: str = None) -> bool:
    """Send email via Resend API to all configured recipients."""
    recipients = _get_all_receivers(receiver)
    if not recipients:
        print("[Email] No recipients configured")
        return False
    if not RESEND_API_KEY:
        print("[Email] Resend API key not set")
        return False
    try:
        import resend
        resend.api_key = RESEND_API_KEY

        sent_any = False
        for addr in recipients:
            try:
                params = {
                    "from": "Alpha Signal <onboarding@resend.dev>",
                    "to": [addr],
                    "subject": subject,
                    "html": html_content,
                }
                email = resend.Emails.send(params)
                eid = email.get("id", "ok") if isinstance(email, dict) else str(email)
                print(f"[Email] Resend: sent to {addr} (id: {eid})")
                sent_any = True
            except Exception as e:
                print(f"[Email] Resend: failed {addr}: {e}")
        return sent_any
    except Exception as e:
        print(f"[Email] Resend failed: {e}")
        return False


def send_email_smtp(subject: str, html_content: str, receiver: str = None) -> bool:
    """Send email via Gmail SMTP to all recipients."""
    recipients = _get_all_receivers(receiver)
    if not recipients or not all([EMAIL_SENDER, EMAIL_PASSWORD]):
        print("[Email] SMTP config incomplete!")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Alpha Signal <{EMAIL_SENDER}>"
    msg["To"] = ", ".join(recipients)

    plain_text = "Please view this email in an HTML-compatible email client."
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()

        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
        server.quit()
        print(f"[Email] SMTP: sent to {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"[Email] SMTP failed: {e}")
        return False


def send_email(subject: str, html_content: str, receiver: str = None) -> bool:
    """Send email - tries SMTP first (supports all recipients), then Resend."""
    if EMAIL_SENDER and EMAIL_PASSWORD:
        return send_email_smtp(subject, html_content, receiver)
    elif RESEND_API_KEY:
        return send_email_resend(subject, html_content, receiver)
    else:
        print("[Email] ERROR: No email method configured!")
        return False


def send_daily_briefing(
    stocks: dict,
    indices: dict,
    news_categories: dict,
    sentiment: dict = None,
    briefing: str = None,
    keywords: dict = None,
    mood: dict = None,
    ai_name: str = "Alpha",
) -> bool:
    """Compose and send the daily briefing email."""
    now = datetime.now(LOCAL_TZ)
    date_str = now.strftime("%A, %B %d, %Y")

    mood_emojis = {
        "ecstatic": "🚀", "happy": "☀️", "calm": "☕",
        "concerned": "😟", "panicking": "🔥",
        "euphoric": "🍷", "calculated": "♟️", "bored": "🥱",
        "predatory": "🦅", "clinical": "🧊",
    }
    mood_name = mood.get("mood", "calm") if mood else "calm"
    mood_emoji = mood_emojis.get(mood_name, "📊")

    data = {
        "date": date_str,
        "stocks": stocks,
        "indices": indices,
        "news": news_categories,
        "sentiment": sentiment,
        "briefing": briefing,
        "keywords": keywords,
        "mood": mood,
        "ai_name": ai_name,
    }

    html = render_email(data)
    subject = f"{mood_emoji} {ai_name} Signal | {mood_name.title()} Day | {now.strftime('%Y-%m-%d')}"

    return send_email(subject, html)


def preview_email(
    stocks: dict,
    indices: dict,
    news_categories: dict,
    sentiment: dict = None,
    briefing: str = None,
    keywords: dict = None,
    mood: dict = None,
    ai_name: str = "Alpha",
) -> str:
    """Generate email HTML for preview (saves to file)."""
    date_str = datetime.now(LOCAL_TZ).strftime("%A, %B %d, %Y")

    data = {
        "date": date_str,
        "stocks": stocks,
        "indices": indices,
        "news": news_categories,
        "sentiment": sentiment,
        "briefing": briefing,
        "keywords": keywords,
        "mood": mood,
        "ai_name": ai_name,
    }

    html = render_email(data)

    preview_path = f"email_preview_{ai_name.lower()}.html"
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Email] Preview saved to {preview_path}")

    return html
