# Interpretacion de resultados de los puntos 4, 6 y sensibilidad FIRMS

Este documento resume e interpreta los analisis complementarios realizados para el proyecto de clasificacion de niveles semanales de actividad FIRMS en Uruguay. El objetivo no es describir solamente el codigo, sino explicar que se hizo, que resultados se obtuvieron, que significan esos resultados y que decision metodologica queda mejor respaldada por la evidencia disponible.

Los resultados citados provienen de los archivos locales generados en `results/analisis_puntos_4_6_plus/` y del modelo final documentado en `artifacts/metadata_modelo.json`. El notebook principal asociado es `Analisis_Puntos_4_6_Plus.ipynb` y el script reproducible es `src/generar_puntos_4_6_plus.py`.

## 1. Problema y metodologia

La unidad de analisis del proyecto es una observacion `departamento-semana`: para cada uno de los 19 departamentos de Uruguay se resume la informacion semanal disponible. La variable `cantidad_detecciones` indica la cantidad de detecciones FIRMS observadas en esa semana y departamento. Estas detecciones corresponden a focos de calor satelitales; por lo tanto, una deteccion no debe interpretarse automaticamente como un incendio confirmado. Es una senal de actividad termica detectada por el producto FIRMS.

La variable objetivo `nivel_actividad_firms` se construye en dos pasos:

1. Las semanas con `cantidad_detecciones == 0` se mantienen separadas como la clase `Sin detecciones`.
2. Las semanas con detecciones positivas se agrupan con K-Means usando `log1p(cantidad_detecciones)`.

Separar los ceros es importante porque representan una masa grande de observaciones identicas. Si se mezclaran con las observaciones positivas dentro de K-Means, los ceros dominarian la particion y el algoritmo tenderia a crear un grupo de ceros automaticamente. En cambio, el proyecto trata los ceros como una categoria explicita y aplica el agrupamiento solo donde hay actividad positiva.

Esta separacion se apoya solamente en una logica conceptual semejante a los modelos *hurdle*, que distinguen el proceso de ceros del de conteos positivos (Feng, 2021). El proyecto no implementa ni estima un modelo *hurdle* o inflado en ceros.

La transformacion `log1p(x)` calcula `log(1+x)`. Se usa porque la distribucion de detecciones es muy asimetrica: hay muchas semanas con pocas detecciones y pocas semanas con valores altos. La escala logaritmica reduce la influencia de valores extremos y permite que K-Means separe mejor rangos de actividad positiva sin que las semanas excepcionales dominen toda la distancia.

K-Means agrupa observaciones segun cercania en esa escala transformada. Luego, los clusters positivos se ordenan por sus centroides de menor a mayor y se renombran ordinalmente. Para la solucion principal con k=3 positivos, los nombres son:

- `Clúster 1`
- `Clúster 2`
- `Clúster 3`

Junto con `Sin detecciones`, esto genera cuatro clases finales. Estas clases son discretizaciones estadisticas de actividad FIRMS, no niveles oficiales de riesgo.

Despues de construir esas clases con aprendizaje no supervisado, se entrena un clasificador supervisado Random Forest para asignar niveles a partir de variables disponibles. El modelo final seleccionado es Random Forest V1, con estas variables:

- `departamento`
- `mes`
- `temperature_2m_max_mean_weekly`
- `relative_humidity_2m_min_mean_weekly`
- `wind_speed_10m_max_mean_weekly`
- `precipitation_sum_weekly`

No se usan como predictores `cantidad_detecciones`, `anio`, `numero_semana`, `fecha_inicio_semana`, ni la propia etiqueta objetivo. La cantidad de detecciones se usa para construir y auditar el target, no como predictor contemporaneo del modelo supervisado.

## 2. Punto 4: distribucion interna de los niveles

La tabla siguiente resume la distribucion real de `cantidad_detecciones` por clase final:

| Clase | Observaciones | % dataset | Min | Q1 | Mediana | Q3 | Max | Media |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sin detecciones | 4967 | 62.6909 | 0 | 0.0 | 0.0 | 0.0 | 0 | 0.0000 |
| Clúster 1 | 1237 | 15.6128 | 1 | 1.0 | 1.0 | 1.0 | 1 | 1.0000 |
| Clúster 2 | 1266 | 15.9788 | 2 | 2.0 | 2.0 | 3.0 | 4 | 2.6627 |
| Clúster 3 | 453 | 5.7175 | 5 | 5.0 | 7.0 | 9.0 | 173 | 8.6093 |

