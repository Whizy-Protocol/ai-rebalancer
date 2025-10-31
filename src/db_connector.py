import psycopg2
from psycopg2.extras import RealDictCursor

from src.utils import get_env_variable


class IndexerDB:
    """Connection to indexer database for fetching user data"""

    def __init__(self, database_url: str | None = None):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL connection string (defaults to DATABASE_URL env var)
        """
        self.database_url = database_url or get_env_variable("DATABASE_URL", "")
        if not self.database_url:
            raise ValueError("DATABASE_URL not set in environment variables")

        self._conn = None

    def _get_connection(self):
        """Get or create database connection"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.database_url)
        return self._conn

    def close(self):
        """Close database connection"""
        if self._conn and not self._conn.closed:
            self._conn.close()

    def get_active_auto_rebalance_users(self) -> list[dict[str, any]]:
        """
        Get all users who have auto-rebalance enabled.

        Returns:
            List of dicts with keys: user (address), risk_profile, enabled_at, is_enabled
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        "user" as address,
                        risk_profile,
                        enabled_at,
                        is_enabled
                    FROM active_auto_rebalance_users
                    WHERE is_enabled = true
                    ORDER BY enabled_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching active auto-rebalance users: {e}")
            return []

    def get_user_balance(self, user_address: str) -> float:
        """
        Get user's current balance (deposits - withdrawals).

        Args:
            user_address: User's wallet address

        Returns:
            Balance in USDC (as float, already divided by 10^6)
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT balance
                    FROM user_balances
                    WHERE "user" = %s
                """,
                    (user_address.lower(),),
                )

                result = cursor.fetchone()
                if result:
                    return float(result["balance"]) / (10**6)
                return 0.0
        except Exception as e:
            print(f"Error fetching user balance for {user_address}: {e}")
            return 0.0

    def get_user_deposits(self, user_address: str) -> list[dict[str, any]]:
        """
        Get all deposit events for a user.

        Args:
            user_address: User's wallet address

        Returns:
            List of deposit events with amount, block_number, block_timestamp, tx_hash
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        "user" as address,
                        amount,
                        block_number,
                        block_timestamp,
                        transaction_hash as tx_hash
                    FROM depositeds
                    WHERE "user" = %s
                    ORDER BY block_timestamp DESC
                """,
                    (user_address.lower(),),
                )

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching deposits for {user_address}: {e}")
            return []

    def get_user_rebalance_history(self, user_address: str) -> list[dict[str, any]]:
        """
        Get rebalancing history for a user.

        Args:
            user_address: User's wallet address

        Returns:
            List of rebalance events with operator, amount, timestamp, tx_hash
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        "user" as address,
                        operator,
                        amount,
                        block_number,
                        block_timestamp,
                        transaction_hash as tx_hash
                    FROM rebalanceds
                    WHERE "user" = %s
                    ORDER BY block_timestamp DESC
                """,
                    (user_address.lower(),),
                )

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching rebalance history for {user_address}: {e}")
            return []

    def get_all_user_addresses(self) -> list[str]:
        """
        Get all unique user addresses from deposits and withdrawals.

        Returns:
            List of user addresses
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT "user" as address
                    FROM (
                        SELECT "user" FROM depositeds
                        UNION
                        SELECT "user" FROM withdrawns
                    ) all_users
                    ORDER BY address
                """)

                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching user addresses: {e}")
            return []

    def refresh_materialized_view(self):
        """
        Refresh the active_auto_rebalance_users materialized view.
        Call this periodically to update the view with latest data.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT refresh_active_auto_rebalance_users()")
                conn.commit()
                print("✓ Refreshed active_auto_rebalance_users materialized view")
        except Exception as e:
            print(f"Error refreshing materialized view: {e}")
            conn.rollback()


_db_instance: IndexerDB | None = None


def get_db() -> IndexerDB:
    """Get or create singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = IndexerDB()
    return _db_instance


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    db = get_db()

    print("Testing database connection...")
    print("\nActive auto-rebalance users:")
    users = db.get_active_auto_rebalance_users()
    for user in users:
        print(f"  - {user['address']}: Risk Profile {user['risk_profile']}")

    if not users:
        print("  (No users with auto-rebalance enabled)")

    print("\nAll user addresses:")
    addresses = db.get_all_user_addresses()
    for addr in addresses[:5]:
        print(f"  - {addr}")

    if len(addresses) > 5:
        print(f"  ... and {len(addresses) - 5} more")

    db.close()
    print("\n✓ Database test complete")
