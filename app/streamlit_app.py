"""Prototipo TRL 5 para inferencia del nivel de actividad FIRMS."""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.inference import load_metadata, load_model, predict, predict_proba  # noqa: E402


@st.cache_resource
def resources():
    return load_metadata(), load_model()


metadata, model = resources()
features = metadata["variables"]

st.title("Nivel estimado de actividad FIRMS")
st.caption("Prototipo del Proyecto de Aprendizaje Automático 2026")
mode = st.radio("Entrada", ["Ejemplo histórico", "Ingreso manual"], horizontal=True)

if mode == "Ejemplo histórico":
    examples = pd.read_parquet(ROOT / "app" / "demo_examples.parquet")
    selected = st.selectbox("Ejemplo", range(len(examples)), format_func=lambda i: f"Ejemplo {i + 1}")
    input_data = examples.iloc[[selected]][features]
    st.dataframe(input_data, hide_index=True)
else:
    values = {}
    for feature in features:
        if feature == "departamento":
            values[feature] = st.selectbox(
                "Departamento",
                ["Artigas", "Canelones", "Cerro Largo", "Colonia", "Durazno", "Flores", "Florida",
                 "Lavalleja", "Maldonado", "Montevideo", "Paysandú", "Río Negro", "Rivera", "Rocha",
                 "Salto", "San José", "Soriano", "Tacuarembó", "Treinta y Tres"],
            )
        elif feature == "mes":
            values[feature] = st.number_input("Mes", min_value=1, max_value=12, value=1, step=1)
        else:
            label = feature.replace("_", " ").capitalize()
            values[feature] = st.number_input(label, value=0.0)
    input_data = pd.DataFrame([values])

if st.button("Estimar nivel"):
    prediction = predict(input_data, model, metadata)[0]
    probabilities = predict_proba(input_data, model, metadata).iloc[0].rename("Probabilidad")
    st.success(f"Nivel de actividad FIRMS estimado: **{prediction}**")
    st.bar_chart(probabilities)

st.warning(
    "El resultado representa un nivel estimado de actividad FIRMS y no confirma "
    "la ocurrencia de un incendio forestal."
)
