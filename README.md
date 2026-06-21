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

1. ** The Tactical Options Screening Desk (`options_screener.py`):** Runs concurrently across the S&P 100 via a 15-thread worker pool. Filters the universe using pure non-token mathematical gates (14-day RSI exhaustion, out-of-the-money open interest, and strict $-0.20$ Delta tracking boundaries) to isolate high-yield premium opportunities.
2. ** The Multi-Agent Orchestration Crew (`options_pipeline.py`):** An advanced CrewAI infrastructure that coordinates specialized AI agents (Equity Analyst, Macro Risk Controller, and Options Execution Engineer) to parse narrative news sentiment, check VIX thresholds, mitigate earnings landmines, and synthesize structural strategy markdown blueprints.
3. ** The Algorithmic JSON Ticket & Ledger Engine (`database_manager.py`):** Converts the crew's strategic output into a production-grade, sanitized multi-leg JSON execution payload, automatically updating real-time system clocks and committing parameters directly into a relational SQLite local database table (`trading_ledger.db`).
4. ** The Intraday Velocity Radar (`run_intraday_radar.py` & `intraday_desk.py`):** An automated market-hours utility that scans assets for momentum breakouts crossing a $\pm3.5\%$ threshold and immediately runs intraday geometry tracking to calculate institutional pivot floors, resistance profit targets, and protective volatility ATR stops.

```

## 💻 Ubuntu / WSL2 Environment Setup Instructions

Follow these configuration baselines to deploy the system smoothly within a Windows Subsystem for Linux (WSL2) Ubuntu development environment.

### 1. System Dependencies and SQLite Configuration
Update your underlying Linux headers and ensure the native SQLite3 compiler libraries are present on your subsystem:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install sqlite3 libsqlite3-dev build-essential git -y
```