# Registro de uso de Inteligencia Artificial

**Proyecto:** Proyecto de Aprendizaje Automático (PAA) 2026  
**Herramientas utilizadas:** ChatGPT y Codex  
**Finalidad del registro:** documentar las intervenciones de IA que tuvieron incidencia relevante en la formulación, verificación de viabilidad y documentación inicial del proyecto.

**Criterio de registro:** no se incluyen todas las consultas realizadas. Se registran únicamente las interacciones que influyeron de manera sustantiva en decisiones metodológicas, auditorías de datos o redacción de la propuesta. Las respuestas de IA se presentan de forma resumida cuando la respuesta original fue extensa. Las decisiones no se adoptaron automáticamente: fueron contrastadas con los datos, el código del proyecto anterior y las verificaciones realizadas en Jupyter/Codex.


## Formulación inicial del problema de aprendizaje automático

**Prompt utilizado**

> ¿Entonces hay que aplicar un modelo de regresión con una serie temporal?

**Respuesta obtenida / aporte de la IA**

La IA indicó que no era necesario formular el problema como una regresión de serie temporal. Propuso distinguir entre:

- clasificación: estimar si habrá al menos una detección de foco de calor;
- regresión de conteos: estimar cuántas detecciones habrá;
- pronóstico de serie temporal: estimar un valor agregado en el tiempo.

Como orientación inicial recomendó una **clasificación supervisada con componente temporal**, donde la salida fuera la probabilidad de registrar al menos una detección FIRMS en una unidad espacial y período futuro. También señaló que el orden temporal debía respetarse en la separación entre entrenamiento, validación y prueba.

**Decisión adoptada**

Se mantuvo como formulación preliminar un problema de clasificación supervisada con componente temporal, sujeto a la viabilidad real de los datos.


## Evaluación de Uruguay como área principal

**Prompt utilizado**

> Tengo 8000 datos de FIRMS solo para Uruguay. En ese caso, ¿conviene utilizarlo o conviene integrar Argentina y Brasil?

**Respuesta obtenida / aporte de la IA**

La IA advirtió que 8.525 detecciones FIRMS no equivalían a 8.525 observaciones de entrenamiento, porque el dataset supervisado debía incluir también períodos y zonas sin detecciones. Recomendó evaluar primero Uruguay y construir una unidad espacio-temporal antes de incorporar Argentina o Brasil.

También señaló que agregar datos regionales sin justificación podía hacer que el modelo aprendiera principalmente patrones de países con mucha mayor cantidad de detecciones y luego no funcionara adecuadamente para Uruguay.

**Verificación posterior**

La construcción preliminar de un panel `departamento-semana` produjo:

- 7.942 observaciones;
- 2.961 observaciones positivas;
- 4.981 observaciones negativas;
- 37,28 % de positivos;
- positivos en todos los departamentos y años considerados.

**Decisión adoptada**

Uruguay se mantiene como ámbito principal del proyecto. Argentina y Brasil no se consideran necesarios en esta etapa para aumentar artificialmente el volumen de datos.


## Definición preliminar de la unidad espacial

**Prompt utilizado**

> El problema es que para Uruguay no he podido encontrar un archivo útil que divida por departamento de manera efectiva y utilizable.

**Respuesta obtenida / aporte de la IA**

Inicialmente la IA propuso evaluar una grilla espacial regular para no depender de una división departamental inexistente o poco confiable. Posteriormente se encontró y descargó un GeoJSON de `geoBoundaries` correspondiente a `URY-ADM1`, con los límites de los departamentos de Uruguay.

Se utilizó GeoPandas para realizar un `spatial join` entre las coordenadas FIRMS y los polígonos departamentales.

**Verificación posterior**

De las 8.525 detecciones FIRMS de Uruguay:

- 8.518 fueron asignadas a un departamento;
- 7 quedaron sin asignar;
- los 7 casos no asignados se encontraron a menos de 1 km del límite de un departamento, principalmente en zonas costeras o fronterizas.

**Decisión adoptada**

Se adoptó **departamento-semana** como unidad preliminar de análisis para evaluar la viabilidad del problema. La decisión sigue abierta a revisión durante etapas posteriores si la integración de variables ambientales lo requiere.


