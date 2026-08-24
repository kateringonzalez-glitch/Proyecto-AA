#!/usr/bin/env python3
"""Evalúa márgenes interiores y genera un catálogo candidato sin usar la red."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd


MARGINS_M = [0, 5000, 7500, 10000]
RECOMMENDED_MARGIN_M = 7500
GENERATION_CRS = "EPSG:32721"
BOUNDARIES = Path("geoBoundaries-URY-ADM1-all/geoBoundaries-URY-ADM1.geojson")
ORIGINAL = Path("data/reference/open_meteo_coordinates.csv")
CANDIDATE = Path("data/reference/open_meteo_coordinates_candidate.csv")
RESULTS = Path("results/open_meteo_spatial_redesign")


def points_with_boundary_distance(catalog: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    polygons = boundaries.to_crs(GENERATION_CRS).set_index("shapeName")
    points = gpd.GeoDataFrame(catalog.copy(), geometry=gpd.points_from_xy(catalog.longitud, catalog.latitud), crs=4326).to_crs(GENERATION_CRS)
    points["distancia_limite_m"] = [
        geometry.distance(polygons.loc[department].geometry.boundary)
        for geometry, department in zip(points.geometry, points.departamento)
    ]
    return points


def filter_margin(points: gpd.GeoDataFrame, margin_m: float) -> gpd.GeoDataFrame:
    return points.loc[points.distancia_limite_m >= margin_m].copy()


def stable_fallback_id(iso: str, geometry) -> str:
    return f"URY_{iso.split('-')[-1]}_F_RP_E{round(geometry.x)}_N{round(geometry.y)}"


def add_reproducible_fallbacks(filtered: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame,
                               margin_m: float, source: str) -> gpd.GeoDataFrame:
    projected = boundaries.to_crs(GENERATION_CRS)
    missing = sorted(set(projected.shapeName).difference(filtered.departamento))
    additions = []
    for department in missing:
        boundary = projected.loc[projected.shapeName.eq(department)].iloc[0]
        point = boundary.geometry.representative_point()
        additions.append({
            "coordenada_id": stable_fallback_id(boundary.shapeISO, point),
            "departamento": department, "departamento_iso": boundary.shapeISO,
            "metodo_seleccion": "representative_point_fallback", "crs_generacion": GENERATION_CRS,
            "separacion_grilla_m": None, "easting_m": point.x, "northing_m": point.y,
            "fuente_limite": source, "distancia_limite_m": point.distance(boundary.geometry.boundary),
            "margen_interior_m": margin_m, "geometry": point,
        })
    result = filtered.copy()
    result["metodo_seleccion"] = "grid"
    result["margen_interior_m"] = margin_m
    if additions:
        result = pd.concat([result, gpd.GeoDataFrame(additions, crs=GENERATION_CRS)], ignore_index=True)
    result = gpd.GeoDataFrame(result, geometry="geometry", crs=GENERATION_CRS)
    geographic = result.to_crs(4326)
    result["latitud"] = geographic.geometry.y
    result["longitud"] = geographic.geometry.x
    return result.sort_values("coordenada_id").reset_index(drop=True)


def margin_tables(points: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    departments = sorted(boundaries.shapeName.tolist())
    summary, by_department = [], pd.DataFrame({"departamento": departments})
    for margin in MARGINS_M:
        selected = filter_margin(points, margin)
        counts = selected.groupby("departamento").size().reindex(departments, fill_value=0)
        missing = counts[counts.eq(0)].index.tolist()
        summary.append({
            "margen_m": margin, "puntos_total": len(selected),
            "departamentos_con_puntos": int(counts.gt(0).sum()),
            "departamentos_sin_puntos": "|".join(missing),
            "cantidad_departamentos_sin_puntos": len(missing),
            "min_puntos_depto": int(counts.min()), "max_puntos_depto": int(counts.max()),
            "puntos_eliminados": len(points) - len(selected),
            "porcentaje_eliminado": 100 * (len(points) - len(selected)) / len(points),
        })
        by_department[f"puntos_margen_{margin}"] = by_department.departamento.map(counts)
    return pd.DataFrame(summary), by_department


def build_candidate(original_path=ORIGINAL, boundary_path=BOUNDARIES,
                    margin_m=RECOMMENDED_MARGIN_M):
    catalog = pd.read_csv(original_path)
    boundaries = gpd.read_file(boundary_path)
    points = points_with_boundary_distance(catalog, boundaries)
    source = catalog.fuente_limite.iloc[0]
    candidate = add_reproducible_fallbacks(filter_margin(points, margin_m), boundaries, margin_m, source)
    return catalog, boundaries, points, candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--margin-m", type=int, default=RECOMMENDED_MARGIN_M)
    args = parser.parse_args()
    if args.margin_m not in MARGINS_M:
        raise SystemExit(f"Margen no evaluado: {args.margin_m}. Opciones: {MARGINS_M}")
    catalog, boundaries, points, candidate = build_candidate(margin_m=args.margin_m)
    summary, by_department = margin_tables(points, boundaries)
    RESULTS.mkdir(parents=True, exist_ok=True); CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(RESULTS / "comparacion_margenes.csv", index=False)
    by_department.to_csv(RESULTS / "puntos_por_departamento_margen.csv", index=False)
    columns = ["coordenada_id", "departamento", "departamento_iso", "latitud", "longitud",
               "easting_m", "northing_m", "distancia_limite_m", "metodo_seleccion",
               "margen_interior_m", "crs_generacion", "separacion_grilla_m", "fuente_limite"]
    candidate[columns].to_csv(CANDIDATE, index=False)
    candidate[columns].to_csv(RESULTS / "catalogo_candidato.csv", index=False)
    report = {
        "margins_evaluated_m": MARGINS_M, "recommended_margin_m": args.margin_m,
        "original_points": len(catalog), "grid_points_after_margin": int((candidate.metodo_seleccion == "grid").sum()),
        "fallback_points": int((candidate.metodo_seleccion == "representative_point_fallback").sum()),
        "candidate_points": len(candidate), "departments": candidate.departamento.nunique(),
        "estimated_one_day_requests_batch_10": (len(candidate) + 9) // 10,
        "expected_one_day_rows": len(candidate),
    }
    (RESULTS / "resumen_diseno.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
