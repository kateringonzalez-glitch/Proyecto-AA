#!/usr/bin/env python3
"""Audita en Open-Meteo, durante un solo día, el catálogo espacial candidato."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

try:
    from .design_open_meteo_extraction import load_config
    from .extract_open_meteo import batches, download_job, expected_days, normalize_job, request_params, url_for_job
except ImportError:
    from design_open_meteo_extraction import load_config
    from extract_open_meteo import batches, download_job, expected_days, normalize_job, request_params, url_for_job


DEFAULT_CONFIG = Path("config/open_meteo_spatial_audit.json")
SCRIPT_VERSION = "1.0.0"
COASTAL = {"Rocha", "Maldonado", "Montevideo", "Canelones", "San José", "Colonia"}
FRONTIER = {"Artigas", "Rivera", "Cerro Largo", "Rocha", "Salto", "Paysandú", "Río Negro"}


def load_audit_config(path: Path = DEFAULT_CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def guarded_jobs(catalog: pd.DataFrame, audit_config: dict) -> list[dict]:
    limits, day = audit_config["limits"], audit_config["date"]
    if len(catalog) > limits["max_coordinates"] or expected_days(day, day) != limits["days"]:
        raise ValueError("Protección: la auditoría sólo admite un día y hasta 200 coordenadas.")
    if catalog.coordenada_id.duplicated().any() or catalog.departamento.nunique() != 19:
        raise ValueError("El catálogo candidato debe tener IDs únicos y 19 departamentos.")
    groups = batches(catalog, int(audit_config["batch_size"]))
    jobs = [{"job_id": f"spatial_audit_b{index:03d}", "start_date": day, "end_date": day,
             "coordinates": group.to_dict("records")} for index, group in enumerate(groups, 1)]
    if len(jobs) > limits["max_requests"]:
        raise ValueError("Protección: la auditoría excedería 20 requests.")
    return jobs


def land_config(main_config: dict) -> dict:
    config = copy.deepcopy(main_config); config["cell_selection"] = "land"; return config


def classify_zone(department: str, distance_national_m: float, displacement_m: float) -> str:
    near_outer = distance_national_m <= max(displacement_m, 7500)
    if near_outer and department in COASTAL and department in FRONTIER:
        return "costa_o_frontera_internacional"
    if near_outer and department in COASTAL:
        return "costa"
    if near_outer and department in FRONTIER:
        return "frontera_internacional"
    return "limite_interdepartamental" if not near_outer else "otra_borde_exterior"


def audit_payload(payload: object, job: dict, boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    responses = payload if isinstance(payload, list) else [payload]
    polygons = boundaries[["shapeName", "geometry"]].to_crs(32721)
    national_boundary = polygons.geometry.union_all().boundary
    rows = []
    for coordinate, response in zip(job["coordinates"], responses):
        requested = gpd.GeoSeries([Point(coordinate["longitud"], coordinate["latitud"])], crs=4326).to_crs(32721).iloc[0]
        reported = gpd.GeoSeries([Point(response["longitude"], response["latitude"])], crs=4326).to_crs(32721).iloc[0]
        matches = polygons.loc[polygons.geometry.covers(reported), "shapeName"].tolist()
        returned_department = matches[0] if len(matches) == 1 else None
        displacement = requested.distance(reported)
        status = ("mismo_departamento" if returned_department == coordinate["departamento"]
                  else "fuera_uruguay" if returned_department is None else "otro_departamento")
        rows.append({
            "coordenada_id": coordinate["coordenada_id"], "departamento_solicitado": coordinate["departamento"],
            "departamento_iso": coordinate["departamento_iso"], "latitud_solicitada": coordinate["latitud"],
            "longitud_solicitada": coordinate["longitud"], "distancia_limite_m": coordinate["distancia_limite_m"],
            "metodo_seleccion": coordinate["metodo_seleccion"], "margen_interior_m": coordinate["margen_interior_m"],
            "latitud_reportada": response["latitude"], "longitud_reportada": response["longitude"],
            "elevacion_reportada_m": response.get("elevation"),
            "distancia_solicitada_reportada_m": displacement,
            "departamento_open_meteo": returned_department, "estado_asignacion": status,
            "mismo_departamento": returned_department == coordinate["departamento"],
            "punto_valido": returned_department == coordinate["departamento"],
            "distancia_limite_nacional_m": requested.distance(national_boundary),
            "tipo_zona": classify_zone(coordinate["departamento"], requested.distance(national_boundary), displacement),
            "timezone": response.get("timezone"), "timezone_abbreviation": response.get("timezone_abbreviation"),
            "utc_offset_seconds": response.get("utc_offset_seconds"),
            "daily_units_json": json.dumps(response.get("daily_units", {}), ensure_ascii=False, sort_keys=True),
        })
    return pd.DataFrame(rows)


def validation_summary(audit: pd.DataFrame, processed: pd.DataFrame, config: dict,
                       records: list[dict], run_id: str) -> dict:
    distances = audit.distancia_solicitada_reportada_m
    invalid = ~audit.punto_valido
    by_department = audit.groupby("departamento_solicitado").punto_valido.agg(["count", "sum", "all"])
    return {
        "run_id": run_id, "audit_date": processed.fecha.dt.strftime("%Y-%m-%d").unique().tolist(),
        "candidate_coordinates": len(audit), "valid_coordinates": int(audit.punto_valido.sum()),
        "invalid_coordinates": int(invalid.sum()), "valid_percentage": float(100 * audit.punto_valido.mean()),
        "changed_department": int(audit.estado_asignacion.eq("otro_departamento").sum()),
        "outside_uruguay": int(audit.estado_asignacion.eq("fuera_uruguay").sum()),
        "departments_all_valid": int(by_department["all"].sum()),
        "departments_with_failures": by_department.index[~by_department["all"]].tolist(),
        "distance_requested_reported_m": {"mean": float(distances.mean()), "median": float(distances.median()),
            "p90": float(distances.quantile(.90)), "p95": float(distances.quantile(.95)), "max": float(distances.max())},
        "network_calls_performed": sum(r["status"] == "downloaded" for r in records),
        "checkpoints_reused": sum(r["status"] == "checkpoint_reused" for r in records),
        "meteorology": {"variables": config["daily_variables"],
            "nulls": int(processed[config["daily_variables"]].isna().sum().sum()),
            "duplicate_keys": int(processed.duplicated(["coordenada_id", "fecha"]).sum()),
            "timezone_values": sorted(processed.timezone.unique().tolist())},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--spatial-audit", action="store_true", help="Confirma auditoría protegida de un día.")
    parser.add_argument("--execute", action="store_true", help="Habilita requests faltantes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.spatial_audit:
        raise SystemExit("Protección: se exige --spatial-audit; no se realizaron llamadas.")
    audit_config = load_audit_config(args.config)
    config = land_config(load_config(Path(audit_config["main_config"])))
    catalog = pd.read_csv(audit_config["candidate_catalog"])
    jobs = guarded_jobs(catalog, audit_config)
    results = Path(audit_config["paths"]["results_directory"]); results.mkdir(parents=True, exist_ok=True)
    plan = {"mode": "execute" if args.execute else "dry-run", "date": audit_config["date"],
            "cell_selection": "land", "candidate_coordinates": len(catalog),
            "departments": catalog.departamento.nunique(), "expected_requests": len(jobs),
            "expected_rows": len(catalog), "network_calls_performed": 0}
    (results / "plan_auditoria_real.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2)); return

    boundaries = gpd.read_file(config["spatial_design"]["boundary_file"])
    raw_root = Path(audit_config["paths"]["raw_directory"])
    parts = Path(audit_config["paths"]["processed_directory"]) / "parts"; parts.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    frames, audits, records = [], [], []
    for job in jobs:
        raw_path = raw_root / f"{job['job_id']}.json"
        result = download_job(job, config, raw_path)
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        frame = normalize_job(payload, job, config)
        part_path = parts / f"{job['job_id']}.parquet"; frame.to_parquet(part_path, index=False)
        frames.append(frame); audits.append(audit_payload(payload, job, boundaries))
        records.append({"run_id": run_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "script_version": SCRIPT_VERSION, "job_id": job["job_id"],
                        "request_url": url_for_job(job, config), "request_parameters": request_params(job, config),
                        "coordinate_ids": [c["coordenada_id"] for c in job["coordinates"]],
                        "raw_path": str(raw_path), "part_path": str(part_path), "records": len(frame), **result})
    processed = pd.concat(frames, ignore_index=True); audit = pd.concat(audits, ignore_index=True)
    if len(processed) != len(catalog) or processed.duplicated(["coordenada_id", "fecha"]).any():
        raise AssertionError("Filas o claves inesperadas en auditoría de un día.")
    audit.to_csv(results / "auditoria_celdas_open_meteo.csv", index=False)
    audit.loc[~audit.punto_valido].to_csv(results / "puntos_problematicos.csv", index=False)
    department_summary = audit.groupby("departamento_solicitado", as_index=False).agg(
        puntos_candidatos=("coordenada_id", "size"), puntos_validos=("punto_valido", "sum"),
        distancia_limite_min_m=("distancia_limite_m", "min"),
        desplazamiento_medio_m=("distancia_solicitada_reportada_m", "mean"),
        desplazamiento_max_m=("distancia_solicitada_reportada_m", "max"),
    )
    department_summary["porcentaje_valido"] = 100 * department_summary.puntos_validos / department_summary.puntos_candidatos
    department_summary.to_csv(results / "resumen_por_departamento.csv", index=False)
    distance_bins = audit.assign(intervalo_distancia_limite=pd.cut(
        audit.distancia_limite_m, bins=[0, 7500, 10000, 15000, float("inf")],
        labels=["0-7.5 km", "7.5-10 km", "10-15 km", ">=15 km"], include_lowest=True
    )).groupby("intervalo_distancia_limite", observed=False).agg(
        puntos=("coordenada_id", "size"), validos=("punto_valido", "sum")
    ).reset_index()
    distance_bins["fallos"] = distance_bins.puntos - distance_bins.validos
    distance_bins["porcentaje_valido"] = 100 * distance_bins.validos / distance_bins.puntos.replace(0, pd.NA)
    distance_bins.to_csv(results / "validez_por_distancia_limite.csv", index=False)
    processed_path = Path(audit_config["paths"]["processed_directory"]) / "open_meteo_spatial_audit_2018-08-06.parquet"
    processed.to_parquet(processed_path, index=False)
    validated = catalog.merge(audit[["coordenada_id", "latitud_reportada", "longitud_reportada",
                                     "departamento_open_meteo", "distancia_solicitada_reportada_m", "punto_valido"]],
                              on="coordenada_id", validate="one_to_one")
    validated = validated.loc[validated.punto_valido].copy()
    validated.to_csv(audit_config["validated_catalog"], index=False)
    validated.to_csv(results / "catalogo_validado.csv", index=False)
    with (results / "manifest.jsonl").open("a", encoding="utf-8") as stream:
        for record in records: stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = validation_summary(audit, processed, config, records, run_id)
    summary["validated_departments"] = validated.departamento.nunique()
    summary["validated_catalog_sha256"] = hashlib.sha256(Path(audit_config["validated_catalog"]).read_bytes()).hexdigest()
    (results / f"run_{run_id}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (results / "resumen_validacion.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