## Revisión de la integración FIRMS–INUMET

**Prompt utilizado**

> Estoy trabajando en Jupyter Notebook con Python, pandas y GeoPandas. Tengo 8.525 registros FIRMS de Uruguay, asigné 8.518 a departamentos y estoy agregando información meteorológica de INUMET mediante la estación más cercana y `merge_asof`. Necesito continuar el análisis a partir de `datos_uruguay_inumet`.

**Respuesta obtenida / aporte de la IA**

La IA identificó dos problemas diferentes:

1. **Proximidad espacial:** asignar la estación INUMET más cercana no garantiza que represente adecuadamente las condiciones meteorológicas del punto FIRMS, especialmente con solo 7 estaciones para todo Uruguay.
2. **Proximidad temporal:** utilizar `direction="nearest"` en `merge_asof` podía seleccionar una medición posterior a la detección y generar fuga de información.

La IA recomendó utilizar esa unión únicamente como auditoría de cobertura y no como diseño final del dataset predictivo. Para una predicción semanal sugirió utilizar únicamente información disponible hasta el cierre de la semana `t` para predecir la semana `t+1`.

**Verificación posterior con Codex**

Se comprobó que:

- INUMET no tiene datos en 2022 ni 2023;
- 2018 y 2019 tampoco quedan cubiertos;
- hay cobertura parcial en 2020 y 2021;
- la distancia mediana entre detecciones FIRMS y la estación INUMET más cercana es aproximadamente 83 km;
- alrededor de un tercio de las detecciones está a más de 100 km;
- `nearest` conservaba 17 coincidencias adicionales respecto a `backward`, demostrando que en algunos casos utilizaba una observación meteorológica posterior.

**Decisión adoptada**

INUMET queda como fuente complementaria y no como única fuente meteorológica del proyecto. Se evitará construir predictores mediante una unión horaria al evento futuro.

## Auditoría de viabilidad del panel departamento-semana

**Prompt enviado a Codex**

> Quiero que continúes el análisis del PAA a partir de `datos_uruguay_inumet` y de los archivos ya disponibles, pero sin entrenar modelos todavía.  
> [...]  
> Construir una unidad preliminar `departamento-semana`, crear todas las combinaciones departamento-semana, completar semanas sin detecciones con cero y evaluar positivos, negativos, distribución anual y departamental.  
> [...]  
> En “¿Es viable continuar solo con Uruguay?” basá la conclusión principalmente en la cantidad de observaciones departamento-semana, porcentaje de positivos, distribución temporal, distribución espacial y cobertura meteorológica.

**Respuesta obtenida de Codex**

Codex determinó que el panel preliminar era viable para continuar evaluando el problema:

- 19 departamentos;
- 418 semanas;
- 7.942 observaciones;
- 2.961 positivas;
- 4.981 negativas;
- 37,28 % de positivos;
- ningún departamento sin positivos.

También concluyó que la principal limitación ya no era la cantidad de detecciones FIRMS, sino la cobertura temporal y espacial de INUMET.

**Decisión adoptada**

Se mantuvo `departamento-semana` como estructura preliminar y se decidió auditar otras fuentes ambientales antes de construir el dataset definitivo.


## Auditoría de METEO y CHIRPS

**Prompt enviado a Codex**

> Quiero continuar únicamente con la verificación de viabilidad de datos para el Entregable 1 del PAA. No corresponde todavía entrenar modelos ni construir el dataset definitivo.  
> [...]  
> Auditar especialmente `meteo_2018_2025.parquet` y `chirps_2018_2025.parquet` para determinar si pueden aportar variables ambientales viables a una futura estructura `departamento-semana`.

**Respuesta obtenida de Codex**

### METEO

Codex encontró que:

- el archivo contiene 325.348 filas;
- 197.215 corresponden a Uruguay;
- posee temperatura, humedad, viento, precipitación y otras variables;
- mezcla datos diarios de 2018–2024 y horarios de 2025;
- tiene mejor cobertura temporal que INUMET;
- la cobertura histórica procesada no es homogénea entre departamentos.

Se clasificó como **viable condicionado**.

### CHIRPS

Codex verificó que el archivo no constituye una única serie homogénea. Mezcla:

