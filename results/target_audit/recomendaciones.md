# Recomendaciones de la auditoría de la variable objetivo

- Clases `0 / 1 / 2–3 / >=4`: **adecuadas con precauciones** para continuar la
  evaluación. Todas aparecen en cada año y departamento, pero su prevalencia
  cambia temporal y espacialmente; no deben congelarse todavía.
- Siete detecciones sin departamento: mantener excluidas mientras no exista una
  capa oficial adicional de frontera/hidrografía. Están a menos de 1 km de un
  límite ADM1. La simulación por cercanía afectaría 7 filas y
  cambiaría 6 clases, pero cercanía no prueba
  pertenencia territorial.
- Semana 29/12/2025–04/01/2026: excluir del futuro dataset supervisado porque
  sólo hay tres días dentro de la cobertura del archivo. La regla reproducible
  recomendada es conservar únicamente semanas cuyo `fecha_fin_semana` sea menor
  o igual que la fecha máxima cubierta por la fuente. Esto quitaría 19 filas y
  dejaría 7923 observaciones.
- No se creó un panel corregido ni se modificó el panel original.
