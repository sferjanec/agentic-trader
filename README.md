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


The Tactical Options Screening Desk (options_screener.py): Runs concurrently across the S&P 100 via a 15-thread worker pool. Filters the universe using pure non-token mathematical gates (14-day RSI exhaustion, out-of-the-money open interest, and strict $-0.20$ Delta tracking boundaries) to isolate high-yield premium opportunities.

The Multi-Agent Orchestration Crew (options_pipeline.py): An advanced CrewAI infrastructure that coordinates specialized AI agents (Equity Analyst, Macro Risk Controller, and Options Execution Engineer) to parse narrative news sentiment, check VIX thresholds, mitigate earnings landmines, and synthesize structural strategy markdown blueprints.

The Algorithmic JSON Ticket & Ledger Engine (database_manager.py): Converts the crew's strategic output into a production-grade, sanitized multi-leg JSON execution payload, automatically updating real-time system clocks and committing parameters directly into a relational SQLite local database table (trading_ledger.db).

The Intraday Velocity Radar (run_intraday_radar.py & intraday_desk.py): An automated market-hours utility that scans assets for momentum breakouts crossing a $\pm3.5\%$ threshold and immediately runs intraday geometry tracking to calculate institutional pivot floors, resistance profit targets, and protective volatility ATR stops.

💻 Ubuntu / WSL2 Environment Setup Instructions
Follow these configuration baselines to deploy the system smoothly within a Windows Subsystem for Linux (WSL2) Ubuntu development environment.

1. System Dependencies and SQLite ConfigurationUpdate your underlying Linux headers and ensure the native SQLite3 compiler libraries are present on your subsystem:Bashsudo apt update && sudo apt upgrade -y
sudo apt install sqlite3 libsqlite3-dev build-essential git -y

2. Environment Verification & Dependency LayoutNavigate to your repository workspace directory, initialize your local isolated virtual environment, and pull your runtime libraries:Bashcd ~/projects/agentic-trader
python3 -m venv venv
source venv/bin/activate
Install the explicit quantitative engineering dependencies:Bashpip install --upgrade pip
pip install crewai yfinance pandas numpy

3. API Token and Configuration ExportThe multi-agent crew requires your secure Large Language Model provider credentials. Export your workspace parameters safely within your terminal instance:Bashexport GEMINI_API_KEY="your_actual_gemini_api_key_here"
(To preserve this variable across subsystem restarts, append this string directly into your local configuration user profile via echo 'export GEMINI_API_KEY="your_key"' >> ~/.bashrc)⚡ 

Execution Matrix: 
How To Run/Ensure your virtual environment is active (source venv/bin/activate) before invoking commands.Weekend Core Options WorkflowScan the S&P 100 universe for high-yield, mathematically sound put options:Bashpython options_screener.py

Review the console leaderboard results, select a target ticker (e.g., NVDA), and pass it directly to the multi-agent execution desk to generate compliance plans, sanitized order tickets, and log the transaction into your database:Bashpython options_pipeline.py nvda bull_credit_spread

Active Intraday Scalp & Swing WorkflowQuery the market velocity scanner to capture fast-moving institutional volume breakout targets and calculate short-term entry and exit pivot brackets:Bashpython run_intraday_radar.py

Auditing Your Persistent Ledger RowsInspect your local SQLite transaction rows directly out of the binary database index from your console:Bashsqlite3 trading_ledger.db "SELECT id, timestamp, ticker, strategy, short_strike, net_credit_or_debit FROM option_tickets;"

📁 Repository Table LayoutPlaintext.
├── sp100_constituents.txt     # Raw comma-separated tracking string array of asset nodes
├── options_screener.py        # 15-Thread zero-token quantitative mathematical sorting radar
├── run_intraday_radar.py      # Momentum velocity tracking monitor (±3.5% change gate)
├── intraday_desk.py           # Intraday geometry analyzer calculating ATR stops and pivots
├── options_pipeline.py        # CrewAI Multi-Agent orchestrator and prompt structure layer
├── database_manager.py        # SQLite persistence wrapper and parameterized SQL insertion logic
├── trading_ledger.db          # Local SQL relational database storing tracking logs
├── options_entry_blueprint.md # Markdown output blueprint generated by active agent analysis
└── order_routing_ticket.json  # Sanitized production-grade multi-leg order execution payload

🛡️ Risk & System Architecture Disclaimer: 
This software repository represents an automated analytical framework built for educational, diagnostic, and risk-management research engineering purposes. It does not constitute financial advice, investment recommendations, or trade solicitation. Options trading involves substantial risk, margin maintenance hazards, and financial variance liabilities. Always verify JSON file output payloads against manual contract variables before mapping to execution brokers.
---

### 💾 GitHub Initialization Directives

Since your database (`trading_ledger.db`) is a local binary file that updates constantly, **you do not want to push your database data to GitHub**. To ensure your git commits stay clean, create a `.gitignore` file in your directory right now:

```bash
nano .gitignore
Paste these lines into it to keep your scratchpads, API outputs, and environment variables out of your cloud repo:Plaintextvenv/
__pycache__/
*.db
options_entry_blueprint.md
order_routing_ticket.json         