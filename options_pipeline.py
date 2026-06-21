import os
import sys
import json
import math
os.environ["OTEL_SDK_DISABLED"] = "true"

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
# Insert this import below your existing standard library tools
from database_manager import initialize_database, log_option_ticket

gemini_llm = LLM(
    model="gemini/gemini-2.5-flash",
    temperature=0.1
)

# ==========================================
# 2. EXTENDED OPTIONS GREEKS TOOL
# ==========================================

@tool("Fetch Advanced Options Chain and Greeks")
def fetch_options_chain_with_greeks(ticker: str, strategy: str) -> str:
    """
    Downloads option data chains dynamically for a given ticker.
    Supported Strategy parameters: 'CASH_SECURED_PUT', 'BULL_PUT_SPREAD', 'BULL_CREDIT_SPREAD', 'LONG_CALL'.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        expirations = stock.options
        if not expirations:
            return f"Error: No listed options chains discovered for {ticker}."
            
        current_price = stock.history(period="1d")['Close'].iloc[-1]
        
        # Isolate optimal 30-45 DTE cycle
        today = datetime.today()
        selected_expiry = next((exp for exp in expirations if 30 <= (datetime.strptime(exp, "%Y-%m-%d") - today).days <= 45), expirations[0])
        dte = max((datetime.strptime(selected_expiry, "%Y-%m-%d") - today).days, 1)
        
        opt_chain = stock.option_chain(selected_expiry)
        
        # --- STRATEGY CONFIGURATION ROUTING ENGINE ---
        strategy_upper = strategy.upper()
        
        # 1. Handle Put Strategies (Now matches SPREAD, PUT, or CREDIT profiles explicitly)
        if "PUT" in strategy_upper or "CREDIT" in strategy_upper:
            df = opt_chain.puts.copy()
            liquid_df = df[df['openInterest'] > 10].copy()
            target_df = liquid_df[liquid_df['strike'] < current_price].copy()
            
            avg_iv = target_df['impliedVolatility'].mean()
            expected_move = current_price * avg_iv * math.sqrt(dte / 365.0)
            floor = current_price - expected_move
            
            target_df['Distance_PCT'] = (current_price - target_df['strike']) / current_price
            target_df['Approx_Delta'] = -0.5 * np.exp(-(target_df['Distance_PCT'] * 3))
            target_df['Approx_Theta'] = -(target_df['lastPrice'] * avg_iv) / (2 * dte)
            
            # Isolate the core safety zone tracking data
            safety_mask = target_df[(target_df['Approx_Delta'] <= -0.10) & (target_df['Approx_Delta'] >= -0.30)]
            if safety_mask.empty:
                safety_mask = target_df
                
            # FIX: Explicitly slice down the 6 specific columns first to align the data dimensions
            snapshot = safety_mask[['strike', 'bid', 'ask', 'impliedVolatility', 'Approx_Delta', 'Approx_Theta']].tail(5).copy()
            
            report = f"--- PUT CHAIN DESK FOR {ticker.upper()} ({strategy_upper}) ---\n"
            report += f"Spot Price: ${current_price:.2f} | Expiry: {selected_expiry} | Implied Move Floor: ${floor:.2f}\n\n"
            
            # Now renaming columns works safely because the layout has exactly 6 elements
            snapshot.columns = ['Strike', 'Bid', 'Ask', 'IV', 'Est_Delta', 'Est_Theta_Decay']
            return report + snapshot.to_string(index=False)
            
        # 2. Handle Long Calls
        elif "CALL" in strategy_upper:
            df = opt_chain.calls.copy()
            liquid_df = df[df['openInterest'] > 10].copy()
            target_df = liquid_df[liquid_df['strike'] >= (current_price * 0.95)].copy()
            
            avg_iv = target_df['impliedVolatility'].mean()
            expected_move = current_price * avg_iv * math.sqrt(dte / 365.0)
            ceiling = current_price + expected_move
            
            target_df['Distance_PCT'] = (target_df['strike'] - current_price) / current_price
            target_df['Approx_Delta'] = 0.5 * np.exp(-(target_df['Distance_PCT'] * 3))
            target_df['Approx_Theta'] = -(target_df['lastPrice'] * avg_iv) / (2 * dte)
            
            safety_mask = target_df[(target_df['Approx_Delta'] >= 0.35) & (target_df['Approx_Delta'] <= 0.60)]
            if safety_mask.empty:
                safety_mask = target_df
                
            # FIX: Explicitly slice columns down to 6 elements first
            snapshot = safety_mask[['strike', 'bid', 'ask', 'impliedVolatility', 'Approx_Delta', 'Approx_Theta']].head(5).copy()
            
            report = f"--- CALL CHAIN DESK FOR {ticker.upper()} ({strategy_upper}) ---\n"
            report += f"Spot Price: ${current_price:.2f} | Expiry: {selected_expiry} | Implied Move Ceiling: ${ceiling:.2f}\n\n"
            
            snapshot.columns = ['Strike', 'Bid', 'Ask', 'IV', 'Est_Delta', 'Est_Theta_Decay']
            return report + snapshot.to_string(index=False)

    except Exception as e:
        return f"Tool Execution Failure: {str(e)}"

# ==========================================
# 3. OPTIONS COMMITTEE AGENT DEFINITIONS
# ==========================================

options_strategist = Agent(
    role='Lead Options Yield Architect',
    goal='Identify asymmetric premium setups backed by strict options Greeks and standard deviation floors.',
    backstory='An expert option market maker who analyzes Delta, Theta decay, and implied expected moves to source safety margins.',
    verbose=True,
    max_iter=2,
    llm=gemini_llm,
    tools=[fetch_options_chain_with_greeks]
)

options_risk_manager = Agent(
    role='Derivatives Risk Controller',
    goal='Generate human-readable entry logic blueprints and compile a concurrent raw JSON order ticket.',
    backstory='A meticulous institutional risk manager who outputs dual compliance files: an executive text analysis and an un-adorned execution JSON payload.',
    verbose=True,
    max_iter=2,
    llm=gemini_llm
)

# ==========================================
# 4. EXPLICIT CONTROLS & SEPARATE DUAL REPORTS
# ==========================================

options_analysis_task = Task(
    description='''
    Fetch and audit the active options chain parameters and Greeks for the target ticker asset: {target_ticker}.
    Determine the optimal strike level that sits safely near or below the -1 Standard Deviation Implied Expected Move floor.
    ''',
    expected_output='A technical report mapping out Greeks, specific implied move targets, and premium pricing corridors.',
    agent=options_strategist
)

options_blueprint_task = Task(
    description='''
    Review the proposed option parameters for {target_ticker} using the {target_strategy} strategy context.
    You MUST output a dual response separated cleanly by the token delimiters.
    
    If the strategy is BULL_PUT_SPREAD, you must configure TWO legs in the JSON object: 
      Leg 1: Short Put (SELL_TO_OPEN at ~0.20 Delta)
      Leg 2: Long Put (BUY_TO_OPEN protection strike located $5 below Leg 1)
    If the strategy is LONG_CALL, configure ONE leg:
      Leg 1: Long Call (BUY_TO_OPEN near-the-money at ~0.50 Delta)
      
    [CONVERSATIONAL ANALYSIS START]
    Provide a detailed explanation of the selected strikes, target strategy dynamics, Greeks risk profiles, and expected entry support limits.
    [CONVERSATIONAL ANALYSIS END]
    
    [JSON TICKET START]
    {{
        "timestamp": "{current_time}",
        "ticker": "{target_ticker}",
        "strategy": "{target_strategy}",
        "action": "MULTI_LEG_EXECUTION",
        "order_type": "LIMIT",
        "legs": [
            {{
                "leg_index": 1,
                "type": "OPTION_TYPE",
                "action": "SELL_TO_OPEN_OR_BUY_TO_OPEN",
                "strike": 0.0,
                "expiration": "YYYY-MM-DD",
                "est_delta": 0.0,
                "est_theta_decay": 0.0
            }}
        ],
        "execution_rules": {{
            "target_net_credit_or_debit": 0.0,
            "margin_or_collateral_required": 0.0
        }}
    }}
    [JSON TICKET END]
    ''',
    expected_output='A combined text stream containing both the conversational entry markdown text and a raw structured multi-leg JSON object.',
    agent=options_risk_manager
)

options_crew = Crew(
    agents=[options_strategist, options_risk_manager],
    tasks=[options_analysis_task, options_blueprint_task],
    process=Process.sequential,
    verbose=True,
    memory=False
)

if __name__ == "__main__":
    # Expect CLI parameters: python options_pipeline.py [ticker] [strategy]
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
    strategy = sys.argv[2].upper() if len(sys.argv) > 2 else "CASH_SECURED_PUT"
    
    print(f"🚀 Launching Algorithmic Derivatives Desk for: {ticker}")
    print(f"💼 Strategy Profile Selected: {strategy}\n")
    
    result = options_crew.kickoff(inputs={
        'target_ticker': ticker,
        'target_strategy': strategy,
        'current_time': datetime.today().strftime('%Y-%m-%d %H:%M:%S')  # <-- Injects active system time
    })
    
    raw_output = result.raw
    
    # --- HARDENED DUAL PARSING ENGINE WITH STRING DEFENSES ---
    try:
        # 1. Parse Conversational Blueprint
        if "[CONVERSATIONAL ANALYSIS START]" in raw_output:
            analysis_text = raw_output.split("[CONVERSATIONAL ANALYSIS START]")[1].split("[CONVERSATIONAL ANALYSIS END]")[0].strip()
            with open("options_entry_blueprint.md", "w") as fm:
                fm.write("# 📝 Options Strategic Entry Blueprint\n")
                fm.write(f"**Asset Target:** `{ticker}` | **Run Date:** {datetime.today().strftime('%Y-%m-%d')}  \n")
                fm.write("--- \n\n")
                fm.write(analysis_text)
            print("📝 Human-Readable Entry Analysis successfully saved to: options_entry_blueprint.md")
        
        # 2. Parse and Sanitize JSON API Order Ticket
        if "[JSON TICKET START]" in raw_output:
            json_text = raw_output.split("[JSON TICKET START]")[1].split("[JSON TICKET END]")[0].strip()
            
            # Sweeper Rule A: Clean out any markdown fence headers (```json or ```text)
            if "```" in json_text:
                cleaned_lines = [
                    line for line in json_text.splitlines() 
                    if "```" not in line and line.strip().lower() != "json" and line.strip().lower() != "text"
                ]
                json_text = "\n".join(cleaned_lines).strip()
            
            # Sweeper Rule B: Repair template-escaped double curly braces from prompt leakage
            if json_text.startswith("{{"):
                json_text = json_text.replace("{{", "{", 1)
            if json_text.endswith("}}"):
                # Rreplace from the right side to ensure safe text closure
                json_text = json_text.rsplit("}}", 1)[0] + "}"
                
            # Extra safety: Clean up general escaped inner brace noise if present
            json_text = json_text.replace("{{", "{").replace("}}", "}")
                    
            # Load string explicitly to verify standard validation format array
            parsed_json = json.loads(json_text)
            
            # Hard save structured object to target file destination
            with open("order_routing_ticket.json", "w") as fj:
                json.dump(parsed_json, fj, indent=4)
            print("✅ Algorithmic JSON Ticket successfully saved to: order_routing_ticket.json")

            # --- NEW EXTENSION LAYER CONNECTION ---
            # 1. Automatically ensure database file structures exist
            initialize_database()
            # 2. Log the parsed JSON ticket into the database
            log_option_ticket(json_text)
        else:
            print("❌ Error: Output stream completely lacked explicit [JSON TICKET START] tokens.")
            
    except Exception as e:
        print(f"\n⚠️ Parser engine failed to isolate json array array: {str(e)}")
        print("=========================================================================")
        print("DIAGNOSTIC DUMP (Raw output captured from LLM channel):")
        print("=========================================================================")
        print(raw_output)
        print("=========================================================================")

# if __name__ == "__main__":
#     # Expect CLI parameters: python options_pipeline.py [ticker] [strategy]
#     ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
#     strategy = sys.argv[2].upper() if len(sys.argv) > 2 else "CASH_SECURED_PUT"
    
#     print(f"🚀 Launching Algorithmic Derivatives Desk for: {ticker}")
#     print(f"💼 Strategy Profile Selected: {strategy}\n")
    
#     result = options_crew.kickoff(inputs={
#         'target_ticker': ticker,
#         'target_strategy': strategy
#     })
    
#     raw_output = result.raw
    
#     # --- DUAL PARSING ENGINE ---
#     try:
#         # Extract Conversational Breakdown
#         if "[CONVERSATIONAL ANALYSIS START]" in raw_output:
#             analysis_text = raw_output.split("[CONVERSATIONAL ANALYSIS START]")[1].split("[CONVERSATIONAL ANALYSIS END]")[0].strip()
#             with open("options_entry_blueprint.md", "w") as fm:
#                 fm.write("# 📝 Options Strategic Entry Blueprint\n")
#                 fm.write(f"**Asset Target:** `{ticker}` | **Run Date:** {datetime.today().strftime('%Y-%m-%d')}  \n")
#                 fm.write("--- \n\n")
#                 fm.write(analysis_text)
#             print("📝 Human-Readable Entry Analysis successfully saved to: options_entry_blueprint.md")
        
#         # Extract JSON API Order Ticket
#         if "[JSON TICKET START]" in raw_output:
#             json_text = raw_output.split("[JSON TICKET START]")[1].split("[JSON TICKET END]")[0].strip()
            
#             # Sanitization logic block
#             if json_text.startswith("```"):
#                 json_text = json_text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
#                 if json_text.startswith("json"):
#                     json_text = json_text.split("\n", 1)[1].strip()
                    
#             parsed_json = json.loads(json_text)
#             with open("order_routing_ticket.json", "w") as fj:
#                 json.dump(parsed_json, fj, indent=4)
#             print("✅ Algorithmic JSON Ticket successfully saved to: order_routing_ticket.json")
            
#     except Exception as e:
#         print(f"⚠️ Parser engine encounter: {str(e)}")
#         print(f"Raw Output stream dump for diagnostic tracking:\n{raw_output}")