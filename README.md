# PAA 2026 — Clasificación de niveles de actividad FIRMS en Uruguay

Proyecto de Aprendizaje Automático que clasifica el nivel semanal de actividad FIRMS para cada uno de los 19 departamentos de Uruguay. La unidad de análisis es `departamento–semana`, el período objetivo es 2018–2025 y las fuentes principales son las detecciones satelitales FIRMS y la meteorología de Open-Meteo.

El proyecto incluye la preparación del panel, construcción reproducible del target multiclase, comparación de modelos y representaciones de variables, un Pipeline entrenado para inferencia y un prototipo funcional en Streamlit.

> FIRMS registra focos de calor o anomalías térmicas. Una detección FIRMS no confirma por sí sola un incendio forestal.

## Objetivo

Clasificar el nivel semanal de actividad FIRMS de cada departamento utilizando contexto espacial y temporal junto con variables meteorológicas. El resultado es una estimación contemporánea de actividad FIRMS, no una predicción directa de incendios ni un pronóstico anticipado: las variables meteorológicas corresponden a la misma semana objetivo.

Las categorías `Sin actividad`, `Bajo`, `Moderado` y `Alto` son clases estadísticas internas. No constituyen niveles oficiales de riesgo.

## Flujo metodológico

```text
FIRMS
  ↓
panel departamento–semana
  ↓
ceros separados + log1p y K-Means sobre semanas positivas
  ↓
nivel_actividad_firms
  ↓
dataset supervisado
  ↓
experimentación V1–V4
  ↓
Random Forest V1
  ↓
Pipeline serializado
  ↓
inferencia y Streamlit
```

## Target

Las semanas sin detecciones se conservan explícitamente. Sobre las observaciones positivas se aplica K-Means con `k=3` a `log1p(cantidad_detecciones)` y se ordenan los centroides para asignar nombres interpretables:

| Clase | Cantidad de detecciones | Observaciones |
|---|---:|---:|
| Sin actividad | 0 | 4.967 |
| Bajo | 1 | 1.237 |
| Moderado | 2–4 | 1.266 |
| Alto | 5–173 | 453 |

Estas clases son una discretización estadística de actividad FIRMS, no categorías naturales ni niveles confirmados de riesgo de incendio.

K-Means fue ajustado sobre todas las observaciones positivas del período histórico objetivo 2018–2025, antes del split supervisado. Esto mantiene una única definición descriptiva del target, pero permite que su discretización conozca la distribución de validation y test; se documenta como limitación metodológica.

La separación entre ceros y conteos positivos sigue solamente una lógica conceptual semejante a la de los modelos *hurdle*: el proyecto no ajusta un modelo *hurdle* ni un modelo de conteo inflado en ceros. La transformación `log1p` reduce la influencia de la cola derecha antes de aplicar K-Means. La solución `k=3` equilibra separación, tamaño de los grupos e interpretabilidad; no fue elegida por maximizar mecánicamente Silhouette, cuyo máximo entre `k=2` y `k=5` aparece en `k=5`.

## Variables del modelo final

Después de comparar V1–V4, la solución seleccionada utiliza:

- `departamento`
- `mes`
- `temperature_2m_max_mean_weekly`
- `relative_humidity_2m_min_mean_weekly`
- `wind_speed_10m_max_mean_weekly`
- `precipitation_sum_weekly`

`cantidad_detecciones` de la semana objetivo **no se utiliza como predictor**. Las variantes con antecedentes FIRMS no mejoraron el mejor resultado de Random Forest, por lo que el modelo final utiliza V1.

## Experimentación

Se compararon cuatro familias:

- `DummyClassifier`, como línea base mayoritaria;
- Regresión Logística;
- Random Forest;
- HistGradientBoosting.

Cada modelo aplicable se evaluó con:

- V1: contexto + meteorología;
- V2: V1 + lags FIRMS;
- V3: V1 + históricos FIRMS agregados;
- V4: todas las variables permitidas.

Las particiones se construyeron mediante un split **aleatorio estratificado**, con `random_state=42`: 5.546 filas de train, 1.188 de validation y 1.189 de test. No es un corte temporal ni una evaluación de extrapolación estricta hacia años futuros.

Mejores resultados de validation:

| Modelo | Variante | F1 macro | Balanced Accuracy |
|---|---:|---:|---:|
| DummyClassifier | — | 0,1927 | 0,2500 |
| Regresión Logística | V3 | 0,3641 | 0,4229 |
| Random Forest | V1 | **0,4052** | **0,4257** |
| HistGradientBoosting | V3 | 0,3565 | 0,3505 |

