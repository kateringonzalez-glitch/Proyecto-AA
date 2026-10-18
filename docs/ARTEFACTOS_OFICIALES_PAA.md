# Artefactos oficiales del PAA 2026

Este inventario distingue los componentes que producen o ejecutan la solución final de los materiales históricos conservados en `archive/`. FIRMS representa detecciones satelitales de focos de calor o anomalías térmicas; las clases del proyecto no son niveles oficiales de riesgo ni incendios confirmados.

## Datos y construcción del target

| Ruta | Función | Dependencias principales | Uso |
|---|---|---|---|
| `results/data/firms_departamento_semana_clean.parquet` | Panel FIRMS limpio 2018–2025, con 19 departamentos, 417 semanas y 7.923 filas | FIRMS, geoBoundaries y scripts de construcción FIRMS | Intermedio reproducible. Sus etiquetas por cortes empíricos son históricas y no constituyen el target oficial |
| `data/processed/firms_open_meteo_weekly/open_meteo_firms_weekly_history.parquet` | Base histórica integrada 2017–2025 | Panel FIRMS histórico y Open-Meteo semanal | Necesario para construir antecedentes FIRMS |
| `Analisis_No_supervisado.ipynb` | Construye el target oficial: cero separado y K-Means `k=3` sobre `log1p(cantidad_detecciones)` positiva | Panel FIRMS limpio | Necesario para reproducir `nivel_actividad_firms` |
| `data/processed/modelado/dataset_niveles_actividad_firms.parquet` | Panel con las etiquetas oficiales K-Means | Notebook anterior | Entrada de la preparación supervisada |
| `Preparacion_Dataset_Modelado.ipynb` | Integra target, meteorología y antecedentes FIRMS; define V1–V4 | Histórico integrado y target K-Means | Necesario para reproducir el dataset final |
| `data/processed/modelado/dataset_modelado_nivel_actividad_firms.parquet` | Dataset final de modelado: 7.923 filas y 19 columnas | Preparación supervisada | Artefacto oficial de entrenamiento y evaluación |

## Particiones y experimentación

| Ruta | Función | Dependencias principales | Uso |
|---|---|---|---|
| `experimentos/00_Preparar_Splits.ipynb` | Genera el split aleatorio estratificado 70/15/15 con semilla 42 | Dataset final | Necesario para reproducir particiones |
| `data/processed/modelado/splits/` | Claves de train, validation y test, más metadatos y hashes lógicos | Notebook de splits | Particiones oficiales |
| `experimentos/Experimento_01_Dummy.ipynb` | Línea base mayoritaria | Dataset y splits | Experimento oficial |
| `experimentos/Experimento_02_LogisticRegression.ipynb` | Regresión Logística V1–V4 y ajuste moderado | Dataset y splits | Experimento oficial |
| `experimentos/Experimento_03_RandomForest.ipynb` | Random Forest V1–V4 y búsqueda aleatoria | Dataset y splits | Experimento oficial |
| `experimentos/Experimento_04_HistGradientBoosting.ipynb` | HistGradientBoosting V1–V4 y búsqueda aleatoria | Dataset y splits | Experimento oficial |
| `results/experimentos_entregable3.csv` | Registro consolidado inmutable de 21 resultados de validation | Cuatro notebooks experimentales | Evidencia de selección |
| `experimentos/Comparacion_Modelos.ipynb` | Selección congelada, reentrenamiento con train+validation y evaluación final en test | Registro, dataset y splits | Evaluación oficial |

## Ejecución operativa

| Ruta | Función | Dependencias principales | Uso |
|---|---|---|---|
| `artifacts/modelo_final.joblib` | Pipeline serializado de Random Forest V1 con preprocesamiento | Resultado de la comparación final | Necesario para inferencia; no se debe sobrescribir |
| `artifacts/metadata_modelo.json` | Features, parámetros, clases, split y métricas oficiales | Modelo final | Contrato documental de inferencia |
| `src/inference.py` | Carga, validación, predicción y probabilidades | Modelo y metadatos | API de inferencia |
| `app/streamlit_app.py` | Interfaz demostrativa sin reentrenamiento | Inferencia, modelo y `app/demo_examples.parquet` | Aplicación del prototipo |
| `tests/` | Controles automatizados de datos, integración, artefactos e inferencia | Archivos oficiales existentes | Validación técnica |

## Relación con el informe

La metodología final sigue la secuencia FIRMS/Open-Meteo → panel departamento–semana → target K-Means → V1–V4 → selección en validation → Random Forest V1 → evaluación final → inferencia. Los contenidos de `archive/` documentan etapas anteriores y no deben usarse para regenerar cifras oficiales.
