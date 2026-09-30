"""Carga y uso del pipeline final del PAA sin reentrenamiento."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "artifacts" / "modelo_final.joblib"
DEFAULT_METADATA_PATH = PROJECT_ROOT / "artifacts" / "metadata_modelo.json"
PROHIBITED_INPUTS = {"cantidad_detecciones", "nivel_actividad_firms", "nivel_actividad_firms_codigo"}


def load_metadata(path: str | Path = DEFAULT_METADATA_PATH) -> dict:
    """Carga la descripción reproducible del modelo final."""
    metadata_path = Path(path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"No se encontró la metadata del modelo: {metadata_path}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def load_model(path: str | Path = DEFAULT_MODEL_PATH):
    """Carga el Pipeline completo ya entrenado."""
    model_path = Path(path)
    if not model_path.exists():
        raise FileNotFoundError(f"No se encontró el modelo serializado: {model_path}")
    return joblib.load(model_path)


def validate_input(data, metadata: dict | None = None) -> pd.DataFrame:
    """Valida columnas y devuelve un DataFrame en el orden esperado."""
    metadata = metadata or load_metadata()
    frame = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    forbidden_present = sorted(PROHIBITED_INPUTS.intersection(frame.columns))
    if forbidden_present:
        raise ValueError(
            "No se permiten variables contemporáneas o del target: "
            + ", ".join(forbidden_present)
        )
    required = list(metadata["variables"])
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Faltan variables requeridas: " + ", ".join(missing))
    if frame[required].isna().any().any():
        null_columns = frame[required].columns[frame[required].isna().any()].tolist()
        raise ValueError("Hay valores nulos en: " + ", ".join(null_columns))
    return frame[required]


def predict(data, model=None, metadata: dict | None = None):
    """Predice el nivel de actividad FIRMS estimado."""
    metadata = metadata or load_metadata()
    model = model or load_model()
    return model.predict(validate_input(data, metadata))


def predict_proba(data, model=None, metadata: dict | None = None) -> pd.DataFrame:
    """Devuelve probabilidades por clase cuando el modelo las soporta."""
    metadata = metadata or load_metadata()
    model = model or load_model()
    if not hasattr(model, "predict_proba"):
        raise AttributeError("El modelo seleccionado no implementa predict_proba().")
    probabilities = model.predict_proba(validate_input(data, metadata))
    return pd.DataFrame(probabilities, columns=model.classes_)
