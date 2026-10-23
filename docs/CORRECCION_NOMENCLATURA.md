# Corrección conceptual de nomenclatura — 23/10/2026

Trabajo exclusivamente local en PAA y en los componentes PAA de LIDIA. Sin commit, push ni acceso a GitHub. No se modificaron documentos académicos, PDF, Canva ni bases de datos.

## Correspondencia definitiva

| Código conservado | Identificador interno conservado | Etiqueta visible | Detecciones | Color conservado |
|---|---|---|---|---|
| 0 | Sin actividad | Sin detecciones | 0 | #6B7280 |
| 1 | Bajo | Clúster 1 | 1 | #2563EB |
| 2 | Moderado | Clúster 2 | 2–4 | #F59E0B |
| 3 | Alto | Clúster 3 | 5–173 | #DC2626 |

Sin detecciones es la categoría definida previamente para cero: **no es un clúster**. Los tres clústeres positivos se numeran por el orden ascendente de sus centroides sobre `log1p(cantidad_detecciones)`. Se verificó ese orden usando las asignaciones guardadas, sin ejecutar K-Means. No son una escala validada de riesgo, peligrosidad o intensidad de incendio. Subestimación y sobreestimación se explican según el orden de los centroides.

## Auditoría y dependencias

Antes de editar se guardaron los estados Git de ambos repositorios, los hashes de artefactos y datos, las predicciones y probabilidades originales con un hilo y el inventario de referencias. PAA tenía un PDF no versionado; LIDIA tenía modificaciones y eliminaciones previas. Se conservaron.

El inventario textual previo contiene 790 líneas de coincidencias en 49 archivos, incluyendo código, documentación, notebooks, tablas y metadatos. Puede haber varias referencias por línea; las líneas extensas de notebooks se acotan en el inventario. La estructura versionada está en `auditoria_nomenclatura/estructura_versionada_previa.txt`.

- El pipeline serializado guarda nombres de clase como texto y expone probabilidades en el orden **Alto, Bajo, Moderado, Sin actividad**. Se conserva exactamente ese orden y se traduce cada etiqueta al renderizar: no se reordenan números.
- Los datasets y particiones conservan sus valores, códigos, tipos y claves. `predict` y `predict_proba` mantienen su API original; `class_labels.py` hace explícita la traducción de presentación.
- `metadata_modelo.json` conserva todos sus campos originales; solamente agrega `etiquetas_visibles` e `interpretacion_clases`. Se actualizó exclusivamente su hash en el fixture de integración. El hash del modelo y todos los demás hashes del fixture siguen iguales.
- Las tablas del análisis complementario son salidas de presentación. Se sustituyeron etiquetas mediante texto, sin parsear ni redondear números. Se comprobaron todos sus bytes contra el contenido previo tras aplicar únicamente la correspondencia.
- Los notebooks mantienen sus cuentas de ejecución y todos los números de las salidas guardadas. Las salidas HTML/texto sólo cambian etiquetas. Se actualizaron 12 figuras exportadas y sus imágenes en el notebook principal; las dos figuras que no contienen categorías quedaron intactas. En el notebook no supervisado, el gráfico descriptivo se volvió a dibujar desde las asignaciones guardadas; el jitter horizontal es presentación y no altera ningún conteo ni asignación. No se ejecutó ningún ajuste ni escritura de datasets.
- El notebook principal carga las métricas de K-Means y las evaluaciones supervisadas ya guardadas. El comando del generador ahora actualiza presentación mediante `src.refresh_presentation`; bloquea `KMeans.fit` y `RandomForestClassifier.fit` durante ese flujo. Las rutinas históricas de ajuste siguen como referencia de metodología y no se invocaron.
- Los perfiles de sensibilidad k=4 y k=5 conservan sus nombres `Perfil positivo N` y sus colores: no se equiparan a los clústeres oficiales de k=3.

## Referencias que se conservaron por compatibilidad o procedencia

Los nombres anteriores permanecen intencionalmente en el modelo, datasets, claves originales de metadatos, correspondencias explícitas, validaciones internas y pruebas de integridad. En los notebooks de construcción también permanecen los identificadores computacionales; sus salidas se presentan con la nomenclatura nueva.

