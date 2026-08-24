import unittest
from datetime import datetime, timezone

from src.run_open_meteo_free_windows import next_daily_window


class OpenMeteoFreeWindowsTest(unittest.TestCase):
    def test_next_window_is_five_minutes_after_next_utc_midnight(self):
        now = datetime(2026, 8, 22, 14, 45, tzinfo=timezone.utc)
        self.assertEqual(next_daily_window(now), datetime(2026, 8, 23, 0, 5, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
