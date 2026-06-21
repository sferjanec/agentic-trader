import os
os.environ["OTEL_SDK_DISABLED"] = "true"  # Blocks telemetry network hangs completely
import yfinance as yf
import pandas as pd
import numpy as np
import time
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from crewai import LLM
import argparse
import sys
from watchlist_screener import load_watchlist, screen_ticker, INPUT_FILE
from concurrent.futures import ThreadPoolExecutor

OUTPUT_FILE = "final_trading_directive.md"

# ==========================================
# 1. ENVIRONMENT & LLM INITIALIZATION
# ==========================================
gemini_llm = LLM(
    model="gemini/gemini-2.5-flash",  
    temperature=0.1
)

# ==========================================
# 2. TOOL DEFINITIONS (Chapters 3 & 10)
# ==========================================

@tool("Fetch Stock Fundamentals")
def fetch_fundamental_ratios(ticker: str) -> str:
    """Extracts balance sheet metrics and corporate valuation ratios."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        metrics = {
            "Ticker": ticker,
            "Current Ratio (Liquidity)": info.get("currentRatio"),
            "Quick Ratio": info.get("quickRatio"),
            "Debt to Equity (Leverage)": info.get("debtToEquity"),
            "Trailing P/E": info.get("trailingPE"),
            "Forward P/E": info.get("forwardPE"),
            "PEG Ratio": info.get("pegRatio"),
            "Dividend Yield": info.get("dividendYield")
        }
        return pd.Series(metrics).to_string()
    except Exception as e:
        return f"Error retrieving fundamental data for {ticker}: {str(e)}"
    
@tool("Compute Chart Technical Indicators")
def compute_technical_indicators(ticker: str) -> str:
    """Use this tool to evaluate price trend momentum, Bollinger Band boundaries, and RSI positions."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if df.empty:
            return f"Error: yfinance returned an empty DataFrame for ticker {ticker}."
            
        if len(df) < 50:
            return f"Error: Found only {len(df)} data points for {ticker}. Need at least 50."
            
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['BB_Middle'] = df['SMA_20']
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / np.where(loss == 0, 0.00001, loss)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        latest = df.iloc[-1]
        
        if pd.isna(latest['SMA_50']) or pd.isna(latest['RSI']):
            return f"Error: Technical indicators computed as NaN for {ticker}."

        metrics = {
            "Ticker": ticker,
            "Current Closing Price": round(latest['Close'], 2),
            "20-Day SMA": round(latest['SMA_20'], 2),
            "50-Day SMA": round(latest['SMA_50'], 2),
            "BB Upper Band": round(latest['BB_Upper'], 2),
            "BB Lower Band": round(latest['BB_Lower'], 2),
            "RSI (14-Day)": round(latest['RSI'], 2)
        }
        return pd.Series(metrics).to_string()
    except Exception as e:
        return f"Exception occurred while computing technical indicator matrices for {ticker}: {str(e)}"

# ==========================================
# 3. CREW FACTORY FUNCTION (Thread-Safe Isolation)
# ==========================================
def create_trading_crew():
    """Generates a fresh, isolated Crew instance to prevent thread cross-contamination."""
    fundamental_analyst = Agent(
        role='Lead Fundamental Value Analyst',
        goal='Determine structural value health and rule out corporate credit risk.',
        backstory='A meticulous equity researcher who parses fundamental financial ratios to find solid balance sheets.',
        verbose=True,
        max_iter=2,
        llm=gemini_llm,
        tools=[fetch_fundamental_ratios]
    )

    technical_analyst = Agent(
        role='Quantitative Chart Analyst',
        goal='Pinpoint immediate trade entry/exit thresholds and check overbought or oversold limits.',
        backstory='A rule-driven financial quant who evaluates historical price metrics and standard deviation envelopes.',
        verbose=True,
        max_iter=2,
        llm=gemini_llm,
        tools=[compute_technical_indicators]
    )

    risk_manager = Agent(
        role='Chief Risk Officer',
        goal='Enforce capital preservation, outline strict stop-loss boundaries, and determine final position sizing limits.',
        backstory='A conservative manager whose primary focus is preventing capital drawdown. Synthesizes inputs to formulate a final execution command.',
        verbose=True,
        max_iter=2,
        llm=gemini_llm
    )

    fundamental_task = Task(
        description='Analyze the underlying value health of the target ticker: {target_ticker}. Identify structural flaws or extreme debt risks.',
        expected_output='A clear report detailing valuation metrics, margin stability, and financial safety.',
        agent=fundamental_analyst
    )

    technical_task = Task(
        description='Examine current price velocity for {target_ticker}. Check if the closing price sits near the Upper or Lower Bollinger Bands, and evaluate RSI levels.',
        expected_output='A momentum profile indicating whether the asset is technically extended, range-bound, or finding a floor.',
        agent=technical_analyst
    )

    execution_task = Task(
        description='''
        Review the fundamental report and technical analysis for {target_ticker}. 
        Formulate a clear investment decision (BUY, SELL, or HOLD). 
        If recommending a BUY or SELL, provide specific risk rules:
        1. A clear entry trigger price.
        2. A strict protective stop-loss level.
        3. Suggested position sizing rule (e.g., maximum 2% of capital allocation).
        ''',
        expected_output='A final, actionable trade execution directive including a clear trade thesis and risk parameters.',
        agent=risk_manager
    )

    return Crew(
        agents=[fundamental_analyst, technical_analyst, risk_manager],
        tasks=[fundamental_task, technical_task, execution_task],
        process=Process.sequential, 
        verbose=True,
        memory=False
    )

