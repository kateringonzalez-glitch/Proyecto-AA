# PAA 2026 — análisis preliminar FIRMS

Este repositorio construye y describe una unidad de análisis
`departamento + semana` para los 19 departamentos de Uruguay. FIRMS se utiliza
como fuente de **detecciones de focos de calor/anomalías térmicas**; no se
interpretan como incendios forestales confirmados. No se entrenan modelos ni se
definen clases finales de riesgo.

## Insumos

- `data/firms_2018_2025.parquet`: archivo regional FIRMS heredado del proyecto
  LIDIA. Uruguay se selecciona mediante la columna real `pais == "URY"`.
- `geoBoundaries-URY-ADM1-all/geoBoundaries-URY-ADM1.geojson`: 19 límites ADM1
  de geoBoundaries, representativos de 2017, fuente original
  OpenStreetMap/Wambacher y CRS EPSG:4326. Véanse los metadatos y condiciones de
  cita incluidos en esa carpeta.

La asignación espacial reutiliza el criterio encontrado en `Analisis.ipynb`:
unión punto-en-polígono en EPSG:4326 con el predicado `within`. Los puntos no
asignados se exportan para revisión y no se fuerzan al departamento más cercano.
Las superficies exploratorias se calculan desde esos mismos polígonos en UTM
21S (EPSG:32721), por lo que son superficies geométricas aproximadas de esta
capa y no cifras oficiales de área legal.

## Ejecución

Desde la raíz del repositorio:

```bash
python src/build_firms_department_week.py
python src/analyze_firms_department_week.py
python src/audit_firms_target_definition.py
python src/build_firms_department_week_clean.py
python src/audit_open_meteo.py
python src/design_open_meteo_extraction.py
python src/extract_open_meteo.py --dry-run
```

Dependencias disponibles en el entorno del repositorio: Python, pandas,
GeoPandas, pyarrow y Altair. Los scripts admiten rutas alternativas mediante
`--help`.

Para crear un entorno local e instalar las dependencias declaradas:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Colaboración mediante GitHub

Los scripts, pruebas, configuraciones, documentación, auditorías y paneles
procesados se versionan en GitHub. Las respuestas crudas de Open-Meteo, las
particiones intermedias y los Parquet heredados ubicados directamente en
`data/` se excluyen mediante `.gitignore` porque son insumos locales o
artefactos regenerables.

En particular, para reconstruir desde cero el panel FIRMS se necesita colocar
localmente el archivo heredado `data/firms_2018_2025.parquet`. Los paneles FIRMS
ya construidos y las agregaciones meteorológicas finales sí están versionados,
de modo que otra persona puede revisar los resultados y continuar las etapas
posteriores sin repetir las descargas crudas.

Flujo recomendado para colaborar:

```bash
git pull --rebase origin main
# realizar y verificar cambios
git add <archivos>
git commit -m "Descripción breve del cambio"
git push origin main
```

## Salidas

- `results/data/`: panel en Parquet/CSV, auditoría JSON, áreas y detecciones no
  asignadas.
- `results/analysis/`: estadísticas generales, departamentales, temporales,
  frecuencias positivas y escenarios de cortes cuantílicos.
- `results/figures/`: visualizaciones HTML interactivas (cargan las bibliotecas
  Vega desde CDN al abrirse).
- `results/target_audit/`: auditoría separada de clases candidatas, siete puntos
  sin departamento y semana final parcial. No reemplaza el panel original.
- `results/data/firms_departamento_semana_clean.parquet`: panel FIRMS depurado
  para su futura integración con predictores. No sobrescribe el panel original.
- `results/clean_audit/`: trazabilidad, distribuciones y filas excluidas durante
  la construcción del panel limpio.
- `results/open_meteo_audit/`: auditoría de cobertura, esquema, calidad y
  compatibilidad potencial del METEO/Open-Meteo heredado con las claves FIRMS.

