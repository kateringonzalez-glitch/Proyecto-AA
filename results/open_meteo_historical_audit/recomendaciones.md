# Recomendación de la extracción histórica Open-Meteo

## Decisión

**Extracción aprobada para continuar con el diseño de agregación espacial y
temporal.** Esta aprobación no autoriza ni ejecuta todavía la agregación por
departamento, la construcción semanal o la integración con FIRMS.

## Evidencia de aceptación

- catálogo activo: 187 coordenadas validadas y 19 departamentos;
- período: 02/01/2017–31/12/2025, 3.286 días por coordenada;
- filas: 614.482 esperadas y 614.482 observadas;
- fechas faltantes: 0;
- duplicados exactos o por `coordenada_id + fecha`: 0;
- nulos e infinitos en las ocho variables: 0;
- inconsistencias temperatura mínima/máxima: 0;
- inconsistencias humedad mínima/máxima: 0;
- anomalías según rangos físicos generales: 0;
- unidades: una combinación uniforme en las 1.683 respuestas de ubicación/año;
- timezone: `America/Montevideo`, `GMT-3`, UTC−10.800 s en todas las respuestas;
- coordenadas con más de una celda reportada entre años: 0;
- diferencias respecto de la auditoría espacial previa: 0;
- cruces departamentales o puntos fuera de Uruguay: 0;
- años y departamentos: 100% de completitud.

La extracción necesitó varias ventanas por límites horario y diario de la API
gratuita. El manifiesto conserva 171 descargas exitosas, los intentos fallidos
por HTTP 429 y las reutilizaciones de checkpoints. La repetición final del
comando reutilizó los 171 raw y realizó cero llamadas nuevas.

## Limitaciones

`era5_seamless` es reanálisis y no garantiza disponibilidad operacional previa
al evento. En una futura predicción temporal deberán respetarse fechas de corte
y rezagos de publicación. La dirección del viento es angular y no debe
promediarse aritméticamente. Todavía debe definirse cómo resumir los múltiples
puntos diarios por departamento y cómo cerrar cada semana sin fuga temporal.