- `CHIRPS_ClimateSERV`;
- `Open-Meteo mensual fallback`;
- `CHIRPS`.

Además:

- la frecuencia es mensual;
- gran parte de las coordenadas históricas son nulas;
- `deficit_hidrico` no tiene una definición uniforme entre bloques.

Se clasificó como **viable condicionado**, principalmente para precipitación mensual rezagada y no como variable semanal directa.

**Decisión adoptada**

METEO pasó a considerarse la principal fuente meteorológica candidata. CHIRPS e INUMET permanecen como fuentes complementarias sujetas a validación y armonización.


## Identificación de la procedencia de METEO

**Prompt / información proporcionada**

> Los datos METEO vienen de Open-Meteo y los descargué mediante código.

Se proporcionó código Python que utiliza:

`https://archive-api.open-meteo.com/v1/archive`

y solicita variables meteorológicas mediante la API de Open-Meteo.

**Respuesta obtenida / aporte de la IA**

La IA identificó que el endpoint corresponde a la **Historical Weather / Archive API de Open-Meteo** y señaló que era necesario distinguir este origen de una API de pronósticos históricos.

También observó que el código proporcionado no coincidía exactamente con la estructura de `meteo_2018_2025.parquet`, por lo que recomendó rastrear el pipeline completo dentro del proyecto anterior.


## Trazabilidad completa del pipeline METEO

**Prompt enviado a Codex**

> Quiero que rastrees de forma reproducible cómo se generó exactamente el archivo `meteo_2018_2025.parquet` dentro del proyecto anterior.  
> [...]  
> Reconstruir con evidencia el pipeline exacto: Open-Meteo API → archivo(s) intermedio(s) → transformaciones → `meteo_2018_2025.parquet`.  
> No inventar pasos y diferenciar lo comprobado, inferido y pendiente.

**Respuesta obtenida de Codex**

Codex reconstruyó el pipeline:

`Open-Meteo Historical Weather API`  
→ CSV diarios por punto  
→ `transform_meteo.py`  
→ `meteo_procesado_todos.parquet`  
→ `preparar_datasets_2018_2025.py`  
→ bloque histórico de `meteo_2018_2025.parquet`  
+ `meteo_2025.parquet` horario  
→ `preparar_meteo_2025.py`  
→ `meteo_2018_2025.parquet` final.

También encontró que:

- las variables diarias históricas fueron solicitadas directamente mediante `daily=` a Open-Meteo;
- el bloque 2025 se obtuvo de forma horaria;
- parte de la pérdida de cobertura histórica se debió a un filtro de nombres incompleto en el procesamiento anterior;
- un punto denominado Rivera tenía coordenadas correspondientes a Tacuarembó;
- los índices `riesgo_temp`, `riesgo_humedad`, `riesgo_viento`, `riesgo_sequia`, `indice_riesgo` y `nivel_riesgo` fueron generados localmente mediante reglas fijas y no utilizan FIRMS.

**Decisión adoptada**

Se decidió considerar trazables las variables meteorológicas originales, pero excluir inicialmente los índices de riesgo derivados para evitar redundancia y depender de ponderaciones no validadas para el nuevo objetivo predictivo.

También se identificó como posible estrategia futura realizar una nueva extracción homogénea y reproducible de Open-Meteo para los 19 departamentos, en lugar de corregir silenciosamente el dataset heredado.


## Auditoría y depuración reproducible del panel FIRMS

**Prompt relevante, resumido**

> Auditar las detecciones sin departamento, los valores extremos y las semanas incompletas. Mantener los extremos si no hay evidencia de error y excluir las semanas incompletas mediante una regla general reproducible.

**Respuesta obtenida / aporte de Codex**

Codex apoyó la implementación del panel FIRMS limpio y de controles de departamentos, continuidad semanal, claves duplicadas, nulos y reconciliación de conteos. La regla aplicada a las semanas fue `fecha_fin_semana <= fecha máxima FIRMS Uruguay`; no se eliminaron manualmente fechas ni valores extremos.

**Uso y verificación posterior**