Las 21 configuraciones ejecutadas están en [`results/experimentos_entregable3.csv`](results/experimentos_entregable3.csv).

## Solución seleccionada

La solución final es **Random Forest + V1**, con:

- `n_estimators=500`;
- `min_samples_leaf=5`;
- `max_depth=None`;
- `max_features="sqrt"`;
- `class_weight="balanced_subsample"`;
- `random_state=42`.

Fue seleccionada antes de consultar test por su mayor F1 macro y Balanced Accuracy en validation, su mejora frente al baseline y su menor dependencia operacional al no requerir antecedentes FIRMS.

## Evaluación final

Después de congelar modelo, variables e hiperparámetros, se entrenó con train + validation y se evaluó una sola vez sobre test.

| Métrica | Test |
|---|---:|
| Accuracy | 0,5559 |
| Balanced Accuracy | 0,4137 |
| Precision macro | 0,3886 |
| Recall macro | 0,4137 |
| F1 macro | 0,3967 |
| F1 weighted | 0,5720 |

El Dummy obtuvo un F1 macro aproximado de 0,1926 en el mismo test. No se prioriza Accuracy porque `Sin actividad` es mayoritaria y esa métrica puede ocultar diferencias importantes entre clases.

El análisis posterior de sensibilidad `k=3/k=4/k=5` reutiliza test para estudiar qué ocurre al fragmentar las clases positivas, pero no se utilizó para seleccionar nuevamente el modelo ni sus hiperparámetros. Las métricas oficiales son las almacenadas en `artifacts/metadata_modelo.json` y corresponden al Pipeline serializado.

## Limitaciones

- FIRMS no equivale a un incendio confirmado.
- El target surge de una discretización estadística del conteo.
- `Bajo` continúa siendo una clase difícil de distinguir y `Alto` es minoritaria.
- Persisten confusiones entre niveles, incluidas algunas no adyacentes.
- La meteorología corresponde a la semana objetivo; un uso anticipado requeriría pronósticos equivalentes disponibles al momento de inferencia.
- K-Means fue ajustado sobre los positivos de todo 2018–2025 y no exclusivamente sobre train.
- El split supervisado es aleatorio estratificado; semanas cercanas de un mismo departamento pueden pertenecer a particiones diferentes.
- Las features FIRMS históricas se construyeron antes del split; la solución final V1 no las utiliza.
- El análisis de sensibilidad `k=3/k=4/k=5` se realizó después de seleccionar el modelo y volvió a consultar test. No modifica las métricas oficiales, pero test no debe reutilizarse para nuevas decisiones.
- Las importancias predictivas no deben interpretarse como relaciones causales.
- El prototipo tiene alcance TRL 5 y no es un sistema productivo.

## Estructura del repositorio

```text
PAA/
├── app/
│   ├── demo_examples.parquet
│   └── streamlit_app.py
├── archive/
│   ├── README.md
│   ├── analisis_antiguos/
│   ├── clasificacion_binaria/
│   ├── clustering_meteorologico/
│   ├── entregable2/
│   ├── fuentes_lidia_no_utilizadas/
│   └── nesterov/
├── artifacts/
│   ├── metadata_modelo.json
│   └── modelo_final.joblib
├── config/
├── data/
├── experimentos/
│   ├── 00_Preparar_Splits.ipynb
│   ├── Experimento_01_Dummy.ipynb
│   ├── Experimento_02_LogisticRegression.ipynb
│   ├── Experimento_03_RandomForest.ipynb
│   ├── Experimento_04_HistGradientBoosting.ipynb
│   └── Comparacion_Modelos.ipynb
├── results/
│   └── experimentos_entregable3.csv
├── src/
│   └── inference.py
├── tests/
│   └── test_inference.py
├── Calidad_Preparacion_Datos.ipynb
├── Analisis_No_supervisado.ipynb
├── Preparacion_Dataset_Modelado.ipynb
├── Auditoria_Coherencia_PAA.ipynb
├── registro_uso_IA.md
└── requirements.txt
```

Los artefactos oficiales están inventariados en [`docs/ARTEFACTOS_OFICIALES_PAA.md`](docs/ARTEFACTOS_OFICIALES_PAA.md). `archive/` conserva el Entregable 2, clasificación binaria, clustering meteorológico, Nesterov y análisis anteriores exclusivamente para trazabilidad; ninguno participa en la generación de las cifras oficiales actuales.

## Instalación

Se recomienda Python 3.11 o posterior.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Orden de ejecución

Para reconstruir los datos desde las fuentes disponibles, revisar primero:

