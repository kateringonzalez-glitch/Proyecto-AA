# Reproducción del catálogo espacial Open-Meteo

El catálogo operativo es `data/reference/open_meteo_coordinates_validated.csv` y contiene 187 coordenadas distribuidas entre los 19 departamentos.

## Secuencia que produjo el catálogo

1. `src/design_open_meteo_extraction.py` genera la grilla regular inicial de 25 km dentro de geoBoundaries ADM1 y el respaldo mediante punto representativo. El catálogo inicial conservado es `data/reference/open_meteo_coordinates.csv`.
2. `src/run_open_meteo_pilot.py` y `config/open_meteo_pilot.json` validan muestras temporales y la respuesta real del servicio.
3. `src/compare_open_meteo_cell_selection.py` compara `cell_selection=land` y `nearest`. Los resultados están en `results/open_meteo_cell_selection_ab/`.
4. `src/redesign_open_meteo_spatial_grid.py` calcula la distancia de cada punto al límite del departamento, conserva una margen interior de 7.500 m y agrega un punto representativo cuando un departamento queda sin punto. Produce `data/reference/open_meteo_coordinates_candidate.csv`.
5. `src/audit_open_meteo_spatial_catalog.py` contrasta las celdas reportadas por la API con los límites. Los resultados están en `results/open_meteo_spatial_redesign/`.
6. El catálogo aprobado se conserva como `data/reference/open_meteo_coordinates_validated.csv`: 187/187 celdas verificadas dentro del departamento solicitado en la fecha de control 06/08/2018.
7. `config/open_meteo.json` apunta al catálogo validado y `src/extract_open_meteo.py` lo consume sin regenerarlo.

## Advertencia de reproducción

No debe ejecutarse `design_open_meteo_extraction.py` directamente contra la ruta del catálogo validado: ese script implementa la grilla inicial, mientras que la estrategia final incluye filtrado por margen y validación posterior. La secuencia aún no está encapsulada en un único comando idempotente. Por ese motivo, esta limpieza no regeneró ni sobrescribió ninguno de los tres catálogos.
