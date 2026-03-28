import sqlite3
import pandas as pd
import streamlit as st

class DashboardDAO:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self):
        """Create a read-only database connection"""
        try:
            conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro",
                uri=True,
                check_same_thread=False
            )
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except sqlite3.OperationalError as e:
                st.warning(f"Could not enable WAL mode: {e}")
            return conn
        except sqlite3.Error as e:
            # TODO: Log as dev/debug information
            # st.error(f"Database connection failed: {e}")
            return None

    @property
    def is_connected(self) -> bool:
        return self._get_connection() is not None

    def get_generation_range(self):
        conn = self._get_connection()
        if not conn:
            return 0, 0

        try:
            query = """
                SELECT MIN(m.generation), MAX(m.generation)
                FROM metrics m
                INNER JOIN snapshots s ON m.generation = s.generation
            """
            result = conn.execute(query).fetchone()
            conn.close()

            if result and result[0] is not None:
                return int(result[0]), int(result[1])
        except Exception as e:
            st.error(f"Error fetching generation range: {e}")

        return 0, 0

    def get_snapshot(self, generation: int):
        """Get data for a specific generation"""
        conn = self._get_connection()
        if not conn:
            return None

        try:
            df = pd.read_sql(
                "SELECT * FROM snapshots WHERE generation = ?",
                conn,
                params=(generation,)
            )
            conn.close()

            if not df.empty:
                return df.iloc[0]
        except Exception as e:
            st.error(f"Error fetching snapshot for generation {generation}: {e}")

        return None


    def get_metrics(self, max_generation: int):
        """Get metrics up to max_generation"""
        conn = self._get_connection()
        if not conn:
            return pd.DataFrame()

        try:
            # Check for column existence to be safe if DB is old
            select_cols = "*"

            df = pd.read_sql(
                f"SELECT {select_cols} FROM metrics WHERE generation <= ? ORDER BY generation ASC",
                conn,
                params=(max_generation,)
            )
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error fetching metrics: {e}")
            return pd.DataFrame()

    def get_initial_code(self):
        """Get the initial seed code"""
        conn = self._get_connection()
        if not conn:
            return "# Initial code not found"

        try:
            df = pd.read_sql(
                "SELECT best_code_snippet FROM snapshots ORDER BY generation ASC LIMIT 1",
                conn
            )
            conn.close()

            if not df.empty:
                return df.iloc[0]['best_code_snippet']
        except Exception as e:
            st.error(f"Error fetching initial code: {e}")

        return "# Initial code not found"

    def get_global_strategies(self):
        """Fetch the single source of truth for all strategies."""
        conn = self._get_connection()
        if not conn:
            return pd.DataFrame()

        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='strategies'")
            if not cursor.fetchone():
                return pd.DataFrame()

            df = pd.read_sql("SELECT * FROM strategies", conn)
            conn.close()

            df = df.rename(columns={
                "idea": "Idea",
                "direction": "Direction",
                "status": "Status",
                "impact": "Impact",
                "best_fit": "Best_Fit"
            })

            return df
        except Exception as e:
            st.error(f"Error fetching global strategies: {e}")
            return pd.DataFrame()

    def get_llm_stats(self, max_generation: int) -> "pd.DataFrame":
        """Fetch LLM call and resource stats up to max_generation."""
        conn = self._get_connection()
        if not conn:
            return pd.DataFrame()
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_stats'"
            )
            if not cursor.fetchone():
                return pd.DataFrame()
            df = pd.read_sql(
                "SELECT * FROM llm_stats WHERE generation <= ? ORDER BY generation ASC",
                conn,
                params=(max_generation,)
            )
            conn.close()
            return df
        except Exception:
            return pd.DataFrame()

    def get_latest_reflection(self, generation: int):
        """Fetch the most recent long-term reflection up to the given generation."""
        conn = self._get_connection()
        if not conn:
            return None

        try:
            cursor = conn.execute(
                "SELECT content FROM reflections WHERE generation <= ? ORDER BY generation DESC LIMIT 1",
                (generation,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return row[0]
            return None
        except Exception as e:
            # Table might not exist yet if no reflections have been logged
            return None
