"""Colores compartidos cuando el color identifica una clase de actividad."""

COLORS = {
    "Sin detecciones": "#6B7280",
    "Clúster 1": "#2563EB",
    "Clúster 2": "#F59E0B",
    "Clúster 3": "#DC2626",
}
# Perfiles ordenados por centroide dentro de cada K; no equivalen a los niveles k=3.
PROFILE_COLORS = {
    "Perfil positivo 1": "#0891B2",
    "Perfil positivo 2": "#7C3AED",
    "Perfil positivo 3": "#059669",
    "Perfil positivo 4": "#DB2777",
    "Perfil positivo 5": "#92400E",
}
CLASS_COLORS = {**COLORS, **PROFILE_COLORS}

# Alias compatibles para consumidores que trabajan con el modelo original.
from .class_labels import DISPLAY_LABELS
INTERNAL_COLORS = {key: COLORS[value] for key, value in DISPLAY_LABELS.items()}