El panel inicial tenía 7.942 filas y 8.518 detecciones asignadas. Se excluyeron las 19 filas de la semana parcial iniciada el 29/12/2025, que contenían 10 detecciones. El panel limpio conservó 7.923 observaciones, 19 departamentos, 417 semanas y 8.508 detecciones. Los siete registros sin departamento permanecieron fuera de los conteos porque no había evidencia suficiente para reasignarlos. Los máximos semanales de 100 y 173 detecciones se conservaron tras la auditoría, sin tratarlos automáticamente como errores. Las comprobaciones quedaron en `src/build_firms_department_week_clean.py` y en los paneles FIRMS procesados.


## Decisión sobre el METEO/Open-Meteo heredado de LIDIA

**Prompt relevante, resumido**

> Auditar cobertura temporal y espacial, frecuencia, variables, calidad, trazabilidad y compatibilidad del METEO/Open-Meteo heredado con `departamento + semana` antes de usarlo como fuente principal.

**Respuesta obtenida / aporte de Codex**

Además de la mezcla de datos diarios históricos y horarios de 2025 ya documentada, la auditoría señaló cobertura departamental no homogénea, cambios de esquema y documentación insuficiente para reproducir exactamente parámetros del request original, producto y unidades en todos los bloques.

**Decisión y verificación posterior**

El equipo no utilizó directamente ese Parquet heredado como fuente meteorológica principal del panel actual ni lo corrigió silenciosamente. Se conservó como antecedente y se diseñó una extracción homogénea nueva; las diferencias de cobertura y esquema se contrastaron con los archivos y el pipeline heredados.


## Diseño y extracción homogénea de Open-Meteo

**Prompt relevante, resumido**

> Diseñar una extracción histórica trazable para los 19 departamentos, manteniendo producto, frecuencia, variables, unidades, zona horaria y criterio espacial constantes durante todo el período.

**Respuesta obtenida / aporte de Codex**

Codex apoyó el diseño de la configuración, el catálogo espacial reproducible, la extracción por lotes y los controles de respuesta, fechas, unidades, duplicados, nulos y cobertura. La configuración final utiliza Open-Meteo Historical Weather API, `era5_seamless`, frecuencia diaria, `cell_selection=land`, `America/Montevideo` y el período 02/01/2017–31/12/2025. Se validaron 187 coordenadas para los 19 departamentos.

**Uso y verificación posterior**

El diseño se incorporó en `config/open_meteo.json`, el catálogo validado y el pipeline `src/extract_open_meteo.py`. La extracción real produjo 614.482 filas coordenada-día (187 × 3.286), sin duplicados de clave ni nulos meteorológicos. Las auditorías de extracción e historial comprobaron cobertura temporal, estabilidad de coordenadas y ausencia de cruces departamentales en el catálogo validado. Los intentos fallidos de descarga se registraron en el manifiesto y no se interpretaron como filas faltantes del dataset final.


## Agregación espacial Open-Meteo a departamento-día

**Prompt relevante, resumido**

> Agregar coordenadas meteorológicas por departamento y día respetando el significado físico de cada variable: no sumar precipitación ni ET0 entre puntos, tratar la dirección del viento circularmente y controlar la cobertura espacial.

**Respuesta obtenida / aporte de Codex**

Se propusieron medias y extremos espaciales según la variable, media circular y longitud resultante para la dirección del viento, además del contraste entre puntos observados y esperados por departamento.

**Uso y verificación posterior**

La implementación quedó en `src/build_open_meteo_department_daily.py`. El resultado contiene 62.434 filas departamento-día (19 × 3.286), sin claves duplicadas ni nulos y con cobertura espacial completa en las comprobaciones del proceso. Los tests y la reconciliación de muestras contrastaron agregados con las filas coordenada-día originales. La precipitación y ET0 no se sumaron entre coordenadas.


## Calidad y selección de variables para clustering

**Prompt relevante, resumido**

> Revisar distribuciones, correlaciones y redundancias de las variables meteorológicas semanales y justificar las transformaciones y la matriz final del clustering.

**Respuesta obtenida / aporte de Codex**

Codex ayudó a examinar cuatro dimensiones meteorológicas: `temperature_2m_max_mean_weekly`, `relative_humidity_2m_min_mean_weekly`, `wind_speed_10m_max_mean_weekly` y `precipitation_sum_weekly`. Se discutió aplicar `log1p` sólo a precipitación y luego `StandardScaler`, ajustado con el período de desarrollo.

