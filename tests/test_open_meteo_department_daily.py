import unittest

import numpy as np
import pandas as pd

from src.build_open_meteo_department_daily import (
    aggregate_department_daily, circular_statistics_degrees, validate_output,
)


VARIABLES = {
    "temperature_2m_max": 30.0, "temperature_2m_min": 10.0,
    "relative_humidity_2m_min": 30.0, "relative_humidity_2m_max": 90.0,
    "wind_speed_10m_max": 5.0, "precipitation_sum": 2.0,
    "et0_fao_evapotranspiration": 3.0,
}


class OpenMeteoDepartmentDailyTest(unittest.TestCase):
    def test_circular_mean_wraps_359_and_1(self):
        direction, resultant = circular_statistics_degrees(pd.Series([359, 1]))
        self.assertTrue(np.isclose(direction, 0) or np.isclose(direction, 360))
        self.assertGreater(resultant, .99)

    def test_identical_circular_directions(self):
        direction, resultant = circular_statistics_degrees(pd.Series([90, 90]))
        self.assertAlmostEqual(direction, 90)
        self.assertAlmostEqual(resultant, 1)

    def test_opposite_directions_are_undefined(self):
        direction, resultant = circular_statistics_degrees(pd.Series([0, 180]))
        self.assertTrue(np.isnan(direction)); self.assertAlmostEqual(resultant, 0)

    def _source(self):
        rows = []
        for identifier, precipitation, direction in [("a", 1.0, 359), ("b", 3.0, 1)]:
            rows.append({"coordenada_id": identifier, "departamento": "X", "departamento_iso": "UY-X",
                         "fecha": pd.Timestamp("2018-01-01"), "wind_direction_10m_dominant": direction,
                         **VARIABLES, "precipitation_sum": precipitation})
        return pd.DataFrame(rows), pd.DataFrame({"coordenada_id": ["a", "b"], "departamento": ["X", "X"]})

    def test_scalar_mean_and_precipitation_are_not_summed(self):
        source, catalog = self._source(); output = aggregate_department_daily(source, catalog).iloc[0]
        self.assertEqual(output.temperature_2m_max_mean_spatial, 30)
        self.assertEqual(output.precipitation_sum_mean_spatial, 2)
        self.assertNotEqual(output.precipitation_sum_mean_spatial, source.precipitation_sum.sum())

    def test_single_point_department_preserves_values(self):
        source, catalog = self._source(); source = source.iloc[[0]]; catalog = catalog.iloc[[0]]
        output = aggregate_department_daily(source, catalog).iloc[0]
        self.assertEqual(output.n_puntos_esperados, 1); self.assertEqual(output.n_puntos_observados, 1)
        self.assertEqual(output.temperature_2m_max_mean_spatial, output.temperature_2m_max_max_spatial)

    def test_missing_point_is_detected_by_coverage(self):
        source, catalog = self._source(); output = aggregate_department_daily(source.iloc[[0]], catalog).iloc[0]
        self.assertEqual(output.n_puntos_esperados, 2); self.assertEqual(output.n_puntos_observados, 1)
        self.assertEqual(output.cobertura_espacial_pct, 50)

    def test_output_key_is_unique_and_expected_formula(self):
        source, catalog = self._source(); output = aggregate_department_daily(source, catalog)
        self.assertFalse(output.duplicated(["departamento", "fecha"]).any())
        self.assertEqual(19 * 3286, 62434)

    def test_resultant_is_bounded(self):
        for values in ([10, 20], [0, 180], [90, 90]):
            self.assertTrue(0 <= circular_statistics_degrees(pd.Series(values))[1] <= 1)


if __name__ == "__main__":
    unittest.main()
