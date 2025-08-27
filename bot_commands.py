# bot_commands.py
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# === Environment & Logging ===
DB_URL = os.getenv("DATABASE_URL1")
logger = logging.getLogger(__name__)

# === Database Functions ===
def get_db_conn():
    """
    Establishes and returns a database connection using RealDictCursor.
    This ensures that database query results are returned as dictionaries,
    allowing access by column name (e.g., row['column_name']).
    """
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        logger.info("✅ Database connection successful.")
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred during DB connection: {e}")
        raise

def init_db():
    """Initializes the database by creating tables if they don't exist."""
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                tier VARCHAR(50) DEFAULT 'Free',
                username VARCHAR(255),
                ref_by_id BIGINT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                referrals INTEGER DEFAULT 0,
                trial_expiry TIMESTAMP WITH TIME ZONE
            );
            CREATE TABLE IF NOT EXISTS upgrades (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                tier VARCHAR(50),
                source VARCHAR(255),
                duration_days INTEGER,
                upgraded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS signals (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                symbol VARCHAR(20) NOT NULL,
                entry_price NUMERIC(10, 4) NOT NULL,
                target_price_1 NUMERIC(10, 4),
                target_price_2 NUMERIC(10, 4),
                target_price_3 NUMERIC(10, 4),
                stop_loss NUMERIC(10, 4),
                status VARCHAR(50) DEFAULT 'Open',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                tags VARCHAR(255) DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT NOT NULL,
                referred_id BIGINT NOT NULL,
                referred_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (referrer_id, referred_id)
            );
        """)
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

def log_upgrade(user_id, tier, source, expiry_days=None):
    """Logs an upgrade and updates user's tier and expiry date."""
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                # First, get current user data
                cur.execute("SELECT tier, trial_expiry FROM users WHERE user_id = %s", (user_id,))
                user_data = cur.fetchone()

                # Calculate new expiry date if a duration is given
                if expiry_days:
                    current_expiry = user_data['trial_expiry'] if user_data and user_data['trial_expiry'] and user_data['trial_expiry'] > datetime.utcnow() else datetime.utcnow()
                    new_expiry = current_expiry + timedelta(days=expiry_days)
                    cur.execute(
                        "UPDATE users SET tier = %s, trial_expiry = %s WHERE user_id = %s",
                        (tier, new_expiry, user_id)
                    )
                else:
                    cur.execute(
                        "UPDATE users SET tier = %s WHERE user_id = %s",
                        (tier, user_id)
                    )

                # Log the upgrade in the upgrades table
                cur.execute(
                    "INSERT INTO upgrades (user_id, tier, source, duration_days) VALUES (%s, %s, %s, %s)",
                    (user_id, tier, source, expiry_days)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log upgrade for user {user_id}: {e}")

async def list_user_signals(user_id):
    """Retrieves all signals for a specific user."""
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, symbol, status FROM signals WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                signals = cur.fetchall()
                return [(signal['id'], signal['symbol'], signal['status']) for signal in signals]
    except Exception as e:
        logger.error(f"Failed to list signals for user {user_id}: {e}")
        return []

