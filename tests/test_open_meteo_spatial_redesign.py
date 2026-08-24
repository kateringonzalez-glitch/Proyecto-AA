import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.audit_open_meteo_spatial_catalog import audit_payload, guarded_jobs, load_audit_config
from src.redesign_open_meteo_spatial_grid import (
    BOUNDARIES, CANDIDATE, ORIGINAL, RECOMMENDED_MARGIN_M, add_reproducible_fallbacks,
    build_candidate, filter_margin, points_with_boundary_distance, stable_fallback_id,
)


class OpenMeteoSpatialRedesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.boundaries, cls.points, cls.candidate = build_candidate()
        cls.audit_config = load_audit_config()

    def test_boundary_distance_is_metric_and_nonnegative(self):
        self.assertTrue(self.points.distancia_limite_m.ge(0).all())
        montevideo = self.points.loc[self.points.departamento.eq("Montevideo")].iloc[0]
        self.assertGreater(montevideo.distancia_limite_m, 1000)

    def test_margin_filter_is_exact(self):
        filtered = filter_margin(self.points, RECOMMENDED_MARGIN_M)
        self.assertTrue(filtered.distancia_limite_m.ge(RECOMMENDED_MARGIN_M).all())
        self.assertEqual(len(filtered), 186)

    def test_generation_is_reproducible_and_ids_stable(self):
        _, _, _, second = build_candidate()
        self.assertEqual(self.candidate.coordenada_id.tolist(), second.coordenada_id.tolist())
        grid_ids = set(self.candidate.loc[self.candidate.metodo_seleccion.eq("grid"), "coordenada_id"])
        self.assertTrue(grid_ids.issubset(set(self.original.coordenada_id)))

    def test_fallback_represents_all_nineteen_departments(self):
        self.assertEqual(self.candidate.departamento.nunique(), 19)
        fallback = self.candidate.loc[self.candidate.metodo_seleccion.eq("representative_point_fallback")]
        self.assertEqual(fallback.departamento.tolist(), ["Montevideo"])
        self.assertEqual(fallback.coordenada_id.nunique(), 1)

    def test_catalog_paths_are_separate(self):
        self.assertNotEqual(ORIGINAL.resolve(), CANDIDATE.resolve())
        self.assertNotEqual(CANDIDATE.resolve(), Path(self.audit_config["validated_catalog"]).resolve())

    def test_guarded_batching_is_one_day_and_nineteen_requests(self):
        jobs = guarded_jobs(pd.DataFrame(self.candidate.drop(columns="geometry")), self.audit_config)
        self.assertEqual(len(jobs), 19)
        self.assertEqual(sum(len(job["coordinates"]) for job in jobs), 187)
        oversized = pd.concat([pd.DataFrame(self.candidate.drop(columns="geometry"))] * 2, ignore_index=True)
        with self.assertRaises(ValueError):
            guarded_jobs(oversized, self.audit_config)

    def test_detects_other_department_and_outside_uruguay(self):
        coordinate = self.candidate.loc[self.candidate.departamento.eq("Montevideo")].iloc[0].drop(labels="geometry").to_dict()
        job = {"coordinates": [coordinate]}
        other = audit_payload({"latitude": -34.4, "longitude": -56.3}, job, self.boundaries)
        self.assertFalse(bool(other.punto_valido.iloc[0]))
        self.assertIn(other.estado_asignacion.iloc[0], {"otro_departamento", "fuera_uruguay"})
        outside = audit_payload({"latitude": 0.0, "longitude": 0.0}, job, self.boundaries)
        self.assertEqual(outside.estado_asignacion.iloc[0], "fuera_uruguay")


if __name__ == "__main__":
    unittest.main()
