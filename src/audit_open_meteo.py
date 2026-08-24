#!/usr/bin/env python3
"""Auditoría reproducible de los datos METEO/Open-Meteo heredados de LIDIA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import altair as alt
import geopandas as gpd
import numpy as np
import pandas as pd


DAILY_VARIABLES = [
    "temperature_2m_max", "temperature_2m_min", "relative_humidity_2m_min",
    "relative_humidity_2m_max", "wind_speed_10m_max",
    "wind_direction_10m_dominant", "precipitation_sum",
    "et0_fao_evapotranspiration",
]
DERIVED_VARIABLES = [
    "riesgo_temp", "riesgo_humedad", "riesgo_viento", "riesgo_sequia",
    "indice_riesgo", "nivel_riesgo",
]
HOURLY_VARIABLES = [
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
    "wind_direction_10m", "rain", "surface_pressure",
]
ALL_VARIABLES = DAILY_VARIABLES + DERIVED_VARIABLES + HOURLY_VARIABLES

# Las unidades configurables de Open-Meteo no pueden reconstruirse sin el request.
UNITS = {
    "temperature_2m_max": ("pendiente", "diaria", "meteorológica"),
    "temperature_2m_min": ("pendiente", "diaria", "meteorológica"),
    "relative_humidity_2m_min": ("pendiente", "diaria", "meteorológica"),
    "relative_humidity_2m_max": ("pendiente", "diaria", "meteorológica"),
    "wind_speed_10m_max": ("pendiente", "diaria", "meteorológica"),
    "wind_direction_10m_dominant": ("pendiente", "diaria", "meteorológica"),
    "precipitation_sum": ("pendiente", "diaria", "meteorológica"),
    "et0_fao_evapotranspiration": ("pendiente", "diaria", "meteorológica"),
    "riesgo_temp": ("sin unidad documentada", "diaria", "derivada heredada"),
    "riesgo_humedad": ("sin unidad documentada", "diaria", "derivada heredada"),
    "riesgo_viento": ("sin unidad documentada", "diaria", "derivada heredada"),
    "riesgo_sequia": ("sin unidad documentada", "diaria", "derivada heredada"),
    "indice_riesgo": ("sin unidad documentada", "diaria", "derivada heredada"),
    "nivel_riesgo": ("categoría sin definición local", "diaria", "derivada heredada"),
    "temperature_2m": ("pendiente", "horaria", "meteorológica"),
    "relative_humidity_2m": ("pendiente", "horaria", "meteorológica"),
    "wind_speed_10m": ("pendiente", "horaria", "meteorológica"),
    "wind_direction_10m": ("pendiente", "horaria", "meteorológica"),
    "rain": ("pendiente", "horaria", "meteorológica"),
    "surface_pressure": ("pendiente", "horaria", "meteorológica"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meteo", type=Path, default=Path("data/meteo_2018_2025.parquet"))
    parser.add_argument("--meteo-2025", type=Path, default=Path("data/meteo_2025.parquet"))
    parser.add_argument("--firms", type=Path,
                        default=Path("results/data/firms_departamento_semana_clean.parquet"))
    parser.add_argument("--boundaries", type=Path,
                        default=Path("geoBoundaries-URY-ADM1-all/geoBoundaries-URY-ADM1.geojson"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/open_meteo_audit"))
    return parser.parse_args()


def monday_start(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="raise", utc=True).dt.tz_localize(None).dt.normalize()
    return dates - pd.to_timedelta(dates.dt.weekday, unit="D")


def completeness(observed: pd.Series | int, expected: pd.Series | int) -> pd.Series | float:
    result = np.asarray(observed, dtype=float) / np.asarray(expected, dtype=float) * 100
    return float(result) if result.ndim == 0 else pd.Series(result, index=getattr(observed, "index", None))


def assign_unique_points(data: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    points = data[["punto", "latitud", "longitud"]].drop_duplicates().copy()
    geo = gpd.GeoDataFrame(
        points, geometry=gpd.points_from_xy(points["longitud"], points["latitud"]), crs="EPSG:4326"
    )
    joined = gpd.sjoin(
        geo, boundaries[["shapeName", "shapeISO", "geometry"]], how="left", predicate="within"
    ).rename(columns={"shapeName": "departamento", "shapeISO": "departamento_iso"})
    metric_boundaries = boundaries.to_crs("EPSG:32721")
    metric_points = joined.to_crs("EPSG:32721")
    distance_to_boundary = []
    for _, point in metric_points.iterrows():
        if pd.isna(point["departamento"]):
            distance_to_boundary.append(np.nan)
        else:
            polygon = metric_boundaries.loc[
                metric_boundaries["shapeISO"].eq(point["departamento_iso"]), "geometry"
            ].iloc[0]
            distance_to_boundary.append(float(point.geometry.distance(polygon.boundary)))
    joined["distancia_limite_departamental_km"] = np.asarray(distance_to_boundary) / 1000
    return joined.drop(columns=["geometry", "index_right"], errors="ignore")


def point_temporal_coverage(data: pd.DataFrame, frequency: str) -> pd.DataFrame:
    timestamp = "fecha" if frequency == "diaria" else "fecha_hora_utc"
    frame = data.copy()
    frame["_timestamp"] = pd.to_datetime(frame[timestamp], errors="coerce", utc=True)
    out = (
        frame.groupby(["departamento", "departamento_iso", "punto", "latitud", "longitud"],
                      dropna=False, as_index=False)
        .agg(fecha_min=("_timestamp", "min"), fecha_max=("_timestamp", "max"),
             registros=("_timestamp", "size"), timestamps_unicos=("_timestamp", "nunique"))
    )
    factor = pd.Timedelta(days=1) if frequency == "diaria" else pd.Timedelta(hours=1)
    out["periodo_esperado_entre_extremos"] = (
        ((out["fecha_max"] - out["fecha_min"]) / factor).astype(int) + 1
    )
    out["completitud_entre_extremos_pct"] = completeness(
        out["timestamps_unicos"], out["periodo_esperado_entre_extremos"]
    )
    block_min = frame["_timestamp"].min()
    block_max = frame["_timestamp"].max()
    block_expected = int((block_max - block_min) / factor) + 1
    out["periodo_esperado_bloque_completo"] = block_expected
    out["completitud_bloque_completo_pct"] = completeness(out["timestamps_unicos"], block_expected)
    out.insert(0, "frecuencia", frequency)
    return out


def variable_inventory(uruguay: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable in ALL_VARIABLES:
        unit, frequency, kind = UNITS[variable]
        applicable = uruguay[uruguay[variable].notna()]
        values = applicable[variable]
        numeric = pd.to_numeric(values, errors="coerce")
        rows.append({
            "variable": variable, "unidad": unit,
            "estado_unidad": "no verificable sin código/metadata de extracción",
            "frecuencia": frequency, "tipo_variable": kind,
            "dtype": str(uruguay[variable].dtype),
            "observaciones_aplicables": int(len(applicable)),
            "nulos_en_bloque_aplicable": int(values.isna().sum()),
            "porcentaje_nulos_en_bloque_aplicable": float(values.isna().mean() * 100) if len(values) else np.nan,
            "minimo": float(numeric.min()) if numeric.notna().any() else None,
            "maximo": float(numeric.max()) if numeric.notna().any() else None,
            "media": float(numeric.mean()) if numeric.notna().any() else None,
            "observaciones": (
                "Nulos del archivo combinado fuera del bloque aplicable son estructurales por cambio de esquema."
            ),
        })
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figures = args.output_dir / "figures"
    figures.mkdir(exist_ok=True)
    alt.data_transformers.disable_max_rows()

    combined = pd.read_parquet(args.meteo)
    meteo_2025 = pd.read_parquet(args.meteo_2025)
    boundaries = gpd.read_file(args.boundaries).to_crs("EPSG:4326")
    firms = pd.read_parquet(args.firms)
    daily = combined.loc[combined["temperature_2m_max"].notna()].copy()
    hourly = combined.loc[combined["fecha_hora_utc"].notna()].copy()
    uruguay_daily = daily.loc[daily["pais_codigo"].eq("URY")].copy()
    uruguay_hourly = hourly.loc[hourly["pais_codigo"].eq("URY")].copy()
    uruguay = combined.loc[combined["pais_codigo"].eq("URY")].copy()

    point_assignments = assign_unique_points(uruguay, boundaries)
    point_assignments.to_csv(args.output_dir / "puntos_open_meteo.csv", index=False)
    daily = daily.merge(point_assignments, on=["punto", "latitud", "longitud"], how="left")
    hourly = hourly.merge(point_assignments, on=["punto", "latitud", "longitud"], how="left")
    uruguay_daily = daily.loc[daily["pais_codigo"].eq("URY")].copy()
    uruguay_hourly = hourly.loc[hourly["pais_codigo"].eq("URY")].copy()

    # Contraste del artefacto 2025 con el bloque horario del combinado.
    compare_columns = list(meteo_2025.columns)
    sort_columns = ["pais_codigo", "punto", "fecha_hora_utc"]
    left = hourly[compare_columns].sort_values(sort_columns).reset_index(drop=True)
    right = meteo_2025[compare_columns].sort_values(sort_columns).reset_index(drop=True)
    artifact_2025_exact_schema_equal = bool(left.equals(right))
    value_differences = {}
    for column in compare_columns:
        if pd.api.types.is_numeric_dtype(left[column]) and pd.api.types.is_numeric_dtype(right[column]):
            equal = left[column].astype(float).eq(right[column].astype(float))
        else:
            equal = left[column].astype("string").eq(right[column].astype("string"))
        equal |= left[column].isna() & right[column].isna()
        value_differences[column] = int((~equal).sum())
    artifact_2025_values_equal = len(left) == len(right) and not any(value_differences.values())

    temporal = pd.concat([
        point_temporal_coverage(uruguay_daily, "diaria"),
        point_temporal_coverage(uruguay_hourly, "horaria"),
    ], ignore_index=True)
    temporal.to_csv(args.output_dir / "cobertura_temporal.csv", index=False)

    spatial_rows = []
    for frequency, frame in [("diaria", uruguay_daily), ("horaria", uruguay_hourly)]:
        for department, group in frame.groupby("departamento"):
            spatial_rows.append({
                "frecuencia": frequency, "departamento": department,
                "cantidad_puntos": int(group[["punto", "latitud", "longitud"]].drop_duplicates().shape[0]),
                "lat_min": float(group["latitud"].min()), "lat_max": float(group["latitud"].max()),
                "lon_min": float(group["longitud"].min()), "lon_max": float(group["longitud"].max()),
                "registros": int(len(group)),
                "fecha_min": str(pd.to_datetime(group["fecha"], errors="coerce").min().date()),
                "fecha_max": str(pd.to_datetime(group["fecha"], errors="coerce").max().date()),
                "variables_disponibles": ";".join(
                    DAILY_VARIABLES + DERIVED_VARIABLES if frequency == "diaria" else HOURLY_VARIABLES
                ),
            })
    spatial = pd.DataFrame(spatial_rows)
    full_spatial_index = pd.MultiIndex.from_product(
        [["diaria", "horaria"], sorted(boundaries["shapeName"])],
        names=["frecuencia", "departamento"],
    )
    spatial = spatial.set_index(["frecuencia", "departamento"]).reindex(full_spatial_index).reset_index()
    spatial[["cantidad_puntos", "registros"]] = spatial[["cantidad_puntos", "registros"]].fillna(0).astype(int)
    spatial.to_csv(args.output_dir / "cobertura_por_departamento.csv", index=False)

    inventory = variable_inventory(uruguay)
    inventory.to_csv(args.output_dir / "inventario_variables.csv", index=False)
    inventory.to_csv(args.output_dir / "calidad_por_variable.csv", index=False)

    # Calidad por bloque, evitando confundir nulos estructurales entre esquemas.
    daily["_timestamp"] = pd.to_datetime(daily["fecha"], errors="coerce", utc=True)
    hourly["_timestamp"] = pd.to_datetime(hourly["fecha_hora_utc"], errors="coerce", utc=True)
    quality = []
    for frequency, frame, variables in [
        ("diaria", uruguay_daily, DAILY_VARIABLES + DERIVED_VARIABLES),
        ("horaria", uruguay_hourly, HOURLY_VARIABLES),
    ]:
        timestamp = pd.to_datetime(
            frame["fecha"] if frequency == "diaria" else frame["fecha_hora_utc"],
            errors="coerce", utc=True,
        )
        numeric = frame[[v for v in variables if v != "nivel_riesgo"]].apply(pd.to_numeric, errors="coerce")
        quality.append({
            "frecuencia": frequency, "registros": int(len(frame)),
            "duplicados_exactos": int(frame.duplicated().sum()),
            "duplicados_punto_timestamp": int(pd.DataFrame({"punto": frame["punto"], "ts": timestamp}).duplicated().sum()),
            "timestamps_invalidos": int(timestamp.isna().sum()),
            "coordenadas_faltantes": int(frame[["latitud", "longitud"]].isna().any(axis=1).sum()),
            "valores_infinitos": int(np.isinf(numeric.to_numpy(dtype=float)).sum()),
            "nulos_variables_aplicables": int(frame[variables].isna().sum().sum()),
        })
    pd.DataFrame(quality).to_csv(args.output_dir / "resumen_calidad.csv", index=False)

    # Cobertura mensual por punto sobre la grilla completa de cada bloque.
    monthly_parts = []
    for frequency, frame, timestamp_col in [
        ("diaria", uruguay_daily, "fecha"), ("horaria", uruguay_hourly, "fecha_hora_utc")
    ]:
        temp = frame.copy()
        temp["timestamp"] = pd.to_datetime(temp[timestamp_col], utc=True)
        temp["anio_mes"] = temp["timestamp"].dt.tz_localize(None).dt.to_period("M").astype(str)
        grouped = temp.groupby(["departamento", "punto", "anio_mes"], as_index=False).agg(
            observaciones=("timestamp", "nunique"), fecha_min=("timestamp", "min"), fecha_max=("timestamp", "max")
        )
        months = pd.period_range(temp["timestamp"].min().tz_localize(None).to_period("M"),
                                 temp["timestamp"].max().tz_localize(None).to_period("M"), freq="M")
        points = temp[["departamento", "punto"]].drop_duplicates()
        grid = points.merge(pd.DataFrame({"anio_mes": months.astype(str)}), how="cross")
        grouped = grid.merge(grouped, on=["departamento", "punto", "anio_mes"], how="left")
        grouped["observaciones"] = grouped["observaciones"].fillna(0).astype(int)
        month_dates = pd.to_datetime(grouped["anio_mes"] + "-01")
        grouped["esperadas"] = month_dates.dt.days_in_month * (1 if frequency == "diaria" else 24)
        grouped["completitud_pct"] = completeness(grouped["observaciones"], grouped["esperadas"])
        grouped.insert(0, "frecuencia", frequency)
        monthly_parts.append(grouped)
    monthly = pd.concat(monthly_parts, ignore_index=True)
    monthly.to_csv(args.output_dir / "cobertura_mensual.csv", index=False)

    aggregation_rows = [
        ("temperature_2m_max", "diaria", "máximo semanal; media de máximas diarias", "sí, con máximo horario 2025"),
        ("temperature_2m_min", "diaria", "mínimo semanal; media de mínimas diarias", "sí, con mínimo horario 2025"),
        ("relative_humidity_2m_min", "diaria", "mínimo semanal; media de mínimas diarias", "sí, derivable de horario 2025"),
        ("relative_humidity_2m_max", "diaria", "máximo semanal", "sí, derivable de horario 2025"),
        ("wind_speed_10m_max", "diaria", "máximo semanal; media de máximos diarios", "sí, derivable de horario 2025"),
        ("wind_direction_10m_dominant", "diaria", "estadística circular, no media aritmética", "requiere metodología circular"),
        ("precipitation_sum", "diaria", "suma semanal; días con precipitación", "no confirmada contra rain 2025"),
        ("et0_fao_evapotranspiration", "diaria", "suma o media semanal", "no: ausente en 2025"),
        ("temperature_2m", "horaria", "media, mínimo y máximo semanal", "sólo 2025"),
        ("relative_humidity_2m", "horaria", "media y mínimo semanal", "sólo 2025"),
        ("wind_speed_10m", "horaria", "media y máximo semanal", "sólo 2025"),
        ("wind_direction_10m", "horaria", "estadística circular", "sólo 2025"),
        ("rain", "horaria", "suma semanal; días/horas con lluvia", "equivalencia con precipitation_sum no probada"),
        ("surface_pressure", "horaria", "media, mínimo y máximo semanal", "no: ausente antes de 2025"),
    ]
    pd.DataFrame(aggregation_rows, columns=[
        "variable", "frecuencia_origen", "agregaciones_semanales_tecnicamente_posibles",
        "armonizacion_2018_2025",
    ]).to_csv(args.output_dir / "agregaciones_semanales_posibles.csv", index=False)
    schema = pd.DataFrame([
        {
            "periodo": "2018-01-01/2024-12-31", "frecuencia": "diaria",
            "timestamp_principal": "fecha", "filas_uruguay": len(uruguay_daily),
            "departamentos_geometricos": uruguay_daily["departamento"].nunique(),
            "variables": ";".join(DAILY_VARIABLES + DERIVED_VARIABLES),
        },
        {
            "periodo": "2025-01-01/2025-12-31", "frecuencia": "horaria",
            "timestamp_principal": "fecha_hora_utc", "filas_uruguay": len(uruguay_hourly),
            "departamentos_geometricos": uruguay_hourly["departamento"].nunique(),
            "variables": ";".join(HOURLY_VARIABLES),
        },
    ])
    schema.to_csv(args.output_dir / "esquema_por_periodo.csv", index=False)

    # Disponibilidad diaria: un departamento está cubierto si al menos un punto
    # tiene el día diario o sus 24 horas completas.
    daily_days = uruguay_daily.assign(dia=pd.to_datetime(uruguay_daily["fecha"])).groupby(
        ["departamento", "dia"], as_index=False
    ).agg(registros=("punto", "size"))
    daily_days["bloque"] = "diario"
    hourly_days = uruguay_hourly.assign(
        dia=pd.to_datetime(uruguay_hourly["fecha_hora_utc"], utc=True).dt.tz_localize(None).dt.normalize()
    ).groupby(["departamento", "dia"], as_index=False).agg(horas=("fecha_hora_utc", "nunique"))
    hourly_days = hourly_days.loc[hourly_days["horas"].eq(24)].copy()
    hourly_days["bloque"] = "horario"
    available_days = pd.concat([
        daily_days[["departamento", "dia", "bloque"]],
        hourly_days[["departamento", "dia", "bloque"]],
    ], ignore_index=True)
    available_days["fecha_inicio_semana"] = monday_start(available_days["dia"])
    weekly = available_days.groupby(["departamento", "fecha_inicio_semana"], as_index=False).agg(
        dias_cubiertos=("dia", "nunique"), bloques=("bloque", lambda x: "+".join(sorted(set(x))))
    )
    weekly["semana_temporalmente_completa"] = weekly["dias_cubiertos"].eq(7)
    weekly.to_csv(args.output_dir / "compatibilidad_departamento_semana.csv", index=False)

    firm_keys = firms[["departamento", "fecha_inicio_semana", "anio"]].copy()
    firm_keys["fecha_inicio_semana"] = pd.to_datetime(firm_keys["fecha_inicio_semana"])
    compatibility = firm_keys.merge(
        weekly, on=["departamento", "fecha_inicio_semana"], how="left", validate="one_to_one"
    )
    compatibility["dias_cubiertos"] = compatibility["dias_cubiertos"].fillna(0).astype(int)
    compatibility["semana_temporalmente_completa"] = (
        compatibility["semana_temporalmente_completa"].fillna(False).astype(bool)
    )
    compatibility.to_csv(args.output_dir / "compatibilidad_con_firms.csv", index=False)
    missing_year = compatibility.groupby("anio", as_index=False).agg(
        observaciones_firms=("departamento", "size"),
        observaciones_cubiertas=("semana_temporalmente_completa", "sum"),
    )
    missing_year["observaciones_sin_meteo_completo"] = (
        missing_year["observaciones_firms"] - missing_year["observaciones_cubiertas"]
    )
    missing_year["porcentaje_cubierto"] = completeness(
        missing_year["observaciones_cubiertas"], missing_year["observaciones_firms"]
    )
    missing_year.to_csv(args.output_dir / "compatibilidad_firms_por_anio.csv", index=False)
    missing_department = compatibility.groupby("departamento", as_index=False).agg(
        observaciones_firms=("fecha_inicio_semana", "size"),
        observaciones_cubiertas=("semana_temporalmente_completa", "sum"),
    )
    missing_department["observaciones_sin_meteo_completo"] = (
        missing_department["observaciones_firms"] - missing_department["observaciones_cubiertas"]
    )
    missing_department["porcentaje_cubierto"] = completeness(
        missing_department["observaciones_cubiertas"], missing_department["observaciones_firms"]
    )
    missing_department.to_csv(args.output_dir / "compatibilidad_firms_por_departamento.csv", index=False)

    # Valores potencialmente fuera de rangos generales; se documentan, no se eliminan.
    checks = [
        ("temperature_2m_max", -90, 60), ("temperature_2m_min", -90, 60),
        ("temperature_2m", -90, 60), ("relative_humidity_2m_min", 0, 100),
        ("relative_humidity_2m_max", 0, 100), ("relative_humidity_2m", 0, 100),
        ("wind_direction_10m_dominant", 0, 360), ("wind_direction_10m", 0, 360),
        ("wind_speed_10m_max", 0, 408), ("wind_speed_10m", 0, 408),
        ("precipitation_sum", 0, np.inf), ("rain", 0, np.inf),
        ("et0_fao_evapotranspiration", 0, np.inf), ("surface_pressure", 500, 1100),
    ]
    range_rows = []
    for variable, lower, upper in checks:
        values = pd.to_numeric(uruguay[variable], errors="coerce")
        bad = values.notna() & (~values.between(lower, upper))
        range_rows.append({"variable": variable, "limite_inferior": lower,
                           "limite_superior": upper, "cantidad_fuera_rango": int(bad.sum())})
    pd.DataFrame(range_rows).to_csv(args.output_dir / "controles_rangos_generales.csv", index=False)

    # Visualizaciones exclusivamente de cobertura.
    bar = alt.Chart(missing_department).mark_bar().encode(
        x=alt.X("porcentaje_cubierto:Q", title="Semanas FIRMS con cobertura temporal completa (%)"),
        y=alt.Y("departamento:N", sort="-x", title="Departamento"),
        tooltip=["departamento:N", "observaciones_cubiertas:Q", "observaciones_sin_meteo_completo:Q",
                 alt.Tooltip("porcentaje_cubierto:Q", format=".2f")],
    ).properties(width=700, height=480, title="Cobertura potencial de METEO sobre claves FIRMS")
    bar.save(figures / "completitud_por_departamento.html")
    heat = alt.Chart(missing_year.assign(cobertura="Cobertura completa")).mark_rect().encode(
        x=alt.X("anio:O", title="Año de inicio de semana"), y=alt.Y("cobertura:N", title=None),
        color=alt.Color("porcentaje_cubierto:Q", scale=alt.Scale(domain=[0, 100]), title="Cobertura (%)"),
        tooltip=["anio:O", "observaciones_cubiertas:Q", "observaciones_sin_meteo_completo:Q",
                 alt.Tooltip("porcentaje_cubierto:Q", format=".2f")],
    ).properties(width=700, height=100, title="Cobertura temporal potencial por año")
    heat.save(figures / "cobertura_por_anio.html")

    common = int(compatibility["semana_temporalmente_completa"].sum())
    summary = {
        "artefacto_auditado": str(args.meteo),
        "artefacto_2025": str(args.meteo_2025),
        "bloque_2025_valores_identicos_al_artefacto_separado": artifact_2025_values_equal,
        "bloque_2025_esquema_dtypes_identico": artifact_2025_exact_schema_equal,
        "diferencias_valores_2025_por_columna": value_differences,
        "evidencia_extraccion_en_repositorio": {
            "endpoint": None, "api_producto": None, "parametros": None,
            "modelo_subyacente": None, "momento_descarga": None,
            "conclusion": "No hay scripts ni metadata suficientes para reconstruir la extracción.",
        },
        "filas_regionales_combinadas": int(len(combined)),
        "filas_uruguay": int(len(uruguay)),
        "bloque_diario_uruguay": {
            "filas": int(len(uruguay_daily)), "fecha_min": "2018-01-01",
            "fecha_max": "2024-12-31", "puntos_nominales": int(uruguay_daily["punto"].nunique()),
            "departamentos_geometricos": int(uruguay_daily["departamento"].nunique()),
        },
        "bloque_horario_uruguay": {
            "filas": int(len(uruguay_hourly)), "fecha_min": "2025-01-01 00:00 UTC",
            "fecha_max": "2025-12-31 23:00 UTC", "puntos": int(uruguay_hourly["punto"].nunique()),
            "departamentos_geometricos": int(uruguay_hourly["departamento"].nunique()),
        },
        "puntos_fuera_uruguay_segun_adm1": int(point_assignments["departamento"].isna().sum()),
        "puntos_a_menos_de_5km_de_limite_departamental": int(
            point_assignments["distancia_limite_departamental_km"].lt(5).sum()
        ),
        "duplicados_exactos_uruguay": int(uruguay.duplicated().sum()),
        "observaciones_firms": int(len(firms)),
        "claves_firms_con_cobertura_temporal_meteo_completa": common,
        "claves_firms_sin_cobertura_temporal_meteo_completa": int(len(firms) - common),
        "porcentaje_firms_cubierto": float(common / len(firms) * 100),
        "advertencia_homogeneidad": (
            "Cobertura temporal completa no implica variables homogéneas: 2018–2024 es diario y 2025 horario."
        ),
        "recomendacion": "Opción C: realizar una nueva extracción uniforme y documentada; no ejecutada.",
    }
    (args.output_dir / "resumen_general.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    recommendations = """# Recomendaciones de la auditoría METEO/Open-Meteo