Los estadisticos se interpretan asi:

- `Min` y `Max` muestran el rango observado dentro de cada clase.
- `Q1`, mediana y `Q3` describen la parte central de la distribucion.
- La media resume el promedio, pero puede subir cuando hay valores extremos.

La clase `Sin detecciones` concentra 62.69% del dataset y todos sus valores son cero. Esto confirma que la ausencia de detecciones es el estado mayoritario.

La clase `Clúster 1` esta completamente concentrada en una deteccion. No hay dispersion interna: todas las observaciones tienen exactamente 1 deteccion.

La clase `Clúster 2` cubre de 2 a 4 detecciones. Su mediana es 2 y Q3 es 3, por lo que la mayor parte de sus observaciones queda en valores bajos dentro del rango positivo.

La clase `Clúster 3` conserva el rango documentado de 5 a 173 detecciones. Sin embargo, su mediana es 7 y Q3 es 9. Esto significa que la mayor parte de las semanas `Clúster 3` no esta cerca del maximo, sino concentrada en cantidades relativamente bajas para esa clase. La media de 8.61 es mayor que la mediana, lo que indica asimetria hacia la derecha: existen pocas semanas con conteos excepcionalmente altos que elevan el promedio.

Conclusion del punto 4: la clase `Clúster 3` no debe describirse como si todas sus observaciones fueran extremas. Es una clase con umbral minimo de 5 detecciones, mucha concentracion entre 5 y 9 detecciones, y una cola alta que llega hasta 173.

## 3. Punto 6.1: seleccion de K en K-Means

Los resultados para k=2,3,4,5 sobre observaciones positivas fueron:

| k | Inercia | Silhouette | Cluster minimo | % minimo positivas |
|---:|---:|---:|---:|---:|
| 2 | 265.630151 | 0.676956 | 1060 | 35.859269 |
| 3 | 121.854778 | 0.744527 | 453 | 15.324763 |
| 4 | 60.383737 | 0.785043 | 174 | 5.886333 |
| 5 | 34.090595 | 0.860780 | 106 | 3.585927 |

La inercia mide la compactacion interna de los clusters: cuanto menor, mas cerca quedan las observaciones de sus centroides. Por construccion, la inercia tiende a bajar cuando aumenta K, porque se permite usar mas grupos.

Silhouette mide que tan separada esta una observacion de otros clusters en comparacion con su propio cluster. Valores mayores sugieren grupos mas separados. En estos datos, Silhouette aumenta al pasar de k=2 a k=5.

Siguiendo el uso de Silhouette como ayuda para interpretar y validar agrupamientos (Rousseeuw, 1987), el indicador se considera junto con el tamaño de los grupos y la utilidad posterior. No se adopta como regla mecanica de seleccion.

El tamano minimo de cluster aporta otra informacion: muestra si el agrupamiento genera clases suficientemente grandes para ser interpretables y utiles despues en el clasificador supervisado. A medida que aumenta K, el grupo positivo mas chico cae de 453 observaciones en k=3 a 174 en k=4 y 106 en k=5.

Por eso, un Silhouette mayor no implica automaticamente una mejor decision para el proyecto. k=5 separa mejor algunos valores de conteo, pero tambien crea grupos pequenos. Esos grupos pueden ser descriptivamente interesantes, aunque menos estables y mas dificiles de aprender en la etapa supervisada.

Conclusion sobre K-Means: k=3 sigue siendo razonable porque mantiene tres perfiles positivos interpretables, con tamanos no tan pequenos, y evita fragmentar demasiado la cola de detecciones. k=4 y k=5 dan mas granularidad, pero esa granularidad debe evaluarse contra la utilidad supervisada y la claridad conceptual.

## 4. Graficos meteorologicos y territoriales

### Temperatura y humedad

Los boxplots de temperatura y humedad comparan las distribuciones de las variables meteorologicas por nivel de actividad. En el resumen de medianas:

