"""Controles de integridad de los artefactos oficiales, sin reentrenamiento."""

from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score

from src.inference import load_metadata, predict, predict_proba


MODEL_PATH = Path("artifacts/modelo_final.joblib")
METADATA_PATH = Path("artifacts/metadata_modelo.json")
DATA_PATH = Path("data/processed/modelado/dataset_modelado_nivel_actividad_firms.parquet")
SPLITS_DIR = Path("data/processed/modelado/splits")
KEY = ["departamento", "fecha_inicio_semana"]
OFFICIAL_CLASSES = {"Sin actividad", "Bajo", "Moderado", "Alto"}
PROHIBITED = {
    "anio", "cantidad_detecciones", "fecha_inicio_semana",
    "nivel_actividad_firms", "nivel_actividad_firms_codigo",
    "numero_semana", "presencia_firms",
}


@pytest.fixture(scope="module")
def official_resources():
    metadata = load_metadata(METADATA_PATH)
    model = joblib.load(MODEL_PATH)
    data = pd.read_parquet(DATA_PATH)
    keys = {
        name: pd.read_parquet(SPLITS_DIR / f"{name}_keys.parquet")
        for name in ("train", "validation", "test")
    }
    return metadata, model, data, keys


def test_official_files_exist():
    assert MODEL_PATH.is_file()
    assert METADATA_PATH.is_file()
    assert DATA_PATH.is_file()
    assert (SPLITS_DIR / "splits_metadata.json").is_file()


def test_model_is_random_forest_v1_and_features_match_metadata(official_resources):
    metadata, model, _, _ = official_resources
    assert metadata["nombre_modelo"] == "RandomForestClassifier V1"
    assert isinstance(model.named_steps["model"], RandomForestClassifier)
    assert list(model.feature_names_in_) == metadata["variables"]
    assert set(metadata["variables"]).isdisjoint(PROHIBITED)
    assert len(metadata["variables"]) == 6


def test_official_classes_are_present(official_resources):
    metadata, model, data, _ = official_resources
    assert set(metadata["clases"]) == OFFICIAL_CLASSES
    assert set(model.classes_) == OFFICIAL_CLASSES
    assert set(data["nivel_actividad_firms"].unique()) == OFFICIAL_CLASSES


def test_final_dataset_integrity_and_target_definition(official_resources):
    _, _, data, _ = official_resources
    assert data.shape == (7923, 19)
    assert data["departamento"].nunique() == 19
    assert data["fecha_inicio_semana"].nunique() == 417
    assert not data.duplicated(KEY).any()
    assert not data.isna().any().any()
    assert int(data["cantidad_detecciones"].sum()) == 8508

    expected = pd.Series("Alto", index=data.index)
    expected.loc[data["cantidad_detecciones"].eq(0)] = "Sin actividad"
    expected.loc[data["cantidad_detecciones"].eq(1)] = "Bajo"
    expected.loc[data["cantidad_detecciones"].between(2, 4)] = "Moderado"
    assert data["nivel_actividad_firms"].astype("string").eq(expected.astype("string")).all()


def test_splits_are_complete_disjoint_and_keep_expected_sizes(official_resources):
    _, _, data, keys = official_resources
    expected_sizes = {"train": 5546, "validation": 1188, "test": 1189}
    key_sets = {}
    for name, frame in keys.items():
        assert len(frame) == expected_sizes[name]
        assert not frame.duplicated(KEY).any()
        key_sets[name] = set(map(tuple, frame[KEY].itertuples(index=False, name=None)))

    assert key_sets["train"].isdisjoint(key_sets["validation"])
    assert key_sets["train"].isdisjoint(key_sets["test"])
    assert key_sets["validation"].isdisjoint(key_sets["test"])
    all_keys = set(map(tuple, data[KEY].itertuples(index=False, name=None)))
    assert set().union(*key_sets.values()) == all_keys


def test_serialized_model_reproduces_official_test_metrics(official_resources):
    metadata, model, data, keys = official_resources
    test = keys["test"].merge(data, on=KEY, how="left", validate="one_to_one")
    y_true = test[metadata["target"]]
    y_pred = model.predict(test[metadata["variables"]])
    observed = {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "f1_macro": f1_score(y_true, y_pred, average="macro"),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted"),
    }
    for metric, value in observed.items():
        assert value == pytest.approx(metadata["metricas_test"][metric], abs=1e-12)


def test_official_inference_uses_existing_artifact(official_resources):
    metadata, model, data, _ = official_resources
    sample = data.loc[[0], metadata["variables"]]
    prediction = predict(sample, model=model, metadata=metadata)
    probabilities = predict_proba(sample, model=model, metadata=metadata)
    assert prediction[0] in OFFICIAL_CLASSES
    assert set(probabilities.columns) == OFFICIAL_CLASSES
    assert probabilities.sum(axis=1).iloc[0] == pytest.approx(1.0)
