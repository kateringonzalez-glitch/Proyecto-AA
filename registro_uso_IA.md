Registro de uso de Inteligencia Artificial

Proyecto: Proyecto de Aprendizaje Automático (PAA) 2026Herramientas utilizadas: ChatGPT y CodexFinalidad del registro: documentar las intervenciones de IA que tuvieron incidencia relevante en la formulación, verificación de viabilidad y documentación inicial del proyecto.

Criterio de registro: no se incluyen todas las consultas realizadas. Se registran únicamente las interacciones que influyeron de manera sustantiva en decisiones metodológicas, auditorías de datos o redacción de la propuesta. Las respuestas de IA se presentan de forma resumida cuando la respuesta original fue extensa. Las decisiones no se adoptaron automáticamente: fueron contrastadas con los datos, el código del proyecto anterior y las verificaciones realizadas en Jupyter/Codex.

1. Formulación inicial del problema de aprendizaje automático

Prompt utilizado

¿Entonces hay que aplicar un modelo de regresión con una serie temporal?

Respuesta obtenida / aporte de la IA

La IA indicó que no era necesario formular el problema como una regresión de serie temporal. Propuso distinguir entre:

clasificación: estimar si habrá al menos una detección de foco de calor;

regresión de conteos: estimar cuántas detecciones habrá;

pronóstico de serie temporal: estimar un valor agregado en el tiempo.

Como orientación inicial recomendó una clasificación supervisada con componente temporal, donde la salida fuera la probabilidad de registrar al menos una detección FIRMS en una unidad espacial y período futuro. También señaló que el orden temporal debía respetarse en la separación entre entrenamiento, validación y prueba.

Decisión adoptada

Se mantuvo como formulación preliminar un problema de clasificación supervisada con componente temporal, sujeto a la viabilidad real de los datos.

2. Evaluación de Uruguay como área principal

Prompt utilizado

Tengo 8000 datos de FIRMS solo para Uruguay. En ese caso, ¿conviene utilizarlo o conviene integrar Argentina y Brasil?

Respuesta obtenida / aporte de la IA

La IA advirtió que 8.525 detecciones FIRMS no equivalían a 8.525 observaciones de entrenamiento, porque el dataset supervisado debía incluir también períodos y zonas sin detecciones. Recomendó evaluar primero Uruguay y construir una unidad espacio-temporal antes de incorporar Argentina o Brasil.

También señaló que agregar datos regionales sin justificación podía hacer que el modelo aprendiera principalmente patrones de países con mucha mayor cantidad de detecciones y luego no funcionara adecuadamente para Uruguay.

Verificación posterior

La construcción preliminar de un panel departamento-semana produjo:

7.942 observaciones;

2.961 observaciones positivas;

4.981 observaciones negativas;

37,28 % de positivos;

positivos en todos los departamentos y años considerados.

Decisión adoptada

Uruguay se mantiene como ámbito principal del proyecto. Argentina y Brasil no se consideran necesarios en esta etapa para aumentar artificialmente el volumen de datos.

3. Definición preliminar de la unidad espacial

Prompt utilizado

El problema es que para Uruguay no he podido encontrar un archivo útil que divida por departamento de manera efectiva y utilizable.

Respuesta obtenida / aporte de la IA

Inicialmente la IA propuso evaluar una grilla espacial regular para no depender de una división departamental inexistente o poco confiable. Posteriormente se encontró y descargó un GeoJSON de geoBoundaries correspondiente a URY-ADM1, con los límites de los departamentos de Uruguay.

Se utilizó GeoPandas para realizar un spatial join entre las coordenadas FIRMS y los polígonos departamentales.

Verificación posterior

De las 8.525 detecciones FIRMS de Uruguay:

8.518 fueron asignadas a un departamento;

7 quedaron sin asignar;

los 7 casos no asignados se encontraron a menos de 1 km del límite de un departamento, principalmente en zonas costeras o fronterizas.

Decisión adoptada

Se adoptó departamento-semana como unidad preliminar de análisis para evaluar la viabilidad del problema. La decisión sigue abierta a revisión durante etapas posteriores si la integración de variables ambientales lo requiere.

4. Revisión de la integración FIRMS–INUMET

Prompt utilizado

Estoy trabajando en Jupyter Notebook con Python, pandas y GeoPandas. Tengo 8.525 registros FIRMS de Uruguay, asigné 8.518 a departamentos y estoy agregando información meteorológica de INUMET mediante la estación más cercana y merge_asof. Necesito continuar el análisis a partir de datos_uruguay_inumet.

Respuesta obtenida / aporte de la IA

