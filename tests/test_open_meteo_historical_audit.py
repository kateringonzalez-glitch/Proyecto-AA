import inspect
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd

import src.audit_open_meteo_historical_extraction as audit_module
from src.audit_open_meteo_historical_extraction import (
    duplicate_report, expected_index, logical_quality, missing_dates_table, spatial_consistency,
)
from src.design_open_meteo_extraction import load_config
from src.extract_open_meteo import expected_days, validate_payload


class OpenMeteoHistoricalAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(Path("config/open_meteo.json"))
        cls.catalog = pd.read_csv(cls.config["paths"]["coordinate_catalog"])

    def test_configuration_requires_validated_catalog(self):
        self.assertEqual(Path(self.config["paths"]["coordinate_catalog"]).name,
                         "open_meteo_coordinates_validated.csv")
        self.assertEqual(len(self.catalog), 187)
        self.assertNotEqual(self.config["paths"]["coordinate_catalog"],
                            "data/reference/open_meteo_coordinates.csv")

    def test_theoretical_days_and_rows(self):
        days = expected_days(self.config["start_date"], self.config["end_date"])
        self.assertEqual(days, 3286)
        self.assertEqual(len(self.catalog) * days, 614482)

    def test_duplicate_detection(self):
        frame = pd.DataFrame({"coordenada_id": ["a", "a"], "fecha": ["2018-01-01"] * 2, "x": [1, 1]})
        self.assertEqual(duplicate_report(frame), {"exact_duplicates": 1, "key_duplicates": 1})

    def test_missing_date_detection(self):
        catalog = pd.DataFrame({"coordenada_id": ["a"]})
        frame = pd.DataFrame({"coordenada_id": ["a", "a"],
                              "fecha": pd.to_datetime(["2018-01-01", "2018-01-03"])})
        missing = missing_dates_table(frame, catalog, "2018-01-01", "2018-01-03")
        self.assertEqual(missing.fecha.dt.strftime("%Y-%m-%d").tolist(), ["2018-01-02"])

    def test_temperature_and_humidity_order_detection(self):
        frame = pd.DataFrame({"temperature_2m_min": [5, 9], "temperature_2m_max": [10, 8],
                              "relative_humidity_2m_min": [30, 90], "relative_humidity_2m_max": [80, 70]})
        result = logical_quality(frame)
        self.assertEqual(result["temperature_min_gt_max"], 1)
        self.assertEqual(result["humidity_min_gt_max"], 1)

    def test_multiple_model_cells_are_detected(self):
        coordinate = self.catalog.iloc[[0]]
        frame = pd.DataFrame({"coordenada_id": [coordinate.coordenada_id.iloc[0]] * 2,
                              "departamento": [coordinate.departamento.iloc[0]] * 2,
                              "latitud_modelo": [coordinate.latitud_reportada.iloc[0], coordinate.latitud_reportada.iloc[0] + .1],
                              "longitud_modelo": [coordinate.longitud_reportada.iloc[0]] * 2})
        boundaries = gpd.read_file(self.config["spatial_design"]["boundary_file"])
        consistency, _ = spatial_consistency(frame, coordinate, boundaries)
        self.assertEqual(consistency.pares_modelo_distintos.iloc[0], 2)

    def test_auditor_has_no_network_dependency(self):
        source = inspect.getsource(audit_module)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("download_job", source)


if __name__ == "__main__":
    unittest.main()
