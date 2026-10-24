# Auditoría técnica integral del PAA — 24/10/2026

## A. Resumen ejecutivo

Se corrigieron referencias vigentes pendientes en los seis notebooks experimentales, dos salidas regenerables de los notebooks de construcción y el ejemplo de inferencia del README. Se incorporaron pruebas de regresión y un inventario reproducible. La metodología, las asignaciones del target, los datos, los splits, el modelo, las métricas y las figuras oficiales existentes se conservaron.

**Resultado:** 126 pruebas PAA aprobadas y 10 pruebas de integración LIDIA aprobadas (5 pruebas SQL real excluidas). Las 1.189 predicciones y probabilidades de test son idénticas a la referencia con un hilo. No se entrenó ningún modelo ni se ajustó K-Means. Se verificaron por SHA-256 los 629 archivos preexistentes protegidos bajo `data/`, `results/`, `artifacts/` y los ejemplos de la app: ninguno cambió.

El Word de referencia se encontró en `/home/pepo/Descargas/Proyecto Aprendizaje Automático (6).docx`. Se leyeron sus párrafos y tablas desde `word/document.xml`; su SHA-256 permanece idéntico. Se contrastaron metodología, resultados y limitaciones con ese texto, no solamente con la solicitud.

**Alcance y límites:** el inventario recorre también archivos ignorados por Git. Incluye fuentes y salidas textuales de notebooks, AST de Python, documentación, JSON, CSV, esquemas y columnas de clases de todos los Parquet, integridad de PNG y directorios/CRC de ZIP. No equivale a una inspección semántica de cada imagen raster, PDF, archivo geoespacial binario o miembro de ZIP. Esos límites se individualizan en `auditoria_integral_2026_10_24/inventario.json`. No se declara revisión visual completa de todos los materiales históricos ni de las imágenes incrustadas en el Word.

## B. Archivos modificados

Rutas relativas a PAA; celdas numeradas desde cero.

| Archivo | Cambio concreto |
|---|---|
| `src/class_labels.py` | Agrega `present`: presentación de Series, DataFrames, diccionarios anidados, confusiones y encabezados de métricas. Copia los resultados y conserva el orden. No altera las funciones previas de compatibilidad. |
| `experimentos/00_Preparar_Splits.ipynb` | Traduce la distribución anidada al mostrar `meta`; conserva la metadata escrita y las claves de los splits. |
| `experimentos/Experimento_01_Dummy.ipynb` | Traduce distribuciones, matrices, reportes y encabezados mostrados; conserva cálculos y CSV persistido. |
| `experimentos/Experimento_02_LogisticRegression.ipynb` | Traduce matrices, reportes, encabezados y clases impresas en la explicación de coeficientes; conserva modelos y métricas. |
| `experimentos/Experimento_03_RandomForest.ipynb` | Traduce matrices, reportes y encabezados de resultados; conserva la búsqueda y la evaluación originales. |
| `experimentos/Experimento_04_HistGradientBoosting.ipynb` | Traduce matrices, reportes y encabezados; conserva entrenamiento y exportaciones originales. |
| `experimentos/Comparacion_Modelos.ipynb` | Traduce métricas, matrices, reportes y diccionario de confusiones. La celda 17 ahora genera también `etiquetas_visibles` e `interpretacion_clases`, antes omitidas. No se ejecutó la serialización. |
| `Analisis_No_supervisado.ipynb` | Envuelve la tabla de rangos/valores de la celda 13 con `display_frame`, evitando volver a mostrar nombres antiguos al ejecutar. |
| `Preparacion_Dataset_Modelado.ipynb` | Traduce el índice del recuento impreso en la celda 9; no cambia el DataFrame persistido. |
| `src/build_firms_department_week_clean.py` | Explicita en su docstring que los cortes candidatos 2–3 / ≥4 son históricos, distintos del target oficial. |
| `src/build_firms_open_meteo_weekly_history.py` | Documenta la procedencia de las clases históricas y la unión posterior con el target K-Means oficial. |
| `README.md` | Ejemplo de inferencia con presentación definitiva, explicación del contrato interno y enlace a esta auditoría. |
| `registro_uso_IA.md` | Nota inicial que distingue decisiones históricas de la metodología actual; no reescribe la bitácora. |

Los seis notebooks experimentales incorporan una aclaración de nomenclatura y limitaciones. Sus salidas textuales guardadas se actualizaron exclusivamente por sustitución contextual de etiquetas/encabezados; ninguna salida numérica, imagen, cuenta de ejecución o celda se eliminó.

