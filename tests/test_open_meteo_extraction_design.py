import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd

from src.design_open_meteo_extraction import generate_catalog, load_config, validate_catalog
from src.extract_open_meteo import (
    batches, build_jobs, expected_days, main as extraction_main, request_params, year_blocks,
)


CONFIG_PATH = Path("config/open_meteo.json")


class OpenMeteoExtractionDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(CONFIG_PATH)
        cls.boundaries = gpd.read_file(cls.config["spatial_design"]["boundary_file"])
        cls.catalog = generate_catalog(cls.boundaries, cls.config)

    def test_catalog_is_reproducible_and_inside(self):
        second = generate_catalog(self.boundaries, self.config)
        self.assertEqual(self.catalog["coordenada_id"].tolist(), second["coordenada_id"].tolist())
        validate_catalog(self.catalog, self.boundaries)

    def test_catalog_has_unique_ids_and_nineteen_departments(self):
        self.assertFalse(self.catalog["coordenada_id"].duplicated().any())
        self.assertEqual(self.catalog["departamento"].nunique(), 19)

    def test_configuration_is_fixed_daily_schema(self):
        self.assertEqual(self.config["frequency"], "daily")
        self.assertEqual(self.config["model"], "era5_seamless")
        self.assertEqual(len(self.config["daily_variables"]), 8)
        self.assertEqual(self.config["timezone"], "America/Montevideo")

    def test_days_and_year_blocks(self):
        self.assertEqual(expected_days("2017-01-02", "2025-12-31"), 3286)
        blocks = year_blocks("2017-01-02", "2025-12-31")
        self.assertEqual(len(blocks), 9)
        self.assertEqual(blocks[0], ("2017-01-02", "2017-12-31"))

    def test_batching_preserves_every_coordinate_once(self):
        groups = batches(pd.DataFrame(self.catalog.drop(columns="geometry")), 10)
        ids = [identifier for group in groups for identifier in group["coordenada_id"]]
        self.assertEqual(sorted(ids), sorted(self.catalog["coordenada_id"]))
        self.assertEqual(len(ids), len(set(ids)))

    def test_requests_use_same_variables_and_parameters(self):
        jobs = build_jobs(pd.DataFrame(self.catalog.drop(columns="geometry")), self.config)
        expected = ",".join(self.config["daily_variables"])
        self.assertTrue(all(request_params(job, self.config)["daily"] == expected for job in jobs))
        self.assertTrue(all(request_params(job, self.config)["models"] == "era5_seamless" for job in jobs))

    def test_dry_run_never_calls_network(self):
        with patch("urllib.request.urlopen") as urlopen, patch.object(
            sys, "argv", ["extract_open_meteo.py", "--dry-run"]
        ):
            extraction_main()
        urlopen.assert_not_called()
        plan = json.loads(Path("results/open_meteo_extraction/dry_run_plan.json").read_text())
        self.assertEqual(plan["network_calls_performed"], 0)


if __name__ == "__main__":
    unittest.main()
