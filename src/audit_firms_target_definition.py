#!/usr/bin/env python3
"""Audita clases preliminares, puntos no asignados y semana final parcial.

No modifica el panel original ni crea un panel definitivo de entrenamiento.
FIRMS representa detecciones de anomalías térmicas/focos de calor, no incendios
forestales confirmados.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import altair as alt
import geopandas as gpd
import pandas as pd


CLASS_ORDER = ["Sin detección", "Bajo", "Moderado", "Alto"]
LAST_WEEK = pd.Timestamp("2025-12-29")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path,
                        default=Path("results/data/firms_departamento_semana.parquet"))
    parser.add_argument("--unassigned", type=Path,
                        default=Path("results/data/firms_uruguay_sin_departamento.csv"))
    parser.add_argument("--boundaries", type=Path,
                        default=Path("geoBoundaries-URY-ADM1-all/geoBoundaries-URY-ADM1.geojson"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/target_audit"))
    parser.add_argument("--figures-dir", type=Path,
                        default=Path("results/target_audit/figures"))
    return parser.parse_args()


def classify(values: pd.Series) -> pd.Categorical:
    return pd.cut(
        values,
        bins=[-1, 0, 1, 3, float("inf")],
        labels=CLASS_ORDER,
        ordered=True,
    )


def long_distribution(data: pd.DataFrame, group: str) -> pd.DataFrame:
    table = (
        data.groupby([group, "clase_preliminar"], observed=False)
        .size().rename("cantidad").reset_index()
    )
    totals = data.groupby(group).size().rename("total_observaciones")
    positives = (
        data.assign(positiva=data["cantidad_detecciones"].gt(0))
        .groupby(group)["positiva"].sum().rename("semanas_positivas")
    )
    table = table.merge(totals, on=group).merge(positives, on=group)
    table["porcentaje"] = table["cantidad"] / table["total_observaciones"] * 100
    table["porcentaje_semanas_positivas"] = (
        table["semanas_positivas"] / table["total_observaciones"] * 100
    )
    table["representacion_baja"] = table["cantidad"].lt(10)
    table["clase_ausente"] = table["cantidad"].eq(0)
    return table


def class_summary(data: pd.DataFrame, scenario: str) -> pd.DataFrame:
    out = (
        data.groupby("clase_preliminar", observed=False)
        .size().rename("cantidad").reset_index()
    )
    out["porcentaje"] = out["cantidad"] / len(data) * 100
    out.insert(0, "escenario", scenario)
    out["observaciones_totales"] = len(data)
    return out


def save_chart(chart: alt.Chart, path: Path) -> None:
    chart.save(path)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.figures_dir.mkdir(parents=True, exist_ok=True)
    alt.data_transformers.disable_max_rows()

    panel = pd.read_parquet(args.panel)
    panel["fecha_inicio_semana"] = pd.to_datetime(panel["fecha_inicio_semana"])
    panel["clase_preliminar"] = classify(panel["cantidad_detecciones"])

    year = long_distribution(panel, "anio")
    year.to_csv(args.output_dir / "clases_por_anio.csv", index=False)
    year.pivot(index="anio", columns="clase_preliminar", values="cantidad").to_csv(
        args.output_dir / "clases_por_anio_cruzada.csv"
    )
    department = long_distribution(panel, "departamento")
    department.to_csv(args.output_dir / "clases_por_departamento.csv", index=False)
    department.pivot(index="departamento", columns="clase_preliminar", values="cantidad").to_csv(
        args.output_dir / "clases_por_departamento_cruzada.csv"
    )

    high = panel.loc[panel["clase_preliminar"].eq("Alto")].copy()
    high_department = (
        high.groupby("departamento").size().rename("casos_altos").reset_index()
        .sort_values("casos_altos", ascending=False)
    )
    high_department["porcentaje_casos_altos"] = (
        high_department["casos_altos"] / len(high) * 100
    )
    high_department["porcentaje_acumulado"] = high_department["porcentaje_casos_altos"].cumsum()
    high_department.to_csv(args.output_dir / "clase_alta_por_departamento.csv", index=False)
    high_year = high.groupby("anio").size().rename("casos_altos").reset_index()
    high_year["porcentaje_casos_altos"] = high_year["casos_altos"] / len(high) * 100
    high_year.to_csv(args.output_dir / "clase_alta_por_anio.csv", index=False)

    # Auditoría espacial y simulación contrafactual; nunca modifica el panel.
    unassigned = pd.read_csv(args.unassigned)
    unassigned["fecha"] = pd.to_datetime(unassigned["fecha"])
    boundaries = gpd.read_file(args.boundaries).to_crs("EPSG:32721")
    points = gpd.GeoDataFrame(
        unassigned,
        geometry=gpd.points_from_xy(unassigned["longitud"], unassigned["latitud"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:32721")
    spatial_rows = []
    simulated = panel.copy()
    simulated["conteo_original"] = simulated["cantidad_detecciones"]
    for source_index, point in points.iterrows():
        distances = boundaries.geometry.distance(point.geometry)
        nearest_index = distances.idxmin()
        distance_m = float(distances.loc[nearest_index])
        nearest = boundaries.loc[nearest_index]
        week_start = point["fecha"] - pd.Timedelta(days=point["fecha"].weekday())
        mask = (
            simulated["departamento"].eq(nearest["shapeName"])
            & simulated["fecha_inicio_semana"].eq(week_start)
        )
        original_count = int(simulated.loc[mask, "cantidad_detecciones"].iloc[0])
        original_class = str(classify(pd.Series([original_count]))[0])
        simulated.loc[mask, "cantidad_detecciones"] += 1
        new_count = original_count + 1
        new_class = str(classify(pd.Series([new_count]))[0])
        if distance_m <= 100:
            proximity = "extremadamente próximo al límite (<=100 m)"
        elif distance_m <= 1000:
            proximity = "muy próximo al límite (<=1 km)"
        elif distance_m <= 5000:
            proximity = "próximo al límite (1–5 km)"
        else:
            proximity = "alejado más de 5 km del límite"
        if nearest["shapeName"] == "San José":
            interpretation = (
                "Zona próxima al borde San José–Colonia; compatible con un hueco o diferencia "
                "topológica entre la capa ADM1 y la codificación FIRMS. Sin capa hidrográfica no "
                "puede afirmarse que el punto esté en agua."
            )
        elif nearest["shapeName"] in {"Artigas", "Rivera"}:
            interpretation = (
                "Zona de frontera internacional; la separación subkilométrica es compatible con "
                "diferencias de precisión o representación de un límite fronterizo/fluvial. "
                "Sin una capa hidrográfica o frontera oficial no puede resolverse el lado correcto."
            )
        else:
            interpretation = (
                "Fuera de la unión ADM1; se requiere una capa cartográfica adicional para explicar el caso."
            )
        spatial_rows.append({
            "indice_fuente": int(source_index),
            "fecha": point["fecha"].date().isoformat(),
            "hora_adq_hhmm": str(point.get("hora_adq_hhmm", "")),
            "latitud": float(point["latitud"]),
            "longitud": float(point["longitud"]),
            "satelite": point.get("satelite", ""),
            "instrumento": point.get("instrumento", ""),
            "departamento_mas_cercano": nearest["shapeName"],
            "departamento_iso_mas_cercano": nearest["shapeISO"],
            "distancia_limite_m": distance_m,
            "distancia_limite_km": distance_m / 1000,
            "diagnostico_geometrico": proximity,
            "interpretacion_cartografica": interpretation,
            "fecha_inicio_semana": week_start.date().isoformat(),
            "conteo_original_semana_departamento": original_count,
            "clase_original": original_class,
            "conteo_simulado_si_reasignado": new_count,
            "clase_simulada_si_reasignado": new_class,
            "cambia_clase": original_class != new_class,
        })
    spatial = pd.DataFrame(spatial_rows)
    spatial.to_csv(args.output_dir / "detalle_sin_departamento.csv", index=False)
    affected = (
        simulated.loc[simulated["cantidad_detecciones"].ne(simulated["conteo_original"]), [
            "departamento", "fecha_inicio_semana", "conteo_original", "cantidad_detecciones"
        ]].copy()
    )
    affected["clase_original"] = classify(affected["conteo_original"])
    affected["clase_simulada"] = classify(affected["cantidad_detecciones"])
    affected["cambia_clase"] = affected["clase_original"] != affected["clase_simulada"]
    affected.to_csv(args.output_dir / "impacto_simulado_reasignacion.csv", index=False)

    partial = panel.loc[panel["fecha_inicio_semana"].eq(LAST_WEEK), [
        "departamento", "departamento_iso", "fecha_inicio_semana", "fecha_fin_semana",
        "cantidad_detecciones", "clase_preliminar"
    ]].sort_values("departamento")
    if len(partial) != 19:
        raise AssertionError("La semana parcial no contiene 19 departamentos.")
    partial.to_csv(args.output_dir / "semana_final_parcial.csv", index=False)
    without_partial = panel.loc[panel["fecha_inicio_semana"].ne(LAST_WEEK)].copy()
    scenario = pd.concat([
        class_summary(panel, "A_mantener_semana_parcial"),
        class_summary(without_partial, "B_excluir_semana_parcial"),
    ], ignore_index=True)
    scenario.to_csv(args.output_dir / "comparacion_semana_final.csv", index=False)

    year_chart = alt.Chart(year).mark_bar().encode(
        x=alt.X("anio:O", title="Año de inicio de semana"),
        y=alt.Y("porcentaje:Q", stack="normalize", title="Proporción de observaciones"),
        color=alt.Color("clase_preliminar:N", sort=CLASS_ORDER, title="Clase preliminar"),
        order=alt.Order("clase_preliminar:N", sort="ascending"),
        tooltip=["anio:O", "clase_preliminar:N", "cantidad:Q", alt.Tooltip("porcentaje:Q", format=".2f")],
    ).properties(width=720, height=420, title="Distribución preliminar de clases por año")
    save_chart(year_chart, args.figures_dir / "clases_por_anio.html")

    department_chart = alt.Chart(department).mark_bar().encode(
        y=alt.Y("departamento:N", title="Departamento"),
        x=alt.X("porcentaje:Q", stack="normalize", title="Proporción de observaciones"),
        color=alt.Color("clase_preliminar:N", sort=CLASS_ORDER, title="Clase preliminar"),
        order=alt.Order("clase_preliminar:N", sort="ascending"),
        tooltip=["departamento:N", "clase_preliminar:N", "cantidad:Q", alt.Tooltip("porcentaje:Q", format=".2f")],
    ).properties(width=720, height=520, title="Distribución preliminar de clases por departamento")
    save_chart(department_chart, args.figures_dir / "clases_por_departamento.html")

    summary = {
        "criterio_exploratorio": {
            "Sin detección": "0", "Bajo": "1", "Moderado": "2–3", "Alto": ">=4"
        },
        "observaciones_panel_original": int(len(panel)),
        "casos_altos": int(len(high)),
        "porcentaje_altos_panel": float(len(high) / len(panel) * 100),
        "porcentaje_altos_entre_positivas": float(len(high) / panel["cantidad_detecciones"].gt(0).sum() * 100),
        "rango_porcentaje_alto_anual": [
            float(year.loc[year["clase_preliminar"].eq("Alto"), "porcentaje"].min()),
            float(year.loc[year["clase_preliminar"].eq("Alto"), "porcentaje"].max()),
        ],
        "mayor_concentracion_alta_departamento": {
            "departamento": str(high_department.iloc[0]["departamento"]),
            "porcentaje": float(high_department.iloc[0]["porcentaje_casos_altos"]),
        },
        "mayor_concentracion_alta_anio": {
            "anio": int(high_year.loc[high_year["casos_altos"].idxmax(), "anio"]),
            "porcentaje": float(high_year["porcentaje_casos_altos"].max()),
        },
        "anios_con_clases_ausentes": sorted(year.loc[year["clase_ausente"], "anio"].unique().tolist()),
        "departamentos_con_clases_ausentes": sorted(
            department.loc[department["clase_ausente"], "departamento"].unique().tolist()
        ),
        "registros_sin_departamento": int(len(spatial)),
        "filas_panel_afectadas_si_reasignacion_cercana": int(len(affected)),
        "clases_que_cambiarian_si_reasignacion_cercana": int(affected["cambia_clase"].sum()),
        "semana_parcial_inicio": LAST_WEEK.date().isoformat(),
        "dias_disponibles_semana_parcial": 3,
        "detecciones_semana_parcial": int(partial["cantidad_detecciones"].sum()),
        "observaciones_si_se_excluye": int(len(without_partial)),
        "observaciones_removidas": int(len(panel) - len(without_partial)),
        "recomendacion_clases": "adecuada con precauciones",
        "recomendacion_no_asignados": "mantener excluidos hasta contar con evidencia cartográfica adicional",
        "recomendacion_semana_parcial": "excluir del futuro dataset supervisado mediante regla general de semana completa",
    }
    (args.output_dir / "resumen_auditoria_objetivo.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    recommendation_text = f"""# Recomendaciones de la auditoría de la variable objetivo

- Clases `0 / 1 / 2–3 / >=4`: **adecuadas con precauciones** para continuar la
  evaluación. Todas aparecen en cada año y departamento, pero su prevalencia
  cambia temporal y espacialmente; no deben congelarse todavía.
- Siete detecciones sin departamento: mantener excluidas mientras no exista una
  capa oficial adicional de frontera/hidrografía. Están a menos de 1 km de un
  límite ADM1. La simulación por cercanía afectaría {len(affected)} filas y
  cambiaría {int(affected['cambia_clase'].sum())} clases, pero cercanía no prueba
  pertenencia territorial.
- Semana 29/12/2025–04/01/2026: excluir del futuro dataset supervisado porque
  sólo hay tres días dentro de la cobertura del archivo. La regla reproducible
  recomendada es conservar únicamente semanas cuyo `fecha_fin_semana` sea menor
  o igual que la fecha máxima cubierta por la fuente. Esto quitaría 19 filas y
  dejaría {len(without_partial)} observaciones.
- No se creó un panel corregido ni se modificó el panel original.
"""
    (args.output_dir / "recomendaciones.md").write_text(recommendation_text, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
