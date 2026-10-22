# Interfaz y validación del prototipo PAA

La aplicación independiente se inicia desde la raíz del repositorio:

```sh
python -m streamlit run app/streamlit_app.py
```

Mantiene las seis variables de `artifacts/metadata_modelo.json`. El modelo serializado incluye el preprocesamiento y no se vuelve a entrenar al usar la interfaz.

## Entrada y evaluación

- Ingreso manual con nombres comprensibles, unidades y mínimos, máximos y medianas observados en train + validation (6.734 filas). Son referencias, no límites físicos ni restricciones de ingreso.
- Ejemplos históricos: las 1.189 claves de test se unen al dataset original por departamento y fecha de inicio de semana. Se comprueba correspondencia uno a uno, etiquetas válidas y separación entre particiones.
- El archivo `app/demo_examples.parquet` conserva sus cinco ejemplos originales: coinciden de forma única con las primeras cinco filas de test, pero la interfaz permite consultar test completo.
- Sólo las seis variables predictoras llegan a `predict()` y `predict_proba()`. La clase real se consulta después para evaluar; nunca se usa como predictor.
- La evaluación distingue acierto exacto, falso positivo de presencia, falso negativo de presencia, subestimación y sobreestimación. Acertar presencia no implica acertar el nivel. En modo manual no se afirma Correcto/Incorrecto.
- Las clases usan una paleta compartida: Sin actividad `#6B7280`, Bajo `#2563EB`, Moderado `#F59E0B`, Alto `#DC2626`. Los perfiles de sensibilidad k=4/k=5 mantienen colores propios, sin equipararlos a los niveles de k=3.

Las etiquetas reales son categorías estadísticas del dataset; FIRMS representa detecciones térmicas y no confirma incendios forestales. La meteorología corresponde a la semana objetivo: el prototipo no demuestra alerta anticipada. Test se reservó durante la selección y luego se consultó en sensibilidad y demostración; no debe reutilizarse para elegir otro modelo.

## Coherencia documental

Las interpretaciones de `Analisis_Puntos_4_6_Plus.ipynb` y `results/analisis_puntos_4_6_plus/interpretaciones.md` se contrastaron con las tablas y matrices persistidas. Los valores verificados son:

| Escenario | F1 macro test | Balanced Accuracy |
|---|---:|---:|
| k=3 | 0,3967 | 0,4137 |
| k=4 | 0,3371 | 0,3636 |
| k=5 | 0,2669 | 0,2836 |

Se corrigieron textos antiguos sin modificar las tablas, el modelo ni los datasets. Para k=3, las predicciones del artefacto reproducen la matriz guardada y las métricas oficiales. Para k=4/k=5, las métricas se verificaron desde sus matrices existentes, sin ajustar modelos.

`src/generar_puntos_4_6_plus.py` genera las interpretaciones desde las tablas y conserva las salidas de las celdas de código sin cambios. La función `make_notebook()` por sí sola no entrena; el flujo completo `main()` sí contiene ajustes de modelos y no es necesario para comprobar esta corrección.

## Pruebas pertinentes

```sh
python -m pytest tests/test_inference.py tests/test_official_artifacts.py tests/test_historical_evaluation.py tests/test_analysis_interpretations.py -q
```

Son 28 casos: inferencia (6), artefactos oficiales (7), evaluación histórica/interfaz (9) y coherencia del análisis (6). Incluyen casos reales de los cinco resultados posibles, ambos modos de entrada, rechazo de etiquetas como predictores, correspondencia con las particiones y regeneración documental sin entrenamiento.

La integración con el dashboard anterior se aloja en `pedrodesouza-code/Proyecto-LIDIA`, bajo `dashboard/main.py`. Su entorno se fija por separado y usa los recursos de este repositorio mediante `PAA_ROOT`; no cambia la metodología ni las métricas oficiales. Las clases predichas permanecen iguales; para probabilidades en paralelo se admite el redondeo de sumas de punto flotante, comprobando además igualdad exacta con un hilo en instancias de prueba.

Verificación de publicación del 22/10/2026: los 28 casos anteriores y la suite completa de 100 casos PAA pasaron sin fallos. No se ejecutó el notebook completo ni entrenamientos para esta comprobación.
