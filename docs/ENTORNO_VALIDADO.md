# Entorno validado

El proyecto fue comprobado el 18 de octubre de 2026 con el entorno siguiente:

| Componente | Versión observada |
|---|---:|
| Python | 3.13.16 |
| pandas | 3.0.1 |
| NumPy | 2.4.3 |
| pyarrow | 23.0.1 |
| scikit-learn | 1.8.0 |
| GeoPandas | 1.1.3 |
| Shapely | 2.1.2 |
| Matplotlib | 3.11.1 |
| seaborn | 0.13.2 |
| SciPy | 1.17.1 |
| Altair | 6.1.0 |
| Streamlit | 1.57.0 |
| joblib | 1.5.3 |

`requirements.txt` declara rangos compatibles y dependencias directas, pero no es un lockfile. Por lo tanto, este registro documenta un entorno comprobado, no garantiza reproducción binaria futura. En particular, los artefactos `joblib` deben cargarse con una versión compatible de scikit-learn.
