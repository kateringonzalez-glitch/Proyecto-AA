#!/usr/bin/env python3
"""Agrega Open-Meteo departamento-día a semanas completas lunes-domingo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .build_open_meteo_department_daily import circular_statistics_degrees
except ImportError:
    from build_open_meteo_department_daily import circular_statistics_degrees


INPUT = Path("data/processed/open_meteo_department_daily/open_meteo_department_daily_2017_2025.parquet")
FIRMS = Path("results/data/firms_departamento_semana_clean.parquet")
OUTPUT = Path("data/processed/open_meteo_department_weekly/open_meteo_department_weekly_2017_2025.parquet")
AUDIT = Path("results/open_meteo_department_weekly_audit")
DAILY_KEY = ["departamento", "fecha"]
WEEKLY_KEY = ["departamento", "fecha_inicio_semana"]
WEEKLY_AGGREGATIONS = {
    "temperature_2m_max_mean_weekly": ("temperature_2m_max_mean_spatial", "mean"),
    "temperature_2m_max_weekly": ("temperature_2m_max_max_spatial", "max"),
    "temperature_2m_min_mean_weekly": ("temperature_2m_min_mean_spatial", "mean"),
    "temperature_2m_min_weekly": ("temperature_2m_min_min_spatial", "min"),
    "relative_humidity_2m_min_mean_weekly": ("relative_humidity_2m_min_mean_spatial", "mean"),
    "relative_humidity_2m_min_weekly": ("relative_humidity_2m_min_min_spatial", "min"),
    "relative_humidity_2m_max_mean_weekly": ("relative_humidity_2m_max_mean_spatial", "mean"),
    "relative_humidity_2m_max_weekly": ("relative_humidity_2m_max_max_spatial", "max"),
    "wind_speed_10m_max_mean_weekly": ("wind_speed_10m_max_mean_spatial", "mean"),
    "wind_speed_10m_max_weekly": ("wind_speed_10m_max_max_spatial", "max"),
    "precipitation_sum_weekly": ("precipitation_sum_mean_spatial", "sum"),
    "precipitation_max_daily_weekly": ("precipitation_sum_mean_spatial", "max"),
    "et0_fao_evapotranspiration_sum_weekly": ("et0_fao_evapotranspiration_mean_spatial", "sum"),
    "et0_fao_evapotranspiration_max_daily_weekly": ("et0_fao_evapotranspiration_max_spatial", "max"),
    "wind_direction_10m_resultant_length_spatial_daily_mean_weekly": ("wind_direction_10m_resultant_length", "mean"),
    "cobertura_espacial_min_pct": ("cobertura_espacial_pct", "min"),
}


def assign_weeks(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(); result["fecha"] = pd.to_datetime(result.fecha, errors="raise")
    result["fecha_inicio_semana"] = result.fecha - pd.to_timedelta(result.fecha.dt.weekday, unit="D")
    result["fecha_fin_semana"] = result.fecha_inicio_semana + pd.Timedelta(days=6)
    return result


def firms_week_number(starts: pd.Series) -> pd.Series:
    starts = pd.to_datetime(starts)
    first_days = pd.to_datetime(starts.dt.year.astype(str) + "-01-01")
    first_mondays = first_days + pd.to_timedelta((7 - first_days.dt.weekday) % 7, unit="D")
    return ((starts - first_mondays).dt.days // 7 + 1).astype(int)


def validate_input(frame: pd.DataFrame) -> None:
    frame = frame.copy(); frame["fecha"] = pd.to_datetime(frame.fecha, errors="raise")
    if (len(frame) != 62434 or frame.departamento.nunique() != 19 or frame.fecha.nunique() != 3286
            or frame.duplicated(DAILY_KEY).any() or frame.isna().any().any()
            or frame.fecha.min() != pd.Timestamp("2017-01-02") or frame.fecha.max() != pd.Timestamp("2025-12-31")):
        raise AssertionError("El dataset departamento-día no cumple las precondiciones aprobadas.")
    ranges = frame.groupby("departamento").fecha.agg(["min", "max", "nunique"])
    if not (ranges["min"].eq(frame.fecha.min()).all() and ranges["max"].eq(frame.fecha.max()).all()
            and ranges["nunique"].eq(3286).all()):
        raise AssertionError("Los departamentos no comparten cobertura diaria completa.")


def incomplete_weeks(assigned: pd.DataFrame) -> pd.DataFrame:
    return assigned.groupby(WEEKLY_KEY, as_index=False).agg(
        departamento_iso=("departamento_iso", "first"), fecha_fin_semana=("fecha_fin_semana", "first"),
        fecha_min_observada=("fecha", "min"), fecha_max_observada=("fecha", "max"),
        n_dias_observados=("fecha", "nunique")
    ).query("n_dias_observados != 7").sort_values(WEEKLY_KEY).reset_index(drop=True)


def aggregate_complete_weeks(assigned: pd.DataFrame) -> pd.DataFrame:
    named = {output: pd.NamedAgg(column=source, aggfunc=operation)
             for output, (source, operation) in WEEKLY_AGGREGATIONS.items()}
    grouped = assigned.groupby(WEEKLY_KEY, sort=True, observed=True)
    weekly = grouped.agg(
        departamento_iso=pd.NamedAgg(column="departamento_iso", aggfunc="first"),
        fecha_fin_semana=pd.NamedAgg(column="fecha_fin_semana", aggfunc="first"),
        n_dias_observados=pd.NamedAgg(column="fecha", aggfunc="nunique"),
        precipitation_days_weekly=pd.NamedAgg(column="precipitation_sum_mean_spatial", aggfunc=lambda s: int(s.gt(0).sum())),
        **named,
    ).reset_index()
    circular = grouped.wind_direction_10m_dominant_circular_mean.apply(
        lambda values: pd.Series(circular_statistics_degrees(values), index=[
            "wind_direction_10m_dominant_circular_mean_weekly", "wind_direction_10m_resultant_length_weekly"
        ])
    ).unstack().reset_index()
    weekly = weekly.merge(circular, on=WEEKLY_KEY, validate="one_to_one")
    weekly["n_dias_esperados"] = 7
    weekly["cobertura_temporal_pct"] = 100 * weekly.n_dias_observados / weekly.n_dias_esperados
    weekly = weekly.loc[weekly.n_dias_observados.eq(7)].copy()
    weekly["anio"] = weekly.fecha_inicio_semana.dt.year
    weekly["numero_semana"] = firms_week_number(weekly.fecha_inicio_semana)
    ids = ["departamento", "departamento_iso", "fecha_inicio_semana", "fecha_fin_semana", "anio",
           "numero_semana", "n_dias_esperados", "n_dias_observados", "cobertura_temporal_pct",
           "cobertura_espacial_min_pct"]
    return weekly[ids + [column for column in weekly if column not in ids]].sort_values(WEEKLY_KEY).reset_index(drop=True)


def validate_output(frame: pd.DataFrame) -> dict:
    weeks = frame.fecha_inicio_semana.nunique(); expected_rows = weeks * 19
    by_department = frame.groupby("departamento").fecha_inicio_semana.nunique()
    per_week = frame.groupby("fecha_inicio_semana").departamento.nunique()
    cross_year = frame.loc[frame.fecha_inicio_semana.dt.year.ne(frame.fecha_fin_semana.dt.year)]
    checks = {
        "complete_weeks": weeks, "expected_rows": expected_rows, "observed_rows": len(frame),
        "departments": frame.departamento.nunique(), "duplicate_keys": int(frame.duplicated(WEEKLY_KEY).sum()),
        "weeks_with_not_19_departments": int(per_week.ne(19).sum()),
        "departments_with_unequal_weeks": int(by_department.ne(weeks).sum()),
        "rows_with_not_7_days": int(frame.n_dias_observados.ne(7).sum()),
        "coverage_temporal_problems": int((~np.isclose(frame.cobertura_temporal_pct, 100)).sum()),
        "coverage_spatial_problems": int((~np.isclose(frame.cobertura_espacial_min_pct, 100)).sum()),
        "start_not_monday": int(frame.fecha_inicio_semana.dt.weekday.ne(0).sum()),
        "end_not_sunday": int(frame.fecha_fin_semana.dt.weekday.ne(6).sum()),
        "wrong_duration": int((frame.fecha_fin_semana-frame.fecha_inicio_semana).dt.days.ne(6).sum()),
        "nulls": int(frame.isna().sum().sum()), "cross_year_rows": len(cross_year),
        "cross_year_unique_weeks": cross_year.fecha_inicio_semana.nunique(),
        "temperature_order_problems": int((frame.temperature_2m_min_weekly > frame.temperature_2m_max_weekly).sum()),
        "humidity_range_problems": int((~frame[["relative_humidity_2m_min_mean_weekly",
            "relative_humidity_2m_min_weekly", "relative_humidity_2m_max_mean_weekly",
            "relative_humidity_2m_max_weekly"]].apply(lambda s: s.between(0,100)).all(axis=1)).sum()),
        "negative_precipitation": int(frame.precipitation_sum_weekly.lt(0).sum()),
        "negative_et0": int(frame.et0_fao_evapotranspiration_sum_weekly.lt(0).sum()),
        "negative_wind": int(frame.wind_speed_10m_max_mean_weekly.lt(0).sum()),
        "direction_range_problems": int((frame.wind_direction_10m_dominant_circular_mean_weekly.notna()
            & ~frame.wind_direction_10m_dominant_circular_mean_weekly.between(0,360,inclusive="left")).sum()),
        "resultant_range_problems": int((~frame.wind_direction_10m_resultant_length_weekly.between(0,1)).sum()),
    }
    problem_keys = [key for key in checks if key.endswith("problems") or key in {"duplicate_keys", "nulls",
        "weeks_with_not_19_departments", "departments_with_unequal_weeks", "rows_with_not_7_days",
        "start_not_monday", "end_not_sunday", "wrong_duration"}]
    if weeks != 469 or len(frame) != expected_rows or checks["departments"] != 19 or any(checks[k] for k in problem_keys):
        raise AssertionError(f"Validación semanal fallida: {checks}")
    return checks


def reconcile_samples(daily: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    departments = sorted(daily.departamento.unique()); chosen_departments = sorted(set([departments[0], departments[-1], "Montevideo"]))
    weeks = sorted(weekly.fecha_inicio_semana.unique()); chosen_weeks = [weeks[0], weeks[len(weeks)//2], weeks[-1]]
    operations = {
        "precipitation_sum_weekly": ("precipitation_sum_mean_spatial", "sum"),
        "temperature_2m_max_mean_weekly": ("temperature_2m_max_mean_spatial", "mean"),
        "temperature_2m_max_weekly": ("temperature_2m_max_max_spatial", "max"),
        "et0_fao_evapotranspiration_sum_weekly": ("et0_fao_evapotranspiration_mean_spatial", "sum"),
    }
    assigned = assign_weeks(daily); rows=[]
    for department in chosen_departments:
        for start in chosen_weeks:
            source=assigned.loc[assigned.departamento.eq(department)&assigned.fecha_inicio_semana.eq(start)]
            target=weekly.loc[weekly.departamento.eq(department)&weekly.fecha_inicio_semana.eq(start)].iloc[0]
            for output,(column,operation) in operations.items():
                expected=getattr(source[column],operation)(); observed=target[output]
                rows.append({"departamento":department,"fecha_inicio_semana":start,"variable":output,
                    "recalculado_desde_diario":expected,"valor_semanal":observed,
                    "diferencia_absoluta":abs(expected-observed),"coincide":bool(np.isclose(expected,observed))})
            expected,_=circular_statistics_degrees(source.wind_direction_10m_dominant_circular_mean)
            observed=target.wind_direction_10m_dominant_circular_mean_weekly
            rows.append({"departamento":department,"fecha_inicio_semana":start,
                "variable":"wind_direction_10m_dominant_circular_mean_weekly",
                "recalculado_desde_diario":expected,"valor_semanal":observed,
                "diferencia_absoluta":abs(expected-observed),"coincide":bool(np.isclose(expected,observed))})
    return pd.DataFrame(rows)


def firms_compatibility(weekly: pd.DataFrame, firms: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    firms_keys=firms[WEEKLY_KEY].drop_duplicates(); meteo_keys=weekly[WEEKLY_KEY].drop_duplicates()
    merged=firms_keys.merge(meteo_keys,on=WEEKLY_KEY,how="left",indicator=True)
    missing=merged.loc[merged._merge.ne("both"),WEEKLY_KEY].copy()
    summary=pd.DataFrame([{"claves_firms":len(firms_keys),"claves_open_meteo":len(meteo_keys),
        "claves_firms_encontradas":int(merged._merge.eq("both").sum()),"claves_firms_sin_meteorologia":len(missing),
        "porcentaje_cobertura_potencial":100*merged._merge.eq("both").mean()}])
    return summary,missing


def descriptive_quality(frame: pd.DataFrame) -> pd.DataFrame:
    excluded=set(WEEKLY_KEY+["departamento_iso","fecha_fin_semana","anio","numero_semana","n_dias_esperados",
        "n_dias_observados","cobertura_temporal_pct","cobertura_espacial_min_pct"])
    return pd.DataFrame([{"variable":c,"min":frame[c].min(),"p01":frame[c].quantile(.01),"p05":frame[c].quantile(.05),
        "media":frame[c].mean(),"mediana":frame[c].median(),"desviacion_estandar":frame[c].std(),
        "p95":frame[c].quantile(.95),"p99":frame[c].quantile(.99),"max":frame[c].max(),"nulos":frame[c].isna().sum()}
        for c in frame.columns if c not in excluded])


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--input",type=Path,default=INPUT)
    parser.add_argument("--firms",type=Path,default=FIRMS); parser.add_argument("--output",type=Path,default=OUTPUT)
    parser.add_argument("--audit-dir",type=Path,default=AUDIT); args=parser.parse_args()
    daily=pd.read_parquet(args.input); daily["fecha"]=pd.to_datetime(daily.fecha); validate_input(daily)
    assigned=assign_weeks(daily); incomplete=incomplete_weeks(assigned); weekly=aggregate_complete_weeks(assigned)
    checks=validate_output(weekly); args.output.parent.mkdir(parents=True,exist_ok=True); weekly.to_parquet(args.output,index=False)
    args.audit_dir.mkdir(parents=True,exist_ok=True); incomplete.to_csv(args.audit_dir/"semanas_incompletas_excluidas.csv",index=False)
    problems=weekly.loc[weekly.n_dias_observados.ne(7)|~np.isclose(weekly.cobertura_temporal_pct,100)]
    problems.to_csv(args.audit_dir/"problemas_cobertura.csv",index=False)
    reconciliation=reconcile_samples(daily,weekly); reconciliation.to_csv(args.audit_dir/"reconciliacion_muestras.csv",index=False)
    descriptive_quality(weekly).to_csv(args.audit_dir/"calidad_variables_semanales.csv",index=False)
    main_vars=["temperature_2m_max_mean_weekly","temperature_2m_min_mean_weekly","wind_speed_10m_max_mean_weekly",
               "precipitation_sum_weekly","et0_fao_evapotranspiration_sum_weekly"]
    dept=weekly.groupby("departamento").agg(semanas=("fecha_inicio_semana","nunique"),fecha_min=("fecha_inicio_semana","min"),
        fecha_max=("fecha_inicio_semana","max"),cobertura_min_pct=("cobertura_temporal_pct","min")).reset_index()
    dept["nulos"]=dept.departamento.map(weekly.groupby("departamento")[main_vars].apply(lambda x:x.isna().sum().sum()))
    for v in main_vars:
        dept[v+"_min"]=dept.departamento.map(weekly.groupby("departamento")[v].min()); dept[v+"_max"]=dept.departamento.map(weekly.groupby("departamento")[v].max())
    dept.to_csv(args.audit_dir/"cobertura_por_departamento.csv",index=False)
    firms=pd.read_parquet(args.firms); firms["fecha_inicio_semana"]=pd.to_datetime(firms.fecha_inicio_semana)
    compatibility,missing=firms_compatibility(weekly,firms); compatibility.to_csv(args.audit_dir/"compatibilidad_claves_firms.csv",index=False)
    missing.to_csv(args.audit_dir/"claves_firms_sin_meteorologia.csv",index=False)
    summary={"input":str(args.input),"firms_keys_source":str(args.firms),"output":str(args.output),
        "output_validation":checks,"incomplete_department_weeks_excluded":len(incomplete),
        "incomplete_unique_weeks":incomplete.fecha_inicio_semana.nunique(),"reconciliation_rows":len(reconciliation),
        "reconciliation_failures":int((~reconciliation.coincide).sum()),"firms_compatibility":compatibility.iloc[0].to_dict()}
    (args.audit_dir/"resumen_general.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str)+"\n")
    print(json.dumps(summary,ensure_ascii=False,indent=2,default=str))


if __name__=="__main__": main()
