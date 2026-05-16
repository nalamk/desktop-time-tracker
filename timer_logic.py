import time
from datetime import datetime

import storage


class TimerLogic:
    def __init__(self, tracker):
        self.tracker = tracker

        self.running = False
        self.start_time = 0.0
        self.elapsed = 0.0
        self.session_start = None

        self.current_task = None
        self.task_start_time = 0.0
        self.task_elapsed = 0.0
        self.task_baseline = 0
        self.task_session_start = None

    def current_total(self):
        return self.elapsed + (time.time() - self.start_time if self.running else 0)

    def task_live_session(self):
        if self.current_task is None:
            return 0
        active = (
            time.time() - self.task_start_time
            if self.running and self.task_start_time > 0
            else 0
        )
        return self.task_elapsed + active

    def task_total(self):
        if self.current_task is None:
            return 0
        return self.task_baseline + self.task_live_session()

    def saved_today_for(self, task_name):
        if not task_name:
            return 0
        date_key = datetime.now().strftime("%Y-%m-%d")
        return int(
            self.tracker.task_data.get(date_key, {})
            .get(task_name, {})
            .get("total_seconds", 0)
        )

    def start(self):
        if self.running:
            return False
        if self.session_start is None:
            self.session_start = datetime.now()
        self.start_time = time.time()
        self.running = True
        if self.current_task is not None:
            self.task_start_time = time.time()
            if self.task_session_start is None:
                self.task_session_start = datetime.now()
        return True

    def pause(self):
        if not self.running:
            return False
        self.elapsed += time.time() - self.start_time
        if self.current_task is not None:
            self.task_elapsed += time.time() - self.task_start_time
            self.task_start_time = 0.0
        self.running = False
        return True

    def stop(self):
        if self.running:
            self.elapsed += time.time() - self.start_time
            if self.current_task is not None and self.task_start_time > 0:
                self.task_elapsed += time.time() - self.task_start_time
            self.running = False
        self.record_session()
        self.record_task_session()
        self.elapsed = 0.0
        self.start_time = 0.0
        self.task_elapsed = 0.0
        self.task_start_time = 0.0
        if self.current_task is not None:
            self.task_baseline = self.saved_today_for(self.current_task)
        else:
            self.task_baseline = 0

    def select_task(self, value, tasks):
        if self.current_task is not None:
            if self.running and self.task_start_time > 0:
                self.task_elapsed += time.time() - self.task_start_time
            self.record_task_session()

        if value == "Select task..." or value not in tasks:
            self.current_task = None
            self.task_start_time = 0.0
            self.task_elapsed = 0.0
            self.task_baseline = 0
            self.task_session_start = None
        else:
            self.current_task = value
            self.task_elapsed = 0.0
            self.task_baseline = self.saved_today_for(value)
            if self.running:
                self.task_start_time = time.time()
                self.task_session_start = datetime.now()
            else:
                self.task_start_time = 0.0
                self.task_session_start = None

    def record_session(self):
        if self.session_start is None:
            self.session_start = None
            return
        duration = int(self.elapsed)
        if duration <= 0:
            self.session_start = None
            return
        end_dt = datetime.now()
        date_key = self.session_start.strftime("%Y-%m-%d")
        day = self.tracker.data.setdefault(
            date_key, {"total_seconds": 0, "sessions": []}
        )
        day.setdefault("sessions", []).append(
            {
                "start": self.session_start.isoformat(timespec="seconds"),
                "end": end_dt.isoformat(timespec="seconds"),
                "duration_seconds": duration,
            }
        )
        day["total_seconds"] = int(day.get("total_seconds", 0)) + duration
        storage.save_time_log(self.tracker.data)
        self.session_start = None

    def record_task_session(self):
        if self.task_session_start is None or self.current_task is None:
            self.task_session_start = None
            return
        duration = int(self.task_elapsed)
        if duration <= 0:
            self.task_session_start = None
            return
        end_dt = datetime.now()
        date_key = self.task_session_start.strftime("%Y-%m-%d")
        day = self.tracker.task_data.setdefault(date_key, {})
        entry = day.setdefault(
            self.current_task, {"total_seconds": 0, "sessions": []}
        )
        entry.setdefault("sessions", []).append(
            {
                "start": self.task_session_start.isoformat(timespec="seconds"),
                "end": end_dt.isoformat(timespec="seconds"),
                "duration_seconds": duration,
            }
        )
        entry["total_seconds"] = int(entry.get("total_seconds", 0)) + duration
        storage.save_task_log(self.tracker.task_data)
        self.task_session_start = None

    def flush_session(self):
        try:
            if self.session_start is None and self.task_session_start is None:
                return
            if self.running:
                self.elapsed += time.time() - self.start_time
                if self.current_task is not None and self.task_start_time > 0:
                    self.task_elapsed += time.time() - self.task_start_time
                self.running = False
            self.record_session()
            self.record_task_session()
        except Exception:
            pass
