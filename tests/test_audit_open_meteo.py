import unittest

import pandas as pd

from src.audit_open_meteo import completeness, monday_start


class OpenMeteoAuditRulesTest(unittest.TestCase):
    def test_monday_week_start(self):
        values = pd.Series(pd.to_datetime(["2021-12-27", "2022-01-02", "2022-01-03"]))
        starts = monday_start(values)
        self.assertEqual(starts.dt.strftime("%Y-%m-%d").tolist(),
                         ["2021-12-27", "2021-12-27", "2022-01-03"])

    def test_completeness(self):
        self.assertEqual(completeness(168, 168), 100.0)
        self.assertEqual(completeness(84, 168), 50.0)

    def test_hourly_2025_has_nineteen_uruguay_points(self):
        data = pd.read_parquet("data/meteo_2025.parquet")
        uruguay = data.loc[data["pais_codigo"].eq("URY")]
        self.assertEqual(uruguay["punto"].nunique(), 19)
        self.assertFalse(uruguay.duplicated(["punto", "fecha_hora_utc"]).any())


if __name__ == "__main__":
    unittest.main()
