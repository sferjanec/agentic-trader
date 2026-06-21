# 🛰️ Autonomous Options Architecture & Momentum Execution Desk

An enterprise-grade, decoupled algorithmic financial environment designed for systematic market screening, multi-agent structural analysis, risk-modeled order construction, and transactional persistence. 

This architecture isolates high-speed mathematical asset filtering from resource-intensive multi-agent LLM parsing to maximize execution speed, maintain zero-token discovery overhead, and provide rigorous mathematical risk management before capital deployment.

---

## 🏗️ System Architecture & Workflow Pipeline

The environment is strictly decoupled into three distinct structural modules to enforce clean engineering boundaries:

```text
                                  [ S&P 100 Universe Source ]
                                               │
                        ┌───────────────────────┴───────────────────────┐
                        ▼                                               ▼
          [ Weekend / Options Lane ]                        [ Active Market Intraday Lane ]
          • python options_screener.py                      • python run_intraday_radar.py
                        │                                               │
              (15-Thread Math Filter)                         (15-Thread Velocity Filter)
                        │                                               │
                        ▼                                               ▼
          Leaderboard Output (Top 29)                       Velocity Output (±3.5% Swings)
                        │                                               │
              (Manual Asset Selection)                        (Auto-Pipes High-Vol Asset)
                        │                                               │
                        ▼                                               ▼
          ┌───────────────────────────┐                   ┌───────────────────────────┐
          │ options_pipeline.py       │                   │ intraday_desk.py          │
          ├───────────────────────────┤                   ├───────────────────────────┤
          │ • CrewAI Multi-Agent Desk │                   │ • Computes Floor Pivots   │
          │ • Risk Agent Validation   │                   │ • Extracts 14-Day ATR     │
          │ • JSON Ticket Engine      │                   │ • Formulates Stop/Targets │
          └─────────────┬─────────────┘                   └───────────────────────────┘
                        │
              (SQL Logging Hook)
                        │
                        ▼
          💾 trading_ledger.db (SQLite)
          • Row Audit & Distance Caching
```

## 📅 The Trader's Daily Operational Workflow

Follow this execution checklist to coordinate your active trading configurations depending on market hours and your strategic goals:

## 🌅 Pre-Market Routine (08:30 AM – 09:15 AM EST)
 **Audit Open Ledger Risk:** Check for expiring or vulnerable options contracts that require early exit or rolling maneuvers before the opening bell chaos:
  ```bash
  sqlite3 trading_ledger.db "SELECT ticker, strategy, short_strike, expiration_date FROM option_tickets WHERE (julianday(expiration_date) - julianday('now')) <= 7;"

  Target Core Watchlist: Update your hand-curated watchlist.txt file with any structural equity tickers you intend to analyze for long-term or swing-trade positions.

## 🔔 Active Market Sessions (09:45 AM – 04:00 PM EST)

Launch Background Day-Trading Radar: Fire up the continuous momentum stream script using a custom interval to run silently on a secondary terminal window. It will monitor the mega-cap universe and send text notifications to your phone when breakouts hit:

``` bash
python run_intraday_radar.py --interval 600
```

## 🌙 Post-Market & Weekends (Research & Derivatives Mode)
Run Systematic Options Sweeper: Query the broad S&P 100 database via the multi-threaded math filter to surface high-yield put candidates:

``` bash
python options_screener.py
```

## Trigger Multi-Agent Options Crew: 

Pass an alpha candidate from the screener array down to the AI agents to generate deep narrative risk checks, clear earnings traps, and export a sanitized JSON order ticket file:

``` bash
python options_pipeline.py PLTR bull_credit_spread
```
## 💻 Ubuntu / WSL2 Environment Setup Instructions
Follow these configuration baselines to deploy the system smoothly within a Windows Subsystem for Linux (WSL2) Ubuntu development environment.

1. System Dependencies and SQLite Configuration
Update your underlying Linux headers and ensure the native SQLite3 compiler libraries are present on your subsystem:

``` bash
sudo apt update && sudo apt upgrade -y
sudo apt install sqlite3 libsqlite3-dev build-essential git -y
```

2. Environment Verification & Dependency Layout
Navigate to your repository workspace directory, initialize your local isolated virtual environment, and pull your runtime libraries:

``` bash
cd ~/projects/agentic-trader
python3 -m venv venv
source venv/bin/activate
```

Install the explicit quantitative engineering dependencies:

``` bash
pip install --upgrade pip
pip install crewai yfinance pandas numpy requests
```

3. API Token and Configuration Export
The multi-agent crew requires your secure Large Language Model provider credentials. Export your workspace parameters safely within your terminal instance:

``` bash
export GEMINI_API_KEY="your_actual_gemini_api_key_here"
export ALERT_EMAIL_SENDER="your_gmail_account@gmail.com"
export ALERT_EMAIL_PASSWORD="your_16_digit_app_password"
export ALERT_SMS_TARGET="2165551234@vtext.com"
```
(To preserve these variables across subsystem restarts, append these strings directly into your local configuration user profile via echo 'export GEMINI_API_KEY="your_key"' >> ~/.bashrc)

## 📁 Repository Table Layout

```text
├── sp100_constituents.txt     # Raw comma-separated tracking string array of S&P mega-caps
├── watchlist.txt              # User-curated list of equities earmarked for long-term/swing analysis
├── options_screener.py        # 15-Thread zero-token quantitative mathematical sorting radar
├── run_intraday_radar.py      # Momentum velocity tracking monitor (±3.5% change gate with SMS alerts)
├── notifier.py                # Email-to-SMS Gateway message routing utility engine
├── intraday_desk.py           # Intraday geometry analyzer calculating ATR stops and ORB pivots
├── options_pipeline.py        # CrewAI Multi-Agent options orchestrator and JSON payload writer
├── trading_pipeline.py        # CrewAI Multi-Agent long-term and equity swing analysis system
├── database_manager.py        # SQLite persistence wrapper and parameterized SQL insertion logic
├── trading_ledger.db          # Local SQL relational database storing tracking logs
├── options_entry_blueprint.md # Markdown output blueprint generated by active agent analysis
└── order_routing_ticket.json  # Sanitized production-grade multi-leg order execution payload

```

## 🛡️ Risk & System Architecture Disclaimer

```text
This software repository represents an automated analytical framework built for educational, diagnostic, and risk-management research engineering purposes. It does not constitute financial advice, investment recommendations, or trade solicitation. Options trading involves substantial risk, margin maintenance hazards, and financial variance liabilities. Always verify JSON file output payloads against manual contract variables before mapping to execution brokers.
```