**Uso y verificación posterior**

La selección y sus controles se documentaron en `Calidad_Preparacion_Datos.ipynb` y se ejecutaron sobre el dataset semanal real. La matriz final no presentó faltantes, por lo que no se imputaron valores. FIRMS se examinó para diagnóstico y contraste, no como dimensión del clustering meteorológico.


## Clustering meteorológico e interpretación de perfiles

**Prompt relevante, resumido**

> Comparar K-Means y DBSCAN usando sólo meteorología; evaluar distintos valores de `k`, Silhouette y estabilidad, sin forzar concordancia entre métodos. Interpretar A/B/C/D como perfiles nominales y contrastarlos después con FIRMS y estaciones, sin convertirlos automáticamente en niveles de riesgo.

**Respuesta obtenida / aporte de Codex**

La IA ayudó a separar la calidad matemática de la interpretabilidad meteorológica. En `Analisis_No_supervisado.ipynb`, Silhouette fue 0,2755 para `k=3` y 0,2561 para `k=4`; se mantuvo provisionalmente `k=4` para estudiar cuatro regímenes. Con `eps=0,50` y `min_samples=10`, DBSCAN obtuvo dos clusters y 397 observaciones de ruido (6,676 %); el ARI frente a K-Means, sin ruido, fue −0,0019. No se ajustó DBSCAN para que reprodujera K-Means.

**Uso y verificación posterior**

Las cifras proceden de las celdas ejecutadas del notebook, no de una respuesta de IA tomada como fuente primaria. Los perfiles se describieron como A (frío y más lluvioso/húmedo), B (frío y más seco), C (cálido y más lluvioso) y D (cálido y más seco). Las letras son nominales, no una escala Bajo–Alto. `cantidad_detecciones` quedó fuera de `StandardScaler`, K-Means y DBSCAN; se utilizó después para comparar asociaciones históricas por perfil, estación y departamento, sin afirmar causalidad ni identificar las detecciones con incendios confirmados.


## Diseño supervisado M1–M4 como propuesta posterior al Entregable 2

**Prompt relevante, resumido**

> Formular un target binario de presencia FIRMS y comparar M1 (contexto), M2 (contexto + perfil), M3 (contexto + meteorología) y M4 (contexto + meteorología + perfil), con el mismo split cronológico y sin usar el test para elegir modelos.

**Respuesta obtenida / aporte de Codex**

La IA ayudó a plantear las ablaciones M2–M1, M2 frente a M3 y M4–M3, así como una línea base `DummyClassifier` y futuras comparaciones con Regresión Logística y Random Forest. Se estableció train 2018–2023, validation 2024 y test 2025 reservado. También se explicitó que una ausencia de mejora al añadir el perfil sería un resultado válido y no justificaría modificar los experimentos para forzarla.

**Uso, revisión y estado actual**

El diseño fue explorado, pero la experimentación supervisada avanzada se retiró del flujo principal por exceder el Entregable 2. El estado actual conserva el dataset binario, el split y únicamente el Dummy mayoritario evaluado en validation; no presenta M1–M4, Regresión Logística ni Random Forest como resultados vigentes del Entregable 2. El test 2025 permanece reservado. Esta entrada documenta el uso metodológico de IA y no implica que esos modelos deban incorporarse ahora.


## Apoyo en redacción y presentación del Entregable 2

**Prompt relevante, resumido**

> Revisar coherencia conceptual y claridad de la redacción sobre FIRMS, clustering, Silhouette, DBSCAN, perfiles meteorológicos y causalidad en el Entregable 2 y su presentación.

**Respuesta obtenida / aporte de ChatGPT**

ChatGPT se utilizó como apoyo para detectar formulaciones potencialmente equívocas y proponer explicaciones más claras: detecciones FIRMS no equivalen a incendios confirmados; los perfiles meteorológicos no son niveles de riesgo; una asociación descriptiva no demuestra causalidad.

**Uso y verificación posterior**

El equipo revisó las propuestas antes de incorporarlas. Los valores numéricos y resultados experimentales se contrastaron con notebooks, datos y controles del proyecto. El registro no permite atribuir a la IA resultados experimentales como fuente primaria ni verificar desde el repositorio cada cambio concreto de una presentación externa.
