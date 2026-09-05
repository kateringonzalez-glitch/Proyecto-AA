import unittest

import pandas as pd

from src.build_firms_department_week_clean import assign_activity_classes
from src.build_firms_history_2017_2025 import (
    complete_monday_starts,
    preserve_target,
)


class FirmsHistory2017Test(unittest.TestCase):
    def test_complete_weeks_exclude_initial_and_final_partial_weeks(self):
        weeks = complete_monday_starts(pd.Timestamp("2017-01-01"), pd.Timestamp("2017-12-31"))
        self.assertEqual(len(weeks), 52)
        self.assertEqual(weeks.min(), pd.Timestamp("2017-01-02"))
        self.assertEqual(weeks.max(), pd.Timestamp("2017-12-25"))
        self.assertTrue((weeks.weekday == 0).all())

    def test_complete_weeks_general_rule(self):
        weeks = complete_monday_starts(pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-20"))
        self.assertEqual(weeks.tolist(), [pd.Timestamp("2020-01-06"), pd.Timestamp("2020-01-13")])

    def test_adding_history_does_not_modify_target(self):
        target = pd.DataFrame({
            "departamento": ["Artigas", "Canelones"],
            "fecha_inicio_semana": pd.to_datetime(["2018-01-01", "2018-01-01"]),
            "cantidad_detecciones": [0, 4],
        })
        target["nivel_actividad_firms"], target["nivel_actividad_firms_codigo"] = (
            assign_activity_classes(target.cantidad_detecciones)
        )
        history_2017 = pd.DataFrame({
            "departamento": ["Artigas", "Canelones"],
            "fecha_inicio_semana": pd.to_datetime(["2017-12-25", "2017-12-25"]),
            "cantidad_detecciones": [1, 2],
        })
        history_2017["nivel_actividad_firms"], history_2017["nivel_actividad_firms_codigo"] = (
            assign_activity_classes(history_2017.cantidad_detecciones)
        )
        history_2017["es_periodo_objetivo"] = False
        target_history = target.copy()
        target_history["es_periodo_objetivo"] = True
        history = pd.concat([history_2017, target_history], ignore_index=True)
        preserve_target(target, history)
        recovered = history.loc[history.es_periodo_objetivo, target.columns].reset_index(drop=True)
        pd.testing.assert_frame_equal(recovered, target)

    def test_activity_classes_remain_current_definition(self):
        labels, codes = assign_activity_classes(pd.Series([0, 1, 2, 3, 4, 10]))
        self.assertEqual(list(labels.astype(str)), [
            "Sin detección", "Bajo", "Moderado", "Moderado", "Alto", "Alto"
        ])
        self.assertEqual(codes.tolist(), [0, 1, 2, 2, 3, 3])


if __name__ == "__main__":
    unittest.main()
