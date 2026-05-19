import time
from datetime import datetime

from data import storage


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
        self.task_accumulated = {}
        self.task_session_starts = {}

    def session_only(self):
        return self.elapsed + (time.time() - self.start_time if self.running else 0)

    def current_total(self):
        return self.session_only()

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
        return self.task_live_session()

    def start(self):
        if self.running:
            return False
        if self.session_start is None:
            self.session_start = datetime.now()
        self.start_time = time.time()
        self.running = True
        if self.current_task is not None:
            self.task_start_time = time.time()
            if self.current_task not in self.task_session_starts:
                self.task_session_starts[self.current_task] = datetime.now()
        return True

    def pause(self):
        if not self.running:
            return False
        self.elapsed += time.time() - self.start_time
        if self.current_task is not None and self.task_start_time > 0:
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
        if self.current_task is not None:
            self.task_accumulated[self.current_task] = self.task_elapsed
        self._record_all_task_sessions()
        self.task_accumulated = {}
        self.task_session_starts = {}
        self.elapsed = 0.0
        self.start_time = 0.0
        self.task_elapsed = 0.0
        self.task_start_time = 0.0

    def select_task(self, value, tasks):
        if self.current_task is not None:
            if self.running and self.task_start_time > 0:
                self.task_elapsed += time.time() - self.task_start_time
            self.task_accumulated[self.current_task] = self.task_elapsed

        if value == "Select task..." or value not in tasks:
            self.current_task = None
            self.task_start_time = 0.0
            self.task_elapsed = 0.0
        else:
            self.current_task = value
            self.task_elapsed = self.task_accumulated.pop(value, 0)
            if self.running:
                self.task_start_time = time.time()
                if value not in self.task_session_starts:
                    self.task_session_starts[value] = datetime.now()
            else:
                self.task_start_time = 0.0

    def record_session(self):
        if self.session_start is None:
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

    def _record_all_task_sessions(self):
        if not self.task_accumulated:
            return
        end_dt = datetime.now()
        changed = False
        for name, accumulated in self.task_accumulated.items():
            duration = int(accumulated)
            if duration <= 0:
                continue
            ssn_start = self.task_session_starts.get(name, end_dt)
            date_key = ssn_start.strftime("%Y-%m-%d")
            day = self.tracker.task_data.setdefault(date_key, {})
            entry = day.setdefault(
                name, {"total_seconds": 0, "sessions": []}
            )
            entry.setdefault("sessions", []).append(
                {
                    "start": ssn_start.isoformat(timespec="seconds"),
                    "end": end_dt.isoformat(timespec="seconds"),
                    "duration_seconds": duration,
                }
            )
            entry["total_seconds"] = int(entry.get("total_seconds", 0)) + duration
            changed = True
        if changed:
            storage.save_task_log(self.tracker.task_data)

    def reset_today_main(self):
        date_key = datetime.now().strftime("%Y-%m-%d")
        if date_key in self.tracker.data:
            del self.tracker.data[date_key]
            storage.save_time_log(self.tracker.data)

        self.elapsed = 0.0
        if self.running:
            self.start_time = time.time()
            self.session_start = datetime.now()
        else:
            self.start_time = 0.0
            self.session_start = None

    def reset_today_task(self):
        if self.current_task is None:
            return
        date_key = datetime.now().strftime("%Y-%m-%d")
        day = self.tracker.task_data.get(date_key, {})
        if self.current_task in day:
            del day[self.current_task]
            if not day:
                del self.tracker.task_data[date_key]
            storage.save_task_log(self.tracker.task_data)

        self.task_elapsed = 0.0
        self.task_session_starts.pop(self.current_task, None)
        if self.running:
            self.task_start_time = time.time()
            self.task_session_starts[self.current_task] = datetime.now()
        else:
            self.task_start_time = 0.0

    def flush_session(self):
        try:
            if (
                self.session_start is None
                and self.current_task is None
                and not self.task_accumulated
            ):
                return
            if self.running:
                self.elapsed += time.time() - self.start_time
                if self.current_task is not None and self.task_start_time > 0:
                    self.task_elapsed += time.time() - self.task_start_time
                self.running = False
            self.record_session()
            if self.current_task is not None:
                self.task_accumulated[self.current_task] = self.task_elapsed
            self._record_all_task_sessions()
        except Exception:
            pass
