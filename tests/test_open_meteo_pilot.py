import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd

from src.design_open_meteo_extraction import load_config
from src.extract_open_meteo import download_job, validate_payload
from src.run_open_meteo_pilot import (
    build_pilot_jobs, load_pilot_config, select_pilot_coordinates,
)


class OpenMeteoPilotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilot = load_pilot_config()
        cls.config = load_config(Path(cls.pilot["main_config"]))
        cls.catalog = pd.read_csv(cls.config["paths"]["coordinate_catalog"])
        cls.boundaries = gpd.read_file(cls.config["spatial_design"]["boundary_file"])
        cls.selected = select_pilot_coordinates(cls.catalog, cls.boundaries, cls.pilot)

    def test_selection_is_reproducible_and_has_five_spatial_cases(self):
        second = select_pilot_coordinates(self.catalog, self.boundaries, self.pilot)
        self.assertEqual(self.selected["coordenada_id"].tolist(), second["coordenada_id"].tolist())
        self.assertEqual(len(self.selected), 5)
        self.assertEqual(self.selected["tipo_caso"].nunique(), 5)
        self.assertEqual(set(self.selected.departamento), {"Montevideo", "Tacuarembó", "Rocha", "Rivera", "Canelones"})

    def test_guard_limits_pilot_to_two_requests_and_seventy_rows(self):
        jobs = build_pilot_jobs(self.selected, self.pilot)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(sum(len(job["coordinates"]) * 7 for job in jobs), 70)
        with self.assertRaises(ValueError):
            build_pilot_jobs(pd.concat([self.selected, self.selected.iloc[[0]]]), self.pilot)

    def _payload(self, job):
        variables = self.config["daily_variables"]
        dates = pd.date_range(job["start_date"], job["end_date"]).strftime("%Y-%m-%d").tolist()
        responses = []
        for coordinate in job["coordinates"]:
            daily = {"time": dates, **{variable: [1.0] * 7 for variable in variables}}
            responses.append({"latitude": coordinate["latitud"], "longitude": coordinate["longitud"],
                              "timezone": self.config["timezone"], "daily": daily,
                              "daily_units": {"time": "iso8601", **self.config["api_response_units"]}})
        return responses

    def test_validation_rejects_wrong_array_length_and_units(self):
        job = build_pilot_jobs(self.selected, self.pilot)[0]
        payload = self._payload(job)
        payload[0]["daily"][self.config["daily_variables"][0]] = [1.0] * 6
        with self.assertRaisesRegex(ValueError, "Longitudes"):
            validate_payload(payload, job, self.config)
        payload = self._payload(job)
        payload[0]["daily_units"][self.config["daily_variables"][0]] = "kelvin"
        with self.assertRaisesRegex(ValueError, "Unidades"):
            validate_payload(payload, job, self.config)

    def test_existing_raw_checkpoint_never_calls_network(self):
        job = build_pilot_jobs(self.selected, self.pilot)[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            path.write_text(json.dumps(self._payload(job)), encoding="utf-8")
            with patch("urllib.request.urlopen") as urlopen:
                result = download_job(job, self.config, path)
            urlopen.assert_not_called()
            self.assertEqual(result["status"], "checkpoint_reused")


if __name__ == "__main__":
    unittest.main()
