import os
import yfinance as yf
import pandas as pd
import numpy as np

# Configuration paths
INPUT_FILE = "watchlist.txt"
OUTPUT_FILE = "screener_report.md"

def load_watchlist(file_path):
    """Reads tickers from a text file, ignoring empty lines and comments."""
    if not os.path.exists(file_path):
        # Fallback default if the file hasn't been created yet
        print(f"⚠️ Warning: '{file_path}' not found. Using a temporary mini-watchlist.")
        return ["AAPL", "MSFT", "GOOGL"]
        
    with open(file_path, "r") as f:
        # Strip whitespace and filter out empty lines or line comments
        tickers = [line.strip().upper() for line in f if line.strip() and not line.strip().startswith("#")]
    return tickers

def screen_ticker(ticker: str):
    """
    Programmatically evaluates a single ticker against Chapter 10 technical rules.
    Returns (metrics_dict, None) if it passes, or (None, failure_reason_string) if it fails.
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if df.empty or len(df) < 50:
            return None, "Insufficient data rows"
            
        # 1. Calculate Technical Moving Averages
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # 2. Calculate 14-Day RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / np.where(loss == 0, 0.00001, loss)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Grab the absolute latest historical metrics
        latest = df.iloc[-1]
        current_price = latest['Close']
        sma_20 = latest['SMA_20']
        sma_50 = latest['SMA_50']
        rsi = latest['RSI']
        
        if pd.isna(sma_20) or pd.isna(sma_50) or pd.isna(rsi):
            return None, "NaN values in calculation warm-up"

        # --- EVALUATE MATRIX CONSTRAINTS ---
        if not (current_price > sma_50):
            return None, f"Bearish Macro Trend (Price ${current_price:.2f} <= 50-SMA ${sma_50:.2f})"
            
        if not (current_price < sma_20):
            return None, f"No Pullback (Price ${current_price:.2f} >= 20-SMA ${sma_20:.2f})"
            
        if not (rsi < 45.0):
            return None, f"Overextended Momentum (RSI {rsi:.1f} >= 45)"
            
        # If all constraints pass
        return {
            "Ticker": ticker,
            "Current Price": round(current_price, 2),
            "20-Day SMA": round(sma_20, 2),
            "50-Day SMA": round(sma_50, 2),
            "RSI": round(rsi, 2)
        }, None
            
    except Exception as e:
        return None, f"API Exception: {str(e)}"

if __name__ == "__main__":
    watchlist = load_watchlist(INPUT_FILE)
    print(f"Initializing Tier 1 Screener for {len(watchlist)} assets from '{INPUT_FILE}'...")
    print("Scanning data structures using zero LLM tokens...\n")
    
    qualified_candidates = []
    skipped_log = []
    
    for ticker in watchlist:
        metrics, rejection_reason = screen_ticker(ticker)
        if metrics:
            qualified_candidates.append(metrics)
            print(f"🔥 MATCH FOUND: {ticker} passes filtering constraints.")
            print(f"   Price: ${metrics['Current Price']} | RSI: {metrics['RSI']}")
        else:
            skipped_log.append((ticker, rejection_reason))
            print(f"• {ticker.ljust(5)}: Skipped -> {rejection_reason}")
            
    # --- EXPORT TO MARKDOWN FILE ---
    with open(OUTPUT_FILE, "w") as md:
        md.write("# Tier 1 Automated Watchlist Screener Report\n\n")
        md.write(f"**Source File:** `{INPUT_FILE}`  \n")
        md.write(f"**Total Assets Scanned:** {len(watchlist)}  \n\n")
        
        md.write("## 🎯 Qualified Candidates Passed to Agent Committee\n\n")
        if qualified_candidates:
            md.write("| Ticker | Current Price | 20-Day SMA | 50-Day SMA | RSI (14-Day) |\n")
            md.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for c in qualified_candidates:
                md.write(f"| **{c['Ticker']}** | ${c['Current Price']} | ${c['20-Day SMA']} | ${c['50-Day SMA']} | {c['RSI']} |\n")
        else:
            md.write("*No assets currently meet the macro pullback criteria.*\n")
            
        md.write("\n## 🛑 Skipped Assets Audit Trail\n\n")
        md.write("| Ticker | Reason for Exclusion |\n")
        md.write("| :--- | :--- |\n")
        for ticker, reason in skipped_log:
            md.write(f"| {ticker} | {reason} |\n")
            
    print("\n==============================================")
    print(f"📝 REPORT EXPORTED SUCCESSFULLY TO: {OUTPUT_FILE}")
    print("==============================================")