Archivos nuevos:

| Archivo | Función |
|---|---|
| `src/audit_paa_project.py` | Inventario recursivo y búsqueda contextual reproducible, sin modificar los archivos inspeccionados. |
| `tests/test_experiment_presentation.py` | Nueve casos de regresión: salidas guardadas, no mutación, orden de probabilidades y contrato de metadata generado. |
| `docs/AUDITORIA_INTEGRAL_PAA_2026_10_24.md` | Este informe. |
| `docs/auditoria_integral_2026_10_24/` | Evidencias enumeradas a continuación. |

Evidencias nuevas dentro de esa carpeta:

- `hashes_antes.json`: hashes de todos los archivos de proyecto preexistentes inventariados, excluyendo caches y Git.
- `git_paa_antes.txt`, `git_lidia_antes.txt`: estados iniciales; preservan el registro de modificaciones locales ajenas.
- `word_sha256.txt`: identidad del documento original.
- `inventario.json`, `referencias_finales.json`: cobertura por archivo y coincidencias con ubicación/contexto.
- `notebooks_cambios.json`: celdas modificadas de los seis experimentos.
- `validacion_metodologica.json`, `validar_metodologia.py`: comprobaciones numéricas, de antecedentes y de integridad, con script reproducible.
- `integracion_inspeccionada.json`: 16 archivos relacionados de LIDIA leídos y sus hashes.
- `ejecucion_notebooks.json`, `ejecutar_notebooks.py` y cinco copias `ejecutado_*.ipynb`: ejecución controlada y salidas nuevas separadas de los originales.
- `pytest_paa.txt`, `pytest_lidia.txt`: resultados de pruebas.

No se modificó ningún archivo de LIDIA en esta auditoría. Su árbol ya tenía modificaciones y eliminaciones locales, registradas antes de la validación. No se hicieron commit ni push.

## C. Referencias antiguas encontradas y sustituciones

Correspondencia exclusiva de la taxonomía oficial guardada:

| Identificador conservado | Representación definitiva | Código | Conteo observado |
|---|---|---:|---|
| `Sin actividad` | Sin detecciones | 0 | 0 |
| `Bajo` | Clúster 1 | 1 | 1 |
| `Moderado` | Clúster 2 | 2 | 2–4 |
| `Alto` | Clúster 3 | 3 | 5–173 |

Ubicaciones corregidas:

| Ubicación | Referencia encontrada | Corrección |
|---|---|---|
| Splits, celda 3 | Claves antiguas en `distribucion` mostrada | `present(meta)` y salida guardada con nombres definitivos. |
| Dummy, celdas 2–3 | Índices de recuentos, matriz y reporte | Traducción de presentación y salidas guardadas. |
| Logística, celdas 2–5 | Matrices, reporte, clases de coeficientes y encabezados | Traducción al mostrar, sin cambiar `classes_` ni coeficientes. |
| RF, celdas 2–4 | Matrices, reporte y encabezados | Traducción al mostrar y en salidas guardadas. |
| HGB, celdas 2–4 | Matrices, reporte y encabezados | Traducción al mostrar y en salidas guardadas. |
| Comparación, celdas 11 y 15 | Reporte, matriz, nombres de métricas y claves como `Sin actividad → Bajo` | Nombres definitivos, incluida `Sin detecciones → Clúster 1`. |
| Experimentos, encabezados mostrados | `precision_bajo`, `recall_moderado`, `f1_alto`, etc. | `precision_clúster_1`, `recall_clúster_2`, `f1_clúster_3`, etc.; sólo representación, no claves de CSV originales. |
| No supervisado, celda 13 | Fuente que regeneraba índices antiguos | `display_frame(...)`. La salida guardada ya estaba corregida. |
| Preparación, celda 9 | Fuente que imprimía índices antiguos | `rename(index=display_label)`. La salida guardada ya estaba corregida. |
| README, ejemplo de inferencia | Impresión directa de etiquetas internas | `present(...)` al imprimir predicción y probabilidades. |

No se sustituyeron expresiones de otros contextos como «temperatura alta», «ajuste moderado», «F1 bajo», ni las categorías de contaminación de fuentes LIDIA. `Riesgo alto` y similares en el proxy Nesterov pertenecen a un análisis complementario histórico, no al target del clasificador final.

