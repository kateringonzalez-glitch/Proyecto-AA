# Manifiesto de datos FIRMS

## Fuentes disponibles

| Archivo | Cobertura observada | Filas | SHA-256 |
|---|---|---:|---|
| `data/firms_2018_2025.parquet` | Archivo regional 2018–2025; se filtra `pais == "URY"` | 2.871.496 | `8c047c3b92bfb9e5db2a012f972c3ee757dc98427408e9815c387c09ebabab24` |
| `DL_FIRE_M-C61_799659.zip` | Descarga usada para el antecedente 2017; contiene registros 2017–2018 | 1.694 registros al descomprimir | `03c0af0e076a550c4a8659c80651503936f9a915f4a909bc18b7712bd3c3bd86` |

La URL exacta, la consulta y la fecha original de descarga no son verificables con los archivos disponibles. Los nombres y contenidos permiten identificar FIRMS, pero no sustituyen un comprobante de adquisición.

Columnas relevantes del Parquet regional: `latitud`, `longitud`, `fecha_adq`, `hora_adq_hhmm`, `satelite`, `instrumento`, `confianza_raw`, `potencia_radiativa`, `pais` y `pais_codigo`. El archivo contiene 20 columnas.

## Transformaciones principales

1. Filtrado exacto `pais == "URY"`: 8.525 registros.
2. Conversión de fecha y validación de coordenadas.
3. Unión espacial `within` con `geoBoundaries-URY-ADM1-all/geoBoundaries-URY-ADM1.geojson` en EPSG:4326.
4. 8.518 detecciones asignadas y 7 sin departamento, excluidas de los conteos.
5. Semana lunes–domingo.
6. Conteo por departamento y semana.
7. Grilla completa de 19 departamentos y ceros explícitos.
8. Exclusión general de semanas cuyo fin no está cubierto por la fecha máxima de la fuente. Se elimina la semana iniciada el 29/12/2025.

## Productos

| Archivo | Filas | Contenido | SHA-256 |
|---|---:|---|---|
| `results/data/firms_departamento_semana.parquet` | 7.942 | Panel previo a retirar la semana parcial | `c00b104c7c43cd4e7aff36bd81ec5cda5cc9a70a8c318b384b696184026f6c6a` |
| `results/data/firms_departamento_semana_clean.parquet` | 7.923 | Panel limpio de 417 semanas | `32dfc44031812d27d87eaf44eb2cdd1db63fb6efb74a6a2356c5bd5fa4ee3a2c` |
| `results/data/firms_departamento_semana_history_2017_2025.parquet` | 8.911 | Histórico de conteos 2017–2025 | `4c171a27e5723e66c4000488e3ef84cc31639eddd2bd0a4689d4ea9ac0c1cc49` |
| `data/processed/modelado/dataset_niveles_actividad_firms.parquet` | 7.923 | Target oficial K-Means | `f3e61b15f0f680d3c179cb4831c20c9d06b7b5ae8ac3136ad91e2f772cd60aec` |

El panel limpio conserva columnas de clases por cortes empíricos de una etapa intermedia. Esas etiquetas no son el target oficial; `Analisis_No_supervisado.ipynb` lo reconstruye mediante K-Means.
