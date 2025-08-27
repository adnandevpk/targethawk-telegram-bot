import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/targethawk")

def get_db_conn():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def register_db():
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    tier TEXT DEFAULT 'Free',
                    trial_expiry TIMESTAMP,
                    referrals INT DEFAULT 0
                );
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS upgrades (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    new_tier TEXT,
                    payment_method TEXT,
                    upgraded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
        conn.commit()
