"""Etiquetas de presentación; los identificadores del modelo permanecen intactos."""
DISPLAY_LABELS = {"Sin actividad": "Sin detecciones", "Bajo": "Clúster 1",
                  "Moderado": "Clúster 2", "Alto": "Clúster 3"}
INTERNAL_ORDER = tuple(DISPLAY_LABELS)
DISPLAY_ORDER = tuple(DISPLAY_LABELS.values())
def display_label(value):
    return DISPLAY_LABELS.get(value, value)

def display_frame(frame):
    """Copia de presentación sin modificar el dataset ni el orden de filas."""
    result = frame.copy()
    for column in result.select_dtypes(include=["object", "string", "category"]):
        result[column] = result[column].map(display_label)
    return result.rename(index=display_label, columns=display_label)


def present(value):
    """Representación de resultados experimentales, sin mutar claves persistidas.

    Incluye Series, diccionarios anidados y nombres de métricas por clase.
    No se usa para entrenar, serializar ni ordenar probabilidades.
    """
    import pandas as pd

    if isinstance(value, str):
        if value in DISPLAY_LABELS:
            return display_label(value)
        for prefix in ("precision_", "recall_", "f1_"):
            for internal, visible in DISPLAY_LABELS.items():
                if value == prefix + internal.lower().replace(" ", "_"):
                    return prefix + visible.lower().replace(" ", "_")
        if " → " in value:
            return " → ".join(display_label(part) for part in value.split(" → "))
        return value
    if isinstance(value, pd.DataFrame):
        result = display_frame(value)
        return result.rename(index=present, columns=present)
    if isinstance(value, pd.Series):
        result = value.map(present).rename(index=present)
        result.name = present(value.name)
        return result
    if isinstance(value, dict):
        return {present(key): present(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(present(item) for item in value)
    return value
