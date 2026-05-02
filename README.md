# Alpha Signal - AI Financial Intelligence System

> UBS Financial Elite Challenge 2026 | AI Analyst Module

## Quick Start (快速开始)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install resend
```

### 2. Configure Email (配置邮件发送)

Edit `.env` file. Choose ONE method:

#### Option A: Resend API (Recommended - 最简单)
1. Go to https://resend.com and sign up (free, 100 emails/day)
2. Get your API key from the dashboard
3. Add to `.env`:
```
RESEND_API_KEY=re_your_key_here
EMAIL_RECEIVER=first@example.com,second@example.com
```
**Note:** Free tier sends from `onboarding@resend.dev`. To use custom domain, upgrade.

#### Option B: Gmail SMTP
1. Create or use a Gmail account
2. Enable 2-Factor Authentication at https://myaccount.google.com/security
3. Create App Password: Google Account > Security > App Passwords > Create
4. Add to `.env`:
```
EMAIL_SENDER=your_gmail@gmail.com
EMAIL_PASSWORD=your_16_char_app_password
EMAIL_RECEIVER=first@example.com,second@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

#### Option C: QQ Mail (QQ邮箱)
1. QQ邮箱 > 设置 > 账户 > 开启SMTP服务 > 获取授权码
2. Add to `.env`:
```
EMAIL_SENDER=your_qq@qq.com
EMAIL_PASSWORD=your_authorization_code
EMAIL_RECEIVER=first@example.com,second@example.com
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
```

### 3. Test Run (测试运行)

```bash
# Generate email preview (no email sent)
python run_daily.py --preview

# Open email_preview.html in browser to see result

# Send actual email
python run_daily.py
```

### 4. Start Daily Scheduler (定时发送)

```bash
# Runs at the time set in .env (default 08:00)
python scheduler.py

# Or run immediately then continue scheduling
python scheduler.py --now
```

### 5. Web Dashboard (网页仪表盘)

```bash
python web_app.py
# Open http://localhost:5000
```

## Project Structure

```
├── .env                 # Configuration (API keys, email)
├── config.py            # Settings and stock watchlists
├── stock_data.py        # Stock price fetching (yfinance)
├── news_fetcher.py      # RSS news aggregation
├── ai_analyzer.py       # DeepSeek AI analysis (sentiment, keywords, valuation)
├── email_service.py     # Email sending (Resend / SMTP)
├── run_daily.py         # Daily pipeline executor
├── scheduler.py         # Automated daily scheduling
├── web_app.py           # Flask web dashboard
├── templates/           # HTML templates for web app
├── static/              # CSS styles
└── latest_data.json     # Cached data for dashboard
```

## AI Modules (比赛要求)

1. **AI Data Insights** - News clustering and trend detection
2. **Sentiment Analysis** - Multi-source financial sentiment scoring
3. **Keyword Extraction** - Key themes and entity recognition
4. **AI Valuation** - Automated stock valuation with comparable screening
5. **AI vs Human** - Comparison framework for AI and human analysis
6. **Personality AI** - "Alpha" (阿尔法) - AI analyst with daily mood based on market

## Tech Stack

- Python 3.11+
- DeepSeek API (LLM analysis)
- yfinance (stock data)
- Flask (web dashboard)
- Plotly (charts)
- Resend / SMTP (email)
