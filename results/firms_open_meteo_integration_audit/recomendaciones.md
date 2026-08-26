# Recomendaciones de la integración FIRMS + Open-Meteo

## Resultado

Integración aprobada con una limitación documental: el Parquet regional demuestra
cobertura desde el 01/01/2018, pero el repositorio no contiene el script ni el
comprobante de la descarga FIRMS original.

Las filas Open-Meteo anteriores a FIRMS conservan el target nulo. Esos nulos
significan **target no disponible**, no `Sin detección`.

## Columnas que NO pueden utilizarse directamente como X predictivo

- meteorología de la misma semana `t`;
- `cantidad_detecciones` de `t`;
- cualquier variable construida con FIRMS de `t`;
- `nivel_actividad_firms` y su código ordinal.

El futuro dataset predictivo deberá usar exclusivamente información cerrada antes
del inicio de la semana objetivo. Esta tarea no crea lags, ventanas, particiones ni
modelos.
