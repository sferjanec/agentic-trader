import os
import sys
import time
import random
import argparse
from datetime import datetime
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from intraday_desk import calculate_intraday_geometry
from notifier import send_text_alert

def check_velocity(ticker):
    """
    Grabs the immediate daily open-to-last distance percentage 
    to see if an asset is experiencing an intraday velocity breakout.
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2d")
        if df.empty or len(df) < 2:
            return None
            
        prev_close = df['Close'].iloc[-2]
        current_spot = df['Close'].iloc[-1]
        
        pct_change = ((current_spot - prev_close) / prev_close) * 100
        
        return {
            "Ticker": ticker,
            "Price": round(current_spot, 2),
            "Change_PCT": round(pct_change, 2)
        }
    except Exception:
        return None

def execute_radar_sweep():
    """Performs a single multi-threaded pass across the constituent nodes."""
    with open("sp100_constituents.txt", "r") as f:
        tickers = [t.strip().upper() for t in f.read().split(",") if t.strip()]
        
    movers = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(check_velocity, tickers)
        for r in results:
            if r is not None and abs(r["Change_PCT"]) >= 3.5:
                movers.append(r)
    return movers

if __name__ == "__main__":
    # --- COMMAND LINE ARGUMENT ROUTING MATRIX ---
    parser = argparse.ArgumentParser(description="Autonomous Intraday Velocity Streaming Radar")
    parser.add_argument(
        "--interval", 
        type=int, 
        default=60, 
        help="Base runtime loop cooldown delay window mapped in seconds (Default: 60)"
    )
    args = parser.parse_args()
    
    base_interval = args.interval
    print("🛰️  Initializing Stream Infrastructure for Intraday Options/Equity Radar...")
    print(f"⚙️  Configuration: Base scanning loop set to {base_interval} seconds.\n")
    time.sleep(2) # Brief pause to allow log verification before terminal wipes
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"🔄 [SCAN CYCLE TRIGGERED] - System Clock: {timestamp}")
            print("Scanning S&P universe for high-velocity momentum breakout signals (±3.5%)...\n")
            
            start_time = time.time()
            movers = execute_radar_sweep()
            scan_duration = time.time() - start_time
            
            if not movers:
                print(f"📊 Market Balance Stable. No symbols currently cross volatility targets.")
                print(f"⏱️  Network sweep time: {scan_duration:.2f}s")
            else:
                movers_df = pd.DataFrame(movers).sort_values(by="Change_PCT", ascending=False).reset_index(drop=True)
                print(f"🔥 ACTIVE VELOCITY LEADERS (Scan completed in {scan_duration:.2f}s):")
                print(movers_df.to_string(index=False))
                print("=========================================================================\n")
                
                top_target = movers_df.iloc[0]['Ticker']
                print(f"🎯 Top opportunity identified: '{top_target}'. Injecting to Execution Desk...\n")
                
                # --- NEW NOTIFICATION LAYER HOOK ---
                send_text_alert(top_target, top_change, top_price)
                
                trade_plan = calculate_intraday_geometry(top_target)
                print(trade_plan)
                
            # Anti-Throttling Jitter Offset Calculation: Adds a small, variable buffer 
            # to prevent rhythmic signature patterns on host firewalls
            jitter = random.randint(5, 15)
            total_cooldown = base_interval + jitter
            
            print(f"\n💤 Entering stream cooldown for {total_cooldown} seconds (Interval: {base_interval}s + Jitter: {jitter}s)...")
            time.sleep(total_cooldown)
            
    except KeyboardInterrupt:
        print("\n🛑 Intraday Stream Scanner terminated cleanly by user request. Exiting.")
        sys.exit(0)