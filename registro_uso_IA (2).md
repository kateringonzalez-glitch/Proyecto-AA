# Registro de uso de Inteligencia Artificial

**Proyecto:** Proyecto de Aprendizaje Automático (PAA) 2026  
**Herramientas utilizadas:** ChatGPT y Codex  

Este registro resume únicamente las interacciones con IA que tuvieron incidencia relevante en la definición del problema, la evaluación de viabilidad y la revisión técnica de los datos. No se incluyen consultas de redacción o completado de la plantilla del Entregable 1.

---

## 1. Evaluación de la aplicación de aprendizaje automático

**Herramienta:** ChatGPT

### Prompt utilizado

> Tenemos que hacer un proyecto de aprendizaje automatico que es realizado teniendo en cuenta el proyecto de base de datos trabajado antriormente consideras que es posible esta aplicacion de AA

### Resultado utilizado

Se analizó la viabilidad de continuar el proyecto anterior mediante una solución de aprendizaje automático. La recomendación fue formular un problema predictivo utilizando los datos ambientales y de focos de calor ya integrados, evitando definir un modelo concreto antes de comprobar la cobertura y calidad de los datos.

---

## 2. Selección del problema más adecuado según los datos disponibles

**Herramienta:** ChatGPT

### Prompt utilizado

> cual crees que seria lo mejor con los datos que tenemos?

### Resultado utilizado

Se compararon distintas posibilidades de aprendizaje automático y se priorizó una formulación relacionada con la estimación de riesgo de futuras detecciones de focos de calor. Se destacó que la elección debía depender de la granularidad, cobertura temporal y disponibilidad real de las variables ambientales.

---

## 3. Utilidad práctica de las propuestas de aprendizaje automático

**Herramienta:** ChatGPT

### Prompt utilizado

> pero de que sirven estas propuestas, que problema pueden resolver?

### Resultado utilizado

Se revisó la utilidad esperada de las posibles propuestas. Se concluyó que la solución debía aportar una función concreta, por ejemplo identificar departamentos y períodos con mayor probabilidad estimada de registrar focos de calor, en lugar de limitarse a predecir una variable sin una finalidad claramente definida.

---

## 4. Evaluación de Uruguay frente a la incorporación de Argentina y Brasil

**Herramienta:** ChatGPT

### Prompt utilizado

> Tengo 8000 datos de FIRMS solo para Uruguay. En ese caso, ¿conviene utilizarlo o conviene integrar Argentina y Brasil?

### Resultado utilizado

Se señaló que la cantidad de detecciones FIRMS no debía interpretarse directamente como el número de observaciones del futuro conjunto de entrenamiento. Se recomendó evaluar primero una estructura espacio-temporal para Uruguay antes de agregar otros países.

Posteriormente se verificó una estructura preliminar de 19 departamentos por 418 semanas, con 7.942 observaciones departamento-semana y 37,28 % de casos positivos. A partir de esta comprobación se mantuvo Uruguay como ámbito principal del proyecto.

---

## 5. Revisión del tipo de problema predictivo

**Herramienta:** ChatGPT

### Prompt utilizado

> ¿Entonces hay que aplicar un modelo de regresión con una serie temporal?

### Resultado utilizado

Se aclaró que el proyecto no requería necesariamente una regresión ni un modelo clásico de series temporales. La alternativa considerada más coherente fue una **clasificación supervisada con componente temporal**, donde cada observación represente un departamento y una semana, y la variable objetivo indique si durante la semana siguiente se registra al menos una detección FIRMS.

También se identificó la necesidad de respetar el orden temporal de los datos y evitar utilizar información posterior al momento de predicción.

---

## 6. Problema de representación espacial de Uruguay

**Herramienta:** ChatGPT

### Prompt utilizado

> El problema es que para Uruguay no he podido encontrar un archivo útil que divida por departamento de manera efectiva y utilizable.

### Resultado utilizado

Se consideró inicialmente utilizar una grilla espacial regular como alternativa. Posteriormente se obtuvo un archivo GeoJSON con los límites departamentales de Uruguay y se realizó la asignación espacial de las detecciones FIRMS.

De 8.525 detecciones de Uruguay, 8.518 pudieron asociarse directamente a un departamento. Esto permitió mantener `departamento-semana` como unidad preliminar de análisis.

---

## 7. Revisión de la integración temporal y espacial con INUMET

**Herramienta:** ChatGPT / Codex

### Prompt utilizado

> Estoy trabajando en Jupyter Notebook con Python, pandas y GeoPandas. Tengo 8.525 registros FIRMS de Uruguay, asigné 8.518 a departamentos mediante un GeoJSON y estoy agregando información meteorológica de INUMET usando la estación más cercana y merge_asof. Necesito continuar el análisis a partir de datos_uruguay_inumet.

### Resultado utilizado

Se identificaron dos riesgos principales:

- la distancia entre una detección FIRMS y la estación INUMET más cercana podía ser demasiado grande para asumir representatividad meteorológica;
- `merge_asof` con `direction="nearest"` podía seleccionar observaciones posteriores al evento, generando fuga de información temporal.

Las verificaciones posteriores mostraron además discontinuidades importantes en INUMET y una cobertura de solo siete estaciones. Por este motivo, INUMET quedó definido como fuente complementaria y no como única fuente meteorológica.

---

## 8. Verificación de la procedencia de los datos METEO

**Herramienta:** ChatGPT / Codex

### Prompt utilizado

> Los datos METEO vienen de Open-Meteo y los descargué mediante código.

### Resultado utilizado

Se identificó Open-Meteo Historical Weather API como origen de los datos meteorológicos. Posteriormente se revisó el código del proyecto anterior para reconstruir el proceso de generación de `meteo_2018_2025.parquet`.

La auditoría permitió comprobar que el archivo final combina datos diarios históricos con datos horarios de 2025 y que parte de las inconsistencias espaciales provenían del procesamiento anterior. Como consecuencia, se definió que METEO/Open-Meteo es la principal fuente meteorológica candidata, pero debe armonizarse antes de utilizarla en el entrenamiento.

---

## 9. Criterio de uso de la IA

Las respuestas de IA fueron utilizadas como apoyo para formular hipótesis, detectar riesgos metodológicos, orientar verificaciones y revisar decisiones técnicas. Las recomendaciones no se aceptaron automáticamente.

Los conteos, coberturas, períodos y características de las fuentes fueron contrastados mediante código, archivos Parquet, GeoPandas, Jupyter Notebook y auditorías del repositorio realizadas con Codex. Durante esta etapa no se entrenaron modelos ni se generaron métricas predictivas finales.
