import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PapiKidsBackupSystemdTemplatesTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / "infra" / "papi-kids" / "systemd" / name).read_text()

    def test_backup_service_is_one_shot_and_runs_opt_in_profile(self):
        service = self.read("papi-kids-backup.service")
        self.assertIn("Type=oneshot", service)
        self.assertIn("--profile backup run --rm papi-kids-backup", service)
        self.assertIn("UMask=0077", service)
        self.assertIn("NoNewPrivileges=true", service)

    def test_timers_are_utc_and_not_enabled_by_default(self):
        backup = self.read("papi-kids-backup.timer")
        offsite = self.read("papi-kids-offsite.timer")
        self.assertIn("02:00:00 UTC", backup)
        self.assertIn("03:00:00 UTC", offsite)
        self.assertIn("Persistent=true", backup)
        self.assertIn("Persistent=true", offsite)
        self.assertNotIn("WantedBy=timers.target", backup)
        self.assertNotIn("WantedBy=timers.target", offsite)

    def test_offsite_service_uses_only_offsite_profile(self):
        service = self.read("papi-kids-offsite.service")
        self.assertIn("--profile offsite run --rm papi-kids-offsite", service)
        self.assertIn("UMask=0077", service)


if __name__ == "__main__":
    unittest.main()
