# Archivo histórico del PAA

Esta carpeta conserva materiales de etapas anteriores para mantener trazabilidad. No son errores: muestran cómo evolucionó el proyecto. Salvo indicación expresa, no deben usarse para reconstruir el target, los 21 experimentos ni el modelo final.

## Contenido

- `entregable2/`: notebook y datasets supervisados de la formulación del Entregable 2. Fueron sustituidos por el dataset multiclase y la experimentación V1–V4 del flujo actual.
- `clustering_meteorologico/`: figuras del enfoque anterior en el que los perfiles se formaban con meteorología y FIRMS se utilizaba como contraste. El target oficial actual se construye con `log1p(cantidad_detecciones)` positiva.
- `clasificacion_binaria/`: dataset de la formulación binaria de presencia FIRMS, reemplazada por las cuatro clases actuales.
- `nesterov/`: análisis complementario basado en un proxy inspirado en Nesterov. No es el índice oficial ni una feature del modelo final. Su dataset derivado permanece temporalmente en `data/processed/nesterov/` para conservar la ejecución histórica.
- `analisis_antiguos/`: scripts exploratorios previos, incluidos cortes empíricos y un análisis del panel anterior a la definición K-Means.
- `fuentes_lidia_no_utilizadas/`: carpeta reservada para fuentes heredadas de LIDIA después de comprobar todas sus dependencias. No se movieron fuentes en esta limpieza porque `data/meteo_2025.parquet` todavía participa en tests y auditorías históricas.

## Componentes que no producen resultados oficiales

No deben emplearse como sustitutos de los notebooks y artefactos enumerados en `docs/ARTEFACTOS_OFICIALES_PAA.md`:

- clasificación binaria de presencia FIRMS;
- cortes empíricos 0, 1, 2–3 y ≥4;
- clustering meteorológico anterior;
- proxy Nesterov;
- notebooks y datasets del Entregable 2.

Los resultados oficiales permanecen fuera de `archive/`: target K-Means `k=3`, 21 experimentos, Random Forest V1, métricas de test, artefacto serializado e inferencia.