| Clase | Temp. max media semanal | Humedad relativa min media semanal | Viento max medio semanal | Precipitacion semanal |
|---|---:|---:|---:|---:|
| Sin detecciones | 21.7333 | 57.8857 | 5.5043 | 14.3000 |
| Clúster 1 | 23.4119 | 54.0102 | 5.4362 | 10.2400 |
| Clúster 2 | 22.1190 | 53.0473 | 5.4832 | 9.0136 |
| Clúster 3 | 20.0408 | 51.8571 | 5.4205 | 4.7929 |

La temperatura mediana mas alta aparece en `Clúster 1`, no en `Clúster 3`. La humedad y la precipitacion medianas disminuyen al pasar hacia niveles de mayor actividad, especialmente la precipitacion, cuya mediana es 4.79 mm en `Clúster 3` frente a 14.30 mm en `Sin detecciones`.

Estos patrones son descriptivos y deben leerse con cuidado. Los boxplots muestran solapamiento entre clases, por lo que no se puede afirmar que una variable meteorologica por si sola determine la clase. Tampoco se puede afirmar causalidad: las variables se asocian con los niveles observados, pero no prueban que causen mayor actividad FIRMS.

### Heatmap meteorologico

El heatmap usa medianas por clase estandarizadas por variable. Esto permite comparar variables con unidades diferentes. La escala de color indica desvios respecto al promedio de cada variable, no valores absolutos comparables entre temperatura, humedad, viento y precipitacion.

El patron mas visible es que `Clúster 3` aparece por debajo del promedio en precipitacion y humedad. `Clúster 1` muestra la mediana de temperatura mas alta. El viento presenta diferencias pequenas entre clases. En conjunto, el heatmap sugiere que las variables meteorologicas aportan senal, pero no separan perfectamente los niveles.

### Distribucion por departamento

La distribucion territorial se calculo como porcentaje dentro de cada departamento. Esto evita confundir cantidad total de filas con mayor actividad relativa.

Departamentos con mayor porcentaje combinado de actividad positiva (`Clúster 1` + `Clúster 2` + `Clúster 3`):

| Departamento | Sin detecciones | Clúster 1 | Clúster 2 | Clúster 3 |
|---|---:|---:|---:|---:|
| Lavalleja | 47.0024 | 18.9448 | 24.7002 | 9.3525 |
| Artigas | 50.5995 | 16.5468 | 23.7410 | 9.1127 |
| Cerro Largo | 51.0791 | 23.7410 | 18.2254 | 6.9544 |
| Rocha | 51.7986 | 17.7458 | 20.8633 | 9.5923 |
| San Jose | 53.9568 | 20.1439 | 20.3837 | 5.5156 |

Departamentos con mayor porcentaje de `Sin detecciones`:

| Departamento | Sin detecciones | Clúster 1 | Clúster 2 | Clúster 3 |
|---|---:|---:|---:|---:|
| Montevideo | 88.2494 | 6.7146 | 4.0767 | 0.9592 |
| Flores | 80.0959 | 13.4293 | 5.7554 | 0.7194 |
| Salto | 78.8969 | 11.5108 | 8.3933 | 1.1990 |

Interpretacion: existen diferencias territoriales claras en la composicion de niveles FIRMS. Algunos departamentos muestran mayor proporcion de semanas con actividad positiva, mientras que otros concentran mayor proporcion de semanas sin detecciones. Esto describe patrones territoriales de la senal FIRMS, no confirma incendios ni riesgo oficial.

## 5. Evaluacion del Random Forest final

El modelo final documentado es Random Forest V1, con estos hiperparametros:

- `n_estimators=500`
- `min_samples_leaf=5`
- `max_depth=None`
- `max_features="sqrt"`
- `class_weight="balanced_subsample"`
- `random_state=42`

Metricas de validation documentadas para `rf_tuned_v1`:

| Metrica | Valor |
|---|---:|
| Accuracy validation | 0.574916 |
| Balanced Accuracy validation | 0.425738 |
| F1 macro validation | 0.405157 |
| F1 weighted validation | 0.579287 |

Metricas de test del modelo final:

