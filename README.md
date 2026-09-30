# Proyecto de Aprendizaje Automático 2026

El PAA estudia **niveles de actividad FIRMS** a nivel departamento–semana en Uruguay. FIRMS registra anomalías térmicas o focos de calor; no confirma incendios forestales.

## Flujo metodológico vigente

```text
FIRMS histórico
      ↓
log1p(cantidad_detecciones)
      ↓
K-Means sobre semanas positivas
      ↓
Sin actividad + niveles positivos de actividad FIRMS
      ↓
target supervisado multiclase
      ↓
meteorología + contexto + antecedentes FIRMS
      ↓
clasificación del nivel de actividad FIRMS
```

Los niveles son una segmentación estadística, no categorías naturales verdaderas ni niveles de riesgo de incendio.

## Notebooks principales

1. `Calidad_Preparacion_Datos.ipynb`: calidad, cobertura, ceros, asimetría y variables disponibles.
2. `Analisis_No_supervisado.ipynb`: tratamiento de ceros, comparación `k=2…5`, caracterización y creación del target.
3. `Preparacion_Dataset_Modelado.ipynb`: lags FIRMS estrictamente históricos e integración supervisada.
4. `data/processed/modelado/Modelos.ipynb`: baseline, Regresión Logística, Random Forest, test aleatorio y evaluación temporal.
5. `Auditoria_Coherencia_PAA.ipynb`: controles automáticos de unidad, target y leakage.

`Analisis_Nesterov.ipynb` es auxiliar. Los notebooks MIRA/FIREDpy son exploratorios. Los notebooks del enfoque anterior fueron retirados para evitar contradicciones con el pipeline vigente; su historia permanece disponible en Git.

## Reproducción

Ejecutar desde la raíz y en este orden:

```bash
python -m nbconvert --to notebook --execute Calidad_Preparacion_Datos.ipynb --output Calidad_Preparacion_Datos.ipynb
python -m nbconvert --to notebook --execute Analisis_No_supervisado.ipynb --output Analisis_No_supervisado.ipynb
python -m nbconvert --to notebook --execute Preparacion_Dataset_Modelado.ipynb --output Preparacion_Dataset_Modelado.ipynb
python -m nbconvert --to notebook --execute data/processed/modelado/Modelos.ipynb --output Modelos.ipynb --output-dir data/processed/modelado
python -m nbconvert --to notebook --execute Analisis_Nesterov.ipynb --output Analisis_Nesterov.ipynb
python -m nbconvert --to notebook --execute Auditoria_Coherencia_PAA.ipynb --output Auditoria_Coherencia_PAA.ipynb
```

No se debe incorporar a `X` `cantidad_detecciones` de la semana objetivo, el target ni derivados contemporáneos del target.
