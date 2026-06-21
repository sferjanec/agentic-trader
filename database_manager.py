import sqlite3
import json
import os

DB_NAME = "trading_ledger.db"

def initialize_database():
    """
    Creates the local SQLite DB file and initializes the options execution ledger schema.
    """
    print(f"📦 Initializing Database Ledger: {DB_NAME}...", end="")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Construct your options strategy auditing ledger table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS option_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategy TEXT NOT NULL,
            short_strike REAL,
            long_strike REAL,
            net_credit_or_debit REAL NOT NULL,
            margin_required REAL,
            raw_json_payload TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print(" [SUCCESS]")

def log_option_ticket(ticket_json_str):
    """
    Parses a raw option ticket JSON string and persists the variables into the DB.
    """
    try:
        data = json.loads(ticket_json_str)
        
        # Pull parameters safely out of the nested schema layers
        timestamp = data.get("timestamp")
        ticker = data.get("ticker", "UNKNOWN").upper()
        strategy = data.get("strategy", "UNKNOWN").upper()
        
        rules = data.get("execution_rules", {})
        net_value = rules.get("target_net_credit_or_debit", 0.0)
        margin = rules.get("margin_or_collateral_required", 0.0)
        
        # Extract individual strikes from multi-leg or single leg arrays dynamically
        legs = data.get("legs", [])
        short_strike = None
        long_strike = None
        
        for leg in legs:
            action = leg.get("action", "").upper()
            if "SELL" in action:
                short_strike = leg.get("strike")
            elif "BUY" in action:
                long_strike = leg.get("strike")
                
        # Connect and insert using clean parameterization bindings
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO option_tickets (
                timestamp, ticker, strategy, short_strike, long_strike, net_credit_or_debit, margin_required, raw_json_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, ticker, strategy, short_strike, long_strike, net_value, margin, json.dumps(data)))
        
        conn.commit()
        inserted_id = cursor.lastrowid
        conn.close()
        
        print(f"💾 Ledger Success: Persisted tracking index record #{inserted_id} for {ticker} into database.")
        return inserted_id
        
    except Exception as e:
        print(f"❌ Database Ledger Writing Error: {str(e)}")
        return None

if __name__ == "__main__":
    # If run directly, verify database setup triggers cleanly
    initialize_database()