La grilla va desde el lunes de la primera fecha FIRMS uruguaya hasta el lunes
de la última, e incluye todas las combinaciones de departamento y semana. La
fecha de inicio es la clave; `anio` es el año de ese lunes y `numero_semana` su
ordinal entre los lunes del año (1–53). Una semana puede cruzar el límite del período;
`fecha_fin_semana` se incluye para hacerlo explícito. Los totales anuales y
mensuales de detecciones usan la fecha original de adquisición. Los ceros significan que
no hay detecciones FIRMS asignadas en el archivo durante esa combinación, no
que se haya probado la ausencia de fuego.

## Alcance metodológico

Las alternativas de terciles, cuartiles y mediana/P90 se calculan sólo sobre
conteos positivos para mostrar balance y cortes repetidos. No son una decisión
de clases. La cantidad de detecciones de la propia semana no debe usarse como
predictor; cualquier futura variable FIRMS deberá estar cerrada antes de la
semana objetivo.

## Depuración final FIRMS para el PAA

Los archivos FIRMS, los límites administrativos y `Analisis.ipynb` provienen de
la etapa heredada del Proyecto LIDIA. Para el PAA se desarrollaron la unión
espacial auditada, la grilla completa departamento-semana, los análisis de
distribución y el constructor del panel limpio.

El panel limpio conserva exclusivamente las 8.518 detecciones que intersectan
un departamento. Los siete puntos no asignados continúan excluidos y disponibles
en la auditoría: están próximos a límites, pero no existe evidencia cartográfica
suficiente para reasignarlos reproduciblemente.

Los conteos extremos de Paysandú (100) y Río Negro (173) de la semana iniciada
el 27/12/2021 se conservan sin clipping, winsorización o imputación. Fueron
auditados sin encontrar duplicación exacta o error evidente y representan
detecciones FIRMS/anomalías térmicas, no incendios confirmados independientes.

Se excluyen automáticamente las semanas cuyo fin teórico supera la fecha máxima
de FIRMS mediante `fecha_fin_semana <= fecha_maxima_firms_uruguay`. La categoría
`nivel_actividad_firms` usa provisionalmente `0 / 1 / 2–3 / >=4`, junto con un
código ordinal 0–3. Es una definición candidata de actividad observada, no una
predicción ni un riesgo estimado, y deberá validarse con la futura partición
cronológica.

La fecha de inicio (lunes) es la referencia semanal principal. `anio` es el año
de ese lunes y `numero_semana` es su ordinal entre los lunes del mismo año; no es
el calendario ISO. Así, 27/12/2021–02/01/2022 se conserva como año 2021, semana
52, sin ambigüedad porque ambas fechas también quedan almacenadas.

Para reconstruir y probar el artefacto limpio:

```bash
python src/build_firms_department_week_clean.py
python -m unittest discover -s tests -v
```

## Auditoría METEO/Open-Meteo heredado

La auditoría se ejecuta con:

```bash
python src/audit_open_meteo.py
```

El repositorio no conserva el extractor, endpoint, parámetros, modelo ni
metadata de unidades de Open-Meteo. El archivo combinado heredado cambia de
estructura: 2018–2024 es diario y sólo representa 12 departamentos mediante
puntos, mientras 2025 es horario y contiene un punto para cada uno de los 19.
Por ello METEO no se considera todavía una fuente definitiva. Los resultados y
la recomendación de extracción uniforme quedan en `results/open_meteo_audit/`.

## Diseño de la nueva extracción Open-Meteo

La descarga heredada no se reutiliza como fuente principal debido a su cambio
de frecuencia/esquema, cobertura incompleta y falta de trazabilidad. Se preparó
una extracción nueva, todavía **no ejecutada**, con la Historical Weather API y
el producto fijo `era5_seamless`.

- período: 02/01/2017–31/12/2025, incluyendo 52 semanas previas a FIRMS;
- frecuencia: diaria;
- timezone: `America/Montevideo`;
- unidades explícitas: °C, m/s, mm, %, grados;
- ocho variables meteorológicas originales, sin índices `riesgo_*` heredados;
- 283 coordenadas de una grilla de 25 km construida en EPSG:32721 y contenida
  estrictamente dentro de los 19 departamentos;
- raw futuro separado de datos normalizados y checkpoints por lote/año.

Configuración y documentación:

