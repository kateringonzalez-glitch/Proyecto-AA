# Recomendaciones de la auditoría METEO/Open-Meteo

## Dictamen

**Opción C: conviene una nueva extracción uniforme y documentada.** El legado
2018–2024 tiene frecuencia diaria y sólo 12 departamentos geométricos, mientras
2025 es horario y cubre los 19. Además, el repositorio no conserva endpoint,
parámetros, unidades configuradas, modelo subyacente ni fecha de descarga.

No se realizó ninguna extracción nueva ni se integraron datos con FIRMS.

## Alcance sugerido para una extracción futura

- Cubrir las semanas completas necesarias para 2018–2025 y los 19 departamentos.
- Definir antes el diseño espacial: un punto reproducible por departamento es
  simple pero no representa su heterogeneidad; una grilla o múltiples puntos
  permitirían mejor representación, con mayor costo y una regla de agregación.
- Registrar endpoint/producto, modelo, timezone, parámetros, unidades, momento
  de descarga y respuesta de metadata.
- Evaluar temperatura, humedad, precipitación y viento sólo después de confirmar
  definiciones y unidades. No reutilizar los índices `riesgo_*` opacos como
  variables definitivas sin recuperar su fórmula.

## Temporalidad y fuga

La meteorología de la misma semana sólo es apropiada para descripción o
clasificación contemporánea. Para anticipar actividad de la semana objetivo,
las variables deberán cerrarse antes de su inicio, por ejemplo con semanas
anteriores. El repositorio no demuestra cuándo estos datos históricos estuvieron
disponibles ni si son observaciones, reanálisis o pronósticos históricos.