## D. Inconsistencias técnicas detectadas

1. **Cobertura incompleta de presentación en los experimentos. Corregida.** Las salidas y su código generador podían mostrar nombres antiguos aunque las interfaces finales estuvieran corregidas. Se corrigieron ambas capas y se probaron contra la revisión inicial `980ce6a18b4be88086b826dce91e6eccc17097a6`.
2. **Generador de metadata incompleto. Corregido.** La serialización del notebook de comparación no incluía los dos campos de presentación presentes en el JSON vigente. Una reproducción futura los habría perdido. Se agregó su construcción sin sobrescribir el artefacto actual.
3. **Ambigüedad de columnas históricas. Documentada sin alterar significado.** Los paneles intermedios usan `nivel_actividad_firms` para cortes 0 / 1 / 2–3 / ≥4. No son K-Means: tienen 1.034 y 685 filas en las dos clases superiores, frente a 1.266 y 453 del target oficial. Traducirlos directamente a los clústeres actuales sería incorrecto. El notebook de preparación descarta esas etiquetas intermedias y une el target oficial por departamento–semana. Se verificó ese flujo y se aclararon los docstrings.
4. **Orden de probabilidades diferente del orden ordinal. Correcto, requiere conservar asociación.** El artefacto expone `Alto, Bajo, Moderado, Sin actividad`, que se presenta como `Clúster 3, Clúster 1, Clúster 2, Sin detecciones`. No corresponde asignarle las etiquetas ordinales 0–3 por posición. La API etiqueta columnas con `model.classes_` y la presentación renombra sin mover valores. Las pruebas confirman esa correspondencia.
5. **API de inferencia de compatibilidad. Conservada explícitamente.** `predict` devuelve identificadores textuales antiguos, no códigos ni nombres de presentación. Cambiarlo habría roto consumidores y pruebas. README y notebooks muestran la traducción; las dos interfaces ya la aplicaban.
6. **Límites metodológicos reconocidos.** Taxonomía retrospectiva construida sobre 2018–2025; partición aleatoria estratificada; meteorología de la misma semana; posibles dependencias entre particiones en V2–V4 por lags anteriores al split. Son limitaciones presentes en el informe, no errores introducidos por nomenclatura. V1 no utiliza lags. No se presentan estos resultados como generalización temporal, predicción de incendios futuros ni alerta temprana.

No se detectó necesidad de una modificación estructural del modelo o de los datasets para resolver los hallazgos.

## E. Código histórico, obsoleto y redundancia

| Componente | Clasificación y decisión |
|---|---|
| `archive/entregable2/`, `archive/clasificacion_binaria/`, `archive/analisis_antiguos/` | Formulaciones sustituidas. Conservar para trazabilidad; no usarlas para resultados oficiales. |
| `archive/clustering_meteorologico/`, `archive/nesterov/`, `data/processed/nesterov/` | Antecedentes/complementos; sus perfiles o niveles no se traducen como si fueran K-Means FIRMS. Conservar. |
| Scripts de limpieza/historia FIRMS | Siguen siendo dependencias de conteos e historia; sólo su discretización candidata está superada. No eliminar el script completo. |
| `src/generar_puntos_4_6_plus.py` | Contiene rutinas originales de ajuste para trazabilidad y reproducción de la sensibilidad. El flujo de presentación usa resultados guardados y bloquea ajustes. No se eliminaron esas rutinas. |
| Dos copias de inferencia/presentación en PAA y LIDIA | Duplicación con riesgo de divergencia futura. Las pruebas de integración contrastan su comportamiento. No se centralizaron módulos durante esta auditoría. |
| `docs/auditoria_nomenclatura/`, `results/figuras_informe_actualizadas/auditoria/` | Instantáneas previas deliberadas. Pueden contener nomenclatura antigua; conservar como evidencia, no como material vigente de presentación. |
| Experimentos oficiales `experimentos/` | Vigentes; no se reclasificaron como históricos para justificar nombres antiguos. Se corrigieron. |

No se detectaron celdas de código exactamente duplicadas dentro de los 17 notebooks preexistentes inventariados. Esto no demuestra ausencia de redundancia conceptual entre notebooks. No se borraron archivos ni experimentos.

## F. Pruebas y verificaciones realizadas

Desde la raíz PAA:

```sh
python -m pytest -q
python -m pytest tests/test_experiment_presentation.py -q
python -m src.audit_paa_project
PYTHONPATH=. python docs/auditoria_integral_2026_10_24/validar_metodologia.py
python docs/auditoria_integral_2026_10_24/ejecutar_notebooks.py
git diff --check
```

