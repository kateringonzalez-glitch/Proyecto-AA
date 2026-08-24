#!/usr/bin/env python3
"""Genera el catálogo espacial reproducible; no realiza llamadas de red."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/open_meteo.json"))
    return parser.parse_args()


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {"endpoint", "model", "start_date", "end_date", "daily_variables",
                "units", "timezone", "spatial_design", "batching", "paths"}
    missing = sorted(required.difference(config))
    if missing:
        raise ValueError(f"Configuración incompleta: {missing}")
    return config


def grid_axis(lower: float, upper: float, spacing: int, anchor: int) -> range:
    first = math.ceil((lower - anchor) / spacing) * spacing + anchor
    last = math.floor((upper - anchor) / spacing) * spacing + anchor
    return range(int(first), int(last) + 1, spacing)


def coordinate_id(iso_code: str, method: str, easting: float, northing: float) -> str:
    suffix = iso_code.replace("UY-", "")
    marker = "G" if method == "regular_grid_25km" else "R"
    return f"URY_{suffix}_{marker}_E{round(easting):06d}_N{round(northing):07d}"


def generate_catalog(boundaries: gpd.GeoDataFrame, config: dict) -> gpd.GeoDataFrame:
    design = config["spatial_design"]
    metric = boundaries.to_crs(design["generation_crs"])
    spacing = int(design["grid_spacing_m"])
    anchor_x = int(design["grid_anchor_easting_m"])
    anchor_y = int(design["grid_anchor_northing_m"])
    rows = []
    for _, department in metric.sort_values("shapeISO").iterrows():
        minx, miny, maxx, maxy = department.geometry.bounds
        points = [
            Point(x, y)
            for x in grid_axis(minx, maxx, spacing, anchor_x)
            for y in grid_axis(miny, maxy, spacing, anchor_y)
            if department.geometry.contains(Point(x, y))
        ]
        method = "regular_grid_25km"
        if not points:
            points = [department.geometry.representative_point()]
            method = "representative_point_fallback"
        for point in points:
            rows.append({
                "coordenada_id": coordinate_id(department["shapeISO"], method, point.x, point.y),
                "departamento": department["shapeName"],
                "departamento_iso": department["shapeISO"],
                "metodo_seleccion": method,
                "crs_generacion": design["generation_crs"],
                "separacion_grilla_m": spacing if method == "regular_grid_25km" else pd.NA,
                "easting_m": point.x,
                "northing_m": point.y,
                "fuente_limite": design["boundary_source"],
                "geometry": point,
            })
    catalog = gpd.GeoDataFrame(rows, geometry="geometry", crs=design["generation_crs"])
    catalog = catalog.to_crs(design["output_crs"])
    catalog["latitud"] = catalog.geometry.y.round(6)
    catalog["longitud"] = catalog.geometry.x.round(6)
    catalog = gpd.GeoDataFrame(
        catalog.drop(columns="geometry"),
        geometry=gpd.points_from_xy(catalog["longitud"], catalog["latitud"]),
        crs=design["output_crs"],
    )
    catalog = catalog.sort_values("coordenada_id").reset_index(drop=True)
    if catalog["coordenada_id"].duplicated().any():
        raise AssertionError("Se generaron identificadores duplicados.")
    if catalog["departamento"].nunique() != 19:
        raise AssertionError("El catálogo no representa los 19 departamentos.")
    return catalog


def validate_catalog(catalog: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame) -> None:
    lookup = boundaries.to_crs(catalog.crs).set_index("shapeISO")["geometry"]
    inside = catalog.apply(
        lambda row: lookup.loc[row["departamento_iso"]].contains(row.geometry), axis=1
    )
    if not inside.all():
        raise AssertionError("Alguna coordenada no está estrictamente dentro de su departamento.")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    boundaries = gpd.read_file(config["spatial_design"]["boundary_file"])
    catalog = generate_catalog(boundaries, config)
    validate_catalog(catalog, boundaries)
    output = Path(config["paths"]["coordinate_catalog"])
    output.parent.mkdir(parents=True, exist_ok=True)
    catalog.drop(columns="geometry").to_csv(output, index=False)
    summary = catalog.groupby(["departamento", "departamento_iso"], as_index=False).agg(
        cantidad_coordenadas=("coordenada_id", "size"),
        puntos_grilla=("metodo_seleccion", lambda x: x.eq("regular_grid_25km").sum()),
        puntos_fallback=("metodo_seleccion", lambda x: x.eq("representative_point_fallback").sum()),
    )
    audit_dir = Path(config["paths"]["audit_directory"])
    audit_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(audit_dir / "coordenadas_por_departamento.csv", index=False)
    result = {
        "catalogo": str(output), "coordenadas": len(catalog),
        "departamentos": catalog["departamento"].nunique(),
        "separacion_grilla_m": config["spatial_design"]["grid_spacing_m"],
        "fallbacks": int(catalog["metodo_seleccion"].eq("representative_point_fallback").sum()),
    }
    (audit_dir / "resumen_diseno_espacial.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
