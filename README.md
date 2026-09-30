# Proyecto de Aprendizaje Automático 2026

El PAA estima **niveles de actividad FIRMS** por departamento y semana en Uruguay. FIRMS registra anomalías térmicas o focos de calor; no confirma incendios forestales.

## Metodología vigente

El target `nivel_actividad_firms` conserva cuatro clases: `Sin actividad`, `Bajo`, `Moderado` y `Alto`. Los ceros se mantienen separados y las observaciones positivas se agrupan mediante K-Means sobre `log1p(cantidad_detecciones)`. El conteo de la semana objetivo nunca se utiliza como predictor.

El Entregable 3 compara cuatro representaciones:

- V1: departamento, mes y meteorología semanal.
- V2: V1 más lags FIRMS t-1 a t-4.
- V3: V1 más variables FIRMS rolling de cuatro semanas.
- V4: V1 más lags y rolling FIRMS.

La partición común es 70 % train, 15 % validation y 15 % test, estratificada con `random_state=42`. La selección se realiza exclusivamente con validation; test se evalúa una sola vez después de congelar la solución.

## Experimentación

Ejecutar desde la raíz del repositorio:

```bash
python -m nbconvert --to notebook --execute experimentos/00_Preparar_Splits.ipynb --inplace
python -m nbconvert --to notebook --execute experimentos/Experimento_01_Dummy.ipynb --inplace
python -m nbconvert --to notebook --execute experimentos/Experimento_02_LogisticRegression.ipynb --inplace
python -m nbconvert --to notebook --execute experimentos/Experimento_03_RandomForest.ipynb --inplace
python -m nbconvert --to notebook --execute experimentos/Experimento_04_HistGradientBoosting.ipynb --inplace
python -m nbconvert --to notebook --execute experimentos/Comparacion_Modelos.ipynb --inplace
```

Los notebooks usan las claves persistidas en `data/processed/modelado/splits/`. Los resultados parciales están en `results/experimentos_parciales/` y la tabla consolidada en `results/experimentos_entregable3.csv`.

El notebook anterior se conserva sólo como antecedente en `archive/Modelos_Entregable2.ipynb`; ya no es la fuente metodológica principal.

## Inferencia sin reentrenar

`artifacts/modelo_final.joblib` contiene preprocessing y clasificador dentro de un único Pipeline. `artifacts/metadata_modelo.json` documenta variables, clases, parámetros, versiones y métricas.

Ejemplo:

```python
import pandas as pd
from src.inference import predict, predict_proba

entrada = pd.DataFrame([{
    "departamento": "Montevideo",
    "mes": 1,
    "temperature_2m_max_mean_weekly": 28.0,
    "relative_humidity_2m_min_mean_weekly": 45.0,
    "wind_speed_10m_max_mean_weekly": 22.0,
    "precipitation_sum_weekly": 4.0,
}])

print(predict(entrada))
print(predict_proba(entrada))
```

Una entrada incompleta o que incluya `cantidad_detecciones` contemporánea produce un error explícito.

## Prototipo TRL 5

```bash
streamlit run app/streamlit_app.py
```

La interfaz carga el artefacto ya entrenado, ofrece ejemplos históricos sin target o ingreso manual y muestra el nivel estimado y sus probabilidades. No reentrena el modelo.

## Pruebas y auditoría

```bash
python -m pytest -q tests/test_inference.py
python -m nbconvert --to notebook --execute Auditoria_Coherencia_PAA.ipynb --inplace
```

La auditoría verifica particiones, ausencia de solapamiento y leakage, reserva de test, resultados, metadata, artefacto e inferencia.

## Advertencia conceptual

Los resultados representan niveles estimados de actividad FIRMS. No equivalen a incendios confirmados ni deben interpretarse automáticamente como riesgo de incendio.