Resultados:

- Suite inicial: **117 passed**, 18,45 s.
- Nuevas regresiones aisladas: **9 passed**, 1,76 s.
- Suite final: **126 passed**, 18,05 s. Incluye integridad de artefactos, datos, métricas, inferencia, presentación, evaluaciones históricas y figuras.
- `git diff --check`: correcto.
- Comparación completa de las salidas de los seis notebooks experimentales: mismo número de celdas, mismas cuentas de ejecución y mismas salidas tras traducir sólo etiquetas/encabezados. Las imágenes guardadas no cambian.
- 1.189 predicciones y probabilidades idénticas a `docs/auditoria_nomenclatura/test_previo.npz` con `n_jobs=1`; la suite también valida tolerancia de sumas en paralelo de `1e-15`.
- Comprobación de las siete variables históricas para **todas** las filas, incluyendo antecedentes 2017; no sólo ejemplos aislados.
- Clases positivas asignadas al centroide de menor distancia en `log1p`; orden ascendente y rangos correctos, sin ejecutar `fit`.
- Parámetros del RF serializado idénticos a metadata. Veintiún experimentos; selección `rf_tuned_v1` coincide con el máximo F1 macro de validation. Las seis métricas de validation guardadas coinciden con su fila del registro.
- Precision, recall y F1 por clase de test recalculados con el artefacto existente coinciden con metadata.

En LIDIA, desde su raíz:

```sh
/home/pepo/.venvs/lidia-paa-dashboard/bin/python -m pytest tests/test_unified_dashboard.py -q -k 'not live_lidia'
```

**10 passed, 5 deselected**, 13,13 s. Comprueban equivalencia de inferencia, navegación y carga diferida, clases reales/predichas, cinco tipos de evaluación, comportamiento con SQL no disponible y conservación del código analítico ajeno al PAA. Las cinco pruebas SQL reales no se ejecutaron; no se valida aquí la disponibilidad de PostgreSQL ni los datos productivos de LIDIA.

### Ejecución de notebooks

Cinco notebooks ejecutados con `nbclient` en kernels separados, conservando los originales:

| Notebook | Celdas de código originales ejecutadas |
|---|---:|
| `Auditoria_Coherencia_PAA.ipynb` | 7 |
| `Calidad_Preparacion_Datos.ipynb` | 6 |
| `Preparacion_Dataset_Modelado.ipynb` | 6 |
| `Analisis_Puntos_4_6_Plus.ipynb` | 22 |
| `figura_clusters.ipynb` | 22 |

En esas copias se agregó un preámbulo que bloquea `fit`, escrituras CSV/Parquet y guardado de figuras originales. En preparación, la escritura Parquet se sustituyó por una comparación exacta del DataFrame calculado contra el dataset existente: pasó. En el análisis complementario se deshabilitó la función de escritura de tablas. Se conservaron las salidas nuevas en la carpeta de auditoría.

Los seis notebooks experimentales y `Analisis_No_supervisado.ipynb` **no se ejecutaron integralmente**, porque contienen ajustes, búsquedas y escrituras oficiales innecesarias para cambiar nombres. Se validaron sus fuentes Python; las pruebas comprobaron salidas guardadas, correspondencias numéricas y construcción de metadata sin entrenar. Los notebooks históricos tampoco se reejecutaron.

### Visualizaciones

Las figuras vigentes ya tenían nombres definitivos antes de esta auditoría. Se revisaron los generadores y las pruebas de etiquetas/paletas, se ejecutaron las visualizaciones de los notebooks actuales bajo las restricciones anteriores y se inspeccionó visualmente la matriz `figura_11_matriz_confusion_random_forest_v1.png`. Las pruebas verifican textos de las doce figuras de clases del análisis, los escenarios de sensibilidad, resolución de figuras para el informe y equivalencia de sus coordenadas registradas.

No se encontró una figura vigente con nombres antiguos que exigiera reemplazar su PNG. Por ello no se sobrescribieron ni reexportaron las figuras oficiales existentes. Las imágenes de notebooks experimentales conservadas no contienen las tablas textuales corregidas: sus representaciones HTML/texto se actualizaron directamente sin alterar datos. No se realizó OCR ni lectura visual individual de los 58 PNG preexistentes o de todas las imágenes históricas embebidas.

