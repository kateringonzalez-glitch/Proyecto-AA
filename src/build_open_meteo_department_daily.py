#!/usr/bin/env python3
"""Agrega Open-Meteo diario desde coordenada-día a departamento-día."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


INPUT = Path("data/processed/open_meteo_daily/open_meteo_daily_2017_2025.parquet")
CATALOG = Path("data/reference/open_meteo_coordinates_validated.csv")
OUTPUT = Path("data/processed/open_meteo_department_daily/open_meteo_department_daily_2017_2025.parquet")
AUDIT = Path("results/open_meteo_department_daily_audit")
INPUT_KEY = ["coordenada_id", "fecha"]
OUTPUT_KEY = ["departamento", "fecha"]
SCALAR_AGGREGATIONS = {
    "temperature_2m_max": ["mean", "max"],
    "temperature_2m_min": ["mean", "min"],
    "relative_humidity_2m_min": ["mean", "min"],
    "relative_humidity_2m_max": ["mean", "max"],
    "wind_speed_10m_max": ["mean", "max"],
    "precipitation_sum": ["mean", "max"],
    "et0_fao_evapotranspiration": ["mean", "max"],
}


def expected_days(start: str, end: str) -> int:
    return len(pd.date_range(start, end, freq="D"))


def validate_input(frame: pd.DataFrame, catalog: pd.DataFrame) -> dict:
    frame = frame.copy(); frame["fecha"] = pd.to_datetime(frame.fecha, errors="raise")
    required = set(INPUT_KEY + ["departamento", "departamento_iso", "wind_direction_10m_dominant"]
                   + list(SCALAR_AGGREGATIONS))
    missing = required.difference(frame.columns)
    if missing:
        raise AssertionError(f"Columnas de entrada ausentes: {sorted(missing)}")
    conditions = {
        "rows": len(frame) == 614482,
        "coordinates": frame.coordenada_id.nunique() == len(catalog) == 187,
        "departments": frame.departamento.nunique() == catalog.departamento.nunique() == 19,
        "date_min": frame.fecha.min() == pd.Timestamp("2017-01-02"),
        "date_max": frame.fecha.max() == pd.Timestamp("2025-12-31"),
        "unique_input_key": not frame.duplicated(INPUT_KEY).any(),
        "coordinate_counts_match_catalog": frame.groupby("departamento").coordenada_id.nunique().sort_index().equals(
            catalog.groupby("departamento").coordenada_id.nunique().sort_index()
        ),
    }
    failed = [name for name, passed in conditions.items() if not passed]
    if failed:
        raise AssertionError(f"Precondiciones de entrada incumplidas: {failed}")
    return conditions


def circular_statistics_degrees(values: pd.Series, tolerance: float = 1e-12) -> tuple[float, float]:
    radians = np.deg2rad(pd.to_numeric(values, errors="raise").to_numpy())
    mean_sin, mean_cos = np.sin(radians).mean(), np.cos(radians).mean()
    resultant = float(np.hypot(mean_sin, mean_cos))
    direction = np.nan if resultant < tolerance else float(np.degrees(np.arctan2(mean_sin, mean_cos)) % 360)
    if not np.isnan(direction) and np.isclose(direction, 360.0, atol=1e-10):
        direction = 0.0
    return direction, min(1.0, max(0.0, resultant))


def aggregate_department_daily(frame: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy(); frame["fecha"] = pd.to_datetime(frame.fecha)
    named = {}
    suffix = {"mean": "mean_spatial", "max": "max_spatial", "min": "min_spatial"}
    for variable, functions in SCALAR_AGGREGATIONS.items():
        for function in functions:
            named[f"{variable}_{suffix[function]}"] = pd.NamedAgg(column=variable, aggfunc=function)
    grouped = frame.groupby(OUTPUT_KEY, sort=True, observed=True)
    output = grouped.agg(
        departamento_iso=pd.NamedAgg(column="departamento_iso", aggfunc="first"),
        n_puntos_observados=pd.NamedAgg(column="coordenada_id", aggfunc="nunique"), **named
    ).reset_index()
    circular = grouped["wind_direction_10m_dominant"].apply(
        lambda values: pd.Series(circular_statistics_degrees(values), index=[
            "wind_direction_10m_dominant_circular_mean", "wind_direction_10m_resultant_length"
        ])
    ).unstack().reset_index()
    output = output.merge(circular, on=OUTPUT_KEY, validate="one_to_one")
    expected_points = catalog.groupby("departamento").coordenada_id.nunique()
    output["n_puntos_esperados"] = output.departamento.map(expected_points).astype(int)
    output["cobertura_espacial_pct"] = 100 * output.n_puntos_observados / output.n_puntos_esperados
    identifiers = ["departamento", "departamento_iso", "fecha", "n_puntos_esperados",
                   "n_puntos_observados", "cobertura_espacial_pct"]
    return output[identifiers + [column for column in output if column not in identifiers]].sort_values(OUTPUT_KEY).reset_index(drop=True)


def validate_output(frame: pd.DataFrame, catalog: pd.DataFrame) -> dict:
    days = expected_days("2017-01-02", "2025-12-31"); expected_rows = catalog.departamento.nunique() * days
    by_department = frame.groupby("departamento").fecha.agg(["nunique", "min", "max"])
    per_date = frame.groupby("fecha").departamento.nunique()
    checks = {
        "expected_rows": expected_rows, "observed_rows": len(frame),
        "departments": frame.departamento.nunique(), "dates": frame.fecha.nunique(),
        "duplicate_keys": int(frame.duplicated(OUTPUT_KEY).sum()),
        "dates_with_not_19_departments": int(per_date.ne(19).sum()),
        "departments_with_not_expected_days": int(by_department["nunique"].ne(days).sum()),
        "departments_with_wrong_min_date": int(by_department["min"].ne(pd.Timestamp("2017-01-02")).sum()),
        "departments_with_wrong_max_date": int(by_department["max"].ne(pd.Timestamp("2025-12-31")).sum()),
        "coverage_problems": int((frame.n_puntos_observados.ne(frame.n_puntos_esperados)
                                  | ~np.isclose(frame.cobertura_espacial_pct, 100)).sum()),
        "nulls": int(frame.isna().sum().sum()),
        "temperature_order_problems": int((frame.temperature_2m_min_mean_spatial > frame.temperature_2m_max_mean_spatial).sum()),
        "humidity_range_problems": int((~frame[["relative_humidity_2m_min_mean_spatial",
            "relative_humidity_2m_min_min_spatial", "relative_humidity_2m_max_mean_spatial",
            "relative_humidity_2m_max_max_spatial"]].apply(lambda s: s.between(0, 100)).all(axis=1)).sum()),
        "negative_wind": int(frame.wind_speed_10m_max_mean_spatial.lt(0).sum()),
        "negative_precipitation": int(frame.precipitation_sum_mean_spatial.lt(0).sum()),
        "negative_et0": int(frame.et0_fao_evapotranspiration_mean_spatial.lt(0).sum()),
        "direction_range_problems": int((frame.wind_direction_10m_dominant_circular_mean.notna()
            & ~frame.wind_direction_10m_dominant_circular_mean.between(0, 360, inclusive="left")).sum()),
        "resultant_range_problems": int((~frame.wind_direction_10m_resultant_length.between(0, 1)).sum()),
    }
    required_zero = [key for key in checks if key.endswith("problems") or key in {"duplicate_keys", "nulls"}]
    if (len(frame) != expected_rows or checks["departments"] != 19 or checks["dates"] != days
            or any(checks[key] != 0 for key in required_zero)):
        raise AssertionError(f"Validación de salida fallida: {checks}")
    return checks


def reconcile_samples(source: pd.DataFrame, aggregated: pd.DataFrame) -> pd.DataFrame:
    departments = sorted(source.departamento.unique())
    selected_departments = sorted(set([departments[0], departments[-1], "Montevideo"]))
    dates = sorted(source.fecha.unique()); selected_dates = [dates[0], dates[len(dates)//2], dates[-1]]
    metrics = {
        "temperature_2m_max_mean_spatial": ("temperature_2m_max", "mean"),
        "precipitation_sum_mean_spatial": ("precipitation_sum", "mean"),
        "wind_speed_10m_max_max_spatial": ("wind_speed_10m_max", "max"),
    }
    rows = []
    for department in selected_departments:
        for day in selected_dates:
            subset = source.loc[source.departamento.eq(department) & source.fecha.eq(day)]
            target = aggregated.loc[aggregated.departamento.eq(department) & aggregated.fecha.eq(day)].iloc[0]
            for output_column, (input_column, operation) in metrics.items():
                recalculated = getattr(subset[input_column], operation)()
                rows.append({"departamento": department, "fecha": day, "variable": output_column,
                             "recalculado_desde_origen": recalculated, "valor_salida": target[output_column],
                             "diferencia_absoluta": abs(recalculated-target[output_column]),
                             "coincide": bool(np.isclose(recalculated, target[output_column]))})
            direction, _ = circular_statistics_degrees(subset.wind_direction_10m_dominant)
            observed = target.wind_direction_10m_dominant_circular_mean
            rows.append({"departamento": department, "fecha": day,
                         "variable": "wind_direction_10m_dominant_circular_mean",
                         "recalculado_desde_origen": direction, "valor_salida": observed,
                         "diferencia_absoluta": abs(direction-observed), "coincide": bool(np.isclose(direction, observed))})
    return pd.DataFrame(rows)


def descriptive_quality(frame: pd.DataFrame) -> pd.DataFrame:
    diagnostic = set(OUTPUT_KEY + ["departamento_iso", "n_puntos_esperados", "n_puntos_observados", "cobertura_espacial_pct"])
    rows = []
    for column in [c for c in frame.columns if c not in diagnostic]:
        values = frame[column]
        rows.append({"variable": column, "min": values.min(), "p01": values.quantile(.01),
                     "p05": values.quantile(.05), "media": values.mean(), "mediana": values.median(),
                     "desviacion_estandar": values.std(), "p95": values.quantile(.95),
                     "p99": values.quantile(.99), "max": values.max(), "nulos": values.isna().sum()})
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT); parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=OUTPUT); parser.add_argument("--audit-dir", type=Path, default=AUDIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args(); source = pd.read_parquet(args.input); source["fecha"] = pd.to_datetime(source.fecha)
    catalog = pd.read_csv(args.catalog); input_checks = validate_input(source, catalog)
    output = aggregate_department_daily(source, catalog); checks = validate_output(output, catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True); output.to_parquet(args.output, index=False)
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    problems = output.loc[output.n_puntos_observados.ne(output.n_puntos_esperados)].copy()
    problems.to_csv(args.audit_dir / "problemas_cobertura.csv", index=False)
    reconciliation = reconcile_samples(source, output); reconciliation.to_csv(args.audit_dir / "reconciliacion_muestras.csv", index=False)
    quality = descriptive_quality(output); quality.to_csv(args.audit_dir / "calidad_variables_agregadas.csv", index=False)
    main_variables = ["temperature_2m_max_mean_spatial", "temperature_2m_min_mean_spatial",
                      "relative_humidity_2m_min_mean_spatial", "wind_speed_10m_max_mean_spatial",
                      "precipitation_sum_mean_spatial", "et0_fao_evapotranspiration_mean_spatial"]
    department = output.groupby("departamento").agg(
        n_puntos=("n_puntos_esperados", "first"), dias=("fecha", "nunique"), fecha_min=("fecha", "min"),
        fecha_max=("fecha", "max"), cobertura_min_pct=("cobertura_espacial_pct", "min"),
        nulos=(main_variables[0], lambda s: 0)
    ).reset_index()
    department["nulos"] = department.departamento.map(output.groupby("departamento")[main_variables].apply(lambda x: x.isna().sum().sum()))
    for variable in main_variables:
        department[f"{variable}_min"] = department.departamento.map(output.groupby("departamento")[variable].min())
        department[f"{variable}_max"] = department.departamento.map(output.groupby("departamento")[variable].max())
    department.to_csv(args.audit_dir / "cobertura_por_departamento.csv", index=False)
    summary = {"input": str(args.input), "catalog": str(args.catalog), "output": str(args.output),
               "input_validation": input_checks, "output_validation": checks,
               "reconciliation_rows": len(reconciliation), "reconciliation_failures": int((~reconciliation.coincide).sum()),
               "montevideo_points": int(output.loc[output.departamento.eq("Montevideo"), "n_puntos_esperados"].iloc[0])}
    (args.audit_dir / "resumen_general.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
