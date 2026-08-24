#!/usr/bin/env python3
"""Audita la extracción histórica Open-Meteo ya descargada, sin llamadas HTTP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

try:
    from .design_open_meteo_extraction import load_config
    from .extract_open_meteo import build_jobs, expected_days
except ImportError:
    from design_open_meteo_extraction import load_config
    from extract_open_meteo import build_jobs, expected_days


RESULTS = Path("results/open_meteo_historical_audit")
KEY = ["coordenada_id", "fecha"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_index(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="D")


def duplicate_report(frame: pd.DataFrame) -> dict:
    return {"exact_duplicates": int(frame.duplicated().sum()),
            "key_duplicates": int(frame.duplicated(KEY).sum())}


def missing_dates_table(frame: pd.DataFrame, catalog: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    expected = pd.MultiIndex.from_product(
        [catalog.coordenada_id.sort_values(), expected_index(start, end)], names=KEY
    )
    observed = pd.MultiIndex.from_frame(frame[KEY].drop_duplicates())
    missing = expected.difference(observed)
    return missing.to_frame(index=False)


def physical_quality(frame: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    anomaly_masks = {
        "temperature_2m_max": ~frame.temperature_2m_max.between(-90, 60),
        "temperature_2m_min": ~frame.temperature_2m_min.between(-90, 60),
        "relative_humidity_2m_min": ~frame.relative_humidity_2m_min.between(0, 100),
        "relative_humidity_2m_max": ~frame.relative_humidity_2m_max.between(0, 100),
        "wind_speed_10m_max": frame.wind_speed_10m_max.lt(0),
        "wind_direction_10m_dominant": ~frame.wind_direction_10m_dominant.between(0, 360),
        "precipitation_sum": frame.precipitation_sum.lt(0),
        "et0_fao_evapotranspiration": frame.et0_fao_evapotranspiration.lt(0),
    }
    rows = []
    for variable in variables:
        values = pd.to_numeric(frame[variable], errors="coerce")
        affected = frame.loc[values.isna() | ~np.isfinite(values), ["coordenada_id", "departamento", "fecha"]]
        nonnull = values.dropna()
        rows.append({
            "variable": variable, "valores_esperados": len(frame), "valores_presentes": int(values.notna().sum()),
            "nulos": int(values.isna().sum()), "porcentaje_nulos": float(100 * values.isna().mean()),
            "infinitos": int(np.isinf(values).sum()), "coordenadas_afectadas": affected.coordenada_id.nunique(),
            "departamentos_afectados": affected.departamento.nunique(),
            "fecha_min_afectada": affected.fecha.min(), "fecha_max_afectada": affected.fecha.max(),
            "min": nonnull.min(), "p01": nonnull.quantile(.01), "mediana": nonnull.median(),
            "p99": nonnull.quantile(.99), "max": nonnull.max(),
            "anomalias_rango_general": int(anomaly_masks[variable].fillna(False).sum()),
        })
    return pd.DataFrame(rows)


def logical_quality(frame: pd.DataFrame) -> dict:
    return {
        "temperature_min_gt_max": int((frame.temperature_2m_min > frame.temperature_2m_max).sum()),
        "humidity_min_gt_max": int((frame.relative_humidity_2m_min > frame.relative_humidity_2m_max).sum()),
    }


def raw_metadata(raw_paths: list[Path], variables: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    unit_rows, timezone_rows = [], []
    for path in raw_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        responses = payload if isinstance(payload, list) else [payload]
        for response in responses:
            for variable in variables:
                unit_rows.append({"variable": variable, "unidad": response["daily_units"].get(variable)})
            timezone_rows.append({"timezone": response.get("timezone"),
                                  "timezone_abbreviation": response.get("timezone_abbreviation"),
                                  "utc_offset_seconds": response.get("utc_offset_seconds")})
    units = pd.DataFrame(unit_rows).value_counts().rename("respuestas").reset_index()
    timezones = pd.DataFrame(timezone_rows).value_counts(dropna=False).rename("respuestas").reset_index()
    return units, timezones


def spatial_consistency(frame: pd.DataFrame, catalog: pd.DataFrame,
                        boundaries: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pairs = frame[["coordenada_id", "departamento", "latitud_modelo", "longitud_modelo"]].drop_duplicates()
    counts = pairs.groupby("coordenada_id").size().rename("pares_modelo_distintos")
    consistency = catalog[["coordenada_id", "departamento", "latitud_reportada", "longitud_reportada"]].merge(
        counts, on="coordenada_id", how="left", validate="one_to_one"
    )
    first = pairs.sort_values(["coordenada_id", "latitud_modelo", "longitud_modelo"]).drop_duplicates("coordenada_id")
    consistency = consistency.merge(first[["coordenada_id", "latitud_modelo", "longitud_modelo"]], on="coordenada_id", how="left")
    consistency["coincide_auditoria_previa"] = (
        np.isclose(consistency.latitud_reportada, consistency.latitud_modelo, atol=1e-6)
        & np.isclose(consistency.longitud_reportada, consistency.longitud_modelo, atol=1e-6)
    )
    points = gpd.GeoDataFrame(pairs, geometry=gpd.points_from_xy(pairs.longitud_modelo, pairs.latitud_modelo), crs=4326)
    joined = gpd.sjoin(points, boundaries[["shapeName", "geometry"]], predicate="within", how="left")
    joined["estado"] = np.where(joined.shapeName.isna(), "fuera_uruguay",
                                np.where(joined.departamento.eq(joined.shapeName), "mismo_departamento", "otro_departamento"))
    problems = joined.loc[~joined.estado.eq("mismo_departamento")].drop(columns=["geometry", "index_right"])
    return consistency, problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/open_meteo.json"))
    parser.add_argument("--output-dir", type=Path, default=RESULTS)
    args = parser.parse_args()
    config = load_config(args.config); output = args.output_dir; output.mkdir(parents=True, exist_ok=True)
    catalog_path = Path(config["paths"]["coordinate_catalog"]); catalog = pd.read_csv(catalog_path)
    if catalog_path.name != "open_meteo_coordinates_validated.csv" or len(catalog) != 187:
        raise AssertionError("La auditoría histórica exige el catálogo validado de 187 coordenadas.")
    dataset_path = Path(config["paths"]["processed_dataset"])
    frame = pd.read_parquet(dataset_path); frame["fecha"] = pd.to_datetime(frame.fecha, errors="raise")
    variables = config["daily_variables"]; expected_days_count = expected_days(config["start_date"], config["end_date"])
    expected_rows = len(catalog) * expected_days_count
    missing = missing_dates_table(frame, catalog, config["start_date"], config["end_date"])
    missing.to_csv(output / "fechas_faltantes.csv", index=False)
    coverage_coordinate = frame.groupby("coordenada_id").fecha.agg(fecha_min="min", fecha_max="max", dias_observados="nunique").reset_index()
    coverage_coordinate = catalog[["coordenada_id", "departamento"]].merge(coverage_coordinate, on="coordenada_id", how="left")
    coverage_coordinate["dias_esperados"] = expected_days_count
    coverage_coordinate["dias_faltantes"] = expected_days_count - coverage_coordinate.dias_observados.fillna(0)
    coverage_coordinate["porcentaje_completitud"] = 100 * coverage_coordinate.dias_observados.fillna(0) / expected_days_count
    coverage_coordinate.to_csv(output / "cobertura_por_coordenada.csv", index=False)
    department_coordinates = catalog.groupby("departamento").coordenada_id.nunique()
    coverage_department = frame.groupby("departamento").agg(coordenadas=("coordenada_id", "nunique"), filas_obtenidas=("fecha", "size")).reset_index()
    coverage_department["filas_esperadas"] = coverage_department.departamento.map(department_coordinates) * expected_days_count
    coverage_department["porcentaje_completitud"] = 100 * coverage_department.filas_obtenidas / coverage_department.filas_esperadas
    coverage_department["nulos_variables"] = coverage_department.departamento.map(frame.groupby("departamento")[variables].apply(lambda x: x.isna().sum().sum()))
    coverage_department["fechas_faltantes"] = coverage_department.departamento.map(coverage_coordinate.groupby("departamento").dias_faltantes.sum())
    coverage_department["puntos_con_problemas"] = coverage_department.departamento.map(coverage_coordinate.groupby("departamento").dias_faltantes.apply(lambda x: x.gt(0).sum()))
    coverage_department.to_csv(output / "cobertura_por_departamento.csv", index=False)
    frame["anio"] = frame.fecha.dt.year
    year_days = pd.Series(expected_index(config["start_date"], config["end_date"]).year).value_counts()
    coverage_year = frame.groupby("anio").agg(filas_obtenidas=("fecha", "size"), coordenadas_observadas=("coordenada_id", "nunique")).reset_index()
    coverage_year["filas_esperadas"] = coverage_year.anio.map(year_days) * len(catalog)
    counts_year_coord = frame.groupby(["anio", "coordenada_id"]).fecha.nunique()
    coverage_year["coordenadas_completas"] = coverage_year.anio.map(counts_year_coord.groupby("anio").apply(lambda s: s.eq(year_days.loc[s.name]).sum()))
    coverage_year["coordenadas_incompletas"] = len(catalog) - coverage_year.coordenadas_completas
    coverage_year["nulos_variables"] = coverage_year.anio.map(frame.groupby("anio")[variables].apply(lambda x: x.isna().sum().sum()))
    coverage_year.to_csv(output / "cobertura_por_anio.csv", index=False)
    quality = physical_quality(frame, variables); quality.to_csv(output / "calidad_por_variable.csv", index=False)
    raw_paths = sorted(Path(config["paths"]["raw_directory"]).glob("*/*.json"))
    units, timezones = raw_metadata(raw_paths, variables)
    units.to_csv(output / "unidades_observadas.csv", index=False); timezones.to_csv(output / "timezone_observado.csv", index=False)
    boundaries = gpd.read_file(config["spatial_design"]["boundary_file"])
    spatial, spatial_problems = spatial_consistency(frame, catalog, boundaries)
    spatial.to_csv(output / "consistencia_espacial.csv", index=False); spatial_problems.to_csv(output / "problemas_espaciales.csv", index=False)
    manifest_path = Path(config["paths"]["audit_directory"]) / "manifest.jsonl"
    manifest = pd.read_json(manifest_path, lines=True) if manifest_path.exists() else pd.DataFrame()
    expected_jobs = len(build_jobs(catalog, config))
    successful = manifest.loc[manifest.status.isin(["downloaded", "checkpoint_reused"])] if not manifest.empty else manifest
    manifest_summary = {"jobs_esperados": expected_jobs, "jobs_exitosos_unicos": int(successful.job_id.nunique()),
        "registros_downloaded": int(manifest.status.eq("downloaded").sum()),
        "registros_checkpoint_reused": int(manifest.status.eq("checkpoint_reused").sum()),
        "registros_failed": int(manifest.status.eq("failed").sum()),
        "jobs_reintentados": int(pd.to_numeric(manifest.get("attempts"), errors="coerce").gt(1).sum()),
        "jobs_duplicados_manifest": int(manifest.duplicated("job_id").sum()),
        "raw_json": len(raw_paths), "raw_checksums_duplicados": len(raw_paths) - len({sha256(p) for p in raw_paths})}
    (output / "resumen_manifest.json").write_text(json.dumps(manifest_summary, ensure_ascii=False, indent=2) + "\n")
    duplicates = duplicate_report(frame)
    summary = {"catalog": str(catalog_path), "coordinates": frame.coordenada_id.nunique(),
        "departments": frame.departamento.nunique(), "expected_days_per_coordinate": expected_days_count,
        "expected_rows": expected_rows, "observed_rows": len(frame), "date_min": frame.fecha.min().date().isoformat(),
        "date_max": frame.fecha.max().date().isoformat(), "missing_dates": len(missing), **duplicates,
        "logical_quality": logical_quality(frame), "spatial_problems": len(spatial_problems),
        "coordinates_with_multiple_model_cells": int(spatial.pares_modelo_distintos.gt(1).sum()),
        "coordinates_different_from_prior_audit": int((~spatial.coincide_auditoria_previa).sum()),
        "checksums_sha256": {"processed": sha256(dataset_path), "config": sha256(args.config), "catalog": sha256(catalog_path)},
        "manifest": manifest_summary}
    (output / "resumen_general.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
