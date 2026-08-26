import unittest

import pandas as pd

from src.build_firms_open_meteo_weekly_history import (
    KEY,
    anti_join,
    integrate_history,
    reconcile_target,
    reject_duplicate_keys,
    validate_weekly_sequence,
)


class FirmsOpenMeteoWeeklyHistoryTest(unittest.TestCase):
    def setUp(self):
        dates = pd.to_datetime(["2017-12-25", "2018-01-01", "2018-01-08"])
        self.meteo = pd.DataFrame({
            "departamento": ["Artigas"] * 3,
            "fecha_inicio_semana": dates,
            "departamento_iso": ["UY-AR"] * 3,
            "fecha_fin_semana": dates + pd.Timedelta(days=6),
            "temperature_2m_max_mean_weekly": [25.0, 26.0, 27.0],
        })
        self.firms = pd.DataFrame({
            "departamento": ["Artigas", "Artigas"],
            "fecha_inicio_semana": pd.to_datetime(["2018-01-01", "2018-01-08"]),
            "cantidad_detecciones": [0, 2],
            "nivel_actividad_firms": pd.Categorical(
                ["Sin detección", "Moderado"],
                categories=["Sin detección", "Bajo", "Moderado", "Alto"],
                ordered=True,
            ),
            "nivel_actividad_firms_codigo": pd.Series([0, 2], dtype="int8"),
        })

    def test_left_join_preserves_historical_rows(self):
        result = integrate_history(self.meteo, self.firms)
        self.assertEqual(len(result), 3)
        self.assertEqual(result.fecha_inicio_semana.min(), pd.Timestamp("2017-12-25"))

    def test_missing_historical_target_is_not_converted_to_zero(self):
        result = integrate_history(self.meteo, self.firms)
        historical = result.loc[result.fecha_inicio_semana.eq("2017-12-25")].iloc[0]
        self.assertTrue(pd.isna(historical.cantidad_detecciones))
        self.assertFalse(historical.target_firms_disponible)

    def test_target_availability_matches_join(self):
        result = integrate_history(self.meteo, self.firms)
        self.assertEqual(result.target_firms_disponible.tolist(), [False, True, True])

    def test_duplicate_keys_are_rejected_before_multiplication(self):
        duplicated = pd.concat([self.firms, self.firms.iloc[[0]]], ignore_index=True)
        with self.assertRaises(AssertionError):
            integrate_history(self.meteo, duplicated)
        with self.assertRaises(AssertionError):
            reject_duplicate_keys(duplicated, "sintético")

    def test_anti_join_returns_only_unmatched_history(self):
        unmatched = anti_join(self.meteo, self.firms)
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched.iloc[0].fecha_inicio_semana, pd.Timestamp("2017-12-25"))

    def test_target_reconciliation(self):
        integrated = integrate_history(self.meteo, self.firms)
        reconciliation = reconcile_target(self.firms, integrated)
        self.assertTrue(reconciliation.coincide.all())
        changed = integrated.copy()
        changed.loc[changed.target_firms_disponible, "cantidad_detecciones"] = [1, 2]
        with self.assertRaises(AssertionError):
            reconcile_target(self.firms, changed)

    def test_weekly_sequence_accepts_seven_days(self):
        sequence = validate_weekly_sequence(self.meteo)
        self.assertEqual(int(sequence.saltos_distintos_de_7_dias.sum()), 0)

    def test_weekly_sequence_rejects_gap(self):
        gap = self.meteo.drop(index=1)
        with self.assertRaises(AssertionError):
            validate_weekly_sequence(gap)

    def test_key_is_department_and_week_start(self):
        self.assertEqual(KEY, ["departamento", "fecha_inicio_semana"])


if __name__ == "__main__":
    unittest.main()
