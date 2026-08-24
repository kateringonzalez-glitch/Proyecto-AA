#!/usr/bin/env python3
"""Construye un panel FIRMS departamento-semana para Uruguay.

Las detecciones FIRMS son anomalías térmicas/focos de calor y no incendios
forestales confirmados. El script no modifica los insumos originales.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd


REQUIRED_FIRMS = {
    "fecha_adq", "latitud", "longitud", "pais", "pais_codigo",
}
REQUIRED_BOUNDARIES = {"shapeName", "shapeISO", "shapeID", "geometry"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firms", type=Path, default=Path("data/firms_2018_2025.parquet"))
    parser.add_argument(
        "--boundaries", type=Path,
        default=Path("geoBoundaries-URY-ADM1-all/geoBoundaries-URY-ADM1.geojson"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/data"))
    return parser.parse_args()


def require_columns(columns: pd.Index, required: set[str], source: Path) -> None:
    missing = sorted(required.difference(columns))
    if missing:
        raise ValueError(f"Faltan columnas en {source}: {missing}")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    firms = pd.read_parquet(args.firms)
    require_columns(firms.columns, REQUIRED_FIRMS, args.firms)
    boundaries = gpd.read_file(args.boundaries)
    require_columns(boundaries.columns, REQUIRED_BOUNDARIES, args.boundaries)
    if boundaries.crs is None:
        raise ValueError("La capa administrativa no declara un CRS.")
    boundaries = boundaries.to_crs("EPSG:4326")
    if len(boundaries) != 19 or boundaries["shapeName"].nunique() != 19:
        raise ValueError("La capa no contiene exactamente los 19 departamentos esperados.")

    uruguay = firms.loc[firms["pais"].eq("URY")].copy()
    uruguay["fecha"] = pd.to_datetime(uruguay["fecha_adq"], errors="coerce")
    valid_core = (
        uruguay["fecha"].notna()
        & uruguay["latitud"].notna()
        & uruguay["longitud"].notna()
    )
    candidates = uruguay.loc[valid_core].copy()
    points = gpd.GeoDataFrame(
        candidates,
        geometry=gpd.points_from_xy(candidates["longitud"], candidates["latitud"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(
        points,
        boundaries[["shapeName", "shapeISO", "shapeID", "geometry"]],
        how="left",
        predicate="within",
    ).rename(columns={"shapeName": "departamento", "shapeISO": "departamento_iso"})
    if joined.index.duplicated().any():
        raise ValueError("La unión espacial produjo más de un departamento para algún punto.")

    unassigned = joined.loc[joined["departamento"].isna()].copy()
    unassigned.drop(columns=["geometry", "index_right"], errors="ignore").to_csv(
        args.output_dir / "firms_uruguay_sin_departamento.csv", index=False
    )
    assigned = joined.loc[joined["departamento"].notna()].copy()
    assigned.drop(columns=["geometry", "index_right"], errors="ignore").to_parquet(
        args.output_dir / "firms_uruguay_asignadas.parquet", index=False
    )

    # Semana calendario con inicio lunes. La fecha de inicio es la clave temporal.
    assigned["fecha_inicio_semana"] = (
        assigned["fecha"] - pd.to_timedelta(assigned["fecha"].dt.weekday, unit="D")
    ).dt.normalize()
    counts = (
        assigned.groupby(["departamento", "departamento_iso", "fecha_inicio_semana"])
        .size().rename("cantidad_detecciones").reset_index()
    )

    first_date = candidates["fecha"].min().normalize()
    last_date = candidates["fecha"].max().normalize()
    first_monday = first_date - pd.Timedelta(days=first_date.weekday())
    last_monday = last_date - pd.Timedelta(days=last_date.weekday())
    weeks = pd.date_range(first_monday, last_monday, freq="W-MON")
    departments = boundaries[["shapeName", "shapeISO"]].rename(
        columns={"shapeName": "departamento", "shapeISO": "departamento_iso"}
    )
    grid = departments.merge(
        pd.DataFrame({"fecha_inicio_semana": weeks}), how="cross"
    )
    panel = grid.merge(
        counts,
        on=["departamento", "departamento_iso", "fecha_inicio_semana"],
        how="left",
        validate="one_to_one",
    )
    panel["cantidad_detecciones"] = panel["cantidad_detecciones"].fillna(0).astype("int64")
    panel["fecha_fin_semana"] = panel["fecha_inicio_semana"] + pd.Timedelta(days=6)
    panel["anio"] = panel["fecha_inicio_semana"].dt.year.astype("int64")
    first_monday_by_year = pd.to_datetime(panel["anio"].astype(str) + "-01-01")
    first_monday_by_year += pd.to_timedelta(
        (7 - first_monday_by_year.dt.weekday) % 7, unit="D"
    )
    panel["numero_semana"] = (
        ((panel["fecha_inicio_semana"] - first_monday_by_year).dt.days // 7) + 1
    ).astype("int64")

    # EPSG:32721 (UTM 21S) permite un cálculo métrico consistente para Uruguay.
    areas = boundaries.to_crs("EPSG:32721").copy()
    areas["superficie_km2"] = areas.geometry.area / 1_000_000
    area_table = areas[["shapeName", "shapeISO", "shapeID", "superficie_km2"]].rename(
        columns={"shapeName": "departamento", "shapeISO": "departamento_iso"}
    )
    panel = panel.merge(
        area_table[["departamento_iso", "superficie_km2"]],
        on="departamento_iso", how="left", validate="many_to_one",
    )
    panel["detecciones_por_1000_km2"] = (
        panel["cantidad_detecciones"] / panel["superficie_km2"] * 1000
    )
    panel = panel[[
        "departamento", "departamento_iso", "anio", "numero_semana",
        "fecha_inicio_semana", "fecha_fin_semana", "cantidad_detecciones",
        "superficie_km2", "detecciones_por_1000_km2",
    ]].sort_values(["fecha_inicio_semana", "departamento"]).reset_index(drop=True)

    if len(panel) != len(departments) * len(weeks):
        raise AssertionError("El tamaño del panel no coincide con departamentos × semanas.")
    if panel["cantidad_detecciones"].sum() != len(assigned):
        raise AssertionError("Los conteos semanales no reconcilian con las detecciones asignadas.")

    panel.to_parquet(args.output_dir / "firms_departamento_semana.parquet", index=False)
    panel.to_csv(args.output_dir / "firms_departamento_semana.csv", index=False)
    area_table.sort_values("departamento").to_csv(
        args.output_dir / "superficie_departamentos_geoBoundaries.csv", index=False
    )

    audit = {
        "fuente_firms": str(args.firms),
        "fuente_limites": str(args.boundaries),
        "crs_union_espacial": "EPSG:4326",
        "predicado_union_espacial": "within",
        "crs_calculo_superficie": "EPSG:32721",
        "filas_firms_originales_regionales": int(len(firms)),
        "filas_pais_ury": int(len(uruguay)),
        "filas_excluidas_no_ury": int(len(firms) - len(uruguay)),
        "duplicados_exactos_firms_original": int(firms.duplicated().sum()),
        "duplicados_exactos_ury": int(uruguay.duplicated().sum()),
        "duplicados_clave_deteccion_ury": int(uruguay.duplicated([
            "latitud", "longitud", "fecha_adq", "hora_adq_hhmm", "satelite", "instrumento"
        ]).sum()),
        "fechas_faltantes_ury": int(uruguay["fecha_adq"].isna().sum()),
        "fechas_invalidas_ury": int(uruguay["fecha"].isna().sum()),
        "latitudes_faltantes_ury": int(uruguay["latitud"].isna().sum()),
        "longitudes_faltantes_ury": int(uruguay["longitud"].isna().sum()),
        "filas_excluidas_campos_espaciales_temporales_invalidos": int((~valid_core).sum()),
        "detecciones_asignadas_departamento": int(len(assigned)),
        "detecciones_sin_departamento": int(len(unassigned)),
        "coordenadas_fuera_poligonos_adm1": int(len(unassigned)),
        "latitud_minima_ury": float(uruguay["latitud"].min()),
        "latitud_maxima_ury": float(uruguay["latitud"].max()),
        "longitud_minima_ury": float(uruguay["longitud"].min()),
        "longitud_maxima_ury": float(uruguay["longitud"].max()),
        "detecciones_utilizadas_panel": int(len(assigned)),
        "fecha_minima_ury": first_date.date().isoformat(),
        "fecha_maxima_ury": last_date.date().isoformat(),
        "primer_inicio_semana": first_monday.date().isoformat(),
        "ultimo_inicio_semana": last_monday.date().isoformat(),
        "departamentos": int(len(departments)),
        "semanas": int(len(weeks)),
        "observaciones_panel": int(len(panel)),
        "suma_conteos_panel": int(panel["cantidad_detecciones"].sum()),
    }
    (args.output_dir / "auditoria_construccion.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
