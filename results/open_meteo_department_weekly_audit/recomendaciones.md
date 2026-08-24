# Recomendación del dataset Open-Meteo departamento-semana

## Decisión

**Dataset aprobado con limitaciones para construir posteriormente variables
predictivas rezagadas.** No se integró FIRMS ni se generaron lags.

La salida contiene 469 semanas completas lunes–domingo y 8.911 claves
departamento-semana. La semana 29/12/2025–04/01/2026 fue excluida de forma
general por observar sólo tres días en los 19 departamentos. No hay duplicados,
nulos ni problemas de cobertura temporal o espacial heredada.

## Agregación

Temperaturas, humedades y viento conservan medias temporales y extremos con
interpretación física. Precipitación y ET₀ se suman a lo largo de los siete
días, pero no entre puntos espaciales. La precipitación conserva además máximo
diario y cantidad de días con valor mayor que cero.

La dirección semanal es una media circular de las siete direcciones dominantes
diarias. Su longitud resultante temporal debe acompañarla: el rango observado
0,0074–0,9955 demuestra que algunas semanas tienen direcciones muy dispersas y
una media poco representativa. La columna separada de consistencia espacial
diaria media no debe confundirse con esta concentración temporal.

Se conservaron íntegramente seis semanas que cruzan años calendario (114 filas),
asignadas al año de su lunes inicial. Las 45 reconciliaciones contra el dataset
diario coincidieron dentro de precisión numérica.

## Compatibilidad y fuga temporal

Las 7.923 claves del panel FIRMS limpio están presentes en Open-Meteo semanal:
100% de cobertura potencial y cero claves faltantes. Esta comprobación no es un
join de datos ni analiza la variable objetivo.

El panel representa meteorología observada durante cada semana. En un escenario
predictivo anticipado, las variables de la semana objetivo no deben utilizarse
como predictores; deberán construirse lags usando únicamente semanas cerradas
antes del lunes objetivo.