- [`docs/MANIFIESTO_DATOS_FIRMS.md`](docs/MANIFIESTO_DATOS_FIRMS.md);
- [`docs/REPRODUCCION_CATALOGO_OPEN_METEO.md`](docs/REPRODUCCION_CATALOGO_OPEN_METEO.md);
- `src/build_firms_department_week.py` y `src/build_firms_department_week_clean.py`;
- `src/extract_open_meteo.py`;
- `src/build_open_meteo_department_daily.py`;
- `src/build_open_meteo_department_weekly.py`;
- `src/build_firms_history_2017_2025.py`;
- `src/build_firms_open_meteo_weekly_history.py`.

La URL y fecha de descarga FIRMS originales no están disponibles, y el catálogo validado de Open-Meteo no se debe sobrescribir. Para reproducir la experimentación desde los datos integrados, ejecutar desde la raíz:

1. `Calidad_Preparacion_Datos.ipynb`
2. `Analisis_No_supervisado.ipynb`
3. `Preparacion_Dataset_Modelado.ipynb`
4. `experimentos/00_Preparar_Splits.ipynb`
5. `experimentos/Experimento_01_Dummy.ipynb`
6. `experimentos/Experimento_02_LogisticRegression.ipynb`
7. `experimentos/Experimento_03_RandomForest.ipynb`
8. `experimentos/Experimento_04_HistGradientBoosting.ipynb`
9. `experimentos/Comparacion_Modelos.ipynb`
10. `Auditoria_Coherencia_PAA.ipynb`

Los notebooks experimentales reutilizan las claves de `data/processed/modelado/splits/`. En el flujo de selección, sólo `Comparacion_Modelos.ipynb` evalúa test después de fijar la solución. El análisis de sensibilidad posterior también consulta test, pero no reabre la selección del modelo.

## Inferencia sin reentrenar

No es necesario volver a ejecutar los notebooks. [`artifacts/modelo_final.joblib`](artifacts/modelo_final.joblib) contiene el preprocessing y el clasificador dentro de un único Pipeline; [`artifacts/metadata_modelo.json`](artifacts/metadata_modelo.json) documenta variables, clases, versiones, configuración y métricas.

La API real de [`src/inference.py`](src/inference.py) se utiliza así:

```python
import pandas as pd
from src.inference import load_model, predict, predict_proba

entrada = pd.DataFrame([{
    "departamento": "Montevideo",
    "mes": 1,
    "temperature_2m_max_mean_weekly": 28.0,
    "relative_humidity_2m_min_mean_weekly": 45.0,
    "wind_speed_10m_max_mean_weekly": 22.0,
    "precipitation_sum_weekly": 4.0,
}])

modelo = load_model()
print(predict(entrada, model=modelo))
print(predict_proba(entrada, model=modelo))
```

La validación devuelve errores claros ante variables faltantes, nulos o inclusión accidental del conteo contemporáneo.

## Prototipo Streamlit

```bash
python -m streamlit run app/streamlit_app.py
```

La interfaz carga el artefacto ya entrenado, permite elegir ejemplos históricos o ingresar variables manualmente y muestra el nivel de actividad FIRMS estimado junto con las probabilidades por clase. No reentrena el modelo.

## Pruebas y auditoría

```bash
python -m pytest -q
python -m nbconvert --to notebook --execute Auditoria_Coherencia_PAA.ipynb --inplace
```

La auditoría controla la integridad del dataset, lags históricos, particiones sin solapamiento, reserva de test, exclusión de variables prohibidas, resultados, metadata, modelo e inferencia.

El entorno comprobado y los hashes de los artefactos protegidos están documentados en:

- [`docs/ENTORNO_VALIDADO.md`](docs/ENTORNO_VALIDADO.md);
- [`docs/HASHES_ARTEFACTOS_OFICIALES.sha256`](docs/HASHES_ARTEFACTOS_OFICIALES.sha256).

## Referencias metodológicas

- Feng, C. X. (2021). *A comparison of zero-inflated and hurdle models for modeling zero-inflated count data*. Journal of Statistical Distributions and Applications, 8. https://doi.org/10.1186/s40488-021-00121-4. Se usa como fundamento conceptual para distinguir ceros y conteos positivos; no implica que aquí se haya ajustado un modelo *hurdle*.
- Rousseeuw, P. J. (1987). *Silhouettes: A graphical aid to the interpretation and validation of cluster analysis*. Journal of Computational and Applied Mathematics, 20, 53–65. https://doi.org/10.1016/0377-0427(87)90125-7. Silhouette se usa como diagnóstico de cohesión y separación, junto con tamaños e interpretabilidad, no como regla automática para elegir `k`.
