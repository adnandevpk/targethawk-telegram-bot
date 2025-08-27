from datetime import datetime, timedelta
from db import get_db_conn

def log_upgrade(user_id: int, new_tier: str, payment_method: str, expiry_days: int = None):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            if expiry_days:
                expiry_date = datetime.utcnow() + timedelta(days=expiry_days)
                cur.execute("UPDATE users SET tier = %s, trial_expiry = %s WHERE user_id = %s", (new_tier, expiry_date, user_id))
            else:
                cur.execute("UPDATE users SET tier = %s, trial_expiry = NULL WHERE user_id = %s", (new_tier, user_id))
            cur.execute(
                "INSERT INTO upgrades (user_id, new_tier, payment_method) VALUES (%s, %s, %s)",
                (user_id, new_tier, payment_method)
            )
        conn.commit()
