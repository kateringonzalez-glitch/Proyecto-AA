#!/usr/bin/env python3
"""Análisis descriptivo del panel FIRMS departamento-semana, sin modelado."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd


COUNT = "cantidad_detecciones"
PERCENTILES = [0.25, 0.50, 0.75, 0.90, 0.95, 0.99]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--panel", type=Path, default=Path("results/data/firms_departamento_semana.parquet")
    )
    parser.add_argument(
        "--assigned", type=Path, default=Path("results/data/firms_uruguay_asignadas.parquet")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/analysis"))
    parser.add_argument("--figures-dir", type=Path, default=Path("results/figures"))
    return parser.parse_args()


def distribution(series: pd.Series, scope: str) -> dict[str, float | int | str]:
    return {
        "alcance": scope,
        "observaciones": int(series.size),
        "ceros": int(series.eq(0).sum()),
        "positivos": int(series.gt(0).sum()),
        "porcentaje_ceros": float(series.eq(0).mean() * 100),
        "porcentaje_positivos": float(series.gt(0).mean() * 100),
        "minimo": int(series.min()),
        "maximo": int(series.max()),
        "media": float(series.mean()),
        "mediana": float(series.median()),
        "desviacion_estandar": float(series.std(ddof=1)),
        "q1": float(series.quantile(.25)),
        "q3": float(series.quantile(.75)),
        "p90": float(series.quantile(.90)),
        "p95": float(series.quantile(.95)),
        "p99": float(series.quantile(.99)),
    }


def quantile_classes(values: pd.Series, probabilities: list[float], method: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = values.quantile(probabilities)
    cuts = sorted(set(float(v) for v in raw.iloc[1:-1]))
    bins = [-np.inf, *cuts, np.inf]
    labels = [f"clase_{i + 1}" for i in range(len(bins) - 1)]
    classes = pd.cut(values, bins=bins, labels=labels, include_lowest=True)
    counts = classes.value_counts(sort=False).rename_axis("clase").reset_index(name="observaciones")
    counts["porcentaje"] = counts["observaciones"] / len(values) * 100
    counts.insert(0, "metodo", method)
    limits = pd.DataFrame({
        "metodo": method,
        "probabilidad": probabilities,
        "cuantil_observado": raw.to_numpy(),
    })
    limits["cortes_internos_unicos"] = ", ".join(map(lambda x: f"{x:g}", cuts))
    limits["clases_resultantes"] = len(labels)
    return counts, limits


def save_chart(chart: alt.Chart, path: Path) -> None:
    """Guarda HTML sin exigir un exportador PNG adicional."""
    chart.save(path)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.figures_dir.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(args.panel)
    assigned = pd.read_parquet(args.assigned)
    assigned["fecha"] = pd.to_datetime(assigned["fecha"], errors="raise")
    alt.data_transformers.disable_max_rows()
    required = {
        "departamento", "anio", "numero_semana", "fecha_inicio_semana",
        COUNT, "superficie_km2", "detecciones_por_1000_km2",
    }
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise ValueError(f"Faltan columnas en el panel: {missing}")
    panel["fecha_inicio_semana"] = pd.to_datetime(panel["fecha_inicio_semana"])
    positive = panel.loc[panel[COUNT].gt(0), COUNT]

    general = pd.DataFrame([
        distribution(panel[COUNT], "todas"),
        distribution(positive, "solo_positivas"),
    ])
    general.to_csv(args.output_dir / "distribucion_general.csv", index=False)

    department = (
        panel.groupby("departamento", as_index=False)
        .agg(
            detecciones_totales=(COUNT, "sum"),
            semanas_disponibles=(COUNT, "size"),
            semanas_sin_detecciones=(COUNT, lambda x: x.eq(0).sum()),
            semanas_con_detecciones=(COUNT, lambda x: x.gt(0).sum()),
            media_semanal=(COUNT, "mean"),
            mediana_semanal=(COUNT, "median"),
            maximo_semanal=(COUNT, "max"),
            p75=(COUNT, lambda x: x.quantile(.75)),
            p90=(COUNT, lambda x: x.quantile(.90)),
            p95=(COUNT, lambda x: x.quantile(.95)),
            p99=(COUNT, lambda x: x.quantile(.99)),
            superficie_km2=("superficie_km2", "first"),
        )
    )
    department["porcentaje_semanas_con_detecciones"] = (
        department["semanas_con_detecciones"] / department["semanas_disponibles"] * 100
    )
    department["detecciones_totales_por_1000_km2"] = (
        department["detecciones_totales"] / department["superficie_km2"] * 1000
    )
    department["ranking_conteo_absoluto"] = department["detecciones_totales"].rank(
        ascending=False, method="min"
    ).astype(int)
    department["ranking_por_superficie"] = department["detecciones_totales_por_1000_km2"].rank(
        ascending=False, method="min"
    ).astype(int)
    department["cambio_ranking_normalizado"] = (
        department["ranking_conteo_absoluto"] - department["ranking_por_superficie"]
    )
    department = department.sort_values("detecciones_totales", ascending=False)
    department.to_csv(args.output_dir / "distribucion_por_departamento.csv", index=False)

    annual_panel = (
        panel.groupby("anio", as_index=False)
        .agg(
            observaciones_departamento_semana=(COUNT, "size"),
            semanas_departamento_positivas=(COUNT, lambda x: x.gt(0).sum()),
            inicios_semana=("fecha_inicio_semana", "nunique"),
        )
    )
    annual_panel["porcentaje_semanas_departamento_positivas"] = (
        annual_panel["semanas_departamento_positivas"]
        / annual_panel["observaciones_departamento_semana"] * 100
    )
    annual_events = (
        assigned.assign(anio=assigned["fecha"].dt.year)
        .groupby("anio").size().rename("detecciones_totales").reset_index()
    )
    annual = annual_panel.merge(annual_events, on="anio", how="left")
    annual["variacion_interanual_pct"] = annual["detecciones_totales"].pct_change() * 100
    annual.to_csv(args.output_dir / "distribucion_anual.csv", index=False)

    monthly = (
        assigned.assign(mes=assigned["fecha"].dt.month)
        .groupby("mes", as_index=False).size().rename(columns={"size": "detecciones_totales"})
    )
    monthly.to_csv(args.output_dir / "distribucion_mensual.csv", index=False)
    week_of_year = (
        panel.groupby("numero_semana", as_index=False)
        .agg(detecciones_totales=(COUNT, "sum"), observaciones=(COUNT, "size"),
             observaciones_positivas=(COUNT, lambda x: x.gt(0).sum()))
    )
    week_of_year["porcentaje_positivas"] = (
        week_of_year["observaciones_positivas"] / week_of_year["observaciones"] * 100
    )
    week_of_year.to_csv(args.output_dir / "distribucion_semana_del_anio.csv", index=False)

    date_range = pd.date_range(assigned["fecha"].min(), assigned["fecha"].max(), freq="D")
    daily = assigned.groupby("fecha").size().reindex(date_range, fill_value=0)
    temporal_coverage = (
        daily.rename("detecciones").rename_axis("fecha").reset_index()
        .assign(anio_mes=lambda x: x["fecha"].dt.to_period("M").astype(str))
        .groupby("anio_mes", as_index=False)
        .agg(detecciones=("detecciones", "sum"), dias_periodo=("fecha", "size"),
             dias_con_detecciones=("detecciones", lambda x: x.gt(0).sum()))
    )
    temporal_coverage["dias_sin_detecciones"] = (
        temporal_coverage["dias_periodo"] - temporal_coverage["dias_con_detecciones"]
    )
    temporal_coverage.to_csv(args.output_dir / "cobertura_temporal_observada.csv", index=False)

    frequency = positive.value_counts().sort_index().rename_axis(COUNT).reset_index(name="observaciones")
    frequency["porcentaje_positivas"] = frequency["observaciones"] / len(positive) * 100
    frequency["porcentaje_acumulado"] = frequency["porcentaje_positivas"].cumsum()
    frequency.to_csv(args.output_dir / "frecuencia_conteos_positivos.csv", index=False)
    class_counts, class_limits = [], []
    for probs, name in [
        ([0, 1/3, 2/3, 1], "terciles_positivos"),
        ([0, .25, .50, .75, 1], "cuartiles_positivos"),
        ([0, .50, .90, 1], "mediana_p90_positivos"),
    ]:
        counts, limits = quantile_classes(positive, probs, name)
        class_counts.append(counts)
        class_limits.append(limits)
    pd.concat(class_counts, ignore_index=True).to_csv(
        args.output_dir / "alternativas_balance_clases.csv", index=False
    )
    pd.concat(class_limits, ignore_index=True).to_csv(
        args.output_dir / "alternativas_cortes_cuantiles.csv", index=False
    )

    heatmap = panel.pivot_table(index="departamento", columns="anio", values=COUNT, aggfunc="sum")
    heatmap.to_csv(args.output_dir / "detecciones_departamento_anio.csv")

    # Visualizaciones: se evita seaborn para no sumar una dependencia.
    base_hist = alt.Chart(panel).mark_bar(color="#386cb0").encode(
        x=alt.X(f"{COUNT}:Q", bin=alt.Bin(step=1), title="Cantidad de detecciones FIRMS"),
        y=alt.Y("count():Q", scale=alt.Scale(type="log"), title="Observaciones departamento-semana"),
        tooltip=[alt.Tooltip(f"{COUNT}:Q", bin=alt.Bin(step=1)), alt.Tooltip("count():Q")],
    ).properties(width=760, height=420, title="Detecciones FIRMS por departamento-semana (incluye ceros)")
    save_chart(base_hist, args.figures_dir / "01_histograma_todas.html")

    positive_frame = panel.loc[panel[COUNT].gt(0), [COUNT]]
    positive_hist = alt.Chart(positive_frame).mark_bar(color="#7fc97f").encode(
        x=alt.X(f"{COUNT}:Q", bin=alt.Bin(step=1), title="Cantidad de detecciones FIRMS"),
        y=alt.Y("count():Q", scale=alt.Scale(type="log"), title="Observaciones positivas"),
        tooltip=[alt.Tooltip(f"{COUNT}:Q", bin=alt.Bin(step=1)), alt.Tooltip("count():Q")],
    ).properties(width=760, height=420, title="Detecciones FIRMS por departamento-semana positivas")
    save_chart(positive_hist, args.figures_dir / "02_histograma_positivas.html")

    order = department["departamento"].tolist()
    box = alt.Chart(panel).mark_boxplot(extent="min-max", color="#386cb0").encode(
        x=alt.X("departamento:N", sort=order, title="Departamento", axis=alt.Axis(labelAngle=-65)),
        y=alt.Y(f"{COUNT}:Q", title="Detecciones FIRMS por semana"),
    ).properties(width=850, height=430, title="Distribución semanal de detecciones FIRMS por departamento")
    save_chart(box, args.figures_dir / "03_boxplot_departamentos.html")

    totals = alt.Chart(department).mark_bar(color="#fdc086").encode(
        x=alt.X("detecciones_totales:Q", title="Cantidad de detecciones FIRMS"),
        y=alt.Y("departamento:N", sort="-x", title="Departamento"),
        tooltip=["departamento:N", "detecciones_totales:Q"],
    ).properties(width=700, height=480, title="Detecciones FIRMS totales por departamento")
    save_chart(totals, args.figures_dir / "04_totales_departamento.html")

    positive_pct = alt.Chart(department).mark_bar(color="#beaed4").encode(
        x=alt.X("porcentaje_semanas_con_detecciones:Q", title="Porcentaje de semanas (%)"),
        y=alt.Y("departamento:N", sort="-x", title="Departamento"),
        tooltip=["departamento:N", alt.Tooltip("porcentaje_semanas_con_detecciones:Q", format=".2f")],
    ).properties(width=700, height=480, title="Semanas con al menos una detección FIRMS por departamento")
    save_chart(positive_pct, args.figures_dir / "05_porcentaje_positivo_departamento.html")

    evolution = alt.Chart(annual).mark_line(point=True, color="#386cb0").encode(
        x=alt.X("anio:O", title="Año calendario"),
        y=alt.Y("detecciones_totales:Q", title="Cantidad de detecciones FIRMS"),
        tooltip=["anio:O", "detecciones_totales:Q"],
    ).properties(width=760, height=420, title="Evolución anual de detecciones FIRMS asignadas")
    save_chart(evolution, args.figures_dir / "06_evolucion_anual.html")

    heat_long = heatmap.stack().rename("detecciones_totales").reset_index()
    heat = alt.Chart(heat_long).mark_rect().encode(
        x=alt.X("anio:O", title="Año de inicio de semana"),
        y=alt.Y("departamento:N", title="Departamento"),
        color=alt.Color("detecciones_totales:Q", scale=alt.Scale(scheme="yelloworangered"),
                        title="Detecciones FIRMS"),
        tooltip=["departamento:N", "anio:O", "detecciones_totales:Q"],
    ).properties(width=700, height=480, title="Detecciones FIRMS por departamento y año ISO")
    save_chart(heat, args.figures_dir / "07_heatmap_departamento_anio.html")

    summary = {
        "observaciones": int(len(panel)),
        "departamentos": int(panel["departamento"].nunique()),
        "semanas": int(panel["fecha_inicio_semana"].nunique()),
        "ceros": int(panel[COUNT].eq(0).sum()),
        "positivos": int(panel[COUNT].gt(0).sum()),
        "detecciones_total_panel": int(panel[COUNT].sum()),
        "conteo_positivo_moda": int(positive.mode().iloc[0]),
        "porcentaje_positivos_con_conteo_1": float(positive.eq(1).mean() * 100),
        "correlacion_spearman_ranking_absoluto_normalizado": float(
            department[["detecciones_totales", "detecciones_totales_por_1000_km2"]]
            .corr(method="spearman").iloc[0, 1]
        ),
        "meses_calendario_observados": int(len(temporal_coverage)),
        "meses_sin_detecciones": int(temporal_coverage["detecciones"].eq(0).sum()),
        "advertencia_discontinuidad": (
            "No hay meses completos sin detecciones, pero los cambios anuales no permiten distinguir "
            "variación real de cambios de cobertura/sensor sin metadatos de adquisiciones esperadas."
        ),
        "nota_temporal": "La grilla usa año de inicio de semana y ordinal de lunes; totales anuales/mensuales usan fecha de adquisición.",
        "nota_objetivo": "Conteos para análisis descriptivo; no se construyen predictores ni clases finales.",
    }
    (args.output_dir / "resumen_analisis.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

