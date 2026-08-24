import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.compare_open_meteo_cell_selection import (
    assert_only_cell_selection_differs, build_ab_jobs, comparison_table,
    load_ab_config, load_exact_pilot_coordinates, spatial_rows, variant_config,
)
from src.design_open_meteo_extraction import load_config
from src.extract_open_meteo import request_params


class OpenMeteoCellSelectionABTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ab = load_ab_config()
        cls.config = load_config(Path(cls.ab["main_config"]))
        cls.coordinates = load_exact_pilot_coordinates(Path(cls.ab["pilot_coordinates"]), cls.ab["limits"])
        cls.jobs = build_ab_jobs(cls.coordinates, cls.ab)

    def test_reuses_exact_five_prior_coordinates(self):
        source = pd.read_csv(self.ab["pilot_coordinates"])
        self.assertEqual(set(self.coordinates.coordenada_id), set(source.coordenada_id))
        self.assertEqual(len(self.coordinates), 5)

    def test_guard_is_two_requests_and_ten_rows(self):
        self.assertEqual(len(self.jobs), 2)
        self.assertEqual(sum(len(job["coordinates"]) for job, _ in self.jobs), 10)
        altered = self.coordinates.iloc[:4]
        with self.assertRaises(ValueError):
            build_ab_jobs(altered, self.ab)

    def test_only_request_difference_is_cell_selection(self):
        job = self.jobs[0][0]
        assert_only_cell_selection_differs(job, self.config)
        land = request_params(job, variant_config(self.config, "land"))
        nearest = request_params(job, variant_config(self.config, "nearest"))
        self.assertEqual(land["cell_selection"], "land")
        self.assertEqual(nearest["cell_selection"], "nearest")

    def test_variant_paths_are_separate(self):
        root = Path(self.ab["paths"]["raw_directory"])
        self.assertNotEqual(root / "land", root / "nearest")

    def test_distance_and_department_change_detection(self):
        coordinate = self.coordinates.iloc[0].to_dict()
        boundaries = gpd.read_file(self.config["spatial_design"]["boundary_file"])
        job = {"coordinates": [coordinate]}
        payload = {"latitude": coordinate["latitud"], "longitude": coordinate["longitud"],
                   "elevation": 1, "timezone": "America/Montevideo", "daily_units": {}}
        same = spatial_rows(payload, job, "nearest", boundaries)
        self.assertAlmostEqual(same.distancia_solicitada_reportada_m.iloc[0], 0.0, places=5)
        self.assertTrue(bool(same.mismo_departamento.iloc[0]))
        payload["latitude"], payload["longitude"] = 0.0, 0.0
        changed = spatial_rows(payload, job, "nearest", boundaries)
        self.assertFalse(bool(changed.mismo_departamento.iloc[0]))

    def test_comparison_calculates_distance_difference(self):
        base = {"coordenada_id": "x", "tipo_caso": "costa", "departamento": "Rocha",
                "lat_solicitada": -34.7, "lon_solicitada": -54.5}
        spatial = pd.DataFrame([
            {**base, "cell_selection": "land", "lat_reportada": -34.8, "lon_reportada": -54.6,
             "distancia_solicitada_reportada_m": 10.0, "departamento_reportado": "Maldonado", "mismo_departamento": False},
            {**base, "cell_selection": "nearest", "lat_reportada": -34.7, "lon_reportada": -54.5,
             "distancia_solicitada_reportada_m": 2.0, "departamento_reportado": "Rocha", "mismo_departamento": True},
        ])
        result = comparison_table(spatial)
        self.assertEqual(result.diferencia_distancia_nearest_menos_land_m.iloc[0], -8.0)
        self.assertTrue(bool(result.nearest_mismo_departamento.iloc[0]))


if __name__ == "__main__":
    unittest.main()
