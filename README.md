# Perfiles meteorológicos y clasificación de la presencia de detecciones de focos de calor en Uruguay

Proyecto de Aprendizaje Automático (PAA) 2026 de la Licenciatura en Ingeniería de Datos e Inteligencia Artificial de UTEC. Continúa el Proyecto LIDIA, pero se desarrolla en un repositorio independiente.

## Descripción y objetivo

El proyecto estudia la relación descriptiva entre meteorología y detecciones FIRMS en Uruguay con una unidad de análisis **departamento–semana**. Combina dos tareas: identificar perfiles meteorológicos mediante aprendizaje no supervisado y preparar una clasificación binaria de la presencia de detecciones FIRMS.

Una detección FIRMS indica una **anomalía térmica o foco de calor observado por satélite**; no confirma por sí sola un incendio forestal. Los perfiles meteorológicos A–D tampoco son niveles de riesgo.

## Datos y preparación

El panel objetivo comprende los **19 departamentos**, desde la semana iniciada el **1 de enero de 2018** hasta la iniciada el **22 de diciembre de 2025**: **417 semanas completas por departamento y 7.923 observaciones**. La semana parcial iniciada el 29 de diciembre de 2025 queda fuera. En el panel se contabilizan **8.508 detecciones FIRMS**.

- **FIRMS:** el archivo regional heredado de LIDIA se filtra con `pais == "URY"`. Las coordenadas se asignan por unión espacial `within` a los límites ADM1 de [geoBoundaries](geoBoundaries-URY-ADM1-all/geoBoundaries-URY-ADM1.geojson), en EPSG:4326. Siete puntos sin departamento no se incorporan a los conteos. Una grilla completa de departamento–semana representa con cero las combinaciones sin detecciones asignadas.
- **Open-Meteo:** la extracción histórica diaria 2017–2025 se agrega primero a departamento–día y luego a semanas lunes–domingo. La agregación semanal exige siete días observados. FIRMS y meteorología se integran por `departamento` y `fecha_inicio_semana`.
- **Historia previa:** FIRMS y Open-Meteo de 2017 se conservan para posibles variables históricas; **2017 no aporta filas al target** 2018–2025. La ausencia de detecciones en una celda no demuestra ausencia de fuego.

El notebook de calidad revisa cobertura, continuidad, nulos, duplicados y valores extremos sin eliminar estos últimos ni imputar faltantes. Para el clustering se aplica `log1p` a la precipitación y luego `StandardScaler`, ajustado solo con el período de desarrollo. Las fuentes, transformaciones y auditorías detalladas están en [`src/`](src/), [`results/`](results/) y los notebooks.

## Aprendizaje no supervisado

K-Means y DBSCAN utilizan **solo cuatro variables meteorológicas**: temperatura máxima, humedad mínima, viento máximo y precipitación semanal. `cantidad_detecciones` no participa en el escalado ni en la formación de clusters; FIRMS se usa **después** para contrastar descriptivamente los perfiles.

El análisis principal conserva provisionalmente **cuatro perfiles nominales A–D** por interpretabilidad, aunque entre los valores explorados **k = 3 obtiene el mayor Silhouette**. DBSCAN encuentra una estructura distinta; la discrepancia entre métodos forma parte del resultado exploratorio y no convierte los perfiles en clases de riesgo. El scaler y K-Means se ajustan con 2018–2023; sus transformaciones y perfiles se aplican a 2024–2025 sin reajuste. PCA se utiliza para visualización.

## Etapa supervisada

La formulación vigente es **clasificación tabular binaria**, no un pronóstico anticipado ni un modelo de series temporales:

- `presencia_firms = 0`: ninguna detección asignada en la semana;
- `presencia_firms = 1`: al menos una detección asignada.

La división cronológica es **train 2018–2023**, **validation 2024** y **test 2025**. El test se reserva para la evaluación final. No se usa `cantidad_detecciones` de la misma semana como predictor.

Para la comparación supervisada posterior se plantean cuatro **configuraciones de variables, no cuatro algoritmos**: M1 (contexto), M2 (contexto + perfil), M3 (contexto + meteorología) y M4 (contexto + meteorología + perfil). Aún no están entrenadas ni comparadas en el flujo principal. El notebook de modelos contiene por ahora únicamente `DummyClassifier(strategy="most_frequent")`, ajustado en train y evaluado en validation como línea base; no presenta resultados finales de Regresión Logística o Random Forest.

## Notebooks principales

| Notebook | Propósito |
| --- | --- |
| [`Calidad_Preparacion_Datos.ipynb`](Calidad_Preparacion_Datos.ipynb) | Cobertura, calidad y selección de variables meteorológicas. |
| [`Analisis_No_supervisado.ipynb`](Analisis_No_supervisado.ipynb) | Perfiles meteorológicos, K-Means, DBSCAN y contraste posterior con FIRMS. |
| [`Preparacion_Dataset_Modelado.ipynb`](Preparacion_Dataset_Modelado.ipynb) | Construcción del dataset binario, perfiles y partición cronológica. |
| [`data/processed/modelado/Modelos.ipynb`](data/processed/modelado/Modelos.ipynb) | Línea base supervisada y evaluación en validation. |

## Archivos y reproducibilidad

- [`src/`](src/): construcción y auditoría reproducible de FIRMS, Open-Meteo y su integración.
- [`data/processed/firms_open_meteo_weekly/`](data/processed/firms_open_meteo_weekly/): histórico integrado 2017–2025 y vista con target disponible 2018–2025.
- [`results/data/firms_departamento_semana_clean.parquet`](results/data/firms_departamento_semana_clean.parquet): panel FIRMS objetivo.
- [`data/processed/modelado/dataset_modelado_presencia_firms.parquet`](data/processed/modelado/dataset_modelado_presencia_firms.parquet): dataset utilizado por `Modelos.ipynb`.
- [`results/`](results/): auditorías y figuras ya generadas. [`docs/`](docs/) conserva documentación de la extracción meteorológica.

Las dependencias declaradas están en [`requirements.txt`](requirements.txt). Desde la raíz del repositorio se puede crear el entorno con `python -m venv .venv` e instalarlo con `python -m pip install -r requirements.txt` tras activar el entorno. Los notebooks usan rutas relativas a esa raíz; para reconstruir etapas desde las fuentes originales también hacen falta los insumos locales indicados por los scripts, entre ellos el Parquet regional FIRMS heredado de LIDIA. No se requiere repetir la descarga cruda para inspeccionar los Parquet procesados presentes en este repositorio.

## Estado y próximos pasos

El Entregable 2 documenta la preparación, los perfiles meteorológicos, su contraste descriptivo con FIRMS y el baseline binario. Para el Entregable 3 se prevé comparar M1–M4, principalmente con Regresión Logística y Random Forest frente al baseline; seleccionar con validation 2024, evaluar **una sola vez** la solución seleccionada en test 2025 y, posteriormente, considerar su integración al dashboard. Esas actividades no se presentan aquí como realizadas.

## Autoría

Los commits del repositorio registran contribuciones de **Katerin González** y **Pedro de Souza**.