`src/build_firms_department_week_clean.py` y el histórico meteorológico conservan una discretización anterior (2–3 y ≥4; además `Sin detección` singular). No se les aplicó la correspondencia oficial 2–4 y 5–173 ni se regeneraron sus datos. La alternativa segura es mantenerlos como procedencia histórica y consumir el dataset oficial mediante la capa de presentación. Tampoco se reescribieron `archive/`, bitácoras históricas o tablas de auditoría de esos datos. Sus nombres no se usan como etiquetas de la solución final.

El inventario de referencias originales y los estados previos son evidencia histórica y muestran deliberadamente los nombres antiguos. No deben confundirse con contenido para el informe o la interfaz actual.

## Validación

- `python -m pytest -q`: **106 passed**, 26,08 s.
- En LIDIA: `/home/pepo/.venvs/lidia-paa-dashboard/bin/python -m pytest tests/test_unified_dashboard.py -q -k 'not live_lidia'`: **10 passed**, 5 pruebas SQL reales deseleccionadas, 17,77 s. Las pruebas simulan la indisponibilidad de SQL; no necesitan consultar ni modificar bases de datos.
- Ambas interfaces: navegación, modo manual e histórico, cinco tipos de evaluación, etiquetas visibles nuevas y gráficos de probabilidades. Las pruebas comprueban además que la lógica ajena a PAA de LIDIA conserve su contrato AST.
- **1.189 predicciones idénticas**; clases y asignaciones originales conservadas. Probabilidades idénticas con un hilo; equivalencia en paralelo con `rtol=0`, `atol=1e-15`, la tolerancia ya validada.
- **F1 macro: 0,39672311525116466 → 0,3967**. **Balanced Accuracy: 0,4137447185549167 → 0,4137**. Matrices de confusión numéricamente idénticas; sólo cambian los rótulos.
- **422 archivos inmutables** verificados por SHA-256 (datos, particiones, modelo y ejemplos). Modelo: `553597e3448a64bd1922012fde856c55b3f00a65d31e20ac57c78b010d4f5582`.
- Todas las tablas del análisis verificadas contra su versión previa: cambios exclusivamente textuales. Salidas no gráficas de los cinco notebooks verificadas: cambios exclusivamente textuales, sin cambios numéricos.
- Comprobación automática de etiquetas de las 12 figuras de categorías y de la paleta de clases; se conserva también la paleta que representa métricas, en lugar de clases. Inspección visual de la matriz k=3 y distribución departamental.
- `git diff --check` pasa para PAA y los componentes editados de LIDIA. No se modificó el serializado, los hiperparámetros ni ningún dato. No se reentrenó, reconstruyó el target o ejecutó la sensibilidad.

## Cambios manuales para informe académico y presentación

1. Reemplazar nombres en texto, tablas, títulos, leyendas y capturas siguiendo la correspondencia definitiva, conservando los colores.
2. Escribir: “Sin detecciones es una categoría previa para conteos cero. Los clústeres 1, 2 y 3 son grupos estadísticos de conteos positivos, ordenados por sus centroides de K-Means; no constituyen niveles validados de riesgo ni intensidad de incendio”.
3. Mantener los rangos 0 / 1 / 2–4 / 5–173, todas las frecuencias, métricas y las cifras de las matrices de confusión. Usar las figuras actualizadas de `results/analisis_puntos_4_6_plus/figures/` y capturas nuevas de ambas interfaces.
4. Donde se mencione subestimación o sobreestimación, indicar que se refiere al orden de los centroides de los grupos de detecciones. Sustituir interpretaciones de intensidad o peligrosidad por conteos/grupos estadísticos.
5. Aclarar que son tres clústeres positivos más una categoría de cero; no cuatro clústeres de K-Means. Las evaluaciones k=4/k=5 siguen siendo sensibilidad posterior, sin cambiar la selección ni los resultados oficiales.

Para ver los cambios en sesiones de Streamlit ya abiertas, recargar la aplicación o reiniciar su proceso. Para reproducir únicamente figuras: `python -m src.refresh_presentation`, desde PAA y con su entorno de análisis (el entorno mínimo del dashboard no incluye matplotlib).

## Archivos modificados y nuevos

En PAA:

