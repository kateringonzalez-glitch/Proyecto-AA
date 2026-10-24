from pathlib import Path
import json
import nbformat
from nbclient import NotebookClient
ROOT=Path.cwd()
OUT=ROOT/'docs/auditoria_integral_2026_10_24'
results=[]
for name in ['Auditoria_Coherencia_PAA.ipynb','Calidad_Preparacion_Datos.ipynb','Preparacion_Dataset_Modelado.ipynb','Analisis_Puntos_4_6_Plus.ipynb','figura_clusters.ipynb']:
    nb=nbformat.read(ROOT/name,as_version=4)
    preamble='''import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from unittest.mock import patch
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from matplotlib.figure import Figure
import pandas as pd

def forbidden(*args, **kwargs):
    raise RuntimeError("La auditoría prohíbe entrenar y escribir datasets")
_guards = [patch.object(KMeans, 'fit', forbidden), patch.object(RandomForestClassifier, 'fit', forbidden), patch.object(pd.DataFrame, 'to_parquet', forbidden), patch.object(pd.DataFrame, 'to_csv', forbidden), patch.object(Figure, 'savefig', lambda *a, **k: None)]
for _guard in _guards: _guard.start()
'''
    if name=='Preparacion_Dataset_Modelado.ipynb':
        preamble+='''# Sólo en esta copia de ejecución: capturar la escritura y comparar el resultado.
_written = []
def compare_parquet(frame, path, *args, **kwargs):
    pd.testing.assert_frame_equal(frame, pd.read_parquet(path))
    _written.append(str(path))
_patch_write = patch.object(pd.DataFrame, 'to_parquet', compare_parquet)
_patch_write.start()
'''
    if name=='Analisis_Puntos_4_6_Plus.ipynb':
        preamble+='''from src import generar_puntos_4_6_plus as _analysis
_analysis.save_csv = lambda *a, **k: None
'''
    nb.cells.insert(0,nbformat.v4.new_code_cell(preamble))
    try:
        NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
        results.append({'notebook':name,'estado':'correcto','celdas_codigo':sum(c.cell_type=='code' for c in nb.cells)-1,'restricciones':'sin fit; sin escribir datasets, tablas ni figuras originales'})
    except Exception as exc:
        results.append({'notebook':name,'estado':'error','error':str(exc)})
    nbformat.write(nb,OUT/('ejecutado_'+name))
    print(json.dumps(results[-1],ensure_ascii=False),flush=True)
(OUT/'ejecucion_notebooks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