- `config/open_meteo.json`;
- `data/reference/open_meteo_coordinates.csv`;
- `docs/open_meteo_extraction_design.md`.

El modo por defecto no usa la red:

```bash
python src/design_open_meteo_extraction.py
python src/extract_open_meteo.py --dry-run
```

Sólo `--execute` habilita llamadas HTTP futuras. Debe aprobarse previamente el
uso de ERA5-Seamless, que mantiene un único producto API pero combina variables
subyacentes ERA5-Land y ERA5.

## Piloto real Open-Meteo

Se ejecutó un piloto protegido de cinco coordenadas y dos semanas de siete días
(06–12/08/2018 y 04–10/08/2025). La única forma de habilitar sus llamadas es:

```bash
python src/run_open_meteo_pilot.py --pilot --execute
```

La primera ejecución realizó dos requests y generó 70 filas; la repetición del
mismo comando realizó cero llamadas y reutilizó ambos JSON raw. Los resultados
están separados en `data/raw/open_meteo_pilot/`,
`data/processed/open_meteo_pilot/` y `results/open_meteo_pilot/`.

El piloto no autoriza aún la extracción completa: la celda devuelta para el
punto costero solicitado en Rocha cae en Maldonado según geoBoundaries. Antes
de escalar debe ajustarse el catálogo usando las coordenadas efectivamente
devueltas por el modelo. Véase `docs/open_meteo_pilot.md`.

### Comparación `cell_selection`

El micro-piloto A/B del 06/08/2018 se reproduce con:

```bash
python src/compare_open_meteo_cell_selection.py --cell-selection-ab --execute
```

`land` y `nearest` mantuvieron 4 de 5 puntos en el departamento solicitado.
Para Rocha, `land` cayó en Maldonado y `nearest` quedó fuera de los polígonos
ADM1 uruguayos. Por tanto, ninguno resuelve el problema: la recomendación es
rediseñar los puntos costeros/fronterizos antes de auditar el catálogo entero,
sin cambiar todavía `config/open_meteo.json`. Los artefactos están en
`results/open_meteo_cell_selection_ab/`.

## Rediseño y auditoría del catálogo espacial

Se mantuvo provisionalmente `cell_selection=land` y se evaluaron márgenes
interiores de 0, 5, 7,5 y 10 km en EPSG:32721. Se eligió 7,5 km: conserva 186
nodos de grilla; Montevideo recibe un `representative_point()` reproducible.
El catálogo candidato suma 187 coordenadas.

La auditoría real de un único día (`2018-08-06`) confirmó que las 187
coordenadas reportadas por Open-Meteo permanecen en su departamento. No hubo
cruces departamentales, puntos fuera de Uruguay, nulos ni duplicados. La segunda
ejecución reutilizó los 19 checkpoints sin llamadas nuevas.

```bash
python src/redesign_open_meteo_spatial_grid.py
python src/audit_open_meteo_spatial_catalog.py --spatial-audit --execute
```

El catálogo auditado queda en
`data/reference/open_meteo_coordinates_validated.csv`. Fue aprobado como
insumo espacial y posteriormente incorporado explícitamente a
`config/open_meteo.json` para iniciar la extracción histórica descrita debajo.

## Extracción histórica diaria 2017–2025

La configuración principal fue actualizada al catálogo validado de 187 puntos,
`era5_seamless`, `cell_selection=land` y 02/01/2017–31/12/2025. El plan produce
614.482 filas mediante 171 jobs anuales/lotes de hasta 10 coordenadas.

```bash
python src/extract_open_meteo.py --dry-run
python src/extract_open_meteo.py --execute
python src/audit_open_meteo_historical_extraction.py
```

La extracción se completó mediante ventanas de cuota gratuita: 171 jobs raw y
171 particiones produjeron 614.482 filas, 187 coordenadas y 3.286 días por
coordenada. El comando `--execute` es reanudable y vuelve a validar cada raw
antes de reutilizarlo. Una repetición final reutilizó los 171 checkpoints sin
llamadas HTTP. La nueva extracción PAA se guarda en `data/raw/open_meteo/` y
`data/processed/open_meteo_daily/`; no reemplaza los METEO heredados de LIDIA.

