import os
import sys
import time
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from intraday_desk import calculate_intraday_geometry

def check_velocity(ticker):
    """
    Grabs the immediate daily open-to-last distance percentage 
    to see if an asset is experiencing an intraday velocity breakout.
    """
    try:
        stock = yf.Ticker(ticker)
        # Fetch minimum footprint data to optimize connection speed
        df = stock.history(period="2d")
        if df.empty or len(df) < 2:
            return None
            
        prev_close = df['Close'].iloc[-2]
        current_spot = df['Close'].iloc[-1]
        
        # Calculate intraday distance rate change
        pct_change = ((current_spot - prev_close) / prev_close) * 100
        
        return {
            "Ticker": ticker,
            "Price": round(current_spot, 2),
            "Change_PCT": round(pct_change, 2)
        }
    except Exception:
        return None

if __name__ == "__main__":
    print("🚀 Initializing Live Intraday Momentum Radar...")
    
    # Ingest your existing S&P text file
    with open("sp100_constituents.txt", "r") as f:
        tickers = [t.strip().upper() for t in f.read().split(",") if t.strip()]
        
    print(f"Scanning {len(tickers)} assets concurrently for high-velocity swings...")
    start = time.time()
    
    movers = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(check_velocity, tickers)
        for r in results:
            if r is not None:
                # Isolate high-momentum swings (Moving up or down more than 3.5%)
                if abs(r["Change_PCT"]) >= 3.5:
                    movers.append(r)
                    
    print(f"⏱️ Scan complete in {time.time() - start:.2f} seconds.")
    
    if not movers:
        print("📊 Market is currently balancing sideways. No assets crossed the ±3.5% momentum threshold.")
        sys.exit(0)
        
    # Display the active velocity targets
    movers_df = pd.DataFrame(movers).sort_values(by="Change_PCT", ascending=False).reset_index(drop=True)
    print("\n🔥 HIGH-VELOCITY ACTIVE MOVERS LEADERS:")
    print(movers_df.to_string(index=False))
    print("=========================================================================\n")
    
    # Process the top opportunity automatically through your intraday math desk
    top_target = movers_df.iloc[0]['Ticker']
    print(f"🎯 Automatically routing top momentum candidate '{top_target}' to Intraday Execution Desk...\n")
    
    # Run your geometry engine logic directly from memory
    trade_plan = calculate_intraday_geometry(top_target)
    print(trade_plan)