"""Prototipo TRL 5 para inferencia del nivel de actividad FIRMS."""

from pathlib import Path
import sys

import altair as alt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.inference import load_metadata, load_model, predict, predict_proba  # noqa: E402
from src.visual_style import COLORS  # noqa: E402
from src.historical_evaluation import TARGET, load_test_examples, evaluate_prediction  # noqa: E402

FIELD_INFO = {
    "temperature_2m_max_mean_weekly": ("Temperatura máxima media semanal (°C)", "°C"),
    "relative_humidity_2m_min_mean_weekly": ("Humedad relativa mínima media semanal (%)", "%"),
    "wind_speed_10m_max_mean_weekly": ("Velocidad máxima media del viento (m/s)", "m/s"),
    "precipitation_sum_weekly": ("Precipitación acumulada semanal (mm)", "mm"),
}


@st.cache_data
def training_references():
    """Referencias del ajuste final: train + validation, excluyendo test."""
    data = pd.read_parquet(ROOT / "data/processed/modelado/dataset_modelado_nivel_actividad_firms.parquet")
    keys = pd.concat([pd.read_parquet(ROOT / f"data/processed/modelado/splits/{split}_keys.parquet")
                      for split in ("train", "validation")], ignore_index=True)
    development = data.merge(keys, on=["departamento", "fecha_inicio_semana"], validate="one_to_one")
    return development[list(FIELD_INFO)].agg(["min", "max", "median"])


@st.cache_resource
def resources():
    return load_metadata(), load_model()


@st.cache_data
def historical_examples():
    return load_test_examples(load_metadata()["variables"])


metadata, model = resources()
features = metadata["variables"]

st.title("Nivel estimado de actividad FIRMS")
st.caption("Prototipo del Proyecto de Aprendizaje Automático 2026")
mode = st.radio("Entrada", ["Ejemplo histórico", "Ingreso manual"], horizontal=True)

if mode == "Ejemplo histórico":
    try:
        examples = historical_examples()
    except (ValueError, FileNotFoundError, KeyError) as exc:
        st.error(f"No se puede verificar la clase real: {exc}")
        st.stop()
    st.caption("Ejemplos de test, excluidos del ajuste final (train + validation). "
               "Etiqueta real recuperada por departamento y semana del dataset original. "
               "Test se evaluó después de fijar el modelo y también en la sensibilidad posterior.")
    selected = st.selectbox(
        "Ejemplo", range(len(examples)),
        format_func=lambda i: (f"{examples.iloc[i]['departamento']} · "
                               f"{examples.iloc[i]['fecha_inicio_semana']:%d/%m/%Y}"),
    )
    input_data = examples.iloc[[selected]][features]
    st.dataframe(input_data.rename(columns={
        "departamento": "Departamento", "mes": "Mes",
        **{feature: info[0] for feature, info in FIELD_INFO.items()},
    }), hide_index=True)
else:
    references = training_references()
    st.caption("Referencias del ajuste final: train + validation (6.734 filas), sin test. "
               "Los rangos observados son orientativos y no limitan el ingreso.")
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
            label, unit = FIELD_INFO[feature]
            ref = references[feature]
            context = (f"Rango observado en los datos de entrenamiento: {ref['min']:.2f} a "
                       f"{ref['max']:.2f} {unit}. Mediana: {ref['median']:.2f} {unit}.")
            values[feature] = st.number_input(label, value=0.0, help=context)
            st.caption(context)
    input_data = pd.DataFrame([values])

if st.button("Estimar nivel"):
    prediction = predict(input_data, model, metadata)[0]
    probabilities = predict_proba(input_data, model, metadata).iloc[0].rename("Probabilidad")
    if mode == "Ingreso manual":
        st.markdown(
            f'<div style="border-left:6px solid {COLORS[prediction]};padding:1rem">'
            f'Nivel de actividad FIRMS estimado: <strong>{prediction}</strong></div>',
            unsafe_allow_html=True,
        )
    if mode == "Ejemplo histórico":
        actual = examples.iloc[selected][TARGET]
        evaluation = evaluate_prediction(actual, prediction)
        real_col, predicted_col = st.columns(2)
        for column, label, value in [(real_col, "Clase real", actual),
                                      (predicted_col, "Clase predicha", prediction)]:
            column.markdown(
                f'<div style="border-left:4px solid {COLORS[value]};padding:0.5rem">'
                f'{label}<br><strong>{value}</strong></div>', unsafe_allow_html=True,
            )
        result = "Correcto" if evaluation["correct"] else "Incorrecto"
        st.write(f"**Evaluación multiclase: {result} — {evaluation['kind']}.**")
        st.caption(evaluation["explanation"])
        presence = "Correcto" if evaluation["presence_correct"] else "Incorrecto"
        st.write(f"**Evaluación binaria de presencia: {presence}.**")
        st.caption("Presencia agrupa Bajo, Moderado y Alto como actividad. "
                   "Puede acertar la presencia y equivocarse en el nivel.")
    st.caption("Probabilidades estimadas para las cuatro clases")
    chart_data = probabilities.rename_axis("Clase").reset_index()
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("Clase:N", sort=list(COLORS)),
        y=alt.Y("Probabilidad:Q", scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("Clase:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values())), legend=None),
        tooltip=["Clase:N", "Probabilidad:Q"],
    )
    st.altair_chart(chart, width="stretch")

st.warning(
    "FIRMS representa detecciones térmicas. El resultado estima su nivel de actividad y no confirma "
    "la ocurrencia de un incendio forestal."
)
