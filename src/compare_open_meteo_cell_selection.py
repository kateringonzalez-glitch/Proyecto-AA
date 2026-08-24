#!/usr/bin/env python3
"""Micro-piloto A/B protegido para comparar cell_selection land y nearest."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

try:
    from .design_open_meteo_extraction import load_config
    from .extract_open_meteo import download_job, normalize_job, request_params, url_for_job
except ImportError:
    from design_open_meteo_extraction import load_config
    from extract_open_meteo import download_job, normalize_job, request_params, url_for_job


SCRIPT_VERSION = "1.0.0"
DEFAULT_CONFIG = Path("config/open_meteo_cell_selection_ab.json")
EXPECTED_CASES = {"montevideo", "costa", "frontera_internacional",
                  "interior_departamento_grande", "departamento_intermedio"}


def load_ab_config(path: Path = DEFAULT_CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_exact_pilot_coordinates(path: Path, limits: dict) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"coordenada_id", "departamento", "departamento_iso", "latitud", "longitud", "tipo_caso"}
    if required.difference(frame.columns):
        raise ValueError("El archivo piloto no contiene las columnas requeridas.")
    if len(frame) != limits["coordinates"] or frame.coordenada_id.duplicated().any():
        raise ValueError("Protección: deben reutilizarse exactamente cinco coordenadas piloto únicas.")
    if set(frame.tipo_caso) != EXPECTED_CASES:
        raise ValueError("Protección: los cinco tipos de caso no coinciden con el piloto previo.")
    return frame.sort_values("coordenada_id").reset_index(drop=True)


def build_ab_jobs(coordinates: pd.DataFrame, ab_config: dict) -> list[tuple[dict, dict]]:
    if ab_config["variants"] != ["land", "nearest"]:
        raise ValueError("La comparación sólo admite land y nearest.")
    date = ab_config["date"]
    jobs = []
    for variant in ab_config["variants"]:
        jobs.append(({
            "job_id": f"{variant}_{date}", "start_date": date, "end_date": date,
            "coordinates": coordinates.to_dict("records")
        }, {"cell_selection": variant}))
    limits = ab_config["limits"]
    if len(jobs) != limits["requests"] or len(coordinates) * len(jobs) != limits["rows"]:
        raise ValueError("Protección: el micro-piloto debe ser exactamente 2 requests y 10 filas.")
    return jobs


def variant_config(main_config: dict, variant: str) -> dict:
    config = copy.deepcopy(main_config)
    config["cell_selection"] = variant
    return config


def assert_only_cell_selection_differs(job: dict, main_config: dict) -> None:
    land = request_params(job, variant_config(main_config, "land"))
    nearest = request_params(job, variant_config(main_config, "nearest"))
    differences = {key for key in set(land) | set(nearest) if land.get(key) != nearest.get(key)}
    if differences != {"cell_selection"}:
        raise AssertionError(f"Parámetros A/B distintos además de cell_selection: {sorted(differences)}")


def spatial_rows(payload: object, job: dict, variant: str,
                 boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    responses = payload if isinstance(payload, list) else [payload]
    polygons = boundaries[["shapeName", "geometry"]].to_crs(32721)
    rows = []
    for coordinate, response in zip(job["coordinates"], responses):
        requested = gpd.GeoSeries([Point(coordinate["longitud"], coordinate["latitud"])], crs=4326).to_crs(32721).iloc[0]
        reported = gpd.GeoSeries([Point(response["longitude"], response["latitude"])], crs=4326).to_crs(32721).iloc[0]
        matches = polygons.loc[polygons.geometry.covers(reported), "shapeName"].tolist()
        reported_department = matches[0] if len(matches) == 1 else None
        rows.append({
            "coordenada_id": coordinate["coordenada_id"], "tipo_caso": coordinate["tipo_caso"],
            "departamento": coordinate["departamento"], "lat_solicitada": coordinate["latitud"],
            "lon_solicitada": coordinate["longitud"], "cell_selection": variant,
            "lat_reportada": response["latitude"], "lon_reportada": response["longitude"],
            "elevacion_reportada_m": response.get("elevation"),
            "distancia_solicitada_reportada_m": requested.distance(reported),
            "departamento_reportado": reported_department,
            "mismo_departamento": reported_department == coordinate["departamento"],
            "timezone": response.get("timezone"), "timezone_abbreviation": response.get("timezone_abbreviation"),
            "utc_offset_seconds": response.get("utc_offset_seconds"),
            "daily_units_json": json.dumps(response.get("daily_units", {}), ensure_ascii=False, sort_keys=True),
        })
    return pd.DataFrame(rows)


def comparison_table(spatial: pd.DataFrame) -> pd.DataFrame:
    identifiers = ["coordenada_id", "tipo_caso", "departamento", "lat_solicitada", "lon_solicitada"]
    pieces = []
    for variant in ["land", "nearest"]:
        subset = spatial.loc[spatial.cell_selection.eq(variant)].copy()
        subset = subset[identifiers + ["lat_reportada", "lon_reportada",
                                        "distancia_solicitada_reportada_m", "departamento_reportado",
                                        "mismo_departamento"]]
        subset = subset.rename(columns={
            "lat_reportada": f"lat_{variant}", "lon_reportada": f"lon_{variant}",
            "distancia_solicitada_reportada_m": f"distancia_{variant}_m",
            "departamento_reportado": f"departamento_{variant}",
            "mismo_departamento": f"{variant}_mismo_departamento",
        })
        pieces.append(subset)
    result = pieces[0].merge(pieces[1], on=identifiers, validate="one_to_one")
    result["diferencia_distancia_nearest_menos_land_m"] = result.distancia_nearest_m - result.distancia_land_m
    return result.sort_values("coordenada_id").reset_index(drop=True)


def summarize(comparison: pd.DataFrame, processed: pd.DataFrame, config: dict,
              run_records: list[dict], run_id: str) -> dict:
    variants = {}
    for variant in ["land", "nearest"]:
        distances = comparison[f"distancia_{variant}_m"]
        same = comparison[f"{variant}_mismo_departamento"]
        variants[variant] = {
            "same_department": int(same.sum()), "changed_department": int((~same).sum()),
            "outside_uruguay_adm1": int(comparison[f"departamento_{variant}"].isna().sum()),
            "problem_coordinate_ids": comparison.loc[~same, "coordenada_id"].tolist(),
            "distance_mean_m": float(distances.mean()), "distance_median_m": float(distances.median()),
            "distance_max_m": float(distances.max()),
        }
    weather = {}
    for variant in ["land", "nearest"]:
        subset = processed.loc[processed.cell_selection.eq(variant)]
        weather[variant] = {"rows": len(subset), "variables": config["daily_variables"],
                            "nulls": int(subset[config["daily_variables"]].isna().sum().sum()),
                            "timezone_values": sorted(subset.timezone.unique().tolist())}
    return {
        "run_id": run_id, "date": processed.fecha.dt.strftime("%Y-%m-%d").unique().tolist(),
        "coordinates": int(processed.coordenada_id.nunique()),
        "network_calls_performed": sum(record["status"] == "downloaded" for record in run_records),
        "checkpoints_reused": sum(record["status"] == "checkpoint_reused" for record in run_records),
        "variants": variants, "meteorological_validation": weather,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cell-selection-ab", action="store_true", help="Confirma el micro-piloto protegido.")
    parser.add_argument("--execute", action="store_true", help="Habilita las dos llamadas si faltan checkpoints.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.cell_selection_ab:
        raise SystemExit("Protección: se exige --cell-selection-ab; no se realizaron llamadas.")
    ab = load_ab_config(args.config)
    main_config = load_config(Path(ab["main_config"]))
    coordinates = load_exact_pilot_coordinates(Path(ab["pilot_coordinates"]), ab["limits"])
    jobs = build_ab_jobs(coordinates, ab)
    assert_only_cell_selection_differs(jobs[0][0], main_config)
    results_dir = Path(ab["paths"]["results_directory"]); results_dir.mkdir(parents=True, exist_ok=True)
    plan = {"mode": "execute" if args.execute else "dry-run", "date": ab["date"],
            "coordinates": coordinates[["coordenada_id", "departamento", "tipo_caso", "latitud", "longitud"]].to_dict("records"),
            "variants": ab["variants"], "expected_requests": 2, "expected_rows": 10,
            "network_calls_performed": 0}
    (results_dir / "plan_ab.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2)); return

    boundaries = gpd.read_file(main_config["spatial_design"]["boundary_file"])
    raw_root = Path(ab["paths"]["raw_directory"])
    processed_root = Path(ab["paths"]["processed_directory"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    frames, spatial_frames, records = [], [], []
    for job, descriptor in jobs:
        variant = descriptor["cell_selection"]
        config = variant_config(main_config, variant)
        raw_path = raw_root / variant / f"{job['job_id']}.json"
        result = download_job(job, config, raw_path)
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        normalized = normalize_job(payload, job, config).rename(columns={"latitud": "latitud_solicitada", "longitud": "longitud_solicitada"})
        normalized["cell_selection"] = variant
        variant_dir = processed_root / variant; variant_dir.mkdir(parents=True, exist_ok=True)
        part_path = variant_dir / f"{job['job_id']}.parquet"; normalized.to_parquet(part_path, index=False)
        frames.append(normalized)
        spatial = spatial_rows(payload, job, variant, boundaries); spatial_frames.append(spatial)
        variant_results = results_dir / variant; variant_results.mkdir(parents=True, exist_ok=True)
        spatial.to_csv(variant_results / "metadata_espacial.csv", index=False)
        records.append({"run_id": run_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "script_version": SCRIPT_VERSION, "variant": variant, "job_id": job["job_id"],
                        "request_url": url_for_job(job, config), "request_parameters": request_params(job, config),
                        "raw_path": str(raw_path), "processed_path": str(part_path), "records": len(normalized), **result})
    processed = pd.concat(frames, ignore_index=True)
    if len(processed) != 10 or processed.duplicated(["coordenada_id", "fecha", "cell_selection"]).any():
        raise AssertionError("La salida A/B no contiene exactamente diez claves únicas por variante.")
    spatial = pd.concat(spatial_frames, ignore_index=True)
    comparison = comparison_table(spatial)
    comparison.to_csv(results_dir / "comparacion_espacial.csv", index=False)
    output = processed_root / "open_meteo_cell_selection_ab.parquet"; processed.to_parquet(output, index=False)
    manifest_path = results_dir / "manifest.jsonl"
    with manifest_path.open("a", encoding="utf-8") as stream:
        for record in records: stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = summarize(comparison, processed, main_config, records, run_id)
    summary["processed_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    (results_dir / f"run_{run_id}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (results_dir / "resumen_comparacion.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
