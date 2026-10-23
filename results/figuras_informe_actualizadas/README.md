# Figuras definitivas del PAA — 23/10/2026

Carpeta: `/home/pepo/Materias/PAA/results/figuras_informe_actualizadas/`.

La numeración se verificó leyendo los pies de figura y las imágenes de `/home/pepo/Descargas/Proyecto Aprendizaje Automático (3).docx`. El Word se abrió exclusivamente para lectura; su SHA-256 final coincide con el previo. No se modificaron el informe, Canva, GitHub ni LIDIA. Sin commit ni push.

## Correspondencia para reemplazar imágenes

| Figura del Word | PNG en esta carpeta | Contenido / origen |
|---|---|---|
| 1 | [figura_01_mapa_firms_uruguay.png](figura_01_mapa_firms_uruguay.png) | Mapa original conservado, sin categorías ni cambios cartográficos |
| 2 | [figura_02_distribucion_detecciones.png](figura_02_distribucion_detecciones.png) | Distribución de conteos con cuartiles y umbral corregidos; notebook nuevo, celda 12 |
| **3** | [figura_03_distribucion_categorias_firms.png](figura_03_distribucion_categorias_firms.png) | Observaciones por categoría, conteos y jitter originales; notebook nuevo, celda 17 |
| 4 | [figura_04_inercia_silhouette.png](figura_04_inercia_silhouette.png) | Métricas de K-Means guardadas, sin ajustar K-Means |
| **5** | [figura_05_medianas_meteorologicas_estandarizadas.png](figura_05_medianas_meteorologicas_estandarizadas.png) | Medianas estandarizadas; mismos valores y escala divergente |
| **6** | [figura_06_distribucion_temperatura.png](figura_06_distribucion_temperatura.png) | Temperatura máxima media semanal, puntos, KDE, media/mediana/moda originales; celda 20 |
| **7** | [figura_07_distribucion_humedad.png](figura_07_distribucion_humedad.png) | Humedad relativa mínima media semanal; celda 18 |
| **8** | [figura_08_distribucion_precipitacion.png](figura_08_distribucion_precipitacion.png) | Precipitación semanal; se conserva el recorte original del eje x en 50 mm; celda 19 |
| **9** | [figura_09_distribucion_viento.png](figura_09_distribucion_viento.png) | Velocidad máxima media semanal del viento, unidad m/s explicitada; celda 21 |
| 10 | [figura_10_sensibilidad_metricas_k3_k4_k5.png](figura_10_sensibilidad_metricas_k3_k4_k5.png) | F1 macro y Balanced Accuracy guardados para k=3/4/5 |
| **11** | [figura_11_matriz_confusion_random_forest_v1.png](figura_11_matriz_confusion_random_forest_v1.png) | Matriz de Random Forest V1; mismos 16 conteos, disposición y escala viridis del Word |
| 12 | [figura_12_importancia_permutacion_original.png](figura_12_importancia_permutacion_original.png) | Copia exacta de la imagen del Word, sin recalcular importancias; no contiene etiquetas de clase |

Las imágenes nuevas de las figuras 2–11 y todas las suplementarias se exportaron a **300 dpi**. Las figuras 1 y 12 no necesitaban cambios de nomenclatura: se incluyen como copias originales, a su resolución existente, sin inventar detalle mediante ampliación. Para reemplazar exclusivamente las figuras solicitadas, usar 3, 5, 6, 7, 8, 9 y 11.

## Convención de clases y colores

| Código / identificador interno conservado | Etiqueta visible | Detecciones | Color |
|---|---|---|---|
| 0 / Sin actividad | Sin detecciones | 0 | #6B7280, gris |
| 1 / Bajo | Clúster 1 | 1 | #2563EB, azul |
| 2 / Moderado | Clúster 2 | 2–4 | #F59E0B, naranja |
| 3 / Alto | Clúster 3 | 5–173 | #DC2626, rojo |

**Sin detecciones no es un clúster de K-Means.** Los tres clústeres positivos siguen el orden ascendente de los centroides. Los números no identifican niveles de riesgo o intensidad de incendio validados externamente.

Se conservaron las posiciones de datos, límites, escalas, orden, número de puntos, jitter, densidades y estadísticas. Las matrices y heatmaps conservan sus escalas cuantitativas: el color de las celdas representa conteos o desviaciones, mientras que las etiquetas de clase usan los colores oficiales. Cambiar el mapa cuantitativo por cuatro colores de clase borraría información de los valores. En las barras de Precision/Recall/F1, el color identifica la clase y las tres métricas se distinguen mediante trama; posiciones y alturas permanecen idénticas.

Los escenarios k=4 y k=5 conservan `Perfil positivo N`, con el escenario explícito y su paleta propia. Sus grupos no se equiparan a los tres clústeres oficiales de k=3.

## Notebooks y scripts modificados

