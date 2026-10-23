"""Evaluación posterior: procedencia real, cinco resultados y ambos modos de UI."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.historical_evaluation import KEY, TARGET, evaluate_prediction, load_test_examples
from src.class_labels import display_label
from src.inference import load_metadata, load_model, predict


@pytest.mark.parametrize("actual,predicted,kind,presence", [
    ("Bajo", "Bajo", "Acierto exacto", True),
    ("Sin actividad", "Alto", "Falso positivo de presencia", False),
    ("Moderado", "Sin actividad", "Falso negativo de presencia", False),
    ("Alto", "Bajo", "Subestimación del nivel", True),
    ("Bajo", "Moderado", "Sobreestimación del nivel", True),
])
def test_error_categories(actual, predicted, kind, presence):
    result = evaluate_prediction(actual, predicted)
    assert result["kind"] == kind
    assert result["presence_correct"] == presence
    assert result["correct"] == (actual == predicted)


def test_unknown_class_cannot_be_evaluated():
    with pytest.raises(ValueError, match="clases conocidas"):
        evaluate_prediction(None, "Bajo")


def test_demo_provenance():
    features = load_metadata()["variables"]
    test = load_test_examples(features)
    demo = pd.read_parquet("app/demo_examples.parquet")
    assert TARGET not in demo
    pd.testing.assert_frame_equal(demo, test[features].head(5), check_dtype=False)
    data = pd.read_parquet("data/processed/modelado/dataset_modelado_nivel_actividad_firms.parquet")
    match = demo.merge(data, on=features, validate="one_to_one")
    assert len(match) == 5
    pd.testing.assert_frame_equal(match[KEY + [TARGET]], test[KEY + [TARGET]].head(5), check_dtype=False)
    assert len(test) == 1189


def test_overlapping_partition_rejected(tmp_path):
    directory = tmp_path / "data/processed/modelado"
    (directory / "splits").mkdir(parents=True)
    row = pd.DataFrame({"departamento": ["Artigas"], "fecha_inicio_semana": [pd.Timestamp("2020-01-06")]})
    row.assign(nivel_actividad_firms="Bajo").to_parquet(directory / "dataset_modelado_nivel_actividad_firms.parquet")
    for split in ("train", "validation", "test"):
        row.to_parquet(directory / f"splits/{split}_keys.parquet")
    with pytest.raises(ValueError, match="compartidas"):
        load_test_examples([], root=tmp_path)


def test_real_cases_and_manual_ui(monkeypatch):
    metadata = load_metadata()
    test = load_test_examples(metadata["variables"])
    predictions = predict(test[metadata["variables"]], load_model(), metadata)
    cases = {}
    for i, (actual, predicted) in enumerate(zip(test[TARGET], predictions)):
        cases.setdefault(evaluate_prediction(actual, predicted)["kind"], i)
    assert len(cases) == 5
    import src.inference as inference
    original_predict = inference.predict
    original_proba = inference.predict_proba
    captured = []

    def checked_predict(frame, model, metadata):
        assert list(frame.columns) == metadata["variables"]
        assert TARGET not in frame.columns
        result = original_predict(frame, model, metadata)
        captured.append(result[0])
        return result

    def checked_proba(frame, model, metadata):
        assert list(frame.columns) == metadata["variables"]
        assert TARGET not in frame.columns
        return original_proba(frame, model, metadata)

    monkeypatch.setattr(inference, "predict", checked_predict)
    monkeypatch.setattr(inference, "predict_proba", checked_proba)
    app = AppTest.from_file("app/streamlit_app.py").run(timeout=30)
    assert not app.exception
    for kind, i in cases.items():
        app.selectbox[0].set_value(i).run(timeout=30)
        app.button[0].click().run(timeout=30)
        assert not app.exception
        text = " ".join(x.value for x in app.markdown)
        assert kind in text
        assert display_label(test.iloc[i][TARGET]) in text
        assert display_label(predictions[i]) in text
        assert not any(old in text for old in ("Sin actividad", "Bajo", "Moderado", "Alto"))
        assert captured[-1] == predictions[i]
        assert "Evaluación binaria de presencia" in text
        assert len(app.get("vega_lite_chart")) == 1
    app.radio[0].set_value("Ingreso manual").run(timeout=30)
    assert len(app.number_input) == 5
    assert "Temperatura máxima media semanal (°C)" in [x.label for x in app.number_input]
    app.button[0].click().run(timeout=30)
    assert not app.exception
    text = " ".join(x.value for x in app.markdown)
    assert "Categoría estadística FIRMS estimada" in text
    assert "Evaluación multiclase" not in text
    assert "Clase real" not in text
    assert not any(old in text for old in ("Sin actividad", "Bajo", "Moderado", "Alto"))
