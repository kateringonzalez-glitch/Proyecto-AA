"""Correspondencia verificable y evaluación posterior a la inferencia."""

from pathlib import Path

import pandas as pd

from src.visual_style import COLORS

ROOT = Path(__file__).resolve().parents[1]
KEY = ["departamento", "fecha_inicio_semana"]
TARGET = "nivel_actividad_firms"
ORDER = tuple(COLORS)


def load_test_examples(features, root=ROOT):
    """Lee test por sus claves originales; no obtiene etiquetas de predicciones."""
    directory = root / "data/processed/modelado"
    data = pd.read_parquet(directory / "dataset_modelado_nivel_actividad_firms.parquet")
    if data.duplicated(KEY).any():
        raise ValueError("El dataset contiene claves departamento-semana duplicadas.")
    partitions = {
        split: pd.read_parquet(directory / f"splits/{split}_keys.parquet")
        for split in ("train", "validation", "test")
    }
    all_keys = pd.concat(partitions.values(), ignore_index=True)
    if all_keys.duplicated(KEY).any():
        raise ValueError("Las particiones tienen claves duplicadas o compartidas.")
    test = partitions["test"].merge(data, on=KEY, how="left", validate="one_to_one", indicator=True)
    if not test["_merge"].eq("both").all() or not test[TARGET].isin(ORDER).all():
        raise ValueError("No se puede verificar la etiqueta real de todas las filas de test.")
    if test[list(features)].isna().any().any():
        raise ValueError("Hay variables predictoras faltantes en los ejemplos de test.")
    return test[KEY + [f for f in features if f not in KEY] + [TARGET]].copy()


def evaluate_prediction(actual, predicted):
    """Separa acierto multiclase y presencia; sólo acepta etiquetas conocidas."""
    if actual not in ORDER or predicted not in ORDER:
        raise ValueError("La evaluación requiere dos clases conocidas.")
    if actual == predicted:
        kind = "Acierto exacto"
        explanation = "La clase predicha coincide con la clase real."
    elif actual == "Sin actividad":
        kind = "Falso positivo de presencia"
        explanation = "Se predijo actividad, pero la etiqueta real indica Sin actividad."
    elif predicted == "Sin actividad":
        kind = "Falso negativo de presencia"
        explanation = "Se predijo Sin actividad, pero la etiqueta real indica actividad."
    elif ORDER.index(predicted) < ORDER.index(actual):
        kind = "Subestimación del nivel"
        explanation = "Se reconoció la presencia de actividad, pero se estimó un nivel menor al real."
    else:
        kind = "Sobreestimación del nivel"
        explanation = "Se reconoció la presencia de actividad, pero se estimó un nivel mayor al real."
    return {
        "correct": actual == predicted,
        "presence_correct": (actual == "Sin actividad") == (predicted == "Sin actividad"),
        "kind": kind,
        "explanation": explanation,
    }
