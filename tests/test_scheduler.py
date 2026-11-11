import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from papi_core.scheduler import SchedulerError, due_schedules, validate_schedule


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "schedules.json"
        self.schedule = {
            "id": "daily-briefing", "title": "Briefing quotidien",
            "type": "daily", "time": "08:00", "timezone": "Africa/Dakar",
            "enabled": True, "task_template": {"handler": "report.preview", "payload": {}},
            "owner_approval_required": False,
        }
        self.write([self.schedule])

    def tearDown(self):
        self.temp.cleanup()

    def write(self, schedules):
        self.path.write_text(json.dumps({"schedules": schedules}), encoding="utf-8")

    def test_daily_schedule_becomes_due_after_local_time(self):
        now = datetime(2026, 11, 12, 8, 5, tzinfo=ZoneInfo("Africa/Dakar"))
        due = due_schedules(now=now, path=self.path)
        self.assertEqual(due[0]["schedule_id"], "daily-briefing")
        self.assertEqual(due[0]["status"], "awaiting_scheduler_review")

    def test_not_due_before_time(self):
        now = datetime(2026, 11, 12, 7, 59, tzinfo=ZoneInfo("Africa/Dakar"))
        self.assertEqual(due_schedules(now=now, path=self.path), [])

    def test_disabled_schedule_is_ignored(self):
        self.schedule["enabled"] = False
        self.write([self.schedule])
        now = datetime(2026, 11, 12, 9, 0, tzinfo=ZoneInfo("Africa/Dakar"))
        self.assertEqual(due_schedules(now=now, path=self.path), [])

    def test_same_day_run_is_not_due_twice(self):
        self.schedule["last_run_at"] = "2026-11-12T08:01:00+00:00"
        self.write([self.schedule])
        now = datetime(2026, 11, 12, 9, 0, tzinfo=ZoneInfo("Africa/Dakar"))
        self.assertEqual(due_schedules(now=now, path=self.path), [])

    def test_weekly_day_filter(self):
        self.schedule.update(type="weekly", weekdays=[3])
        self.write([self.schedule])
        thursday = datetime(2026, 11, 12, 9, 0, tzinfo=ZoneInfo("Africa/Dakar"))
        friday = datetime(2026, 11, 13, 9, 0, tzinfo=ZoneInfo("Africa/Dakar"))
        self.assertEqual(len(due_schedules(now=thursday, path=self.path)), 1)
        self.assertEqual(due_schedules(now=friday, path=self.path), [])

    def test_naive_clock_is_rejected(self):
        with self.assertRaises(SchedulerError):
            due_schedules(now=datetime(2026, 11, 12, 9, 0), path=self.path)

    def test_invalid_time_is_rejected(self):
        self.schedule["time"] = "25:99"
        self.assertTrue(validate_schedule(self.schedule))

    def test_duplicate_ids_are_rejected(self):
        self.write([self.schedule, self.schedule])
        with self.assertRaises(SchedulerError):
            due_schedules(now=datetime(2026, 11, 12, 9, 0, tzinfo=ZoneInfo("Africa/Dakar")), path=self.path)


if __name__ == "__main__":
    unittest.main()