- `figura_clusters.ipynb`: revisadas sus 26 celdas; etiquetas de código, títulos, ejes, leyendas, colores y Markdown actualizados; carga local del dataset oficial; rutas de otra computadora eliminadas; exportación numerada a esta carpeta; activada la exportación de humedad que estaba comentada. Fuentes sans serif disponibles localmente, sin depender de Arial instalado. Las fórmulas, filtros, semillas, coordenadas de jitter y KDE no cambiaron.
- `Analisis_No_supervisado.ipynb`: celda gráfica 14 con la paleta canónica y salida actualizada desde asignaciones persistidas. Los identificadores internos y las celdas históricas de ajuste/construcción de target se conservaron y no se ejecutaron.
- `Analisis_Puntos_4_6_Plus.ipynb`: imágenes incrustadas actualizadas desde las exportaciones definitivas. Las salidas numéricas guardadas se conservaron.
- `src/generar_puntos_4_6_plus.py`: colores de etiquetas de clase, también en matrices/heatmaps; barras de métricas con colores por clase y trama por métrica. Sin cambios en cálculos, hiperparámetros ni resultados.
- `src/export_report_figures.py`: nuevo exportador a 300 dpi desde datos/asignaciones y resultados guardados; verifica que los valores gráficos del notebook nuevo coincidan antes/después y bloquea ajustes de modelos.
- `tests/test_report_figures.py`: integridad de recursos anteriores, comparación de coordenadas, resolución de los PNG principales, nombres visibles, ausencia de errores en el notebook nuevo y separación de escenarios.
- `tests/test_class_presentation.py`: los notebooks nuevos sin versión en HEAD se validan mediante su referencia de auditoría, en lugar de exigir una versión inexistente en Git.

No se modificó `src/inference.py`, el serializado, la metadata del modelo, los datasets, las particiones, las tablas ni los PNG anteriores. Se conservan los cambios locales previos a esta tarea.

## Validación realizada

- Suite completa: **117 passed in 17.18s**. Incluye igualdad de las **1.189 predicciones**, probabilidades idénticas con un hilo y equivalentes con `rtol=0`, `atol=1e-15` en paralelo, conservación de códigos, clases, matrices y métricas.
- F1 macro test: **0,39672311525116466 → 0,3967**. Balanced Accuracy test: **0,4137447185549167 → 0,4137**.
- Todas las coordenadas, curvas KDE, puntos, anotaciones numéricas y límites de las cinco figuras por categoría del notebook nuevo son idénticos a los originales, excluyendo nombres, colores y tipografía. Evidencia: `auditoria/coordenadas_antes_despues.json`.
- Los datos y geometría de las 14 figuras complementarias son idénticos antes/después: líneas, imágenes, barras, puntos, cajas, matrices y anotaciones numéricas. Evidencia: `auditoria/coordenadas_figuras_guardadas.json`.
- Ejecución completa sin errores de `figura_clusters.ipynb`, `Analisis_Puntos_4_6_Plus.ipynb`, `Calidad_Preparacion_Datos.ipynb` y `Auditoria_Coherencia_PAA.ipynb`, con `KMeans.fit` y `RandomForestClassifier.fit` bloqueados. En los otros notebooks validados no se sobrescribieron salidas ni archivos de datos.
- En `Analisis_No_supervisado.ipynb` se ejecutó exclusivamente la celda gráfica desde las asignaciones guardadas. No se ejecutaron sus celdas de ajuste ni escritura de dataset; tampoco los notebooks experimentales o de preparación que entrenan o escriben datos.
- Hashes previos y posteriores idénticos para todos los recursos de entrada inventariados, incluidas las figuras anteriores. `git diff --check` sin errores.
- Inspección visual de las figuras 3, 6 y 11 y corrección del margen de la figura 11 para que no se recorte “Clase real”. Nombres y textos renderizados comprobados también durante la exportación.

## Detalles conservados y pendientes

No quedan denominaciones anteriores en las figuras definitivas que muestran clases. Los nombres originales en correspondencias, datasets y copias de auditoría son intencionales y no son etiquetas para el informe.

**Figura 2 — corregida:** las marcas, los textos y la banda intercuartílica ahora se anclan a los valores calculados sobre las 2.956 observaciones positivas: Q1 = 1, mediana = 2, Q3 = 3, RIC = 2 y límite superior de Tukey = 6 detecciones. Se conserva la población y las fórmulas estadísticas originales. Las posiciones son `log1p(1)`, `log1p(2)`, `log1p(3)` y `log1p(6)`; el eje muestra las cantidades originales. Se verificó la igualdad exacta de los 7.923 puntos, jitter, límites y ticks antes/después. Datos, modelo y los otros PNG no cambiaron. Evidencia: `auditoria/figura_02_valores_verificados.json`.

**Mapa:** el notebook original descargaba cartografía y tenía rutas de otra computadora. La celda actual muestra la imagen original conservada en `auditoria/mapa_original_sin_cambios.png`; así ejecuta íntegramente en local sin sustituir límites geográficos. Su regeneración cartográfica no forma parte de esta corrección.