- `Analisis_No_supervisado.ipynb`
- `Analisis_Puntos_4_6_Plus.ipynb`
- `Auditoria_Coherencia_PAA.ipynb`
- `Calidad_Preparacion_Datos.ipynb`
- `Preparacion_Dataset_Modelado.ipynb`
- `README.md`
- `app/streamlit_app.py`
- `artifacts/metadata_modelo.json`
- `docs/CORRECCION_NOMENCLATURA.md`
- `docs/INTERFAZ_Y_VALIDACION.md`
- `docs/INTERPRETACION_RESULTADOS_ANALISIS_FIRMS.md`
- `docs/auditoria_nomenclatura/ (inventario, estados Git, hashes, referencia NPZ y validación JSON)`
- `results/analisis_puntos_4_6_plus/figures/plus_f1_por_clase_k.png`
- `results/analisis_puntos_4_6_plus/figures/plus_matriz_confusion_k3.png`
- `results/analisis_puntos_4_6_plus/figures/plus_matriz_confusion_k4.png`
- `results/analisis_puntos_4_6_plus/figures/plus_matriz_confusion_k5.png`
- `results/analisis_puntos_4_6_plus/figures/plus_tamanos_clase_por_k.png`
- `results/analisis_puntos_4_6_plus/figures/punto4_distribucion_conteos_por_nivel.png`
- `results/analisis_puntos_4_6_plus/figures/punto6_02_boxplot_detecciones_positivas.png`
- `results/analisis_puntos_4_6_plus/figures/punto6_03_boxplot_temperatura_por_nivel.png`
- `results/analisis_puntos_4_6_plus/figures/punto6_04_boxplot_humedad_por_nivel.png`
- `results/analisis_puntos_4_6_plus/figures/punto6_05_heatmap_meteo_medianas_estandarizadas.png`
- `results/analisis_puntos_4_6_plus/figures/punto6_06_distribucion_niveles_departamento.png`
- `results/analisis_puntos_4_6_plus/figures/punto6_07_metricas_rf_por_clase_test.png`
- `results/analisis_puntos_4_6_plus/interpretaciones.md`
- `results/analisis_puntos_4_6_plus/tables/plus_distribucion_clases_por_k.csv`
- `results/analisis_puntos_4_6_plus/tables/plus_matriz_confusion_k3.csv`
- `results/analisis_puntos_4_6_plus/tables/plus_matriz_confusion_k4.csv`
- `results/analisis_puntos_4_6_plus/tables/plus_matriz_confusion_k5.csv`
- `results/analisis_puntos_4_6_plus/tables/plus_metricas_por_clase_test.csv`
- `results/analisis_puntos_4_6_plus/tables/punto4_resumen_estadistico_niveles.csv`
- `results/analisis_puntos_4_6_plus/tables/punto6_03_boxplot_temperatura_por_nivel_observaciones_validas.csv`
- `results/analisis_puntos_4_6_plus/tables/punto6_04_boxplot_humedad_por_nivel_observaciones_validas.csv`
- `results/analisis_puntos_4_6_plus/tables/punto6_departamento_porcentajes_por_nivel.csv`
- `results/analisis_puntos_4_6_plus/tables/punto6_departamento_recuentos_por_nivel.csv`
- `results/analisis_puntos_4_6_plus/tables/punto6_heatmap_meteo_medianas_estandarizadas.csv`
- `results/analisis_puntos_4_6_plus/tables/punto6_heatmap_meteo_medianas_originales.csv`
- `results/analisis_puntos_4_6_plus/tables/punto6_meteo_nulos_por_clase.csv`
- `results/analisis_puntos_4_6_plus/tables/punto6_metricas_rf_final_test_por_clase.csv`
- `src/class_labels.py`
- `src/generar_puntos_4_6_plus.py`
- `src/historical_evaluation.py`
- `src/refresh_presentation.py`
- `src/visual_style.py`
- `tests/test_class_presentation.py`
- `tests/test_historical_evaluation.py`

En LIDIA (rutas relativas a `/home/pepo/Datos completos/Proyecto-LIDIA-ec3-pedro`):

- `dashboard/paa_module/class_labels.py`
- `dashboard/paa_module/visual_style.py`
- `dashboard/paa_module/historical_evaluation.py`
- `dashboard/paa_module/ui.py`
- `tests/test_unified_dashboard.py`
- `tests/fixtures/paa_artifact_hashes.json`
- `docs/integracion_paa/NOMENCLATURA.md`
