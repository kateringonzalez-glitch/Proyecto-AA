# Recomendación del rediseño espacial Open-Meteo

## Decisión

**Catálogo aprobado para una futura extracción histórica**, sin ejecutar todavía
2017–2025 y sin modificar aún `config/open_meteo.json`.

El catálogo aprobado es
`data/reference/open_meteo_coordinates_validated.csv`: contiene 187 coordenadas
y mantiene los 19 departamentos.

## Margen seleccionado

Se evaluaron 0, 5.000, 7.500 y 10.000 metros respecto de todo el límite del
departamento en EPSG:32721.

| Margen | Puntos de grilla | Departamentos con grilla | Eliminados |
|---:|---:|---:|---:|
| 0 m | 283 | 19 | 0 |
| 5.000 m | 206 | 18 | 77 |
| 7.500 m | 186 | 18 | 97 |
| 10.000 m | 154 | 18 | 129 |

Se seleccionaron 7.500 m porque superan como referencia el desplazamiento
máximo de 6,46 km observado en el piloto, conservan 186 puntos regulares y
evitan perder otros 32 puntos frente a 10 km. No se interpreta esa referencia
empírica como una garantía universal.

Montevideo queda sin nodos regulares con cualquier margen desde 5 km. Se agregó
un único `representative_point()` reproducible, no manual, a 5.540,56 m de su
límite. Así, el catálogo candidato contiene 186 puntos de grilla y un fallback.

## Auditoría real

Se consultaron las 187 coordenadas para el 06/08/2018 con `era5_seamless`,
`cell_selection=land`, timezone `America/Montevideo`, las ocho variables y las
unidades del diseño principal.

- primera ejecución: 19 requests HTTP 200;
- segunda ejecución: 0 llamadas, 19 checkpoints reutilizados;
- válidas: 187/187 (100%);
- cambios de departamento: 0;
- fuera de Uruguay: 0;
- departamentos con 100% de validez: 19;
- nulos meteorológicos: 0;
- claves duplicadas: 0.

El desplazamiento solicitado–reportado tuvo media 3.833,64 m, mediana 3.910,23
m, P90 5.519,56 m, P95 5.917,29 m y máximo 6.578,32 m.

## Casos sensibles

El fallback de Montevideo fue reportado como `(-34.8, -56.199997)`, a 3.883,07
m, dentro de Montevideo. Los 12 puntos de Rocha fueron válidos; el punto regular
problemático del piloto anterior ya no pertenece al candidato. Artigas, Rivera,
Cerro Largo, Rocha, Salto, Paysandú y Río Negro tuvieron 100% de puntos válidos
y ninguna celda reportada fuera de Uruguay.

No hubo puntos problemáticos que reemplazar o excluir. Si una auditoría futura
detectara un fallo, la regla propuesta es excluirlo y evaluar el siguiente nodo
de la misma grilla con mayor distancia interior; sólo usar un
`representative_point()` cuando el departamento no conserve nodos. No se
ejecutó ese ciclo porque no fue necesario.

## Cambio futuro pendiente

Cuando se autorice la extracción histórica, la configuración debería apuntar a
`data/reference/open_meteo_coordinates_validated.csv`, conservar el margen
documentado de 7.500 m y registrar 187 coordenadas definitivas. Ese cambio no se
aplicó todavía.