| Metrica | Valor |
|---|---:|
| Accuracy test | 0.555929 |
| Balanced Accuracy test | 0.413745 |
| Precision macro test | 0.388613 |
| Recall macro test | 0.413745 |
| F1 macro test | 0.396723 |
| F1 weighted test | 0.571963 |

Metricas por clase en test:

| Clase | Precision | Recall | F1 | Soporte |
|---|---:|---:|---:|---:|
| Sin detecciones | 0.788520 | 0.700671 | 0.742004 | 745 |
| Clúster 1 | 0.240196 | 0.263441 | 0.251282 | 186 |
| Clúster 2 | 0.308756 | 0.352632 | 0.329238 | 190 |
| Clúster 3 | 0.216981 | 0.338235 | 0.264368 | 68 |

Matriz de confusion en test para k=3:

| Real \ Predicho | Sin detecciones | Clúster 1 | Clúster 2 | Clúster 3 |
|---|---:|---:|---:|---:|
| Sin detecciones | 522 | 106 | 84 | 33 |
| Clúster 1 | 72 | 49 | 46 | 19 |
| Clúster 2 | 53 | 39 | 67 | 31 |
| Clúster 3 | 15 | 10 | 20 | 23 |

El modelo reconoce mejor `Sin detecciones` que las clases positivas. Su F1 para `Sin detecciones` es 0.742. En cambio, las clases positivas tienen F1 bajos: 0.251 para `Clúster 1`, 0.329 para `Clúster 2` y 0.264 para `Clúster 3`.

Estas son las metricas oficiales de `artifacts/metadata_modelo.json` y del Pipeline de `artifacts/modelo_final.joblib`. En el entorno documentado (`scikit-learn 1.8.0`, `pandas 3.0.1`), reentrenar k=3 con las mismas claves, orden de desarrollo, variables e hiperparametros produjo exactamente las mismas predicciones y probabilidades equivalentes salvo precision numerica. Una ejecucion historica del analisis de sensibilidad habia producido diferencias minimas; su causa exacta no puede determinarse con los artefactos disponibles porque aquella salida no registro versiones, hash del orden de entrenamiento ni predicciones fila a fila.

Precision indica, entre las semanas que el modelo predice como una clase, que proporcion realmente era de esa clase. Recall indica, entre las semanas reales de una clase, que proporcion logro recuperar el modelo. F1 resume precision y recall.

Confundir `Clúster 3` con `Clúster 2` significa subestimar el orden del grupo según sus centroides de conteos. Confundir `Sin detecciones` con `Clúster 1` significa marcar actividad donde no hubo detecciones. En este proyecto ambas confusiones son relevantes, pero tienen implicancias distintas: una afecta el grupo estadístico asignado y la otra afecta la presencia misma de actividad.

El rendimiento es razonable como aproximacion exploratoria, porque supera claramente al baseline mayoritario en F1 macro de validation y aprende senales asociadas a la clase sin usar `cantidad_detecciones` como predictor. Sin embargo, sus limitaciones son importantes: la separacion entre niveles positivos es dificil y las clases minoritarias tienen desempeno bajo.

## 6. Sensibilidad k=3, k=4 y k=5

El analisis de sensibilidad mantiene constantes:

- las mismas 7923 observaciones;
- las mismas claves `departamento-fecha_inicio_semana`;
- los mismos splits: train 5546, validation 1188, test 1189;
- las mismas variables predictoras V1;
- los mismos hiperparametros del Random Forest;
- el mismo criterio de evaluacion en test;
- la separacion de ceros como `Sin detecciones`.

Ademas, se verifico que el target reconstruido con k=3 coincide exactamente con el target vigente: 0 diferencias.

### Distribucion de clases por escenario