# ==========================================
# 4. PARALLEL WORKER EXECUTION LOOP
# ==========================================
def process_single_ticker(ticker, metrics):
    """Isolates the CrewAI execution loop for a single asset so it can run concurrently."""
    print(f"🤖 Deploying Parallel Gemini Agent Committee for: {ticker}...")
    ticker_start = time.time()

    try:
        # Generate a fresh, un-locked crew instance for this worker thread
        local_crew = create_trading_crew()
        
        crew_output = local_crew.kickoff(inputs={
            'target_ticker': ticker,
            'pre_calculated_metrics': str(metrics)
        })

        ticker_duration = time.time() - ticker_start
        print(f"⏱️  [Performance] {ticker} Agent Audit completed in {ticker_duration:.2f} seconds.")

        # Capture metrics before thread completes
        captured_usage = local_crew.usage_metrics

        # Cleaned up return statement matching exactly what we unpack below!
        return ticker, metrics, crew_output, captured_usage, ticker_duration
    except Exception as e:
        print(f"❌ Error processing {ticker}: {str(e)}")
        return ticker, metrics, None, None, 0.0

# ==========================================
# 5. MAIN SYSTEM ORCHESTRATOR
# ==========================================
if __name__ == "__main__":
    global_start = time.time()

    parser = argparse.ArgumentParser(description="High-Performance Agentic Trading Pipeline")
    parser.add_argument("--use-screener", type=str, default="true")
    parser.add_argument("--ticker", type=str, default=None)
    
    args = parser.parse_args()
    use_screener_flag = args.use_screener.lower() == "true"
    target_ticker = args.ticker.upper() if args.ticker else None
    
    if not use_screener_flag and not target_ticker:
        print("\n🛑 Execution Stopped: Safe Exit Enforced.")
        sys.exit(0)

    tickers_to_process = []

    if use_screener_flag:
        print(f"🔄 Running Tier 1 Screener against '{INPUT_FILE}'...")
        watchlist = load_watchlist(INPUT_FILE)
        
        for ticker in watchlist:
            metrics_dict, _ = screen_ticker(ticker)
            if metrics_dict:
                tickers_to_process.append((ticker, metrics_dict))
                
        print(f"\nScreener complete. Found {len(tickers_to_process)} target assets.")
        if not tickers_to_process:
            print("No assets passed today. Terminating.")
            sys.exit(0)
            
    elif target_ticker:
        print(f"🎯 Direct forced entry mode for: {target_ticker}")
        metrics_dict, _ = screen_ticker(target_ticker)
        
        if not metrics_dict:
            try:
                stock = yf.Ticker(target_ticker)
                df = stock.history(period="1y")
                df['SMA_20'] = df['Close'].rolling(window=20).mean()
                df['SMA_50'] = df['Close'].rolling(window=50).mean()
                df['BB_Middle'] = df['SMA_20']
                df['BB_Std'] = df['Close'].rolling(window=20).std()
                latest = df.iloc[-1]
                
                metrics_dict = {
                    "Ticker": target_ticker,
                    "Current Price": round(latest['Close'], 2),
                    "20-Day SMA": round(latest['SMA_20'], 2),
                    "50-Day SMA": round(latest['SMA_50'], 2),
                    "BB Upper Band": round(latest['SMA_20'] + (latest['BB_Std'] * 2), 2),
                    "BB Lower Band": round(latest['SMA_20'] - (latest['BB_Std'] * 2), 2),
                    "RSI (14-Day)": "Available via tool"
                }
            except Exception:
                metrics_dict = {"Ticker": target_ticker, "Current Price": "Fetched via tool"}
                
        tickers_to_process.append((target_ticker, metrics_dict))

    # --- INITIALIZE MASTER FILE ---
    with open(OUTPUT_FILE, "w") as f:
        f.write("# 📋 Master High-Performance Trading Committee Directive Report\n")
        f.write(f"**Generated on:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write("--- \n\n")

    # --- TIER 2 MULTI-THREADED AGENT EXECUTION ---
    print(f"🚀 Launching Parallel Processing Thread Pool for {len(tickers_to_process)} assets...\n")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_single_ticker, t, m) for t, m in tickers_to_process]
        
        for future in futures:
            # Unpacks the exactly matching 5-element tuple safely!
            ticker, metrics, crew_output, usage_metrics, duration = future.result()
            
            if not crew_output:
                continue
                
            with open(OUTPUT_FILE, "a") as f:
                f.write(f"## 📊 Execution Directive for: {ticker}\n\n")
                f.write(f"### 📈 Raw Ingestion Metrics (Pre-Calculated Snapshot)\n")
                f.write("| Technical Metric | Value |\n| :--- | :--- |\n")
                for k, v in metrics.items():
                    f.write(f"| **{k}** | {v} |\n")
                f.write("\n")
                
                f.write(f"### 🧠 Committee Consensus & Breakdown\n")
                f.write(f"{crew_output.raw}\n\n")
                
                f.write("### 🧮 Performance & Token Accounting Trace\n")
                f.write(f"- **Execution Time:** {duration:.2f} seconds\n")
                if usage_metrics:
                    f.write(f"- **Input Tokens:** {getattr(usage_metrics, 'prompt_tokens', 0):,}\n")
                    f.write(f"- **Output Tokens:** {getattr(usage_metrics, 'completion_tokens', 0):,}\n")
                f.write("\n---\n\n")
            
            print(f"✅ Concurrently appended {ticker} details completely to {OUTPUT_FILE}.")

    total_pipeline_time = time.time() - global_start
    
    print(f"\n==============================================")
    print(f"🏁 ALL TARGET AUDITS COMPLETE. REPORT: {OUTPUT_FILE}")
    print(f"⏱️  Total Pipeline Execution Time: {total_pipeline_time:.2f} seconds")
    print("==============================================")