## Dictamen

**Opción C: conviene una nueva extracción uniforme y documentada.** El legado
2018–2024 tiene frecuencia diaria y sólo 12 departamentos geométricos, mientras
2025 es horario y cubre los 19. Además, el repositorio no conserva endpoint,
parámetros, unidades configuradas, modelo subyacente ni fecha de descarga.

No se realizó ninguna extracción nueva ni se integraron datos con FIRMS.

## Alcance sugerido para una extracción futura

- Cubrir las semanas completas necesarias para 2018–2025 y los 19 departamentos.
- Definir antes el diseño espacial: un punto reproducible por departamento es
  simple pero no representa su heterogeneidad; una grilla o múltiples puntos
  permitirían mejor representación, con mayor costo y una regla de agregación.
- Registrar endpoint/producto, modelo, timezone, parámetros, unidades, momento
  de descarga y respuesta de metadata.
- Evaluar temperatura, humedad, precipitación y viento sólo después de confirmar
  definiciones y unidades. No reutilizar los índices `riesgo_*` opacos como
  variables definitivas sin recuperar su fórmula.

## Temporalidad y fuga

La meteorología de la misma semana sólo es apropiada para descripción o
clasificación contemporánea. Para anticipar actividad de la semana objetivo,
las variables deberán cerrarse antes de su inicio, por ejemplo con semanas
anteriores. El repositorio no demuestra cuándo estos datos históricos estuvieron
disponibles ni si son observaciones, reanálisis o pronósticos históricos.
"""
    (args.output_dir / "recomendaciones.md").write_text(recommendations, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
