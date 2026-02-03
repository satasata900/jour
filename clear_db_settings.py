import os
import sys
from sqlalchemy import create_engine, text

# Database connection URL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/jour2"

def clear_settings():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Delete entries that might override our defaults
            conn.execute(text("DELETE FROM system_config WHERE config_key IN ('agent_llm_model', 'summary_model', 'mobile_model');"))
            conn.commit()
            print("Successfully cleared model settings from database.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_settings()
