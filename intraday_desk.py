import sys
import yfinance as yf
import pandas as pd
import numpy as np

def calculate_intraday_geometry(ticker):
    """
    Analyzes short-term momentum and structural pivots to map intraday/swing entry and exit boundaries.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        
        # 1. Fetch short-term hourly data for direct momentum profiling
        hourly_df = stock.history(period="1wk", interval="1h")
        if hourly_df.empty or len(hourly_df) < 14:
            return f"❌ Missing sufficient short-term structural data for {ticker}."
            
        # Fast 14-period Hourly RSI
        delta = hourly_df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / np.where(loss == 0, 0.00001, loss)
        hourly_rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # 2. Fetch daily data to compute institutional trading bands and pivot support
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
        output += f"Current Spot Price: ${current_price:.2f} | Hourly RSI(14): {hourly_rsi:.2f}\n"
        output += f"Daily Average Variance Range (ATR): ${atr:.2f}\n\n"
        
        output += f"📐 STRUCTURAL EXECUTION CHANNELS:\n"
        output += f"-------------------------------------------------------------------------\n"
        output += f"🔴 Aggressive Profit Target (R1):    ${resistance_1:.2f}\n"
        output += f"⚪ Median Pivot Baseline:             ${pivot_point:.2f}\n"
        output += f"🟢 Optimal Mean-Reversion Entry (S1): ${support_1:.2f}\n\n"
        
        # Risk management threshold recommendations based on volatility ATR multipliers
        suggested_stop_loss = support_1 - (atr * 0.5)
        output += f"🛡️  RISK MANAGEMENT ENVELOPE:\n"
        output += f"-------------------------------------------------------------------------\n"
        output += f"⚠️  Suggested Hard Invalidated Stop:   ${suggested_stop_loss:.2f} (ATR Buffer)\n"
        output += f"📊 Risk-to-Reward Ratio Matrix:     1:2.5 Base Profile\n"
        output += f"=========================================================================\n"
        return output

    except Exception as e:
        return f"❌ Intraday pipeline execution breakdown: {str(e)}"

if __name__ == "__main__":
    target_ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "NVDA"
    print(calculate_intraday_geometry(target_ticker))