La auditoría final está en `results/open_meteo_historical_audit/`: confirmó
100% de completitud temporal y departamental, cero nulos, duplicados, fechas
faltantes, cambios de celda o cruces departamentales. Todavía no se agregaron
los puntos por departamento o semana ni se integró Open-Meteo con FIRMS.

## Open-Meteo departamento-día

El trabajo nuevo del PAA transforma las 614.482 filas `coordenada + día` en
62.434 filas `departamento + día`:

```bash
python src/build_open_meteo_department_daily.py
```

La agregación utiliza medias espaciales no ponderadas sobre la grilla regular y
conserva extremos espaciales interpretables. Precipitación y ET₀ no se suman
entre puntos, porque eso dependería artificialmente de la cantidad de
coordenadas. La dirección del viento usa media circular y longitud resultante.

Montevideo tiene un único punto fallback; sus medias y extremos coinciden y no
representan variabilidad interna. La media espacial no es una media areal exacta
ponderada por superficie.

- dataset: `data/processed/open_meteo_department_daily/open_meteo_department_daily_2017_2025.parquet`;
- auditoría: `results/open_meteo_department_daily_audit/`.

En esa etapa, la salida diaria quedó validada antes de construir la agregación
semanal descrita a continuación. Todavía no se construyeron lags ni se integró
Open-Meteo con FIRMS.

## Open-Meteo departamento-semana

La transformación temporal del PAA agrupa el dataset departamento-día en
semanas completas lunes–domingo:

```bash
python src/build_open_meteo_department_weekly.py
```

Se obtuvieron 469 semanas completas y 8.911 filas. La semana parcial iniciada
el 29/12/2025 se excluye mediante conteo real de días. Temperatura, humedad y
viento utilizan medias/extremos; precipitación y ET₀ se acumulan temporalmente;
la dirección utiliza media circular y longitud resultante.

- dataset: `data/processed/open_meteo_department_weekly/open_meteo_department_weekly_2017_2025.parquet`;
- auditoría: `results/open_meteo_department_weekly_audit/`.

La auditoría previa confirmó que las 7.923 claves del panel FIRMS limpio tienen
correspondencia meteorológica. Estas variables describen la misma semana; para
predicción anticipada deberán generarse posteriormente versiones rezagadas con
información cerrada antes de la semana objetivo.

## Integración histórica FIRMS + Open-Meteo

La primera integración utiliza Open-Meteo como tabla principal y realiza un
`LEFT JOIN` 1:1 mediante la clave exacta
`departamento + fecha_inicio_semana`:

```bash
python src/build_firms_open_meteo_weekly_history.py
```

Se conservan las 469 semanas meteorológicas y los 19 departamentos. Las 52
semanas de 2017 mantienen `cantidad_detecciones`, `nivel_actividad_firms` y su
código ordinal como nulos, con `target_firms_disponible=False`. Esos nulos
significan **target no disponible** y no deben interpretarse como la clase
`Sin detección`.

Artefactos principales:

- histórico completo: `data/processed/firms_open_meteo_weekly/open_meteo_firms_weekly_history.parquet`;
- vista con target: `data/processed/firms_open_meteo_weekly/open_meteo_firms_weekly_target_available.parquet`;
- auditoría: `results/firms_open_meteo_integration_audit/`.

El archivo FIRMS regional contiene registros desde el 01/01/2018 en Argentina
y Brasil; Uruguay presenta su primera detección positiva el 02/01/2018. Esto
permite defender la semana iniciada el 01/01 como cubierta, aunque no se encontró
en el repositorio el script o comprobante original de descarga FIRMS.

Las variables meteorológicas integradas describen la misma semana `t` y todavía
no forman el conjunto `X` predictivo. Tampoco pueden utilizarse directamente
como predictores `cantidad_detecciones`, el nivel FIRMS, su código ni ninguna
variable FIRMS de `t`. La historia de 2017 se conserva para construir en una
etapa posterior lags y ventanas cerrados antes del inicio de la semana objetivo.
