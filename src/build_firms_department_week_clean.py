#!/usr/bin/env python3
"""Construye la versión depurada del panel FIRMS departamento-semana.

Conserva el panel original, excluye semanas incompletas mediante una regla
general y agrega una definición candidata del objetivo. No incorpora
predictores ni entrena modelos.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


VERSION = "1.0.0"
CLASS_ORDER = ["Sin detección", "Bajo", "Moderado", "Alto"]
CLASS_TO_CODE = {label: code for code, label in enumerate(CLASS_ORDER)}
KEY = ["departamento", "fecha_inicio_semana"]
REQUIRED = {
    "departamento", "departamento_iso", "anio", "numero_semana",
    "fecha_inicio_semana", "fecha_fin_semana", "cantidad_detecciones",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firms", type=Path, default=Path("data/firms_2018_2025.parquet"))
    parser.add_argument("--panel", type=Path,
                        default=Path("results/data/firms_departamento_semana.parquet"))
    parser.add_argument("--construction-audit", type=Path,
                        default=Path("results/data/auditoria_construccion.json"))
    parser.add_argument("--unassigned-audit", type=Path,
                        default=Path("results/target_audit/detalle_sin_departamento.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/data"))
    parser.add_argument("--audit-dir", type=Path, default=Path("results/clean_audit"))
    return parser.parse_args()


def complete_week_mask(frame: pd.DataFrame, maximum_source_date: pd.Timestamp) -> pd.Series:
    """Indica si el fin teórico de cada semana está cubierto por la fuente."""
    ends = pd.to_datetime(frame["fecha_fin_semana"], errors="raise").dt.normalize()
    return ends.le(pd.Timestamp(maximum_source_date).normalize())


def assign_activity_classes(counts: pd.Series) -> tuple[pd.Categorical, pd.Series]:
    """Asigna etiquetas y códigos ordinales a conteos FIRMS no negativos."""
    numeric = pd.to_numeric(counts, errors="raise")
    if numeric.isna().any() or numeric.lt(0).any():
        raise ValueError("cantidad_detecciones debe ser no nula y no negativa.")
    labels = pd.cut(
        numeric, bins=[-1, 0, 1, 3, float("inf")],
        labels=CLASS_ORDER, ordered=True,
    )
    codes = pd.Series(labels, index=counts.index).map(CLASS_TO_CODE).astype("int8")
    return labels, codes


def expected_monday_ordinal(starts: pd.Series) -> pd.Series:
    """Ordinal 1–53 entre los lunes del año del inicio de semana."""
    starts = pd.to_datetime(starts, errors="raise").dt.normalize()
    years = starts.dt.year
    first_monday = pd.to_datetime(years.astype(str) + "-01-01")
    first_monday += pd.to_timedelta((7 - first_monday.dt.weekday) % 7, unit="D")
    return (((starts - first_monday).dt.days // 7) + 1).astype("int64")


def validate_clean_panel(frame: pd.DataFrame, maximum_source_date: pd.Timestamp) -> dict[str, int]:
    """Valida integridad, cobertura temporal y grilla rectangular."""
    missing_columns = sorted(REQUIRED.difference(frame.columns))
    if missing_columns:
        raise AssertionError(f"Faltan columnas requeridas: {missing_columns}")
    required_not_null = [
        "departamento", "fecha_inicio_semana", "fecha_fin_semana",
        "cantidad_detecciones", "nivel_actividad_firms", "nivel_actividad_firms_codigo",
    ]
    if frame[required_not_null].isna().any().any():
        raise AssertionError("Hay nulos en columnas obligatorias del panel limpio.")
    if frame.duplicated(KEY).any():
        raise AssertionError("Hay claves departamento-semana duplicadas.")
    if frame["cantidad_detecciones"].lt(0).any():
        raise AssertionError("Hay conteos negativos.")
    if not complete_week_mask(frame, maximum_source_date).all():
        raise AssertionError("El panel limpio conserva al menos una semana incompleta.")
    if frame["departamento"].nunique() != 19:
        raise AssertionError("El panel limpio no contiene exactamente 19 departamentos.")
    weeks = frame["fecha_inicio_semana"].nunique()
    if not frame.groupby("fecha_inicio_semana").size().eq(19).all():
        raise AssertionError("Alguna semana no contiene los 19 departamentos.")
    if not frame.groupby("departamento").size().eq(weeks).all():
        raise AssertionError("Algún departamento no contiene todas las semanas.")
    starts = pd.to_datetime(frame["fecha_inicio_semana"])
    ends = pd.to_datetime(frame["fecha_fin_semana"])
    if not starts.dt.weekday.eq(0).all() or not ends.sub(starts).dt.days.eq(6).all():
        raise AssertionError("Las semanas no comienzan en lunes o no duran siete días teóricos.")
    if not frame["anio"].eq(starts.dt.year).all():
        raise AssertionError("anio no coincide con el año del lunes de inicio.")
    if not frame["numero_semana"].eq(expected_monday_ordinal(starts)).all():
        raise AssertionError("numero_semana no coincide con el ordinal de lunes documentado.")
    expected_labels, expected_codes = assign_activity_classes(frame["cantidad_detecciones"])
    actual_labels = frame["nivel_actividad_firms"].astype("string")
    expected_labels_series = pd.Series(expected_labels, index=frame.index).astype("string")
    if not actual_labels.eq(expected_labels_series).all():
        raise AssertionError("Las etiquetas de actividad no coinciden con los conteos.")
    if not frame["nivel_actividad_firms_codigo"].eq(expected_codes).all():
        raise AssertionError("Los códigos ordinales no coinciden con las etiquetas.")
    return {
        "departamentos": int(frame["departamento"].nunique()),
        "semanas": int(weeks), "filas": int(len(frame)),
        "duplicados_clave": int(frame.duplicated(KEY).sum()),
        "nulos_columnas_obligatorias": int(frame[required_not_null].isna().sum().sum()),
        "semanas_incompletas": int((~complete_week_mask(frame, maximum_source_date)).sum()),
    }


def class_distribution(frame: pd.DataFrame, group: str | None = None) -> pd.DataFrame:
    groups = ([group] if group else []) + ["nivel_actividad_firms"]
    out = frame.groupby(groups, observed=False).size().rename("cantidad").reset_index()
    if group:
        totals = frame.groupby(group).size().rename("total_observaciones")
        out = out.merge(totals, on=group, validate="many_to_one")
    else:
        out["total_observaciones"] = len(frame)
    out["porcentaje"] = out["cantidad"] / out["total_observaciones"] * 100
    return out


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    firms = pd.read_parquet(args.firms)
    uruguay = firms.loc[firms["pais"].eq("URY")].copy()
    source_dates = pd.to_datetime(uruguay["fecha_adq"], errors="raise")
    minimum_source_date = source_dates.min().normalize()
    maximum_source_date = source_dates.max().normalize()
    original = pd.read_parquet(args.panel)
    original["fecha_inicio_semana"] = pd.to_datetime(original["fecha_inicio_semana"])
    original["fecha_fin_semana"] = pd.to_datetime(original["fecha_fin_semana"])
    construction = json.loads(args.construction_audit.read_text(encoding="utf-8"))
    unassigned = pd.read_csv(args.unassigned_audit)

    keep = complete_week_mask(original, maximum_source_date)
    excluded = original.loc[~keep].copy()
    clean = original.loc[keep].copy()
    clean["nivel_actividad_firms"], clean["nivel_actividad_firms_codigo"] = (
        assign_activity_classes(clean["cantidad_detecciones"])
    )
    clean = clean[[
        "departamento", "departamento_iso", "anio", "numero_semana",
        "fecha_inicio_semana", "fecha_fin_semana", "cantidad_detecciones",
        "nivel_actividad_firms", "nivel_actividad_firms_codigo",
        "superficie_km2", "detecciones_por_1000_km2",
    ]].sort_values(["fecha_inicio_semana", "departamento"]).reset_index(drop=True)

    validations = validate_clean_panel(clean, maximum_source_date)
    assigned_total = int(construction["detecciones_asignadas_departamento"])
    excluded_detections = int(excluded["cantidad_detecciones"].sum())
    if clean["cantidad_detecciones"].sum() != assigned_total - excluded_detections:
        raise AssertionError("La suma limpia no reconcilia con asignadas menos semana parcial.")
    for key, expected in {"departamentos": 19, "semanas": 417, "filas": 7923}.items():
        if validations[key] != expected:
            raise AssertionError(f"Valor inesperado para {key}: {validations[key]} != {expected}")

    output_panel = args.output_dir / "firms_departamento_semana_clean.parquet"
    clean.to_parquet(output_panel, index=False)
    overall = class_distribution(clean)
    by_year = class_distribution(clean, "anio")
    by_department = class_distribution(clean, "departamento")
    overall.to_csv(args.audit_dir / "distribucion_clases_final.csv", index=False)
    by_year.to_csv(args.audit_dir / "distribucion_clases_final_por_anio.csv", index=False)
    by_department.to_csv(args.audit_dir / "distribucion_clases_final_por_departamento.csv", index=False)
    excluded.to_csv(args.audit_dir / "semanas_incompletas_excluidas.csv", index=False)

    observed_distribution = dict(zip(
        overall["nivel_actividad_firms"].astype(str), overall["cantidad"].astype(int)
    ))
    expected_distribution = {
        "Sin detección": 4967, "Bajo": 1237, "Moderado": 1034, "Alto": 685,
    }
    if observed_distribution != expected_distribution:
        raise AssertionError(
            f"Distribución final inesperada: {observed_distribution} != {expected_distribution}"
        )

    audit = {
        "proceso": "depuracion_final_firms_departamento_semana",
        "version_proceso": VERSION,
        "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "fuente_firms": str(args.firms), "panel_original": str(args.panel),
        "panel_limpio": str(output_panel),
        "registros_firms_uruguay_originales": int(len(uruguay)),
        "registros_asignados_espacialmente": assigned_total,
        "registros_no_asignados_mantenidos_excluidos": int(len(unassigned)),
        "proporcion_no_asignados_pct": float(len(unassigned) / len(uruguay) * 100),
        "fecha_minima_firms_uruguay": minimum_source_date.date().isoformat(),
        "fecha_maxima_firms_uruguay": maximum_source_date.date().isoformat(),
        "regla_semana_completa": "fecha_fin_semana <= fecha_maxima_firms_uruguay",
        "semanas_originales": int(original["fecha_inicio_semana"].nunique()),
        "semanas_completas_conservadas": int(clean["fecha_inicio_semana"].nunique()),
        "semanas_parciales_excluidas": sorted(
            excluded["fecha_inicio_semana"].dt.date.astype(str).unique().tolist()
        ),
        "filas_panel_antes": int(len(original)), "filas_panel_despues": int(len(clean)),
        "filas_excluidas_semana_parcial": int(len(excluded)),
        "detecciones_asignadas_antes_de_excluir_semana_parcial": assigned_total,
        "detecciones_excluidas_unicamente_por_semana_parcial": excluded_detections,
        "detecciones_conservadas_panel_limpio": int(clean["cantidad_detecciones"].sum()),
        "valores_extremos_conservados": {
            "Paysandú_2021-12-27": int(clean.loc[
                clean["departamento"].eq("Paysandú")
                & clean["fecha_inicio_semana"].eq(pd.Timestamp("2021-12-27")),
                "cantidad_detecciones"].iloc[0]),
            "Río Negro_2021-12-27": int(clean.loc[
                clean["departamento"].eq("Río Negro")
                & clean["fecha_inicio_semana"].eq(pd.Timestamp("2021-12-27")),
                "cantidad_detecciones"].iloc[0]),
        },
        "criterio_clase_candidata": {
            "0": "Sin detección", "1": "Bajo", "2-3": "Moderado", ">=4": "Alto",
        },
        "codificacion_ordinal": CLASS_TO_CODE,
        "distribucion_final": {
            row["nivel_actividad_firms"]: {
                "cantidad": int(row["cantidad"]), "porcentaje": float(row["porcentaje"]),
            } for row in overall.to_dict("records")
        },
        "validaciones": validations,
        "nota_objetivo": (
            "Definición candidata de actividad FIRMS observada, sujeta a validación "
            "posterior con partición cronológica; no es riesgo estimado ni predicción."
        ),
    }
    (args.audit_dir / "auditoria_panel_firms_clean.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
