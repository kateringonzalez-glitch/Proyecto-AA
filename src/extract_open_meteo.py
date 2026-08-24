#!/usr/bin/env python3
"""Planifica o ejecuta explícitamente la extracción diaria de Open-Meteo.

Sin ``--execute`` opera siempre en dry-run y no realiza llamadas HTTP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .design_open_meteo_extraction import load_config
except ImportError:  # ejecución directa: python src/extract_open_meteo.py
    from design_open_meteo_extraction import load_config


SCRIPT_VERSION = "1.0.0"
KEY = ["coordenada_id", "fecha"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/open_meteo.json"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Sólo muestra y guarda el plan (default).")
    mode.add_argument("--execute", action="store_true", help="Habilita explícitamente llamadas HTTP.")
    return parser.parse_args()


def expected_days(start_date: str, end_date: str) -> int:
    return (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1


def year_blocks(start_date: str, end_date: str) -> list[tuple[str, str]]:
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    return [
        (max(start, date(year, 1, 1)).isoformat(), min(end, date(year, 12, 31)).isoformat())
        for year in range(start.year, end.year + 1)
    ]


def batches(frame: pd.DataFrame, size: int) -> list[pd.DataFrame]:
    if size <= 0:
        raise ValueError("El tamaño del lote debe ser positivo.")
    ordered = frame.sort_values("coordenada_id").reset_index(drop=True)
    return [ordered.iloc[i:i + size].copy() for i in range(0, len(ordered), size)]


def build_jobs(catalog: pd.DataFrame, config: dict) -> list[dict]:
    coordinate_batches = batches(catalog, int(config["batching"]["coordinates_per_request"]))
    jobs = []
    for period_start, period_end in year_blocks(config["start_date"], config["end_date"]):
        for batch_number, coordinate_batch in enumerate(coordinate_batches, start=1):
            jobs.append({
                "job_id": f"{period_start[:4]}_b{batch_number:03d}",
                "start_date": period_start, "end_date": period_end,
                "coordinates": coordinate_batch.to_dict("records"),
            })
    return jobs


def request_params(job: dict, config: dict) -> dict[str, str]:
    coordinates = job["coordinates"]
    return {
        "latitude": ",".join(f"{row['latitud']:.6f}" for row in coordinates),
        "longitude": ",".join(f"{row['longitud']:.6f}" for row in coordinates),
        "start_date": job["start_date"], "end_date": job["end_date"],
        "daily": ",".join(config["daily_variables"]), "models": config["model"],
        "temperature_unit": config["units"]["temperature_unit"],
        "wind_speed_unit": config["units"]["wind_speed_unit"],
        "precipitation_unit": config["units"]["precipitation_unit"],
        "timezone": config["timezone"], "timeformat": config["timeformat"],
        "cell_selection": config["cell_selection"], "format": config["format"],
    }


def url_for_job(job: dict, config: dict) -> str:
    return config["endpoint"] + "?" + urllib.parse.urlencode(request_params(job, config))


def validate_payload(payload: object, job: dict, config: dict) -> list[dict]:
    responses = payload if isinstance(payload, list) else [payload]
    if len(responses) != len(job["coordinates"]):
        raise ValueError("Cantidad de respuestas distinta a la cantidad de coordenadas.")
    expected = expected_days(job["start_date"], job["end_date"])
    for response in responses:
        if not isinstance(response, dict) or "daily" not in response or "daily_units" not in response:
            raise ValueError("Respuesta sin daily o daily_units.")
        expected_variables = set(config["daily_variables"])
        returned_variables = set(response["daily"]).difference({"time"})
        missing = expected_variables.difference(returned_variables)
        if missing:
            raise ValueError(f"Variables ausentes en respuesta: {sorted(missing)}")
        extra = returned_variables.difference(expected_variables)
        if extra:
            raise ValueError(f"Variables diarias no solicitadas: {sorted(extra)}")
        returned_dates = response["daily"].get("time", [])
        if len(returned_dates) != expected:
            raise ValueError("Cantidad de fechas diaria inesperada.")
        start = date.fromisoformat(job["start_date"])
        expected_dates = [(start + timedelta(days=index)).isoformat() for index in range(expected)]
        if returned_dates != expected_dates:
            raise ValueError("Secuencia de fechas diaria diferente a la solicitada.")
        wrong_lengths = {
            variable: len(response["daily"].get(variable, []))
            for variable in config["daily_variables"]
            if len(response["daily"].get(variable, [])) != expected
        }
        if wrong_lengths:
            raise ValueError(f"Longitudes diarias inesperadas: {wrong_lengths}")
        if response.get("timezone") != config["timezone"]:
            raise ValueError("Timezone de respuesta diferente al solicitado.")
        returned_units = response["daily_units"]
        unexpected_units = {
            variable: {"esperada": unit, "recibida": returned_units.get(variable)}
            for variable, unit in config["api_response_units"].items()
            if returned_units.get(variable) != unit
        }
        if unexpected_units:
            raise ValueError(f"Unidades de respuesta inesperadas: {unexpected_units}")
    return responses


def normalize_job(payload: object, job: dict, config: dict) -> pd.DataFrame:
    responses = validate_payload(payload, job, config)
    rows = []
    for coordinate, response in zip(job["coordinates"], responses):
        daily = response["daily"]
        for index, day in enumerate(daily["time"]):
            row = {
                "coordenada_id": coordinate["coordenada_id"],
                "departamento": coordinate["departamento"],
                "departamento_iso": coordinate["departamento_iso"],
                "latitud_solicitada": coordinate["latitud"],
                "longitud_solicitada": coordinate["longitud"],
                "latitud_modelo": response.get("latitude"),
                "longitud_modelo": response.get("longitude"),
                "elevacion_modelo_m": response.get("elevation"),
                "fecha": day, "modelo": config["model"],
                "timezone": response.get("timezone"),
                "timezone_abbreviation": response.get("timezone_abbreviation"),
                "utc_offset_seconds": response.get("utc_offset_seconds"),
            }
            row.update({variable: daily[variable][index] for variable in config["daily_variables"]})
            rows.append(row)
    frame = pd.DataFrame(rows)
    frame["fecha"] = pd.to_datetime(frame["fecha"], errors="raise")
    if frame.duplicated(KEY).any():
        raise ValueError("La normalización generó claves duplicadas.")
    return frame


def physical_range_report(frame: pd.DataFrame) -> dict[str, int]:
    limits = {
        "temperature_2m_max": (-90, 60), "temperature_2m_min": (-90, 60),
        "relative_humidity_2m_min": (0, 100), "relative_humidity_2m_max": (0, 100),
        "wind_speed_10m_max": (0, 120), "wind_direction_10m_dominant": (0, 360),
        "precipitation_sum": (0, np.inf), "et0_fao_evapotranspiration": (0, np.inf),
    }
    return {
        variable: int((~pd.to_numeric(frame[variable], errors="coerce").between(low, high)).sum())
        for variable, (low, high) in limits.items()
    }


def validate_processed(frame: pd.DataFrame, catalog: pd.DataFrame, config: dict) -> dict:
    variables = config["daily_variables"]
    required = set(KEY + ["departamento", "departamento_iso", "latitud_solicitada",
                          "longitud_solicitada", "latitud_modelo", "longitud_modelo"] + variables)
    missing_columns = sorted(required.difference(frame.columns))
    if missing_columns:
        raise AssertionError(f"Columnas procesadas ausentes: {missing_columns}")
    frame = frame.copy()
    frame["fecha"] = pd.to_datetime(frame["fecha"], errors="raise")
    expected = expected_days(config["start_date"], config["end_date"])
    counts = frame.groupby("coordenada_id")["fecha"].nunique()
    date_ranges = frame.groupby("coordenada_id")["fecha"].agg(["min", "max"])
    if set(frame["coordenada_id"]) != set(catalog["coordenada_id"]):
        raise AssertionError("No están presentes todas las coordenadas esperadas.")
    if not counts.eq(expected).all() or frame.duplicated(KEY).any():
        raise AssertionError("Fechas incompletas o claves duplicadas.")
    if not date_ranges["min"].eq(pd.Timestamp(config["start_date"])).all():
        raise AssertionError("Alguna coordenada tiene una fecha mínima inesperada.")
    if not date_ranges["max"].eq(pd.Timestamp(config["end_date"])).all():
        raise AssertionError("Alguna coordenada tiene una fecha máxima inesperada.")
    if frame[variables].isna().any().any():
        raise AssertionError("Hay nulos meteorológicos; no se imputan automáticamente.")
    return {
        "filas": len(frame), "coordenadas": frame["coordenada_id"].nunique(),
        "departamentos": frame["departamento"].nunique(), "dias_por_coordenada": expected,
        "duplicados_clave": int(frame.duplicated(KEY).sum()),
        "nulos_variables": int(frame[variables].isna().sum().sum()),
        "fuera_rangos_generales": physical_range_report(frame),
    }


def download_job(job: dict, config: dict, raw_path: Path) -> dict:
    if raw_path.exists():
        content = raw_path.read_bytes()
        try:
            validate_payload(json.loads(content), job, config)
            return {"status": "checkpoint_reused", "http_status": None,
                    "validation": "valid", "checksum_sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content)}
        except (ValueError, json.JSONDecodeError) as error:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            invalid_path = raw_path.with_name(f"{raw_path.name}.invalid.{timestamp}")
            raw_path.rename(invalid_path)
    url = url_for_job(job, config)
    attempts = int(config["batching"]["max_retries"])
    backoff = int(config["batching"]["initial_backoff_seconds"])
    timeout = int(config["batching"]["request_timeout_seconds"])
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                content, status = response.read(), response.status
            validate_payload(json.loads(content), job, config)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(content)
            return {"status": "downloaded", "http_status": status, "attempts": attempt,
                    "validation": "valid", "checksum_sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content)}
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            last_error = repr(error)
            if attempt < attempts:
                if isinstance(error, urllib.error.HTTPError) and error.code == 429:
                    retry_after = error.headers.get("Retry-After") if error.headers else None
                    wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else int(
                        config["batching"].get("rate_limit_backoff_seconds", 60)
                    )
                    time.sleep(wait_seconds)
                else:
                    time.sleep(min(backoff * (2 ** (attempt - 1)), 60))
    raise RuntimeError(f"Falló {job['job_id']} tras {attempts} intentos: {last_error}")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    catalog = pd.read_csv(config["paths"]["coordinate_catalog"])
    jobs = build_jobs(catalog, config)
    rows_expected = len(catalog) * expected_days(config["start_date"], config["end_date"])
    audit_dir = Path(config["paths"]["audit_directory"])
    audit_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "mode": "execute" if args.execute else "dry-run", "script_version": SCRIPT_VERSION,
        "endpoint": config["endpoint"], "model": config["model"],
        "period": [config["start_date"], config["end_date"]],
        "days_per_coordinate": expected_days(config["start_date"], config["end_date"]),
        "coordinates": len(catalog), "departments": catalog["departamento"].nunique(),
        "variables": config["daily_variables"], "units": config["units"],
        "timezone": config["timezone"], "estimated_rows": rows_expected,
        "estimated_requests": len(jobs),
        "estimated_processed_parquet_mib": round(
            rows_expected * config["size_estimation"]["processed_parquet_bytes_per_row"]
            / 1024 / 1024, 2
        ),
        "estimated_raw_json_size": None,
        "coordinates_per_request": config["batching"]["coordinates_per_request"],
        "network_calls_performed": 0,
    }
    expected_coordinates = config.get("spatial_design", {}).get("validated_coordinate_count")
    if expected_coordinates is not None and len(catalog) != expected_coordinates:
        raise AssertionError(
            f"Catálogo activo con {len(catalog)} coordenadas; se esperaban {expected_coordinates}."
        )
    if expected_days(config["start_date"], config["end_date"]) != 3286:
        raise AssertionError("El período definitivo debe contener exactamente 3.286 días.")
    (audit_dir / "dry_run_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    raw_dir = Path(config["paths"]["raw_directory"])
    parts_dir = Path(config["paths"]["processed_parts_directory"])
    parts_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = audit_dir / "manifest.jsonl"
    for job in jobs:
        raw_path = raw_dir / job["start_date"][:4] / f"{job['job_id']}.json"
        try:
            result = download_job(job, config, raw_path)
        except RuntimeError as error:
            failure = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(), "job_id": job["job_id"],
                "endpoint": config["endpoint"], "request_parameters": request_params(job, config),
                "start_date": job["start_date"], "end_date": job["end_date"],
                "coordinate_ids": [row["coordenada_id"] for row in job["coordinates"]],
                "status": "failed", "validation": "not_completed", "error": str(error),
                "raw_path": str(raw_path),
            }
            with manifest_path.open("a", encoding="utf-8") as manifest:
                manifest.write(json.dumps(failure, ensure_ascii=False) + "\n")
            raise
        part = normalize_job(json.loads(raw_path.read_text(encoding="utf-8")), job, config)
        part_path = parts_dir / f"{job['job_id']}.parquet"
        if not part_path.exists():
            part.to_parquet(part_path, index=False)
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(), "job_id": job["job_id"],
            "endpoint": config["endpoint"], "request_url": url_for_job(job, config),
            "request_parameters": request_params(job, config),
            "start_date": job["start_date"], "end_date": job["end_date"],
            "coordinate_ids": [row["coordenada_id"] for row in job["coordinates"]],
            "coordinates": len(job["coordinates"]),
            "records": len(part), "raw_path": str(raw_path), "part_path": str(part_path), **result,
        }
        with manifest_path.open("a", encoding="utf-8") as manifest:
            manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
        if result["status"] == "downloaded":
            time.sleep(float(config["batching"].get("delay_between_requests_seconds", 0)))
    processed = pd.concat(
        [pd.read_parquet(path) for path in sorted(parts_dir.glob("*.parquet"))], ignore_index=True
    )
    validations = validate_processed(processed, catalog, config)
    output = Path(config["paths"]["processed_dataset"])
    output.parent.mkdir(parents=True, exist_ok=True)
    processed.to_parquet(output, index=False)
    (audit_dir / "execution_summary.json").write_text(
        json.dumps(validations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
