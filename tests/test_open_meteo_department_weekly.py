import unittest

import numpy as np
import pandas as pd

from src.build_open_meteo_department_weekly import (
    aggregate_complete_weeks, assign_weeks, firms_compatibility, incomplete_weeks,
)


def synthetic_daily(days=7, directions=None):
    dates=pd.date_range("2021-12-27",periods=days,freq="D"); directions=directions or [359,1,0,2,358,1,359][:days]
    return pd.DataFrame({"departamento":["X"]*days,"departamento_iso":["UY-X"]*days,"fecha":dates,
        "cobertura_espacial_pct":[100.0]*days,"temperature_2m_max_mean_spatial":range(20,20+days),
        "temperature_2m_max_max_spatial":range(21,21+days),"temperature_2m_min_mean_spatial":[10.0]*days,
        "temperature_2m_min_min_spatial":[9.0]*days,"relative_humidity_2m_min_mean_spatial":[40.0]*days,
        "relative_humidity_2m_min_min_spatial":[30.0]*days,"relative_humidity_2m_max_mean_spatial":[80.0]*days,
        "relative_humidity_2m_max_max_spatial":[90.0]*days,"wind_speed_10m_max_mean_spatial":[5.0]*days,
        "wind_speed_10m_max_max_spatial":[7.0]*days,"precipitation_sum_mean_spatial":[1,0,2,0,3,0,4][:days],
        "et0_fao_evapotranspiration_mean_spatial":[2.0]*days,"et0_fao_evapotranspiration_max_spatial":[2.5]*days,
        "wind_direction_10m_dominant_circular_mean":directions,
        "wind_direction_10m_resultant_length":[.9]*days})


class OpenMeteoDepartmentWeeklyTest(unittest.TestCase):
    def test_monday_start_sunday_end_and_cross_year(self):
        assigned=assign_weeks(synthetic_daily())
        self.assertTrue(assigned.fecha_inicio_semana.eq(pd.Timestamp("2021-12-27")).all())
        self.assertTrue(assigned.fecha_fin_semana.eq(pd.Timestamp("2022-01-02")).all())
        self.assertEqual(assigned.fecha_inicio_semana.nunique(),1)

    def test_partial_week_is_detected_and_excluded(self):
        assigned=assign_weeks(synthetic_daily(6)); incomplete=incomplete_weeks(assigned)
        self.assertEqual(incomplete.n_dias_observados.iloc[0],6)
        self.assertTrue(aggregate_complete_weeks(assigned).empty)

    def test_weekly_scalar_operations(self):
        weekly=aggregate_complete_weeks(assign_weeks(synthetic_daily())).iloc[0]
        self.assertEqual(weekly.precipitation_sum_weekly,10)
        self.assertEqual(weekly.precipitation_days_weekly,4)
        self.assertEqual(weekly.et0_fao_evapotranspiration_sum_weekly,14)
        self.assertEqual(weekly.temperature_2m_max_mean_weekly,23)
        self.assertEqual(weekly.temperature_2m_max_weekly,27)

    def test_weekly_circular_mean_near_north_and_resultant_bounded(self):
        weekly=aggregate_complete_weeks(assign_weeks(synthetic_daily())).iloc[0]
        self.assertTrue(weekly.wind_direction_10m_dominant_circular_mean_weekly < 5 or weekly.wind_direction_10m_dominant_circular_mean_weekly > 355)
        self.assertTrue(0 <= weekly.wind_direction_10m_resultant_length_weekly <= 1)

    def test_identical_and_dispersed_weekly_directions(self):
        same=aggregate_complete_weeks(assign_weeks(synthetic_daily(directions=[90]*7))).iloc[0]
        dispersed=aggregate_complete_weeks(assign_weeks(synthetic_daily(directions=[0,45,90,135,180,225,270]))).iloc[0]
        self.assertAlmostEqual(same.wind_direction_10m_dominant_circular_mean_weekly,90)
        self.assertAlmostEqual(same.wind_direction_10m_resultant_length_weekly,1)
        self.assertLess(dispersed.wind_direction_10m_resultant_length_weekly,.2)

    def test_missing_day_and_weekly_key_uniqueness(self):
        weekly=aggregate_complete_weeks(assign_weeks(synthetic_daily()))
        self.assertFalse(weekly.duplicated(["departamento","fecha_inicio_semana"]).any())
        self.assertEqual(weekly.n_dias_observados.iloc[0],7)

    def test_firms_key_compatibility(self):
        weekly=aggregate_complete_weeks(assign_weeks(synthetic_daily()))
        firms=pd.DataFrame({"departamento":["X","Y"],"fecha_inicio_semana":pd.to_datetime(["2021-12-27"]*2)})
        summary,missing=firms_compatibility(weekly,firms)
        self.assertEqual(summary.claves_firms_encontradas.iloc[0],1); self.assertEqual(len(missing),1)


if __name__=="__main__": unittest.main()