**Figuras 1 y 12:** se preservó la resolución original (987×965 y 960×469 píxeles). No se recalcularon mapas ni importancias para aumentar resolución. Las siete figuras solicitadas están disponibles a 300 dpi.

El Word conserva por decisión del usuario sus textos y pies antiguos. Al reemplazar manualmente las imágenes, actualizar también sus pies y explicaciones a “categoría FIRMS” y las cuatro etiquetas nuevas.

## Reproducir las exportaciones

1. Ejecutar `figura_clusters.ipynb` desde la raíz de PAA: sus celdas sólo cargan datos, calculan estadísticas descriptivas y dibujan; no ajustan modelos.
2. Ejecutar `python -m src.export_report_figures` desde la raíz para las restantes imágenes. Requiere el entorno de análisis de PAA y la referencia original guardada en `auditoria/` para verificar coordenadas.
3. Las figuras 1 y 12 se conservan como recursos originales; no se recomputan. La imagen suplementaria del notebook no supervisado está también incrustada en ese notebook; ejecutar sólo su celda gráfica con datos/asignaciones ya cargados, sin sus celdas de entrenamiento.

## Inventario exacto de PNG

| Archivo | Tamaño en píxeles | Resolución |
|---|---|---|
| [figura_01_mapa_firms_uruguay.png](figura_01_mapa_firms_uruguay.png) | 987 × 965 | Original conservada |
| [figura_02_distribucion_detecciones.png](figura_02_distribucion_detecciones.png) | 3331 × 1348 | 300 dpi |
| [figura_03_distribucion_categorias_firms.png](figura_03_distribucion_categorias_firms.png) | 3315 × 1348 | 300 dpi |
| [figura_04_inercia_silhouette.png](figura_04_inercia_silhouette.png) | 3600 × 1380 | 300 dpi |
| [figura_05_medianas_meteorologicas_estandarizadas.png](figura_05_medianas_meteorologicas_estandarizadas.png) | 2760 × 1440 | 300 dpi |
| [figura_06_distribucion_temperatura.png](figura_06_distribucion_temperatura.png) | 3509 × 1350 | 300 dpi |
| [figura_07_distribucion_humedad.png](figura_07_distribucion_humedad.png) | 3509 × 1350 | 300 dpi |
| [figura_08_distribucion_precipitacion.png](figura_08_distribucion_precipitacion.png) | 3536 × 1350 | 300 dpi |
| [figura_09_distribucion_viento.png](figura_09_distribucion_viento.png) | 3509 × 1350 | 300 dpi |
| [figura_10_sensibilidad_metricas_k3_k4_k5.png](figura_10_sensibilidad_metricas_k3_k4_k5.png) | 2250 × 1440 | 300 dpi |
| [figura_11_matriz_confusion_random_forest_v1.png](figura_11_matriz_confusion_random_forest_v1.png) | 1828 × 1604 | 300 dpi |
| [figura_12_importancia_permutacion_original.png](figura_12_importancia_permutacion_original.png) | 960 × 469 | Original conservada |
| [suplementaria_clusters_log_conteos_tamanos.png](suplementaria_clusters_log_conteos_tamanos.png) | 4769 × 1169 | 300 dpi |
| [suplementaria_conteos_clusters_positivos.png](suplementaria_conteos_clusters_positivos.png) | 2340 × 1500 | 300 dpi |
| [suplementaria_conteos_por_categoria_boxplots.png](suplementaria_conteos_por_categoria_boxplots.png) | 3900 × 1500 | 300 dpi |
| [suplementaria_humedad_boxplots.png](suplementaria_humedad_boxplots.png) | 2520 × 1500 | 300 dpi |
| [suplementaria_matriz_confusion_k3.png](suplementaria_matriz_confusion_k3.png) | 2040 × 1740 | 300 dpi |
| [suplementaria_matriz_confusion_k4.png](suplementaria_matriz_confusion_k4.png) | 2040 × 1740 | 300 dpi |
| [suplementaria_matriz_confusion_k5.png](suplementaria_matriz_confusion_k5.png) | 2040 × 1740 | 300 dpi |
| [suplementaria_porcentajes_departamento.png](suplementaria_porcentajes_departamento.png) | 3450 × 1950 | 300 dpi |
| [suplementaria_precision_recall_f1_por_clase.png](suplementaria_precision_recall_f1_por_clase.png) | 2700 × 1500 | 300 dpi |
| [suplementaria_sensibilidad_f1_por_clase.png](suplementaria_sensibilidad_f1_por_clase.png) | 3600 × 1740 | 300 dpi |
| [suplementaria_sensibilidad_tamanos_clase.png](suplementaria_sensibilidad_tamanos_clase.png) | 3000 × 1620 | 300 dpi |
| [suplementaria_temperatura_boxplots.png](suplementaria_temperatura_boxplots.png) | 2520 × 1500 | 300 dpi |

Las rutas absolutas y hashes de cada PNG están en `auditoria/png_finales.json`. La copia original del notebook, los pies extraídos del Word, las imágenes de referencia, los estados Git y los registros de ejecución se guardan en `auditoria/`.