| Escenario | Clase | Observaciones | % dataset | Rango |
|---|---|---:|---:|---|
| k3 | Sin detecciones | 4967 | 62.6909 | 0-0 |
| k3 | Clúster 1 | 1237 | 15.6128 | 1-1 |
| k3 | Clúster 2 | 1266 | 15.9788 | 2-4 |
| k3 | Clúster 3 | 453 | 5.7175 | 5-173 |
| k4 | Sin detecciones | 4967 | 62.6909 | 0-0 |
| k4 | Perfil positivo 1 | 1237 | 15.6128 | 1-1 |
| k4 | Perfil positivo 2 | 1034 | 13.0506 | 2-3 |
| k4 | Perfil positivo 3 | 511 | 6.4496 | 4-7 |
| k4 | Perfil positivo 4 | 174 | 2.1961 | 8-173 |
| k5 | Sin detecciones | 4967 | 62.6909 | 0-0 |
| k5 | Perfil positivo 1 | 1237 | 15.6128 | 1-1 |
| k5 | Perfil positivo 2 | 659 | 8.3176 | 2-2 |
| k5 | Perfil positivo 3 | 607 | 7.6612 | 3-4 |
| k5 | Perfil positivo 4 | 347 | 4.3797 | 5-9 |
| k5 | Perfil positivo 5 | 106 | 1.3379 | 10-173 |

Al pasar de k=3 a k=4 y k=5, los ceros y el grupo de una deteccion se mantienen estables. Lo que cambia es la fragmentacion de los conteos positivos mayores. En k=4, la cola alta queda reducida a 174 observaciones. En k=5, el perfil mas alto queda en solo 106 observaciones, y en test su soporte baja a 17 casos.

### Metricas globales

| Escenario | Clases | F1 macro test | Balanced Accuracy test |
|---|---:|---:|---:|
| k3 | 4 | 0.396723 | 0.413745 |
| k4 | 5 | 0.337121 | 0.363607 |
| k5 | 6 | 0.266867 | 0.283632 |

k=4 y k=5 no mejoran el rendimiento general. Ambas metricas globales bajan al aumentar K. Esto es importante: aunque Silhouette era mayor para k=4 y k=5 en la etapa no supervisada, la capacidad del Random Forest para clasificar esas categorias empeora.

### F1 por clase

| Escenario | Clase | F1 | Soporte test |
|---|---|---:|---:|
| k3 | Sin detecciones | 0.742004 | 745 |
| k3 | Clúster 1 | 0.251282 | 186 |
| k3 | Clúster 2 | 0.329238 | 190 |
| k3 | Clúster 3 | 0.264368 | 68 |
| k4 | Sin detecciones | 0.727273 | 745 |
| k4 | Perfil positivo 1 | 0.236181 | 186 |
| k4 | Perfil positivo 2 | 0.266272 | 157 |
| k4 | Perfil positivo 3 | 0.209302 | 76 |
| k4 | Perfil positivo 4 | 0.246575 | 25 |
| k5 | Sin detecciones | 0.729361 | 745 |
| k5 | Perfil positivo 1 | 0.245700 | 186 |
| k5 | Perfil positivo 2 | 0.149254 | 97 |
| k5 | Perfil positivo 3 | 0.205405 | 93 |
| k5 | Perfil positivo 4 | 0.158273 | 51 |
| k5 | Perfil positivo 5 | 0.113208 | 17 |

Las clases nuevas no son reconocidas de forma solida. k=5 crea una clase superior con soporte de test de solo 17 casos y F1 de 0.113. Esto muestra que la mayor granularidad no se traduce en una clasificacion supervisada mas util.

### Matrices de confusion

En k=3, el modelo acierta 522 de 745 semanas `Sin detecciones`, pero reparte muchas semanas positivas entre clases vecinas y tambien hacia `Sin detecciones`.

En k=4 y k=5, la confusion se distribuye entre mas clases. Esto vuelve mas dificil distinguir perfiles positivos finos, especialmente los de mayores conteos, porque hay menos ejemplos por clase.

Respuestas a las preguntas principales:

1. Al pasar de k=3 a k=4 y k=5, las clases positivas se fragmentan en rangos mas estrechos y aparecen clases pequenas.
2. Las nuevas clases describen mejor algunos cortes de conteos, pero no necesariamente son mas utiles para clasificar con las variables disponibles.
3. No mejora el rendimiento general del Random Forest. F1 macro y Balanced Accuracy bajan en k=4 y k=5.
4. Tampoco mejoran todas las clases individualmente. Varias clases nuevas tienen F1 bajo.
5. Las clases pequenas tienen soportes reducidos y el modelo las reconoce peor.
6. La mejora descriptiva de Silhouette no justifica, con estos resultados, la perdida de simplicidad e interpretabilidad.
7. La alternativa recomendada por ahora es conservar k=3 positivos + `Sin detecciones`.

