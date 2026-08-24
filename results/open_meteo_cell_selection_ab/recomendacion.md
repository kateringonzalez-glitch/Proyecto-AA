# Recomendación del micro-piloto `cell_selection`

## Decisión

**Opción C — ninguno es suficiente; rediseñar los puntos problemáticos.**

No se modifica `config/open_meteo.json` ni se reconstruye el catálogo en esta
etapa. Tampoco se autoriza la extracción de las 283 coordenadas.

## Evidencia

Se consultó el 06/08/2018 para las cinco coordenadas exactas del piloto previo.
La única diferencia entre requests fue `cell_selection=land` frente a
`cell_selection=nearest`.

| Variante | Mismo departamento | Cambios/problemáticos | Distancia media | Mediana | Máximo |
|---|---:|---:|---:|---:|---:|
| `land` | 4/5 | 1 | 4.530,88 m | 4.323,32 m | 6.464,59 m |
| `nearest` | 4/5 | 1 | 4.287,50 m | 4.323,32 m | 5.400,82 m |

`nearest` reduce 243,38 m la media y 1.063,77 m el máximo, pero no mejora la
correspondencia departamental.

### Rocha

- solicitada: `(-34.767374, -54.541496)`;
- `land`: `(-34.8, -54.6)`, 6.464,59 m, ubicada en Maldonado;
- `nearest`: `(-34.8, -54.5)`, 5.247,68 m, fuera de los 19 polígonos ADM1 de
  Uruguay según geoBoundaries;
- reducción de distancia: 1.216,91 m, sin resolver la asignación espacial.

### Montevideo

Ambas variantes devolvieron `(-34.8, -56.199997)`, a 2.156,34 m del punto
solicitado, dentro de Montevideo.

### Frontera — Rivera

Ambas variantes devolvieron `(-31.0, -55.699997)`, a 5.400,82 m del punto
solicitado, dentro de Rivera y de Uruguay según la capa utilizada.

## Compatibilidad técnica

Ambas variantes devolvieron cinco filas, las ocho variables diarias, unidades
esperadas (`°C`, `%`, `m/s`, `°`, `mm`), timezone `America/Montevideo`, arreglos
de un elemento y cero nulos. La primera corrida realizó dos requests HTTP 200;
la segunda realizó cero llamadas y reutilizó dos checkpoints.

## Interpretación de coordenadas

La documentación oficial describe la latitud/longitud de respuesta como el
centro WGS84 de la celda meteorológica utilizada. Indica además que `land`
prefiere una celda terrestre con elevación similar usando un modelo digital de
elevación, mientras `nearest` elige la celda posible más cercana. Por ello se
tratan como coordenadas reportadas por la API y no como las coordenadas pedidas.

Fuentes oficiales:

- https://open-meteo.com/en/docs/historical-weather-api
- https://github.com/open-meteo/open-meteo/blob/main/openapi/historical-weather.yml

Antes de una extracción masiva corresponde definir y probar un margen interior
respecto de costas y límites departamentales. Esa reconstrucción queda fuera de
este micro-piloto.
