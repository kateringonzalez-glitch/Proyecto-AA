from pathlib import Path
import json,hashlib,ast
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report,accuracy_score,balanced_accuracy_score,f1_score
from src.inference import load_model,load_metadata
from src.class_labels import INTERNAL_ORDER,DISPLAY_LABELS
root=Path.cwd();out=root/'docs/auditoria_integral_2026_10_24'
d=pd.read_parquet('data/processed/modelado/dataset_modelado_nivel_actividad_firms.parquet')
h=pd.read_parquet('data/processed/firms_open_meteo_weekly/open_meteo_firms_weekly_history.parquet').sort_values(['departamento','fecha_inicio_semana'])
key=['departamento','fecha_inicio_semana']; g=h.groupby('departamento').cantidad_detecciones_hist
expected=h[key].copy()
for i in range(1,5):expected[f'cantidad_detecciones_lag{i}']=g.shift(i)
lag1=g.shift(1)
for column,method in [('promedio_detecciones_ultimas_4_semanas','mean'),('max_detecciones_ultimas_4_semanas','max')]:
 expected[column]=getattr(lag1.groupby(h.departamento).rolling(4,min_periods=4),method)().reset_index(level=0,drop=True)
expected['semanas_con_actividad_ultimas_4']=lag1.gt(0).astype(int).groupby(h.departamento).rolling(4,min_periods=4).sum().reset_index(level=0,drop=True)
check=d.merge(expected,on=key,validate='one_to_one',suffixes=('','_expected'))
for c in expected.columns.difference(key):np.testing.assert_array_equal(check[c],check[c+'_expected'])
pos=d.loc[d.cantidad_detecciones.gt(0)].copy();pos['log']=np.log1p(pos.cantidad_detecciones)
centroids=pos.groupby('nivel_actividad_firms',observed=True)['log'].mean().reindex(INTERNAL_ORDER[1:])
assert centroids.is_monotonic_increasing
nearest=np.abs(pos['log'].to_numpy()[:,None]-centroids.to_numpy()).argmin(axis=1)
np.testing.assert_array_equal(np.array(INTERNAL_ORDER[1:])[nearest],pos.nivel_actividad_firms)
meta=load_metadata();model=load_model();params=model.named_steps['model'].get_params()
assert all(params[k]==v for k,v in meta['hiperparametros'].items())
r=pd.read_csv('results/experimentos_entregable3.csv');assert len(r)==21
selected=r.set_index('experiment_id').loc['rf_tuned_v1'];assert selected.f1_macro_validation==r.f1_macro_validation.max()
for k,v in meta['metricas_validation'].items():np.testing.assert_allclose(selected[k],v,rtol=0,atol=1e-15)
splits={n:pd.read_parquet(f'data/processed/modelado/splits/{n}_keys.parquet') for n in ['train','validation','test']}
test=splits['test'].merge(d,on=key,validate='one_to_one');model.set_params(model__n_jobs=1)
pred=model.predict(test[meta['variables']]);prob=model.predict_proba(test[meta['variables']]);saved=np.load('docs/auditoria_nomenclatura/test_previo.npz',allow_pickle=True)
# The reference's ordering is the explicit test-keys ordering.
np.testing.assert_array_equal(pred,saved['pred']);np.testing.assert_array_equal(prob,saved['proba'])
report=classification_report(test[meta['target']],pred,output_dict=True,zero_division=0)
for label in INTERNAL_ORDER:
 suffix=label.lower().replace(' ','_')
 for metric,k in [('precision','precision'),('recall','recall'),('f1','f1-score')]:
  np.testing.assert_allclose(report[label][k],meta['metricas_test'][f'{metric}_{suffix}'],atol=1e-15,rtol=0)
before=json.loads((out/'hashes_antes.json').read_text())
changed=[p for p,sha in before.items() if not Path(p).exists() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=sha]
protected=[p for p in before if p.startswith(('data/','artifacts/','results/')) or p=='app/demo_examples.parquet']
assert not set(protected)&set(changed)
word=Path('/home/pepo/Descargas/Proyecto Aprendizaje Automático (6).docx');assert (out/'word_sha256.txt').read_text().startswith(hashlib.sha256(word.read_bytes()).hexdigest())
lidia=Path('/home/pepo/Datos completos/Proyecto-LIDIA-ec3-pedro')
related=sorted((lidia/'dashboard/paa_module').glob('*.py'))+[lidia/'dashboard/main.py',lidia/'tests/test_unified_dashboard.py',lidia/'tests/fixtures/paa_artifact_hashes.json']+sorted((lidia/'docs/integracion_paa').glob('*.md'))
integration=[]
for p in related:
 source=p.read_text()
 if p.suffix=='.py':ast.parse(source)
 integration.append({'ruta':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'integracion_inspeccionada.json').write_text(json.dumps(integration,ensure_ascii=False,indent=2))
result={'filas':len(d),'semanas':d.fecha_inicio_semana.nunique(),'departamentos':d.departamento.nunique(),'conteos':int(d.cantidad_detecciones.sum()),'distribucion':{DISPLAY_LABELS[k]:int(v) for k,v in d.nivel_actividad_firms.value_counts().items()},'centroides_log1p':centroids.tolist(),'centroides_original':np.expm1(centroids).tolist(),'asignaciones_centroides_correctas':True,'antecedentes_7923_filas_7_variables_correctos':True,'experimentos':len(r),'probabilidades_identicas':True,'predicciones_identicas':len(pred),'orden_probabilidades':[DISPLAY_LABELS[k] for k in model.classes_],'test':{'accuracy':accuracy_score(test[meta['target']],pred),'f1_macro':f1_score(test[meta['target']],pred,average='macro'),'balanced_accuracy':balanced_accuracy_score(test[meta['target']],pred)},'protegidos_inmutables':len(protected),'archivos_modificados_desde_inicio':changed,'word_inmutable':True,'integracion_archivos_leidos':len(integration)}
(out/'validacion_metodologica.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
