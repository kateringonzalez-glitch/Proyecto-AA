# Piloto real y acotado de Open-Meteo

Estado: **ejecutado; ajustar antes de aprobar la extracción completa**.

## Alcance y ejecución

El piloto usa exactamente cinco coordenadas del catálogo de 283 puntos y dos
ventanas lunes–domingo: 06–12/08/2018 y 04–10/08/2025. Son 70 filas esperadas y
dos requests. No se descargaron años completos, no se agregó semanalmente y no
se integró FIRMS.

```bash
python src/run_open_meteo_pilot.py --pilot --execute
```

El script aborta si el plan deja de ser 5 coordenadas × 2 ventanas × 7 días.
Sin `--pilot` no funciona y sin `--execute` sólo escribe el plan. Los períodos
se eligieron en el mismo mes y estación, y como semanas completas, para probar
consistencia temporal sin pretender comparar climatología.

## Selección espacial reproducible

La selección se calcula en EPSG:32721 a partir del catálogo y geoBoundaries ADM1:

- Montevideo: punto del departamento de máxima distancia a su límite;
- interior grande: punto más interior de Tacuarembó;
- costa: punto más austral de Rocha, sobre la franja atlántica;
- frontera: punto de Rivera más próximo al borde nacional;
- departamento intermedio: punto más interior de Canelones.

Los IDs, coordenadas, distancias y criterios exactos están en
`results/open_meteo_pilot/coordenadas_piloto.csv`.

## Resultado observado

La primera corrida válida (`20260822T114246838609Z`) hizo dos llamadas HTTP 200,
una por ventana, con 35 filas cada una. La repetición idéntica
(`20260822T114250077829Z`) hizo cero llamadas y reutilizó dos checkpoints. Los
SHA-256 raw permanecieron iguales y el Parquet combinado conservó el SHA-256
`0a0797fc39ff7f9cb181c679b69e73ecfebe787057b08924b15ec6bacb71312c`.

Se obtuvieron 70 claves `coordenada_id + fecha`, sin duplicados y sin nulos en
las ocho variables. Todas las respuestas tuvieron exactamente siete fechas,
las ocho variables solicitadas, sus arreglos de longitud siete, unidades
esperadas y timezone `America/Montevideo` (`GMT-3`, offset −10.800 segundos).
El manifiesto conserva URL, parámetros, estado, intentos, rutas, timestamps y
checksums. La metadata separa coordenadas solicitadas y coordenadas devueltas,
además de elevación y tiempo de generación.

## Hallazgo espacial

Open-Meteo devolvió coordenadas redondeadas a la celda del modelo. Las
distancias solicitada–devuelta fueron de aproximadamente 2,16 a 6,46 km. Los
puntos devueltos de Montevideo, Canelones, Rivera y Tacuarembó permanecieron en
su departamento. El punto costero solicitado en Rocha
(`URY_RO_G_E725000_N6150000`) fue devuelto como `(-34.8, -54.6)` y cae en
Maldonado según la misma capa geoBoundaries. Esto ocurre en ambas ventanas y no
es una variación temporal.

La auditoría completa está en `results/open_meteo_pilot/auditoria_espacial.csv`.
Una corrida preliminar con un criterio costero ambiguo fue preservada, no
mezclada, en `results/open_meteo_pilot_preliminary_superseded/`.

## Recomendación

**Ajustar; no aprobar todavía la extracción completa.** El endpoint, modelo,
timezone, unidades, esquema, normalización y checkpoints funcionaron como se
esperaba. Sin embargo, el catálogo asigna departamento a la coordenada pedida,
mientras la meteorología corresponde a la coordenada/celda devuelta. Antes de
escalar se debe consultar o resolver todas las coordenadas del catálogo y
reasignar departamento según el punto efectivamente devuelto, revisar puntos
que cambien de departamento o salgan del territorio, decidir una regla explícita
para ellos y volver a estimar cobertura departamental. No corresponde aprobar
la descarga masiva hasta cerrar esa decisión.
