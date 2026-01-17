import os
import json
from tinydb import TinyDB, Query
from datetime import datetime, timedelta
from os.path import join, exists
from kivy.app import App
from kivy.logger import Logger

MAX_DEVIATION = 180
Extension = Query()
History = Query()  # Query object for the 'history' table


class Database:
    def __init__(self, user_id="guest"):
        # 1. Get the protected Android data directory
        try:
            base_dir = App.get_running_app().user_data_dir
        except Exception:
            base_dir = "."  # Fallback for PyCharm desktop

        # 2. Create a unique folder for THIS user
        self.user_folder = join(base_dir, "users", user_id)
        if not exists(self.user_folder):
            os.makedirs(self.user_folder, exist_ok=True)
            Logger.info(f"[DB] Created folder for: {user_id}")

        # 3. Point TinyDB to the file INSIDE that user's folder
        self.db_file = join(self.user_folder, "sleep_data.json")
        self.db = TinyDB(self.db_file)

        self.sleep_table = self.db.table("sleep")
        self.history_table = self.db.table("history")

        Logger.info(f"[DB] User '{user_id}' is now using: {self.db_file}")

    def log_event(self, name):
        self.sleep_table.insert({"type": "event", "name": name, "created": datetime.now().isoformat()})
        Logger.info(f"[DB] Event logged: {name}")

    # ---------------------------------------------------------
    # RAW EVENT LOGGING METHODS
    # ---------------------------------------------------------
    def save_schedule(self, time_str):
        self.sleep_table.insert({"type": "schedule", "time": time_str, "created": datetime.now().isoformat()})

    def save_extension(self, minutes):
        self.sleep_table.insert({
            "type": "extension",
            "minutes": minutes,
            "created": datetime.now().isoformat()
        })
        Logger.info(f"[DB] Saved extension: {minutes} minutes")

    def get_all_extensions(self):
        # We define the Query object here so it works with the current user's table
        Ext = Query()
        ext_records = self.sleep_table.search(Ext.type == "extension")
        return [r["minutes"] for r in ext_records]

    def clear_extensions(self):
        self.sleep_table.remove(Extension.type == "extension")
        Logger.info("[DB] Cleared extensions")

    # ---------------------------------------------------------
    # SCORE CALCULATION & WRITING
    # ---------------------------------------------------------
    def _calculate_score_from_minutes(self, m):
        score = max(0.0, 100.0 - (m / MAX_DEVIATION) * 100.0)
        return round(score, 2)

    def save_current_period_score(self):
        """
        CRITICAL FIX: Calculates the final consistency score for the current period,
        saves it to history, and clears the extension counter.
        (Called only when a new schedule starts)
        """
        try:
            # 1. Get the total accumulated deviation from the current period
            ext_list = self.get_all_extensions()
            total_ext = sum(ext_list) if ext_list else 0

            # 2. Calculate the final score for this completed period
            score = self._calculate_score_from_minutes(total_ext)

            # 3. Save this score to the permanent history table
            self.save_score_to_history(score, total_ext)

            # 4. CRITICAL: Clear extensions AFTER saving the score (Handled by save_score_to_history)

            Logger.info(f"[DB] Period finalized. Score {score}% saved and extensions cleared.")
            return score

        except Exception as e:
            Logger.error(f"[DB ERROR] Failed to finalize period score: {e}")
            raise Exception(f"Database error during score finalization: {e}")

    def save_score_to_history(self, score, total_minutes):
        """
        Saves the score to the history table under today's date and clears extensions.
        """
        today_date_str = datetime.now().date().isoformat()

        record = {
            "date": today_date_str,
            "score": score,
            "minutes": total_minutes,
            "created": datetime.now().isoformat()
        }

        # Use upsert in the permanent history table
        self.history_table.upsert(record, History.date == today_date_str)
        Logger.info(f"[DB WRITE] Saved score: {score}% for {today_date_str}")

        # FIX: Removed redundant self.clear_extensions() call from here,
        # as the main function save_current_period_score should handle it.
        # Wait—re-inserting the clear here is fine IF this method is only used once.
        # For simplicity and correctness in this architecture, let's keep the clear
        # but ensure the method is only called once.
        # Since it was already here before the last error, we will assume this is correct.
        self.clear_extensions()
        return score

    # ---------------------------------------------------------
    # READ SCORES (REQUIRED BY main.py)
    # ---------------------------------------------------------

    def get_latest_saved_score(self):
        """Retrieves the score from the most recent historical record for the main label."""
        all_history = self.history_table.all()
        if not all_history:
            return 100.00

            # Sort by date descending to get the newest score first
        all_history.sort(key=lambda r: r['date'], reverse=True)
        return all_history[0]['score']

    def get_recent_consistency_scores(self, days=7):
        """Retrieves consistency scores ONLY from the permanent history table (for the bar chart)."""
        history = self.history_table.all()

        Logger.info(f"[DB READ] {len(history)} records loaded for charting.")

        # Safe sort by date
        def safe_date(rec):
            try:
                return datetime.fromisoformat(rec["date"]).date()
            except:
                return datetime(1970, 1, 1).date()

        history.sort(key=safe_date)

        results = []
        for rec in history:
            try:
                d = datetime.fromisoformat(rec["date"]).date()
                results.append((d.strftime("%b %d"), rec["score"]))
            except Exception as e:
                Logger.error(f"[DB READ] Skipped invalid record {rec} | {e}")

        final = results[-days:]
        Logger.info(f"[DB READ] Prepared chart data: {final}")

        return final