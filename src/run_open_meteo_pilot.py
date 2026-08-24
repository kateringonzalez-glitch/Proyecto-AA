#!/usr/bin/env python3
"""Ejecuta exclusivamente el piloto acotado de Open-Meteo.

La red sólo se habilita con la combinación explícita ``--pilot --execute``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

try:
    from .design_open_meteo_extraction import load_config
    from .extract_open_meteo import download_job, expected_days, normalize_job, physical_range_report, url_for_job
except ImportError:
    from design_open_meteo_extraction import load_config
    from extract_open_meteo import download_job, expected_days, normalize_job, physical_range_report, url_for_job


SCRIPT_VERSION = "1.0.0"
PILOT_CONFIG = Path("config/open_meteo_pilot.json")


def load_pilot_config(path: Path = PILOT_CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def select_pilot_coordinates(catalog: pd.DataFrame, boundaries: gpd.GeoDataFrame,
                             pilot_config: dict) -> pd.DataFrame:
    projected_boundaries = boundaries.to_crs("EPSG:32721")
    department_geometry = projected_boundaries.set_index("shapeName").geometry
    national_boundary = projected_boundaries.geometry.union_all().boundary
    points = gpd.GeoDataFrame(
        catalog.copy(), geometry=gpd.points_from_xy(catalog.longitud, catalog.latitud),
        crs="EPSG:4326"
    ).to_crs("EPSG:32721")
    selected = []
    for specification in pilot_config["selection"]:
        department = specification["department"]
        candidates = points.loc[points["departamento"].eq(department)].copy()
        if candidates.empty or department not in department_geometry.index:
            raise ValueError(f"No hay candidatos o límite para {department}.")
        candidates["distancia_limite_departamental_m"] = candidates.geometry.distance(
            department_geometry.loc[department].boundary
        )
        candidates["distancia_limite_nacional_m"] = candidates.geometry.distance(national_boundary)
        if specification["rule"] == "min_latitude_southernmost":
            metric = "latitud"
        else:
            metric = ("distancia_limite_departamental_m" if specification["rule"].startswith("max_")
                      else "distancia_limite_nacional_m")
        candidates = candidates.sort_values(
            [metric, "coordenada_id"], ascending=[not specification["rule"].startswith("max_"), True]
        )
        row = candidates.iloc[0].copy()
        row["tipo_caso"] = specification["case"]
        row["criterio_seleccion"] = specification["rule"]
        selected.append(row)
    result = pd.DataFrame(selected).drop(columns="geometry")
    return result.sort_values("tipo_caso").reset_index(drop=True)


def build_pilot_jobs(coordinates: pd.DataFrame, pilot_config: dict) -> list[dict]:
    limits = pilot_config["limits"]
    if len(coordinates) != limits["coordinates"] or len(pilot_config["windows"]) != limits["windows"]:
        raise ValueError("El piloto no tiene exactamente cinco coordenadas y dos ventanas.")
    jobs = []
    records = coordinates.to_dict("records")
    for window in pilot_config["windows"]:
        if expected_days(window["start_date"], window["end_date"]) != limits["days_per_window"]:
            raise ValueError("Cada ventana piloto debe contener exactamente siete días.")
        jobs.append({"job_id": window["window_id"], "start_date": window["start_date"],
                     "end_date": window["end_date"], "coordinates": records})
    if len(jobs) != limits["requests"] or sum(
        len(job["coordinates"]) * expected_days(job["start_date"], job["end_date"])
        for job in jobs
    ) != limits["rows"]:
        raise ValueError("La protección detectó un volumen distinto de 2 requests y 70 filas.")
    return jobs


def response_metadata(payload: object, job: dict, config: dict) -> pd.DataFrame:
    responses = payload if isinstance(payload, list) else [payload]
    rows = []
    for coordinate, response in zip(job["coordinates"], responses):
        rows.append({
            "job_id": job["job_id"], "coordenada_id": coordinate["coordenada_id"],
            "tipo_caso": coordinate["tipo_caso"], "departamento_solicitado": coordinate["departamento"],
            "latitud_solicitada": coordinate["latitud"], "longitud_solicitada": coordinate["longitud"],
            "latitud_modelo": response.get("latitude"), "longitud_modelo": response.get("longitude"),
            "elevacion_modelo_m": response.get("elevation"), "timezone_respuesta": response.get("timezone"),
            "abreviatura_timezone": response.get("timezone_abbreviation"),
            "utc_offset_seconds": response.get("utc_offset_seconds"),
            "generationtime_ms": response.get("generationtime_ms"),
            "daily_units_json": json.dumps(response.get("daily_units", {}), ensure_ascii=False, sort_keys=True),
            "modelo_solicitado": config["model"], "fecha_inicio": job["start_date"],
            "fecha_fin": job["end_date"]
        })
    return pd.DataFrame(rows)


def spatial_audit(metadata: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    polygons = boundaries[["shapeName", "geometry"]].to_crs("EPSG:32721")
    records = []
    for row in metadata.itertuples(index=False):
        requested = gpd.GeoSeries([Point(row.longitud_solicitada, row.latitud_solicitada)], crs=4326).to_crs(32721).iloc[0]
        returned = gpd.GeoSeries([Point(row.longitud_modelo, row.latitud_modelo)], crs=4326).to_crs(32721).iloc[0]
        matches = polygons.loc[polygons.geometry.covers(returned), "shapeName"].tolist()
        returned_department = matches[0] if len(matches) == 1 else None
        records.append({
            "job_id": row.job_id, "coordenada_id": row.coordenada_id, "tipo_caso": row.tipo_caso,
            "departamento_solicitado": row.departamento_solicitado,
            "departamento_punto_modelo": returned_department,
            "mismo_departamento": returned_department == row.departamento_solicitado,
            "distancia_solicitado_modelo_m": requested.distance(returned),
            "latitud_solicitada": row.latitud_solicitada, "longitud_solicitada": row.longitud_solicitada,
            "latitud_modelo": row.latitud_modelo, "longitud_modelo": row.longitud_modelo,
        })
    return pd.DataFrame(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PILOT_CONFIG)
    parser.add_argument("--pilot", action="store_true", help="Confirma el alcance piloto protegido.")
    parser.add_argument("--execute", action="store_true", help="Realiza las dos llamadas si no hay checkpoints.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.pilot:
        raise SystemExit("Protección: este script exige --pilot; no se ejecutó ninguna llamada.")
    pilot = load_pilot_config(args.config)
    config = load_config(Path(pilot["main_config"]))
    catalog = pd.read_csv(config["paths"]["coordinate_catalog"])
    boundaries = gpd.read_file(config["spatial_design"]["boundary_file"])
    coordinates = select_pilot_coordinates(catalog, boundaries, pilot)
    jobs = build_pilot_jobs(coordinates, pilot)
    results_dir = Path(pilot["paths"]["results_directory"])
    results_dir.mkdir(parents=True, exist_ok=True)
    coordinates.to_csv(results_dir / "coordenadas_piloto.csv", index=False)
    plan = {"mode": "execute" if args.execute else "dry-run", "coordinates": len(coordinates),
            "windows": pilot["windows"], "requests": len(jobs), "expected_rows": pilot["limits"]["rows"],
            "network_calls_performed": 0}
    (results_dir / "plan_piloto.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2)); return

    raw_dir = Path(pilot["paths"]["raw_directory"])
    processed_dir = Path(pilot["paths"]["processed_directory"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    frames, metadata_frames, manifest_records = [], [], []
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for job in jobs:
        raw_path = raw_dir / f"{job['job_id']}.json"
        result = download_job(job, config, raw_path)
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        frame = normalize_job(payload, job, config).rename(columns={
            "latitud": "latitud_solicitada", "longitud": "longitud_solicitada"
        })
        responses = payload if isinstance(payload, list) else [payload]
        returned = {coordinate["coordenada_id"]: response for coordinate, response in zip(job["coordinates"], responses)}
        frame["latitud_modelo"] = frame["coordenada_id"].map(lambda identifier: returned[identifier]["latitude"])
        frame["longitud_modelo"] = frame["coordenada_id"].map(lambda identifier: returned[identifier]["longitude"])
        frame["tipo_caso"] = frame["coordenada_id"].map(coordinates.set_index("coordenada_id")["tipo_caso"])
        frame["job_id"] = job["job_id"]
        part_path = processed_dir / f"{job['job_id']}.parquet"
        frame.to_parquet(part_path, index=False)
        frames.append(frame); metadata_frames.append(response_metadata(payload, job, config))
        manifest_records.append({
            "run_id": run_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "script_version": SCRIPT_VERSION, "job_id": job["job_id"],
            "request_url": url_for_job(job, config), "request_parameters": url_for_job(job, config).split("?", 1)[1],
            "coordinate_ids": [item["coordenada_id"] for item in job["coordinates"]],
            "start_date": job["start_date"], "end_date": job["end_date"], "records": len(frame),
            "raw_path": str(raw_path), "part_path": str(part_path), **result
        })
    processed = pd.concat(frames, ignore_index=True)
    if len(processed) != pilot["limits"]["rows"] or processed.duplicated(["coordenada_id", "fecha"]).any():
        raise AssertionError("El dataset piloto no contiene exactamente 70 claves únicas.")
    processed_path = processed_dir / "open_meteo_pilot_daily.parquet"
    processed.to_parquet(processed_path, index=False)
    metadata = pd.concat(metadata_frames, ignore_index=True)
    metadata.to_csv(results_dir / "metadata_respuestas.csv", index=False)
    audit = spatial_audit(metadata, boundaries)
    audit.to_csv(results_dir / "auditoria_espacial.csv", index=False)
    manifest_path = results_dir / "manifest.jsonl"
    with manifest_path.open("a", encoding="utf-8") as stream:
        for record in manifest_records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = {
        "run_id": run_id, "network_calls_performed": sum(r["status"] == "downloaded" for r in manifest_records),
        "checkpoints_reused": sum(r["status"] == "checkpoint_reused" for r in manifest_records),
        "rows": len(processed), "coordinates": processed.coordenada_id.nunique(),
        "date_windows": pilot["windows"], "variables": config["daily_variables"],
        "missing_weather_values": int(processed[config["daily_variables"]].isna().sum().sum()),
        "duplicate_keys": int(processed.duplicated(["coordenada_id", "fecha"]).sum()),
        "same_department_all": bool(audit["mismo_departamento"].all()),
        "returned_department_mismatches": int((~audit["mismo_departamento"]).sum()),
        "max_requested_returned_distance_m": float(audit["distancia_solicitado_modelo_m"].max()),
        "outside_general_physical_ranges": physical_range_report(processed),
        "processed_sha256": hashlib.sha256(processed_path.read_bytes()).hexdigest(),
    }
    (results_dir / f"run_{run_id}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (results_dir / "ultima_ejecucion.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (results_dir / "validacion_piloto.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