## G. Coherencia con el informe

| Aspecto | Evidencia y resultado |
|---|---|
| Unidad y cobertura | 7.923 filas, 19 departamentos, 417 semanas, 2018-01-01 a 2025-12-22; semana final incompleta excluida. Coincide. |
| Target | Cero separado; positivos exclusivamente en `log1p(cantidad_detecciones)`; K-Means `k=3`, semilla 42 y `n_init=50` en código. Coincide. |
| Orden de centroides | Escala log: 0,693147 / 1,277437 / 2,143294. Inversa: 1,0000 / 2,5874 / 7,5275. Coincide con las aproximaciones del Word. |
| Distribución | Sin detecciones 4.967; Clúster 1 1.237; Clúster 2 1.266; Clúster 3 453. Rangos 0 / 1 / 2–4 / 5–173. Coincide. |
| V1 | Departamento, mes y cuatro meteorológicas semanales: temperatura máxima media, humedad mínima media, viento máximo medio y precipitación acumulada. Coincide. |
| V2–V4 | V2 añade lags 1–4; V3 agrega media, máximo y semanas positivas de las cuatro semanas anteriores; V4 combina ambos. Verificados todos los antecedentes. |
| Exclusiones | Conteo contemporáneo y target fuera de los predictores; año y semana no se incorporan a V1. Coincide. |
| Splits | 5.546 / 1.188 / 1.189, aleatorios estratificados, semilla 42; claves completas y disjuntas. Coincide. |
| RF final | 500 árboles, hoja mínima 5, profundidad ilimitada, `sqrt`, `balanced_subsample`, semilla 42. Reajuste original con 6.734 filas documentado; ningún reajuste nuevo. Coincide. |
| Validation | F1 macro 0,4051571008 y Balanced Accuracy 0,4257384811; redondean a 0,4052 y 0,4257. Coincide con Word y registro. |
| Test | Accuracy 0,5559293524; F1 macro 0,3967231153; Balanced Accuracy 0,4137447186. Coincide. |
| Sensibilidad | Tablas k3/k4/k5 conservadas: F1 macro 0,3967 / 0,3371 / 0,2669 y Balanced Accuracy 0,4137 / 0,3636 / 0,2836. Se verificó consumo y coherencia de resultados guardados; no se reentrenaron escenarios. |
| Inferencia e interfaces | Pipeline con preprocesamiento y clasificador existente; etiquetas visibles definitivas y probabilidades asociadas a `classes_`. PAA y LIDIA compatibles en pruebas. |
| Interpretación | Grupos estadísticos, cero no es clúster; sin equivalencia con riesgo oficial o incendios confirmados. Limitaciones retrospectivas, de split y contemporaneidad preservadas. |

Diferencia intencional con el lenguaje del informe: el almacenamiento y la API de compatibilidad conservan etiquetas internas originales. La representación de resultados utiliza los nombres del Word. Los cortes de los paneles intermedios históricos no se confunden con la taxonomía oficial.

## H. Estado final

**Sí: la presentación vigente revisada del PAA y su integración utiliza Sin detecciones, Clúster 1, Clúster 2 y Clúster 3.** Se corrigieron tanto las salidas pendientes como el código que las vuelve a generar.

**No: no se eliminaron literalmente todas las etiquetas antiguas del repositorio.** Permanecen deliberadamente en:

- `artifacts/modelo_final.joblib`, datasets oficiales, metadata original, claves de métricas CSV y `splits_metadata.json`: contrato de almacenamiento conservado.
- Diccionarios de compatibilidad, constantes internas de notebooks, evaluación e inferencia y pruebas de integridad: permiten decodificar exactamente ese contrato.
- Paneles limpios/históricos intermedios y scripts asociados: otra discretización, que no debe renombrarse como si fuera el target oficial.
- `archive/`, proxy Nesterov, fuentes heredadas de LIDIA, bitácoras y evidencias previas: procedencia y trazabilidad.
- Esta auditoría e inventarios: documentan explícitamente las referencias encontradas.

El inventario final permite localizar esas referencias; sus coincidencias incluyen palabras de otros contextos y no representan automáticamente errores. No quedan fallos de pruebas en el alcance ejecutado. Quedan los límites expresamente identificados: SQL real, ejecución integral con entrenamiento y análisis visual/semántico de todos los binarios históricos. Estos puntos impiden afirmar una inspección manual completa de absolutamente todos los contenidos.
