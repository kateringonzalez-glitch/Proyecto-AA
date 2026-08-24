# Recomendación del dataset Open-Meteo departamento-día

## Decisión

**Dataset aprobado con limitaciones metodológicas documentadas** para diseñar
posteriormente la agregación temporal departamento-semana. No se realizó esa
agregación ni se integró FIRMS.

## Transformación

Las 187 observaciones espaciales diarias se reducen a una fila por departamento
y fecha mediante medias espaciales no ponderadas. Temperatura, humedad, viento,
precipitación y ET₀ conservan medias y extremos con significado explícito. La
precipitación y ET₀ no se suman entre puntos. La dirección dominante utiliza
media circular y conserva la longitud resultante como medida de coherencia.

La salida tiene 62.434 filas (19 departamentos × 3.286 días), sin duplicados,
nulos o problemas de cobertura. Todas las filas utilizaron el 100% de los
puntos esperados. Las 36 comprobaciones reproducibles de muestra coincidieron
con el origen dentro de precisión numérica.

## Limitaciones

La media de una grilla regular aproxima condiciones departamentales, pero no es
una integración areal exacta ni pondera el área efectiva de cada celda.
Montevideo está representado por un único `representative_point()`; por ello no
captura variabilidad espacial interna y sus medias y extremos coinciden. Los
departamentos tienen entre 1 y 19 puntos, aunque esto no induce sumas mayores
porque las variables principales se basan en medias.

La dirección circular sólo debe interpretarse junto con
`wind_direction_10m_resultant_length`. En la salida real su rango fue
0,0254–1: los valores bajos señalan días en que la media direccional es poco
representativa. No se eliminaron esos casos.
