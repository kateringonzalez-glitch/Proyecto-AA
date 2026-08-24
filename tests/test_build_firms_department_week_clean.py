import unittest

import pandas as pd

from src.build_firms_department_week_clean import (
    assign_activity_classes,
    complete_week_mask,
    validate_clean_panel,
)


class CleanPanelRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = pd.read_parquet("results/data/firms_departamento_semana_clean.parquet")

    def assert_class(self, count, expected_label, expected_code):
        labels, codes = assign_activity_classes(pd.Series([count]))
        self.assertEqual(str(labels[0]), expected_label)
        self.assertEqual(int(codes.iloc[0]), expected_code)

    def test_zero_is_no_detection(self):
        self.assert_class(0, "Sin detección", 0)

    def test_one_is_low(self):
        self.assert_class(1, "Bajo", 1)

    def test_two_and_three_are_moderate(self):
        self.assert_class(2, "Moderado", 2)
        self.assert_class(3, "Moderado", 2)

    def test_four_or_more_is_high(self):
        self.assert_class(4, "Alto", 3)
        self.assert_class(25, "Alto", 3)

    def test_incomplete_week_is_excluded(self):
        frame = pd.DataFrame({"fecha_fin_semana": pd.to_datetime(["2026-01-04"])})
        self.assertFalse(complete_week_mask(frame, pd.Timestamp("2025-12-31")).iloc[0])

    def test_complete_week_is_kept(self):
        frame = pd.DataFrame({"fecha_fin_semana": pd.to_datetime(["2025-12-28"])})
        self.assertTrue(complete_week_mask(frame, pd.Timestamp("2025-12-31")).iloc[0])

    def test_no_duplicate_department_week_keys(self):
        self.assertFalse(self.panel.duplicated(["departamento", "fecha_inicio_semana"]).any())

    def test_exactly_nineteen_departments(self):
        self.assertEqual(self.panel["departamento"].nunique(), 19)

    def test_real_clean_panel_full_validation(self):
        result = validate_clean_panel(self.panel, pd.Timestamp("2025-12-31"))
        self.assertEqual(result["departamentos"], 19)
        self.assertEqual(result["semanas"], 417)
        self.assertEqual(result["filas"], 7923)


if __name__ == "__main__":
    unittest.main()
