import os
import sys
import math
import time
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

def load_tickers_from_file(filename="sp100_constituents.txt"):
    """Reads a comma-separated list of tickers from a local text file."""
    try:
        with open(filename, "r") as f:
            content = f.read().strip()
            # Split by comma and strip extra whitespaces or newlines
            tickers = [t.strip().upper() for t in content.split(",") if t.strip()]
            return tickers
    except Exception as e:
        print(f"❌ Failed to read {filename}: {str(e)}")
        sys.exit(1)

def analyze_option_opportunity(ticker):
    """
    Performs fast math filtering on an asset to verify IV and premium yield metrics.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Pull historical data for pullback verification
        df = stock.history(period="3mo")
        if df.empty or len(df) < 20:
            return None
            
        # 14-Day RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / np.where(loss == 0, 0.00001, loss)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        current_price = df['Close'].iloc[-1]
        
        # Target broad month-out chain cycles
        expirations = stock.options
        if not expirations:
            return None
            
        today = datetime.today()
        selected_expiry = next((exp for exp in expirations if 30 <= (datetime.strptime(exp, "%Y-%m-%d") - today).days <= 45), expirations[0])
        dte = (datetime.strptime(selected_expiry, "%Y-%m-%d") - today).days
        
        chain = stock.option_chain(selected_expiry)
        puts = chain.puts
        
        otm_puts = puts[(puts['openInterest'] > 10) & (puts['strike'] < current_price)].copy()
        if otm_puts.empty:
            return None
            
        avg_iv = otm_puts['impliedVolatility'].mean()
        expected_move_floor = current_price - (current_price * avg_iv * math.sqrt(dte / 365.0))
        
        # Mathematical estimation of Delta corridors
        otm_puts['Distance_PCT'] = (current_price - otm_puts['strike']) / current_price
        otm_puts['Est_Delta'] = -0.5 * np.exp(-(otm_puts['Distance_PCT'] * 3))
        
        # Match nearest option context targeting a -0.20 Delta structure
        target_contract = otm_puts.iloc[(otm_puts['Est_Delta'] - (-0.20)).abs().argsort()[:1]]
        if target_contract.empty:
            return None
            
        contract = target_contract.iloc[0]
        strike = contract['strike']
        bid = contract['bid']
        
        if bid <= 0.05: # Filters out illiquid or microscopic premiums
            return None
            
        # Capital allocation optimization formula: Annualized Yield Rate
        raw_yield = (bid / strike) * 100
        annualized_yield = raw_yield * (365.0 / dte)
        
        return {
            "Ticker": ticker,
            "Spot_Price": round(current_price, 2),
            "RSI_14": round(rsi, 2),
            "Mean_IV": round(avg_iv * 100, 1),
            "Exp_Move_Floor": round(expected_move_floor, 2),
            "Target_Strike": strike,
            "Bid_Premium": bid,
            "Est_Delta": round(contract['Est_Delta'], 2),
            "Ann_Yield_Pct": round(annualized_yield, 2)
        }
    except Exception:
        return None

if __name__ == "__main__":
    ticker_source = "sp100_constituents.txt"
    print(f"🛰️  Loading targets from {ticker_source}...")
    SP100_TICKERS = load_tickers_from_file(ticker_source)
    print(f"Loaded {len(SP100_TICKERS)} liquid S&P assets. Commencing radar scan...")
    
    start_time = time.time()
    opportunities = []
    
    # Process up to 15 concurrent workers to minimize network latency constraints safely
    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(analyze_option_opportunity, SP100_TICKERS)
        for r in results:
            if r is not None:
                opportunities.append(r)
                
    if not opportunities:
        print("❌ Scan finished. No setups discovered satisfying baseline criteria conditions.")
        sys.exit(0)
        
    leaderboard = pd.DataFrame(opportunities)
    leaderboard = leaderboard.sort_values(by="Ann_Yield_Pct", ascending=False).reset_index(drop=True)
    
    print("\n=========================================================================")
    print("🏆 SYSTEMATIC OPTIONS LEADERBOARD REPORT (Ranked by Annualized Yield)")
    print("=========================================================================")
    print(leaderboard.to_string(index=False))
    print("=========================================================================")
    print(f"⏱️  Scan completed across entire universe in {time.time() - start_time:.2f} seconds.")