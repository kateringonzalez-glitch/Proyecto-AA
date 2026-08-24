# Diseño propuesto para la nueva extracción Open-Meteo

Estado: **diseño preparado; descarga no ejecutada**.

## Producto y período

Se propone la Historical Weather API de Open-Meteo:

- endpoint: `https://archive-api.open-meteo.com/v1/archive`;
- modelo: `era5_seamless`;
- frecuencia solicitada: diaria;
- período: 02/01/2017–31/12/2025;
- timezone: `America/Montevideo`;
- selección de celda: `land`.

El comienzo agrega exactamente 52 semanas completas anteriores al inicio del
panel FIRMS. Permite evaluar posteriormente antecedentes semanales y
estacionales de hasta un año sin truncar 2018; no obliga a utilizar ese máximo
como feature.

Open-Meteo documenta ERA5 desde 1940 a resolución 0,25° (~25 km) y ERA5-Land
desde 1950 a 0,1° (~11 km). Para disponer conjuntamente de las ocho variables,
`era5_seamless` combina temperatura y humedad de ERA5-Land con viento y
radiación de ERA5. Precipitación también depende de ERA5. Es un único parámetro
API y un esquema constante, pero su composición interna debe aprobarse antes de
ejecutar.

Documentación primaria:

- https://open-meteo.com/en/docs/historical-weather-api
- https://github.com/open-meteo/open-meteo/blob/main/openapi/historical-weather.yml

## Variables y unidades

| Parámetro diario | Significado | Unidad solicitada | Disponibilidad propuesta |
|---|---|---:|---|
| `temperature_2m_max` | Máxima diaria a 2 m | °C | 2017–2025 |
| `temperature_2m_min` | Mínima diaria a 2 m | °C | 2017–2025 |
| `relative_humidity_2m_min` | Mínima diaria de humedad a 2 m | % | 2017–2025 |
| `relative_humidity_2m_max` | Máxima diaria de humedad a 2 m | % | 2017–2025 |
| `wind_speed_10m_max` | Máxima diaria de velocidad a 10 m | m/s | 2017–2025 |
| `wind_direction_10m_dominant` | Dirección dominante diaria a 10 m | grados | 2017–2025 |
| `precipitation_sum` | Precipitación diaria total | mm | 2017–2025 |
| `et0_fao_evapotranspiration` | ET₀ diaria de referencia FAO-56 | mm | 2017–2025 |

Open-Meteo define `precipitation_sum` como precipitación diaria total y ET₀
como evapotranspiración de referencia de un césped bien regado, calculada con
FAO-56 Penman-Monteith y supuesto de agua no limitante. En una futura agregación
semanal ambas son candidatas naturales a suma. La dirección del viento es
angular: nunca debe promediarse aritméticamente; requerirá estadística circular
o seno/coseno.

No se incluyen `riesgo_*`, `indice_riesgo` ni `nivel_riesgo` heredados.

## Diseño espacial

Se compararon:

- **Un punto por departamento:** 19 coordenadas y 62.434 filas. Es simple, pero
  representa un punto y no la variabilidad interna.
- **Grilla múltiple:** grilla regular de 25 km, compatible con la resolución más
  gruesa de ERA5-Seamless. Produce 283 coordenadas y 929.938 filas.

Se recomienda la grilla múltiple. Se construye en EPSG:32721, anclada a
múltiplos absolutos de 25.000 m y retiene sólo puntos estrictamente dentro de
cada polígono geoBoundaries. Si un departamento no contuviera un nodo se usaría
`representative_point()`; en la capa actual no fue necesario. Esto evita puntos
manuales y consultas mucho más densas que la resolución meteorológica.

Los IDs contienen ISO departamental y coordenadas métricas, por ejemplo
`URY_AR_G_E425000_N6600000`; no dependen del orden de un DataFrame.

## Requests y volumen

- 3.286 días por coordenada.
- 283 coordenadas.
- 929.938 filas procesadas esperadas.
- lotes de 10 coordenadas y bloques por año;
- 29 lotes × 9 períodos = 261 requests estimados.
- tamaño Parquet procesado aproximado: 9,01 MiB, extrapolado de 30.775 filas
  heredadas equivalentes. No se estima JSON raw porque depende de serialización
  y compresión HTTP no observadas.

## Raw, procesado y trazabilidad

- Raw inmutable: `data/raw/open_meteo/<año>/<job_id>.json`.
- Partes normalizadas/checkpoint:
  `data/processed/open_meteo_daily/parts/<job_id>.parquet`.
- Dataset diario futuro:
  `data/processed/open_meteo_daily/open_meteo_daily_2017_2025.parquet`.
- Auditoría: `results/open_meteo_extraction/` con plan, manifiesto JSONL,
  timestamps, URL/params, HTTP status, intentos, filas, rutas y SHA-256.

La tabla diaria futura tendrá una fila por `coordenada_id + fecha`, identificador
departamental, coordenadas, modelo, timezone y las ocho variables. No contiene
semanas, rezagos, rolling windows ni FIRMS.

## Fuga de información

ERA5-Seamless es reanálisis histórico, no un pronóstico que necesariamente
hubiera estado disponible antes del fenómeno. La meteorología de la semana
objetivo sólo es válida para descripción contemporánea. Una futura predicción
deberá usar información cerrada antes del lunes objetivo y considerar el retraso
de publicación documentado del reanálisis.
