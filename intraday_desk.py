import sys
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def calculate_intraday_geometry(ticker):
    """
    Analyzes short-term momentum, Daily Floor Pivots, and structures
    Opening Range Breakout (ORB) execution channels.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        
        # 1. Fetch 15-Minute Intraday Bar History for Live Momentum Profiling
        intraday_df = stock.history(period="1d", interval="15m")
        
        # Fallback to hourly if market hasn't opened yet or data footprint is thin
        if intraday_df.empty or len(intraday_df) < 1:
            hourly_df = stock.history(period="1wk", interval="1h")
            hourly_rsi = 50.0 # Neutral placeholder
            opening_high = None
            opening_low = None
        else:
            # Fast Intraday RSI calculation
            delta = intraday_df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / np.where(loss == 0, 0.00001, loss)
            hourly_rsi = (100 - (100 / (1 + rs))).iloc[-1]
            
            # Extract the first 15-minute bar of the current session
            opening_high = intraday_df['High'].iloc[0]
            opening_low = intraday_df['Low'].iloc[0]

        # 2. Fetch Daily Data to Compute Structural Floor Pivots & ATR
        daily_df = stock.history(period="1mo")
        current_price = daily_df['Close'].iloc[-1]
        high = daily_df['High'].iloc[-1]
        low = daily_df['Low'].iloc[-1]
        close = daily_df['Close'].iloc[-1]
        
        # Compute Traditional Floor Pivots
        pivot_point = (high + low + close) / 3.0
        support_1 = (2 * pivot_point) - high
        resistance_1 = (2 * pivot_point) - low
        
        # Compute Average True Range (ATR) to measure active intraday volatility bandwidth
        high_low = daily_df['High'] - daily_df['Low']
        high_close = np.abs(daily_df['High'] - daily_df['Close'].shift())
        low_close = np.abs(daily_df['Low'] - daily_df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        
        # 3. Compile the Trade Plan Output Blueprint
        output = f"=========================================================================\n"
        output += f"⚡ INTRADAY MOTION ARCHITECT PROFILE FOR: {ticker.upper()}\n"
        output += f"=========================================================================\n"
        output += f"Current Spot Price: ${current_price:.2f} | 15m Momentum RSI: {hourly_rsi:.2f}\n"
        output += f"Daily Average Variance Range (ATR): ${atr:.2f}\n\n"
        
        if opening_high and opening_low:
            output += f"⏱️  15-MINUTE OPENING RANGE BOUNDARIES:\n"
            output += f"-------------------------------------------------------------------------\n"
            output += f"🚀 Bullish Breakout Trigger (High):  ${opening_high:.2f}\n"
            output += f"📉 Bearish Breakdown Trigger (Low):  ${opening_low:.2f}\n\n"
        
        output += f"📐 STRUCTURAL PIVOT CHANNELS (DAILY):\n"
        output += f"-------------------------------------------------------------------------\n"
        output += f"🔴 Aggressive Profit Target (R1):    ${resistance_1:.2f}\n"
        output += f"⚪ Median Pivot Baseline:             ${pivot_point:.2f}\n"
        output += f"🟢 Optimal Mean-Reversion Entry (S1): ${support_1:.2f}\n\n"
        
        # Risk management threshold recommendations based on volatility ATR multipliers
        suggested_stop_loss = current_price - (atr * 0.5) if not opening_low else opening_low - (atr * 0.25)
        output += f"🛡️  RISK MANAGEMENT ENVELOPE:\n"
        output += f"-------------------------------------------------------------------------\n"
        output += f"⚠️  Suggested Hard Invalidated Stop:   ${suggested_stop_loss:.2f} (ATR Guard)\n"
        output += f"📊 Risk-to-Reward Ratio Matrix:     1:2.5 Base Profile\n"
        output += f"=========================================================================\n"
        return output

    except Exception as e:
        return f"❌ Intraday pipeline execution breakdown: {str(e)}"

if __name__ == "__main__":
    target_ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "NVDA"
    print(calculate_intraday_geometry(target_ticker))