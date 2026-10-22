# Interpretaciones sinteticas

## Punto 4
- `Sin actividad` concentra 4967 observaciones (62.69% del dataset) y todos sus conteos son cero.
- `Alto` conserva en los datos locales el rango 5-173, pero su mediana es 7 y el tercer cuartil es 9; el maximo representa una cola extrema, no el comportamiento tipico.
- Los cuartiles se calcularon sobre observaciones reales agrupadas por la etiqueta final; no se eliminaron valores extremos.

## Punto 6
- La inercia baja de 265.63 con k=2 a 34.09 con k=5. La mejora se desacelera, y Silhouette por si sola no define la solucion porque al aumentar K se fragmentan los conteos positivos.
- Los boxplots meteorologicos comparan distribuciones por clase; son evidencia descriptiva y no prueban causalidad ni significacion estadistica.
- En el Random Forest V1 evaluado en test, la clase con menor F1 en k=3 es `Bajo` (F1=0.251).

## Plus
- El mejor F1 macro de test dentro de la sensibilidad fue 0.3967 en k3; esto no reabre la seleccion del modelo, solo documenta sensibilidad al target.
- Al aumentar K, las clases positivas representan particiones distintas del conteo, por lo que sus F1 por clase no son comparables como si fueran las mismas categorias.
- Clase mas pequena por escenario:
  - k3: Alto, 453 observaciones (5.72%).
  - k4: Perfil positivo 4, 174 observaciones (2.20%).
  - k5: Perfil positivo 5, 106 observaciones (1.34%).

Todas las ejecuciones usaron las mismas claves departamento-semana, variables V1 permitidas, splits guardados e hiperparametros del Random Forest seleccionado.