La IA identificó dos problemas diferentes:

Proximidad espacial: asignar la estación INUMET más cercana no garantiza que represente adecuadamente las condiciones meteorológicas del punto FIRMS, especialmente con solo 7 estaciones para todo Uruguay.

Proximidad temporal: utilizar direction="nearest" en merge_asof podía seleccionar una medición posterior a la detección y generar fuga de información.

La IA recomendó utilizar esa unión únicamente como auditoría de cobertura y no como diseño final del dataset predictivo. Para una predicción semanal sugirió utilizar únicamente información disponible hasta el cierre de la semana t para predecir la semana t+1.

Verificación posterior con Codex

Se comprobó que:

INUMET no tiene datos en 2022 ni 2023;

2018 y 2019 tampoco quedan cubiertos;

hay cobertura parcial en 2020 y 2021;

la distancia mediana entre detecciones FIRMS y la estación INUMET más cercana es aproximadamente 83 km;

alrededor de un tercio de las detecciones está a más de 100 km;

nearest conservaba 17 coincidencias adicionales respecto a backward, demostrando que en algunos casos utilizaba una observación meteorológica posterior.

Decisión adoptada

INUMET queda como fuente complementaria y no como única fuente meteorológica del proyecto. Se evitará construir predictores mediante una unión horaria al evento futuro.

5. Auditoría de viabilidad del panel departamento-semana

Prompt enviado a Codex

Quiero que continúes el análisis del PAA a partir de datos_uruguay_inumet y de los archivos ya disponibles, pero sin entrenar modelos todavía.[...]Construir una unidad preliminar departamento-semana, crear todas las combinaciones departamento-semana, completar semanas sin detecciones con cero y evaluar positivos, negativos, distribución anual y departamental.[...]En “¿Es viable continuar solo con Uruguay?” basá la conclusión principalmente en la cantidad de observaciones departamento-semana, porcentaje de positivos, distribución temporal, distribución espacial y cobertura meteorológica.

Respuesta obtenida de Codex

Codex determinó que el panel preliminar era viable para continuar evaluando el problema:

19 departamentos;

418 semanas;

7.942 observaciones;

2.961 positivas;

4.981 negativas;

37,28 % de positivos;

ningún departamento sin positivos.

También concluyó que la principal limitación ya no era la cantidad de detecciones FIRMS, sino la cobertura temporal y espacial de INUMET.

Decisión adoptada

Se mantuvo departamento-semana como estructura preliminar y se decidió auditar otras fuentes ambientales antes de construir el dataset definitivo.

6. Auditoría de METEO y CHIRPS

Prompt enviado a Codex

Quiero continuar únicamente con la verificación de viabilidad de datos para el Entregable 1 del PAA. No corresponde todavía entrenar modelos ni construir el dataset definitivo.[...]Auditar especialmente meteo_2018_2025.parquet y chirps_2018_2025.parquet para determinar si pueden aportar variables ambientales viables a una futura estructura departamento-semana.

Respuesta obtenida de Codex

METEO

Codex encontró que:

el archivo contiene 325.348 filas;

197.215 corresponden a Uruguay;

posee temperatura, humedad, viento, precipitación y otras variables;

mezcla datos diarios de 2018–2024 y horarios de 2025;

tiene mejor cobertura temporal que INUMET;

la cobertura histórica procesada no es homogénea entre departamentos.

Se clasificó como viable condicionado.

CHIRPS

Codex verificó que el archivo no constituye una única serie homogénea. Mezcla:

CHIRPS_ClimateSERV;

Open-Meteo mensual fallback;

CHIRPS.

Además:

la frecuencia es mensual;

gran parte de las coordenadas históricas son nulas;

deficit_hidrico no tiene una definición uniforme entre bloques.

Se clasificó como viable condicionado, principalmente para precipitación mensual rezagada y no como variable semanal directa.

Decisión adoptada

METEO pasó a considerarse la principal fuente meteorológica candidata. CHIRPS e INUMET permanecen como fuentes complementarias sujetas a validación y armonización.

7. Identificación de la procedencia de METEO

Prompt / información proporcionada

Los datos METEO vienen de Open-Meteo y los descargué mediante código.

Se proporcionó código Python que utiliza:

https://archive-api.open-meteo.com/v1/archive

y solicita variables meteorológicas mediante la API de Open-Meteo.

Respuesta obtenida / aporte de la IA

La IA identificó que el endpoint corresponde a la Historical Weather / Archive API de Open-Meteo y señaló que era necesario distinguir este origen de una API de pronósticos históricos.

