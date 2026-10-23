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
