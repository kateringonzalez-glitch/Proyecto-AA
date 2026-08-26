#!/usr/bin/env python3
"""Integra Open-Meteo semanal con el target histórico FIRMS, sin crear predictores."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


KEY = ["departamento", "fecha_inicio_semana"]
TARGET_COLUMNS = [
    "cantidad_detecciones",
    "nivel_actividad_firms",
    "nivel_actividad_firms_codigo",
]
FIRMS_DEFAULT = Path("results/data/firms_departamento_semana_clean.parquet")
METEO_DEFAULT = Path(
    "data/processed/open_meteo_department_weekly/"
    "open_meteo_department_weekly_2017_2025.parquet"
)
RAW_FIRMS_DEFAULT = Path("data/firms_2018_2025.parquet")
OUTPUT_DIR_DEFAULT = Path("data/processed/firms_open_meteo_weekly")
AUDIT_DIR_DEFAULT = Path("results/firms_open_meteo_integration_audit")
CLASS_ORDER = ["Sin detección", "Bajo", "Moderado", "Alto"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firms", type=Path, default=FIRMS_DEFAULT)
    parser.add_argument("--meteo", type=Path, default=METEO_DEFAULT)
    parser.add_argument("--raw-firms", type=Path, default=RAW_FIRMS_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR_DEFAULT)
    parser.add_argument("--audit-dir", type=Path, default=AUDIT_DIR_DEFAULT)
    return parser.parse_args()


def prepare_dates(frame: pd.DataFrame) -> pd.DataFrame:
    """Convierte únicamente las claves temporales; no normaliza nombres."""
    result = frame.copy()
    result["fecha_inicio_semana"] = pd.to_datetime(
        result["fecha_inicio_semana"], errors="raise"
    )
    if "fecha_fin_semana" in result:
        result["fecha_fin_semana"] = pd.to_datetime(
            result["fecha_fin_semana"], errors="raise"
        )
    return result


def reject_duplicate_keys(frame: pd.DataFrame, source: str) -> None:
    duplicates = int(frame.duplicated(KEY).sum())
    if duplicates:
        raise AssertionError(f"{source} tiene {duplicates} claves duplicadas; JOIN 1:1 rechazado.")


def class_distribution(frame: pd.DataFrame) -> dict[str, int]:
    observed = frame["nivel_actividad_firms"].astype("string").value_counts()
    return {label: int(observed.get(label, 0)) for label in CLASS_ORDER}


def validate_firms(frame: pd.DataFrame) -> dict:
    required = set(KEY + ["departamento_iso", "fecha_fin_semana"] + TARGET_COLUMNS)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise AssertionError(f"Faltan columnas FIRMS: {missing}")
    reject_duplicate_keys(frame, "FIRMS")
    if frame[KEY + TARGET_COLUMNS].isna().any().any():
        raise AssertionError("FIRMS contiene nulos en clave o target.")
    if frame["departamento"].nunique() != 19:
        raise AssertionError("FIRMS no contiene 19 departamentos.")
    if frame["fecha_inicio_semana"].nunique() != 417 or len(frame) != 7923:
        raise AssertionError("FIRMS no coincide con el panel limpio aprobado de 7.923 filas.")
    if not frame["fecha_inicio_semana"].dt.weekday.eq(0).all():
        raise AssertionError("FIRMS contiene semanas que no comienzan en lunes.")
    return {
        "filas": int(len(frame)),
        "columnas": int(frame.shape[1]),
        "departamentos": int(frame["departamento"].nunique()),
        "semanas": int(frame["fecha_inicio_semana"].nunique()),
        "fecha_min": frame["fecha_inicio_semana"].min().date().isoformat(),
        "fecha_max": frame["fecha_inicio_semana"].max().date().isoformat(),
        "duplicados_clave": int(frame.duplicated(KEY).sum()),
        "suma_cantidad_detecciones": int(frame["cantidad_detecciones"].sum()),
        "distribucion_target": class_distribution(frame),
    }


def meteorological_columns(frame: pd.DataFrame) -> list[str]:
    identifiers = {
        "departamento", "departamento_iso", "fecha_inicio_semana",
        "fecha_fin_semana", "anio", "numero_semana", "n_dias_esperados",
        "n_dias_observados", "cobertura_temporal_pct", "cobertura_espacial_min_pct",
    }
    return [column for column in frame.columns if column not in identifiers]


def validate_meteo(frame: pd.DataFrame) -> dict:
    required = set(KEY + ["departamento_iso", "fecha_fin_semana"])
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise AssertionError(f"Faltan columnas Open-Meteo: {missing}")
    reject_duplicate_keys(frame, "Open-Meteo")
    meteo_columns = meteorological_columns(frame)
    if frame[KEY + ["departamento_iso"]].isna().any().any():
        raise AssertionError("Open-Meteo contiene nulos en claves.")
    if frame[meteo_columns].isna().any().any():
        raise AssertionError("Open-Meteo contiene nulos meteorológicos.")
    if len(frame) != 8911 or frame["departamento"].nunique() != 19:
        raise AssertionError("Open-Meteo no coincide con las 8.911 filas aprobadas.")
    if frame["fecha_inicio_semana"].nunique() != 469:
        raise AssertionError("Open-Meteo no contiene 469 semanas completas.")
    return {
        "filas": int(len(frame)),
        "columnas": int(frame.shape[1]),
        "departamentos": int(frame["departamento"].nunique()),
        "semanas": int(frame["fecha_inicio_semana"].nunique()),
        "fecha_min": frame["fecha_inicio_semana"].min().date().isoformat(),
        "fecha_max": frame["fecha_inicio_semana"].max().date().isoformat(),
        "duplicados_clave": int(frame.duplicated(KEY).sum()),
        "nulos_meteorologicos": int(frame[meteo_columns].isna().sum().sum()),
    }


def compare_departments(firms: pd.DataFrame, meteo: pd.DataFrame) -> pd.DataFrame:
    firms_names = set(firms["departamento"].astype(str).unique())
    meteo_names = set(meteo["departamento"].astype(str).unique())
    names = sorted(firms_names | meteo_names)
    rows = []
    for name in names:
        firms_iso = sorted(firms.loc[firms.departamento.eq(name), "departamento_iso"].astype(str).unique())
        meteo_iso = sorted(meteo.loc[meteo.departamento.eq(name), "departamento_iso"].astype(str).unique())
        rows.append({
            "departamento": name,
            "presente_firms": name in firms_names,
            "presente_open_meteo": name in meteo_names,
            "iso_firms": "|".join(firms_iso),
            "iso_open_meteo": "|".join(meteo_iso),
            "iso_coincide": firms_iso == meteo_iso,
            "espacio_exterior": name != name.strip(),
        })
    result = pd.DataFrame(rows)
    if not result[["presente_firms", "presente_open_meteo", "iso_coincide"]].all().all():
        raise AssertionError("Los catálogos departamentales FIRMS y Open-Meteo no coinciden.")
    return result


def audit_first_firms_week(raw_path: Path, panel: pd.DataFrame) -> dict:
    """Clasifica cobertura inicial usando evidencia directa del archivo regional."""
    evidence = {
        "archivo_regional_disponible": raw_path.exists(),
        "archivo_original_de_descarga_o_configuracion_encontrado": False,
    }
    if not raw_path.exists():
        return {
            **evidence,
            "clasificacion": "C. No determinable",
            "conclusion": "No está disponible el archivo regional para comprobar el 01/01/2018.",
        }
    raw = pd.read_parquet(raw_path)
    if not {"fecha_adq", "pais"}.issubset(raw.columns):
        raise AssertionError("El FIRMS regional no contiene fecha_adq y pais.")
    dates = pd.to_datetime(raw["fecha_adq"], errors="raise").dt.normalize()
    uruguay = raw.loc[raw["pais"].eq("URY")].copy()
    uruguay_dates = pd.to_datetime(uruguay["fecha_adq"], errors="raise").dt.normalize()
    january_first = pd.Timestamp("2018-01-01")
    rows_first = raw.loc[dates.eq(january_first)]
    countries_first = {
        str(country): int(count)
        for country, count in rows_first["pais"].value_counts().sort_index().items()
    }
    first_week = panel.loc[panel.fecha_inicio_semana.eq(january_first)]
    defendible = dates.min() == january_first and len(rows_first) > 0
    classification = "A. Semana completa defendible" if defendible else "C. No determinable"
    conclusion = (
        "El archivo regional contiene detecciones del 01/01/2018 en países vecinos; "
        "la primera detección uruguaya del 02/01/2018 no marca el inicio del archivo."
        if defendible else
        "La evidencia disponible no demuestra cobertura regional desde el 01/01/2018."
    )
    return {
        **evidence,
        "clasificacion": classification,
        "conclusion": conclusion,
        "limitacion": (
            "No se encontró en este repositorio el script, parámetros o comprobante de la "
            "descarga FIRMS original; la clasificación se apoya en el contenido del Parquet regional."
        ),
        "fecha_minima_archivo_regional": dates.min().date().isoformat(),
        "fecha_maxima_archivo_regional": dates.max().date().isoformat(),
        "filas_regionales_2018_01_01": int(len(rows_first)),
        "filas_por_pais_2018_01_01": countries_first,
        "fecha_primera_deteccion_uruguay": uruguay_dates.min().date().isoformat(),
        "detecciones_uruguay_2018_01_01": int(uruguay_dates.eq(january_first).sum()),
        "detecciones_uruguay_2018_01_02": int(uruguay_dates.eq(pd.Timestamp("2018-01-02")).sum()),
        "filas_panel_primera_semana": int(len(first_week)),
        "detecciones_asignadas_primera_semana": int(first_week.cantidad_detecciones.sum()),
        "impacto_si_se_excluyera": {
            "filas": int(len(first_week)),
            "semanas": int(first_week.fecha_inicio_semana.nunique()),
            "detecciones": int(first_week.cantidad_detecciones.sum()),
        },
    }


def anti_join(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    right_keys = right[KEY].drop_duplicates()
    merged = left.merge(right_keys, on=KEY, how="left", indicator=True, validate="many_to_one")
    return merged.loc[merged["_merge"].eq("left_only")].drop(columns="_merge")


def integrate_history(meteo: pd.DataFrame, firms: pd.DataFrame) -> pd.DataFrame:
    """LEFT JOIN 1:1; los nulos fuera del período FIRMS se conservan."""
    reject_duplicate_keys(meteo, "Open-Meteo")
    reject_duplicate_keys(firms, "FIRMS")
    target = firms[KEY + TARGET_COLUMNS]
    integrated = meteo.merge(target, on=KEY, how="left", validate="one_to_one")
    if len(integrated) != len(meteo):
        raise AssertionError("El LEFT JOIN multiplicó o eliminó filas meteorológicas.")
    integrated["target_firms_disponible"] = integrated["cantidad_detecciones"].notna()
    integrated["cantidad_detecciones"] = integrated["cantidad_detecciones"].astype("Int64")
    integrated["nivel_actividad_firms_codigo"] = integrated[
        "nivel_actividad_firms_codigo"
    ].astype("Int8")
    return integrated.sort_values(KEY).reset_index(drop=True)


def reconcile_target(firms: pd.DataFrame, integrated: pd.DataFrame) -> pd.DataFrame:
    available = integrated.loc[integrated.target_firms_disponible, KEY + TARGET_COLUMNS]
    compared = firms[KEY + TARGET_COLUMNS].merge(
        available, on=KEY, how="outer", suffixes=("_antes", "_despues"),
        indicator=True, validate="one_to_one",
    )
    count_equal = compared["cantidad_detecciones_antes"].eq(
        compared["cantidad_detecciones_despues"]
    )
    label_equal = compared["nivel_actividad_firms_antes"].astype("string").eq(
        compared["nivel_actividad_firms_despues"].astype("string")
    )
    code_equal = compared["nivel_actividad_firms_codigo_antes"].eq(
        compared["nivel_actividad_firms_codigo_despues"]
    )
    rows = [{
        "control": "total",
        "valor_antes": len(firms),
        "valor_despues": len(available),
        "coincide": len(firms) == len(available),
    }, {
        "control": "suma_cantidad_detecciones",
        "valor_antes": int(firms.cantidad_detecciones.sum()),
        "valor_despues": int(available.cantidad_detecciones.sum()),
        "coincide": int(firms.cantidad_detecciones.sum()) == int(available.cantidad_detecciones.sum()),
    }]
    before_distribution = class_distribution(firms)
    after_distribution = class_distribution(available)
    for label in CLASS_ORDER:
        rows.append({
            "control": f"clase_{label}",
            "valor_antes": before_distribution[label],
            "valor_despues": after_distribution[label],
            "coincide": before_distribution[label] == after_distribution[label],
        })
    rows.append({
        "control": "claves_y_valores_sin_cambios",
        "valor_antes": len(firms),
        "valor_despues": int((compared._merge.eq("both") & count_equal & label_equal & code_equal).sum()),
        "coincide": bool(
            compared._merge.eq("both").all()
            and count_equal.all() and label_equal.all() and code_equal.all()
        ),
    })
    result = pd.DataFrame(rows)
    if not result["coincide"].all():
        raise AssertionError("El target no reconcilia después de la integración.")
    return result


def validate_weekly_sequence(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for department, group in frame.sort_values(KEY).groupby("departamento"):
        differences = group.fecha_inicio_semana.diff().dropna().dt.days
        rows.append({
            "departamento": department,
            "semanas": int(len(group)),
            "saltos_distintos_de_7_dias": int(differences.ne(7).sum()),
            "diferencia_min_dias": int(differences.min()),
            "diferencia_max_dias": int(differences.max()),
        })
    result = pd.DataFrame(rows)
    if result["saltos_distintos_de_7_dias"].sum():
        raise AssertionError("La secuencia integrada contiene saltos semanales.")
    return result


def null_summary(integrated: pd.DataFrame, meteo_columns: list[str]) -> pd.DataFrame:
    rows = []
    for column in integrated.columns:
        missing_available = int(integrated.loc[integrated.target_firms_disponible, column].isna().sum())
        missing_unavailable = int(integrated.loc[~integrated.target_firms_disponible, column].isna().sum())
        is_target = column in TARGET_COLUMNS
        rows.append({
            "columna": column,
            "rol": "target" if is_target else ("meteorologia" if column in meteo_columns else "identificador_control"),
            "nulos_target_disponible": missing_available,
            "nulos_target_no_disponible": missing_unavailable,
            "nulos_totales": missing_available + missing_unavailable,
            "nulos_esperados": missing_unavailable if is_target else 0,
            "nulos_no_esperados": missing_available + (0 if is_target else missing_unavailable),
        })
    result = pd.DataFrame(rows)
    if result["nulos_no_esperados"].sum():
        raise AssertionError("La integración contiene nulos no esperados.")
    return result


def main() -> None:
    args = parse_args()
    firms = prepare_dates(pd.read_parquet(args.firms))
    meteo = prepare_dates(pd.read_parquet(args.meteo))
    firms_validation = validate_firms(firms)
    meteo_validation = validate_meteo(meteo)
    departments = compare_departments(firms, meteo)
    first_week = audit_first_firms_week(args.raw_firms, firms)
    if first_week["clasificacion"] != "A. Semana completa defendible":
        raise AssertionError("La primera semana FIRMS no quedó defendida; revisar antes de integrar.")

    firms_without_meteo = anti_join(firms[KEY + TARGET_COLUMNS], meteo)
    meteo_without_firms = anti_join(meteo, firms)
    integrated = integrate_history(meteo, firms)
    available = integrated.loc[integrated.target_firms_disponible].copy()
    reconciliation = reconcile_target(firms, integrated)
    sequence = validate_weekly_sequence(integrated)
    meteo_columns = meteorological_columns(meteo)
    nulls = null_summary(integrated, meteo_columns)

    if len(firms_without_meteo):
        raise AssertionError("Existen claves FIRMS sin meteorología; integración no aprobada.")
    coverage = 100 * len(available) / len(firms)
    if not np.isclose(coverage, 100):
        raise AssertionError("La cobertura meteorológica del target no es 100%.")

    first_firms_week = firms.fecha_inicio_semana.min()
    prior = meteo.loc[meteo.fecha_inicio_semana.lt(first_firms_week)]
    prior_weeks = int(prior.fecha_inicio_semana.nunique())
    lags = {str(lag): prior_weeks >= lag for lag in [1, 2, 4, 52]}

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    history_path = args.output_dir / "open_meteo_firms_weekly_history.parquet"
    available_path = args.output_dir / "open_meteo_firms_weekly_target_available.parquet"
    integrated.to_parquet(history_path, index=False)
    available.to_parquet(available_path, index=False)

    firms_without_meteo.to_csv(args.audit_dir / "firms_sin_open_meteo.csv", index=False)
    meteo_without_firms.to_csv(args.audit_dir / "open_meteo_sin_firms.csv", index=False)
    reconciliation.to_csv(args.audit_dir / "reconciliacion_target.csv", index=False)
    nulls.to_csv(args.audit_dir / "nulos_integracion.csv", index=False)
    departments.to_csv(args.audit_dir / "comparacion_departamentos.csv", index=False)
    sequence.to_csv(args.audit_dir / "secuencia_semanal_por_departamento.csv", index=False)

    by_department = integrated.groupby("departamento", as_index=False).agg(
        filas=("fecha_inicio_semana", "size"),
        semanas=("fecha_inicio_semana", "nunique"),
        target_disponible=("target_firms_disponible", "sum"),
    )
    by_department["target_no_disponible"] = by_department.filas - by_department.target_disponible
    by_department["cobertura_target_pct"] = 100 * by_department.target_disponible / by_department.filas
    by_department.to_csv(args.audit_dir / "cobertura_por_departamento.csv", index=False)

    by_year = integrated.groupby("anio", as_index=False).agg(
        filas=("fecha_inicio_semana", "size"),
        semanas=("fecha_inicio_semana", "nunique"),
        target_disponible=("target_firms_disponible", "sum"),
    )
    by_year["target_no_disponible"] = by_year.filas - by_year.target_disponible
    by_year["cobertura_target_pct"] = 100 * by_year.target_disponible / by_year.filas
    by_year.to_csv(args.audit_dir / "cobertura_por_anio.csv", index=False)

    (args.audit_dir / "auditoria_primera_semana_firms.json").write_text(
        json.dumps(first_week, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    unexpected_nulls = int(nulls.nulos_no_esperados.sum())
    expected_nulls = int(nulls.nulos_esperados.sum())
    summary = {
        "proceso": "integracion_historica_firms_open_meteo_semanal",
        "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {"firms": str(args.firms), "open_meteo": str(args.meteo), "firms_regional": str(args.raw_firms)},
        "clave": KEY,
        "auditoria_primera_semana": first_week["clasificacion"],
        "validacion_previa_firms": firms_validation,
        "validacion_previa_open_meteo": meteo_validation,
        "salida_historica": str(history_path),
        "salida_target_disponible": str(available_path),
        "filas_integradas": int(len(integrated)),
        "columnas_integradas": int(integrated.shape[1]),
        "filas_target_disponible": int(integrated.target_firms_disponible.sum()),
        "filas_meteorologicas_sin_target": int((~integrated.target_firms_disponible).sum()),
        "firms_sin_open_meteo": int(len(firms_without_meteo)),
        "open_meteo_sin_firms": int(len(meteo_without_firms)),
        "cobertura_meteorologica_target_pct": float(coverage),
        "duplicados_clave_salida": int(integrated.duplicated(KEY).sum()),
        "nulos_esperados_target": expected_nulls,
        "nulos_no_esperados": unexpected_nulls,
        "reconciliacion_target_aprobada": bool(reconciliation.coincide.all()),
        "semanas_meteorologicas_previas": prior_weeks,
        "periodo_meteorologico_previo": [
            prior.fecha_inicio_semana.min().date().isoformat(),
            prior.fecha_inicio_semana.max().date().isoformat(),
        ],
        "antecedentes_suficientes_para_lag_semanas": lags,
        "secuencia_semanal_aprobada": bool(sequence.saltos_distintos_de_7_dias.eq(0).all()),
        "resultado": "integracion aprobada con limitacion documental sobre la descarga FIRMS original",
        "advertencia_fuga": (
            "La meteorología corresponde a semana t y no integra aún X predictivo. Tampoco pueden "
            "usarse como X cantidad_detecciones, variables FIRMS de t ni el target."
        ),
    }
    (args.audit_dir / "resumen_general.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    recommendations = """# Recomendaciones de la integración FIRMS + Open-Meteo

## Resultado

Integración aprobada con una limitación documental: el Parquet regional demuestra
cobertura desde el 01/01/2018, pero el repositorio no contiene el script ni el
comprobante de la descarga FIRMS original.

Las filas Open-Meteo anteriores a FIRMS conservan el target nulo. Esos nulos
significan **target no disponible**, no `Sin detección`.

## Columnas que NO pueden utilizarse directamente como X predictivo

- meteorología de la misma semana `t`;
- `cantidad_detecciones` de `t`;
- cualquier variable construida con FIRMS de `t`;
- `nivel_actividad_firms` y su código ordinal.

El futuro dataset predictivo deberá usar exclusivamente información cerrada antes
del inicio de la semana objetivo. Esta tarea no crea lags, ventanas, particiones ni
modelos.
"""
    (args.audit_dir / "recomendaciones.md").write_text(recommendations, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