También observó que el código proporcionado no coincidía exactamente con la estructura de meteo_2018_2025.parquet, por lo que recomendó rastrear el pipeline completo dentro del proyecto anterior.

8. Trazabilidad completa del pipeline METEO

Prompt enviado a Codex

Quiero que rastrees de forma reproducible cómo se generó exactamente el archivo meteo_2018_2025.parquet dentro del proyecto anterior.[...]Reconstruir con evidencia el pipeline exacto: Open-Meteo API → archivo(s) intermedio(s) → transformaciones → meteo_2018_2025.parquet.No inventar pasos y diferenciar lo comprobado, inferido y pendiente.

Respuesta obtenida de Codex

Codex reconstruyó el pipeline:

Open-Meteo Historical Weather API→ CSV diarios por punto→ transform_meteo.py→ meteo_procesado_todos.parquet→ preparar_datasets_2018_2025.py→ bloque histórico de meteo_2018_2025.parquet

meteo_2025.parquet horario→ preparar_meteo_2025.py→ meteo_2018_2025.parquet final.

También encontró que:

las variables diarias históricas fueron solicitadas directamente mediante daily= a Open-Meteo;

el bloque 2025 se obtuvo de forma horaria;

parte de la pérdida de cobertura histórica se debió a un filtro de nombres incompleto en el procesamiento anterior;

un punto denominado Rivera tenía coordenadas correspondientes a Tacuarembó;

los índices riesgo_temp, riesgo_humedad, riesgo_viento, riesgo_sequia, indice_riesgo y nivel_riesgo fueron generados localmente mediante reglas fijas y no utilizan FIRMS.

Decisión adoptada

Se decidió considerar trazables las variables meteorológicas originales, pero excluir inicialmente los índices de riesgo derivados para evitar redundancia y depender de ponderaciones no validadas para el nuevo objetivo predictivo.

También se identificó como posible estrategia futura realizar una nueva extracción homogénea y reproducible de Open-Meteo para los 19 departamentos, en lugar de corregir silenciosamente el dataset heredado.

9. Revisión de la propuesta académica

Prompts utilizados

Se solicitaron revisiones sucesivas de las secciones de la plantilla oficial, entre ellas:

“Cómo completar — estudiante(s): Describir la situación actual [...] Formular con precisión qué se pretende predecir [...]”

“Cómo completar — estudiante(s): Redactar un objetivo general [...] y entre tres y cinco objetivos específicos [...]”

“Cómo completar — estudiante(s): Identificar fuentes, responsables o propietarios, modalidad de acceso [...] calidad conocida y formato [...]”

“Cómo completar — estudiante(s): Presentar una idea preliminar de cómo podría abordarse el proyecto [...]”

“Cómo completar — estudiante(s): Explicar por qué el problema resulta pertinente [...]”

“Cómo completar — estudiante(s): Describir con claridad qué se pretende alcanzar al finalizar el proyecto [...]”

Respuesta obtenida / aporte de la IA

La IA ayudó a redactar y revisar las secciones de la propuesta conforme se incorporaba nueva evidencia. Entre los principales cambios realizados:

reemplazar formulaciones generales por la unidad preliminar departamento-semana;

precisar el horizonte como una semana futura;

evitar presentar INUMET como fuente principal;

incorporar METEO/Open-Meteo como fuente meteorológica candidata;

mantener CHIRPS e INUMET como fuentes complementarias;

evitar denominar incendios confirmados a las detecciones FIRMS;

explicitar riesgos de fuga temporal, cobertura ambiental e integración espacial;

evitar anticipar métricas, modelos o resultados que corresponden a entregables posteriores.

Decisión adoptada

La IA se utilizó como apoyo de redacción y revisión metodológica, mientras que los valores, períodos, coberturas y decisiones técnicas se incorporaron únicamente después de ser contrastados con auditorías de datos y código.

Consideraciones sobre el uso responsable de IA

No se utilizaron respuestas de IA como evidencia empírica por sí mismas.

Los conteos, períodos, coberturas y estructuras de datos fueron verificados mediante Python, Jupyter Notebook, GeoPandas, Parquet y auditorías realizadas con Codex.

Las sugerencias metodológicas fueron revisadas y, cuando fue necesario, modificadas posteriormente.

No se solicitaron ni utilizaron resultados inventados de modelos.

Durante el Entregable 1 no se entrenaron modelos ni se reportaron métricas predictivas finales.

La IA se utilizó principalmente para:

análisis crítico de alternativas;

detección de riesgos metodológicos;

generación de prompts de auditoría;

interpretación de resultados técnicos;

revisión de redacción académica;

organización de documentación y trazabilidad.
