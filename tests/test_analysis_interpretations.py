"""Coherencia documental desde artefactos guardados, sin ajustar modelos."""
from html.parser import HTMLParser
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier

from src import generar_puntos_4_6_plus as analysis

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results/analisis_puntos_4_6_plus/tables"


class TableCells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(self.cell.strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def saved_tables(notebook, cell):
    result = []
    for output in notebook["cells"][cell].get("outputs", []):
        html = output.get("data", {}).get("text/html")
        if html:
            parser = TableCells()
            parser.feed("".join(html))
            result.append(parser.rows)
    return result


def assert_saved_table(rows, expected):
    actual = [row[-len(expected.columns):] for row in rows[-len(expected):]]
    assert len(actual) == len(expected)
    for observed_row, expected_row in zip(actual, expected.itertuples(index=False, name=None)):
        for observed, value in zip(observed_row, expected_row):
            if isinstance(value, (int, float, np.number)):
                assert float(observed) == pytest.approx(float(value), abs=1e-9)
            else:
                assert observed == str(value)


@pytest.mark.parametrize("scenario", ["k3", "k4", "k5"])
def test_metrics_are_reproduced_from_saved_confusion(scenario):
    cm = pd.read_csv(TABLES / f"plus_matriz_confusion_{scenario}.csv", index_col=0)
    values = cm.to_numpy()
    correct = np.diag(values)
    recall = correct / values.sum(axis=1)
    precision = correct / values.sum(axis=0)
    f1 = 2 * correct / (values.sum(axis=0) + values.sum(axis=1))
    global_metrics = pd.read_csv(TABLES / "plus_metricas_globales_test.csv").set_index("escenario").loc[scenario]
    assert values.sum() == global_metrics["test"] == 1189
    assert f1.mean() == pytest.approx(global_metrics["f1_macro_test"], abs=0.5e-6)
    assert recall.mean() == pytest.approx(global_metrics["balanced_accuracy_test"], abs=0.5e-6)
    per_class = pd.read_csv(TABLES / "plus_metricas_por_clase_test.csv")
    per_class = per_class[per_class.escenario.eq(scenario)].set_index("clase").loc[cm.index]
    np.testing.assert_allclose(per_class[["precision", "recall", "f1"]], np.c_[precision, recall, f1], rtol=0, atol=0.5e-6)
    np.testing.assert_array_equal(per_class.support, values.sum(axis=1))


def test_all_notebook_tables_match_saved_artifacts():
    notebook = json.loads((ROOT / "Analisis_Puntos_4_6_Plus.ipynb").read_text())
    def csv(name):
        return pd.read_csv(TABLES / name)
    global_metrics = csv("plus_metricas_globales_test.csv")
    per_class = csv("plus_metricas_por_clase_test.csv")
    class_summary = csv("plus_distribucion_clases_por_k.csv")
    smallest = class_summary.sort_values(["escenario", "observaciones"]).groupby("escenario").first().reset_index()
    expected = {
        3: [csv("punto4_resumen_estadistico_niveles.csv").round(4)],
        7: [csv("punto6_kmeans_metricas_k_2_5.csv").round(4)],
        15: [csv("punto6_03_boxplot_temperatura_por_nivel_observaciones_validas.csv")],
        19: [csv("punto6_04_boxplot_humedad_por_nivel_observaciones_validas.csv")],
        23: [csv("punto6_heatmap_meteo_medianas_originales.csv").set_index(analysis.TARGET).round(3), csv("punto6_meteo_nulos_por_clase.csv")],
        27: [csv("punto6_departamento_recuentos_por_nivel.csv").set_index("departamento"), csv("punto6_departamento_porcentajes_por_nivel.csv").set_index("departamento").round(2)],
        31: [global_metrics[global_metrics.escenario.eq("k3")].round(4), per_class[per_class.escenario.eq("k3")].round(4)],
        35: [global_metrics.round(4), class_summary.round(4)],
        39: [per_class.round(4)],
        41: [csv(f"plus_matriz_confusion_{scenario}.csv").set_index("real") for scenario in ("k3", "k4", "k5")],
        43: [smallest[["escenario", "clase", "observaciones", "porcentaje_dataset"]].round(4)],
    }
    for cell, frames in expected.items():
        tables = saved_tables(notebook, cell)
        assert len(tables) == len(frames), cell
        for rows, frame in zip(tables, frames):
            assert_saved_table(rows, frame)


def test_generation_refreshes_notes_and_preserves_executed_cells(tmp_path, monkeypatch):
    before = json.loads((ROOT / "Analisis_Puntos_4_6_Plus.ipynb").read_text())
    before["cells"][32]["source"] = ["Interpretación antigua: F1=0.741; Bajo=0.253."]
    before["cells"][36]["source"] = ["Interpretación antigua: F1 macro=0.3963; k4=0.3384."]
    path = tmp_path / "Analisis_Puntos_4_6_Plus.ipynb"
    path.write_text(json.dumps(before))
    monkeypatch.setattr(analysis, "ROOT", tmp_path)
    monkeypatch.setattr(analysis, "TABLES", TABLES)
    def forbidden(*args, **kwargs):
        pytest.fail("Una regeneración documental no puede ajustar modelos")
    monkeypatch.setattr(KMeans, "fit", forbidden)
    monkeypatch.setattr(RandomForestClassifier, "fit", forbidden)
    analysis.make_notebook()
    after = json.loads(path.read_text())
    assert len(before["cells"]) == len(after["cells"]) == 44
    assert after["metadata"] == before["metadata"]
    for old, new in zip(before["cells"], after["cells"]):
        assert old["cell_type"] == new["cell_type"]
        if old["cell_type"] == "code":
            assert old == new
    notes = "".join(after["cells"][32]["source"])
    assert "F1=0.742" in notes and "F1=0.251" in notes
    sensitivity = "".join(after["cells"][36]["source"])
    for value in ("0.3967", "0.4137", "0.3371", "0.3636", "0.2669", "0.2836"):
        assert value in sensitivity
    assert "0.3963" not in sensitivity


def test_summary_uses_verified_values():
    summary = (ROOT / "results/analisis_puntos_4_6_plus/interpretaciones.md").read_text()
    assert "F1=0.251" in summary
    assert "0.3967 en k3" in summary
    assert "0.3963" not in summary and "F1=0.253" not in summary