## 7. Conclusiones

### Resultados observados

- La mayoria de observaciones no tiene detecciones FIRMS: 62.69% son `Sin detecciones`.
- `Clúster 1` equivale a una deteccion, `Clúster 2` a 2-4 y `Clúster 3` a 5-173.
- `Clúster 3` tiene cola larga: mediana 7, Q3 9 y maximo 173.
- K-Means mejora Silhouette al aumentar K, pero reduce mucho el tamano de las clases positivas mas pequenas.
- Las variables meteorologicas muestran patrones descriptivos, especialmente menor precipitacion mediana en `Clúster 3`, pero con solapamiento entre clases.
- Hay diferencias territoriales en la composicion de niveles por departamento.
- El Random Forest reconoce mejor `Sin detecciones` que los niveles positivos.
- En sensibilidad, k=4 y k=5 empeoran F1 macro y Balanced Accuracy frente a k=3.

### Interpretacion

El proyecto trabaja con una senal dificil: muchas semanas sin detecciones, muchas semanas positivas con conteos bajos y pocas semanas con conteos altos. La construccion del target k=3 logra una discretizacion comprensible y con tamanos razonables. Aumentar K describe mas finamente los conteos, pero esa finura no parece estar respaldada por la capacidad del modelo supervisado para separar las nuevas clases.

### Decision recomendada

Conviene conservar, por ahora, la solucion principal:

- `Sin detecciones`
- `Clúster 1`
- `Clúster 2`
- `Clúster 3`

Esta alternativa no es perfecta, pero ofrece el mejor equilibrio observado entre interpretabilidad, tamanos de clase y rendimiento supervisado.

### Limitaciones

- Las clases son categorias estadisticas de actividad FIRMS, no incendios confirmados.
- Las asociaciones meteorologicas son descriptivas y no causales.
- El rendimiento de las clases positivas es bajo, especialmente para clases minoritarias.
- La evaluacion de sensibilidad usa test para comparar escenarios predefinidos, pero no debe usarse para redisenar hiperparametros.
- El modelo no es una prediccion temporal anticipada: clasifica el nivel asociado a las condiciones disponibles en el dataset.

### Proximos pasos razonables

- Explorar validacion temporal o por anios para evaluar generalizacion fuera de la particion aleatoria.
- Revisar si variables adicionales no contemporaneas y metodologicamente validas mejoran la separacion de niveles positivos.
- Analizar errores por departamento y estacion para entender donde falla el modelo.
- Considerar metricas enfocadas en clases positivas si el objetivo operativo prioriza detectar actividad.
- Mantener k=3 como base y documentar k=4/k=5 como sensibilidad descriptiva, no como reemplazo recomendado.

## 8. Trazabilidad y reproduccion

Archivos principales:

- Notebook principal: `Analisis_Puntos_4_6_Plus.ipynb`
- Script reproducible: `src/generar_puntos_4_6_plus.py`
- Documento de interpretacion: `docs/INTERPRETACION_RESULTADOS_ANALISIS_FIRMS.md`
- Tablas: `results/analisis_puntos_4_6_plus/tables/`
- Figuras: `results/analisis_puntos_4_6_plus/figures/`
- Validaciones: `results/analisis_puntos_4_6_plus/resumen_validaciones.json`
- Interpretacion sintetica previa: `results/analisis_puntos_4_6_plus/interpretaciones.md`
- Metadatos del modelo final: `artifacts/metadata_modelo.json`

Para regenerar tablas, figuras y el notebook desde la raiz del proyecto:

```powershell
.\.venv\Scripts\python.exe src\generar_puntos_4_6_plus.py
```

Verificaciones realizadas por el script:

- El dataset usado es `data/processed/modelado/dataset_modelado_nivel_actividad_firms.parquet`.
- El dataset contiene 7923 filas.
- Los splits conservan claves unicas: train 5546, validation 1188, test 1189.
- k=3 reconstruido coincide con el target vigente: 0 diferencias.
- Las distribuciones de k=3, k=4 y k=5 suman 7923 observaciones.
- Las variables predictoras coinciden con Random Forest V1.
- Los hiperparametros coinciden con `artifacts/metadata_modelo.json`.

