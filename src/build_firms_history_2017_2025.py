#!/usr/bin/env python3
"""Incorpora FIRMS 2017 como historia previa sin ampliar el período objetivo."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pandas.testing import assert_frame_equal

try:
    from .build_firms_department_week_clean import assign_activity_classes
    from .build_firms_open_meteo_weekly_history import integrate_history
except ImportError:
    from build_firms_department_week_clean import assign_activity_classes
    from build_firms_open_meteo_weekly_history import integrate_history


KEY = ["departamento", "fecha_inicio_semana"]
ARCHIVE = Path("DL_FIRE_M-C61_799659.zip")
REGIONAL = Path("data/firms_2018_2025.parquet")
BOUNDARIES = Path("geoBoundaries-URY-ADM1-all/geoBoundaries-URY-ADM1.geojson")
TARGET = Path("results/data/firms_departamento_semana_clean.parquet")
METEO = Path("data/processed/open_meteo_department_weekly/open_meteo_department_weekly_2017_2025.parquet")
HISTORY_OUTPUT = Path("results/data/firms_departamento_semana_history_2017_2025.parquet")
INTEGRATED_OUTPUT = Path("data/processed/firms_open_meteo_weekly/open_meteo_firms_weekly_history.parquet")
AUDIT_DIR = Path("results/firms_history_2017_audit")
RAW_REQUIRED = {
    "LATITUDE", "LONGITUDE", "BRIGHTNESS", "SCAN", "TRACK", "ACQ_DATE",
    "ACQ_TIME", "SATELLITE", "INSTRUMENT", "CONFIDENCE", "VERSION",
    "BRIGHT_T31", "FRP", "DAYNIGHT", "TYPE", "geometry",
}
TARGET_COLUMNS = [
    "cantidad_detecciones", "nivel_actividad_firms",
    "nivel_actividad_firms_codigo",
]
HISTORY_COLUMNS = [
    "cantidad_detecciones_hist", "nivel_actividad_firms_hist",
    "nivel_actividad_firms_codigo_hist",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--regional", type=Path, default=REGIONAL)
    parser.add_argument("--boundaries", type=Path, default=BOUNDARIES)
    parser.add_argument("--target", type=Path, default=TARGET)
    parser.add_argument("--meteo", type=Path, default=METEO)
    parser.add_argument("--history-output", type=Path, default=HISTORY_OUTPUT)
    parser.add_argument("--integrated-output", type=Path, default=INTEGRATED_OUTPUT)
    parser.add_argument("--audit-dir", type=Path, default=AUDIT_DIR)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def complete_monday_starts(coverage_start: pd.Timestamp, coverage_end: pd.Timestamp) -> pd.DatetimeIndex:
    """Devuelve semanas lunes-domingo contenidas por completo en la cobertura."""
    start = pd.Timestamp(coverage_start).normalize()
    end = pd.Timestamp(coverage_end).normalize()
    first_monday = start + pd.Timedelta(days=(7 - start.weekday()) % 7)
    last_monday = end - pd.Timedelta(days=end.weekday())
    if last_monday + pd.Timedelta(days=6) > end:
        last_monday -= pd.Timedelta(days=7)
    if first_monday > last_monday:
        return pd.DatetimeIndex([])
    return pd.date_range(first_monday, last_monday, freq="W-MON")


def normalize_archive(raw: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    missing = sorted(RAW_REQUIRED.difference(raw.columns))
    if missing:
        raise AssertionError(f"Faltan columnas FIRMS 2017: {missing}")
    result = raw.copy()
    result["ACQ_DATE"] = pd.to_datetime(result["ACQ_DATE"], errors="raise").dt.normalize()
    result["ACQ_TIME"] = result["ACQ_TIME"].astype("string").str.zfill(4)
    if result.crs is None:
        raise AssertionError("El archivo FIRMS nuevo no declara CRS.")
    return result.to_crs("EPSG:4326")


def archive_audit(raw: gpd.GeoDataFrame) -> dict:
    return {
        "filas": int(len(raw)),
        "columnas": int(raw.shape[1]),
        "columnas_reales": list(raw.columns),
        "tipos": {column: str(dtype) for column, dtype in raw.dtypes.items()},
        "crs": str(raw.crs),
        "fecha_min": raw.ACQ_DATE.min().date().isoformat(),
        "fecha_max": raw.ACQ_DATE.max().date().isoformat(),
        "filas_por_anio": {str(year): int(count) for year, count in raw.ACQ_DATE.dt.year.value_counts().sort_index().items()},
        "columna_pais_disponible": False,
        "paises_declarados": None,
        "nulos_por_columna": {column: int(value) for column, value in raw.isna().sum().items()},
        "nulos_totales": int(raw.isna().sum().sum()),
        "duplicados_exactos_sin_geometria": int(raw.drop(columns="geometry").duplicated().sum()),
        "instrumentos": sorted(raw.INSTRUMENT.astype(str).unique().tolist()),
        "satelites": sorted(raw.SATELLITE.astype(str).unique().tolist()),
    }


def compare_2018(raw: gpd.GeoDataFrame, regional: pd.DataFrame) -> dict:
    new = raw.loc[raw.ACQ_DATE.dt.year.eq(2018)].copy()
    old = regional.loc[
        regional.pais.eq("URY") & pd.to_datetime(regional.fecha_adq).dt.year.eq(2018)
    ].copy()
    comparable_new = pd.DataFrame({
        "latitud": new.LATITUDE,
        "longitud": new.LONGITUDE,
        "fecha_adq": new.ACQ_DATE.dt.strftime("%Y-%m-%d"),
        "hora_adq_hhmm": new.ACQ_TIME,
        "satelite": new.SATELLITE,
        "instrumento": new.INSTRUMENT,
        "confianza_raw": new.CONFIDENCE,
        "potencia_radiativa": new.FRP,
    })
    columns = list(comparable_new.columns)
    comparison = comparable_new.merge(
        old[columns].drop_duplicates(), on=columns, how="left", indicator=True,
        validate="one_to_one",
    )
    matched = int(comparison._merge.eq("both").sum())
    if matched != len(new) or len(new) != len(old):
        raise AssertionError("El bloque 2018 del ZIP no coincide con FIRMS regional existente.")
    return {
        "filas_zip_2018": int(len(new)),
        "filas_regional_ury_2018": int(len(old)),
        "coincidencias_exactas_campos_clave": matched,
        "sin_coincidencia": int(len(new) - matched),
        "compatibilidad": "completa",
        "mapeo_columnas": {
            "LATITUDE": "latitud", "LONGITUDE": "longitud", "BRIGHTNESS": "brillo_ti4",
            "ACQ_DATE": "fecha_adq", "ACQ_TIME": "hora_adq_hhmm", "SATELLITE": "satelite",
            "INSTRUMENT": "instrumento", "CONFIDENCE": "confianza_raw",
            "BRIGHT_T31": "brillo_ti5", "FRP": "potencia_radiativa",
            "DAYNIGHT": "dia_noche", "TYPE": "type",
        },
    }


def assign_departments(raw_2017: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    if len(boundaries) != 19 or boundaries.shapeName.nunique() != 19:
        raise AssertionError("La cartografía no contiene 19 departamentos.")
    points = gpd.GeoDataFrame(
        raw_2017.drop(columns="geometry").copy(),
        geometry=gpd.points_from_xy(raw_2017.LONGITUDE, raw_2017.LATITUDE),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(
        points,
        boundaries.to_crs("EPSG:4326")[["shapeName", "shapeISO", "geometry"]],
        how="left", predicate="within",
    ).rename(columns={"shapeName": "departamento", "shapeISO": "departamento_iso"})
    if joined.index.duplicated().any():
        raise AssertionError("La unión espacial produjo asignaciones múltiples.")
    return joined.loc[joined.departamento.notna()].copy(), joined.loc[joined.departamento.isna()].copy()


def build_2017_panel(
    assigned: gpd.GeoDataFrame,
    boundaries: gpd.GeoDataFrame,
    coverage_start: pd.Timestamp,
    coverage_end: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = assigned.copy()
    data["fecha_inicio_semana"] = data.ACQ_DATE - pd.to_timedelta(data.ACQ_DATE.dt.weekday, unit="D")
    weeks = complete_monday_starts(coverage_start, coverage_end)
    complete_mask = data.fecha_inicio_semana.isin(weeks)
    excluded = data.loc[~complete_mask].copy()
    counts = (
        data.loc[complete_mask]
        .groupby(["departamento", "departamento_iso", "fecha_inicio_semana"])
        .size().rename("cantidad_detecciones").reset_index()
    )
    departments = boundaries[["shapeName", "shapeISO"]].rename(
        columns={"shapeName": "departamento", "shapeISO": "departamento_iso"}
    )
    panel = departments.merge(pd.DataFrame({"fecha_inicio_semana": weeks}), how="cross")
    panel = panel.merge(counts, on=KEY + ["departamento_iso"], how="left", validate="one_to_one")
    panel["cantidad_detecciones"] = panel.cantidad_detecciones.fillna(0).astype("int64")
    panel["fecha_fin_semana"] = panel.fecha_inicio_semana + pd.Timedelta(days=6)
    panel["anio"] = panel.fecha_inicio_semana.dt.year.astype("int64")
    first_monday = pd.to_datetime(panel.anio.astype(str) + "-01-01")
    first_monday += pd.to_timedelta((7 - first_monday.dt.weekday) % 7, unit="D")
    panel["numero_semana"] = ((panel.fecha_inicio_semana - first_monday).dt.days // 7 + 1).astype("int64")
    panel["nivel_actividad_firms"], panel["nivel_actividad_firms_codigo"] = assign_activity_classes(
        panel.cantidad_detecciones
    )
    panel["es_periodo_objetivo"] = False
    columns = ["departamento", "departamento_iso", "anio", "numero_semana", "fecha_inicio_semana",
               "fecha_fin_semana", "cantidad_detecciones", "nivel_actividad_firms",
               "nivel_actividad_firms_codigo", "es_periodo_objetivo"]
    return panel[columns].sort_values(KEY).reset_index(drop=True), excluded


def preserve_target(target_before: pd.DataFrame, history: pd.DataFrame) -> None:
    compare_columns = KEY + TARGET_COLUMNS
    historical_target = history.loc[history.es_periodo_objetivo, compare_columns].reset_index(drop=True)
    expected = target_before[compare_columns].sort_values(KEY).reset_index(drop=True)
    assert_frame_equal(historical_target, expected, check_dtype=True, check_categorical=True)


def validate_history(history: pd.DataFrame, meteo: pd.DataFrame) -> dict:
    weeks = history.fecha_inicio_semana.nunique()
    gaps = history.sort_values(KEY).groupby("departamento").fecha_inicio_semana.diff().dropna().dt.days
    missing_meteo = history[KEY].merge(meteo[KEY], on=KEY, how="left", indicator=True, validate="one_to_one")
    checks = {
        "filas": int(len(history)), "departamentos": int(history.departamento.nunique()),
        "semanas": int(weeks), "duplicados_clave": int(history.duplicated(KEY).sum()),
        "nulos": int(history.isna().sum().sum()), "saltos_distintos_7_dias": int(gaps.ne(7).sum()),
        "filas_esperadas": int(19 * weeks),
        "claves_sin_open_meteo": int(missing_meteo._merge.ne("both").sum()),
    }
    if checks != {"filas": 8911, "departamentos": 19, "semanas": 469, "duplicados_clave": 0,
                   "nulos": 0, "saltos_distintos_7_dias": 0, "filas_esperadas": 8911,
                   "claves_sin_open_meteo": 0}:
        raise AssertionError(f"Falló la validación histórica: {checks}")
    return checks


def main() -> None:
    args = parse_args()
    raw = normalize_archive(gpd.read_file(f"zip://{args.archive.resolve()}"))
    raw_summary = archive_audit(raw)
    regional = pd.read_parquet(args.regional)
    compatibility = compare_2018(raw, regional)
    boundaries = gpd.read_file(args.boundaries)
    raw_2017 = raw.loc[raw.ACQ_DATE.dt.year.eq(2017)].copy()
    assigned, unassigned = assign_departments(raw_2017, boundaries)

    # El ZIP contiene evidencia desde 01/01/2017 hasta 31/12/2018. Para 2017,
    # la cobertura defendible es la intersección con el año calendario completo.
    coverage_start = max(raw.ACQ_DATE.min(), pd.Timestamp("2017-01-01"))
    coverage_end = min(raw.ACQ_DATE.max(), pd.Timestamp("2017-12-31"))
    panel_2017, partial = build_2017_panel(assigned, boundaries, coverage_start, coverage_end)

    target_checksum_before = sha256(args.target)
    target = pd.read_parquet(args.target)
    target["fecha_inicio_semana"] = pd.to_datetime(target.fecha_inicio_semana)
    target["fecha_fin_semana"] = pd.to_datetime(target.fecha_fin_semana)
    if len(target) != 7923 or target.cantidad_detecciones.sum() != 8508:
        raise AssertionError("El panel objetivo de entrada no cumple sus invariantes aprobados.")
    target_history = target[["departamento", "departamento_iso", "anio", "numero_semana",
                             "fecha_inicio_semana", "fecha_fin_semana"] + TARGET_COLUMNS].copy()
    target_history["es_periodo_objetivo"] = True
    history = pd.concat([panel_2017, target_history], ignore_index=True).sort_values(KEY).reset_index(drop=True)

    meteo = pd.read_parquet(args.meteo)
    meteo["fecha_inicio_semana"] = pd.to_datetime(meteo.fecha_inicio_semana)
    preserve_target(target, history)
    history_checks = validate_history(history, meteo)

    integrated = integrate_history(meteo, target)
    historical_for_join = history[KEY + TARGET_COLUMNS].rename(columns={
        "cantidad_detecciones": "cantidad_detecciones_hist",
        "nivel_actividad_firms": "nivel_actividad_firms_hist",
        "nivel_actividad_firms_codigo": "nivel_actividad_firms_codigo_hist",
    })
    integrated = integrated.merge(historical_for_join, on=KEY, how="left", validate="one_to_one")
    if integrated[HISTORY_COLUMNS].isna().any().any():
        raise AssertionError("La base integrada contiene nulos FIRMS históricos inesperados.")
    if integrated.duplicated(KEY).any() or len(integrated) != len(meteo):
        raise AssertionError("La actualización integrada alteró la grilla meteorológica.")
    target_after = integrated.loc[integrated.target_firms_disponible, KEY + TARGET_COLUMNS]
    assert_frame_equal(
        target_after.sort_values(KEY).reset_index(drop=True),
        target[KEY + TARGET_COLUMNS].sort_values(KEY).reset_index(drop=True),
        check_dtype=False, check_categorical=True,
    )

    args.history_output.parent.mkdir(parents=True, exist_ok=True)
    args.integrated_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    history.to_parquet(args.history_output, index=False)
    integrated.to_parquet(args.integrated_output, index=False)
    target_checksum_after = sha256(args.target)
    if target_checksum_after != target_checksum_before:
        raise AssertionError("El archivo objetivo original fue modificado.")
    assigned.drop(columns=["geometry", "index_right"], errors="ignore").to_parquet(
        args.audit_dir / "firms_2017_asignadas.parquet", index=False
    )
    unassigned.drop(columns=["geometry", "index_right"], errors="ignore").to_csv(
        args.audit_dir / "firms_2017_sin_departamento.csv", index=False
    )
    partial.drop(columns=["geometry", "index_right"], errors="ignore").to_csv(
        args.audit_dir / "detecciones_semanas_parciales_excluidas.csv", index=False
    )
    pd.DataFrame([compatibility]).to_json(
        args.audit_dir / "compatibilidad_esquema_2018.json", orient="records", indent=2, force_ascii=False
    )

    class_distribution = {
        str(label): int(count) for label, count in
        target.nivel_actividad_firms.astype("string").value_counts().items()
    }
    summary = {
        "proceso": "incorporacion_firms_2017_como_historia_previa",
        "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "archivo_firms_nuevo": str(args.archive),
        "auditoria_archivo": raw_summary,
        "compatibilidad_con_firms_2018_2025": compatibility,
        "registros_2017": int(len(raw_2017)),
        "registros_2017_asignados": int(len(assigned)),
        "registros_2017_sin_departamento": int(len(unassigned)),
        "detecciones_excluidas_semana_parcial": int(len(partial)),
        "semana_parcial_excluida": sorted(partial.fecha_inicio_semana.dt.date.astype(str).unique().tolist()),
        "detecciones_2017_utilizadas": int(panel_2017.cantidad_detecciones.sum()),
        "semanas_completas_2017": int(panel_2017.fecha_inicio_semana.nunique()),
        "filas_departamento_semana_2017": int(len(panel_2017)),
        "periodo_semanal_2017": [panel_2017.fecha_inicio_semana.min().date().isoformat(),
                                  panel_2017.fecha_fin_semana.max().date().isoformat()],
        "panel_historico": str(args.history_output),
        "validacion_panel_historico": history_checks,
        "base_integrada_actualizada": str(args.integrated_output),
        "columnas_firms_historicas_integradas": HISTORY_COLUMNS,
        "filas_objetivo_sin_cambios": int(target_after.shape[0]),
        "detecciones_objetivo_sin_cambios": int(target_after.cantidad_detecciones.sum()),
        "distribucion_objetivo_sin_cambios": class_distribution,
        "checksum_sha256_panel_objetivo_antes_y_despues": target_checksum_after,
        "nulos_target_esperados_en_2017": int(
            integrated.loc[~integrated.target_firms_disponible, TARGET_COLUMNS].isna().sum().sum()
        ),
        "nulos_firms_historicos_inesperados": int(integrated[HISTORY_COLUMNS].isna().sum().sum()),
        "nota": "FIRMS 2017 es historia previa para futuros lags; target_firms_disponible continúa falso en 2017.",
    }
    (args.audit_dir / "resumen_general.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.audit_dir / "recomendaciones.md").write_text(
        "# Incorporación FIRMS 2017\n\n"
        "FIRMS 2017 queda aprobado exclusivamente como antecedente histórico. La detección del "
        "01/01/2017 se excluye porque pertenece a una semana iniciada antes de la cobertura. "
        "Las 52 semanas completas restantes son compatibles con Open-Meteo. No se crearon lags "
        "ni se amplió el target 2018–2025.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
