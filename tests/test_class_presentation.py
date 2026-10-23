"""Contrato de presentación neutral y equivalencia con la referencia previa."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import confusion_matrix, f1_score, balanced_accuracy_score

from src.class_labels import DISPLAY_LABELS, INTERNAL_ORDER, DISPLAY_ORDER, display_frame, display_label
from src.inference import load_metadata, load_model, predict, predict_proba
from src.historical_evaluation import TARGET, load_test_examples
from src.visual_style import COLORS, INTERNAL_COLORS

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs/auditoria_nomenclatura'
# Versión anterior a la corrección; no usar HEAD porque avanzará al publicarla.
BASELINE_REF = '2381460683fdd93af35c9509ea9c4b99efd22be1'


def rename_text(s):
    for a, b in DISPLAY_LABELS.items():
        s = re.sub(r'\b' + a + r'\b', b, s)
    return s


def test_class_codes_centroid_order_and_colors():
    data = pd.read_parquet(ROOT / 'data/processed/modelado/dataset_niveles_actividad_firms.parquet')
    assert dict(zip(INTERNAL_ORDER, DISPLAY_ORDER)) == {
        'Sin actividad': 'Sin detecciones', 'Bajo': 'Clúster 1',
        'Moderado': 'Clúster 2', 'Alto': 'Clúster 3',
    }
    for code, name in enumerate(INTERNAL_ORDER):
        assert data.loc[data[TARGET].eq(name), 'nivel_actividad_firms_codigo'].eq(code).all()
    counts = data.cantidad_detecciones
    expected = np.select([counts.eq(0), counts.eq(1), counts.between(2,4)], DISPLAY_ORDER[:3], default=DISPLAY_ORDER[3])
    np.testing.assert_array_equal(display_frame(data)[TARGET], expected)
    positive = data.loc[counts.gt(0)].assign(log_count=np.log1p(counts.loc[counts.gt(0)]))
    centroids = positive.groupby(TARGET).log_count.mean().reindex(INTERNAL_ORDER[1:])
    assert centroids.is_monotonic_increasing
    assert list(COLORS.values()) == ['#6B7280','#2563EB','#F59E0B','#DC2626']
    assert all(INTERNAL_COLORS[k] == COLORS[v] for k,v in DISPLAY_LABELS.items())
    pd.testing.assert_frame_equal(data, pd.read_parquet(ROOT / 'data/processed/modelado/dataset_niveles_actividad_firms.parquet'))


def test_model_datasets_partitions_and_original_metadata_unchanged():
    hashes = json.loads((AUDIT / 'integridad_previa.json').read_text())
    for name, expected in hashes.items():
        if name == 'artifacts/metadata_modelo.json':
            continue
        path = ROOT / name
        # La auditoría incluye fuentes locales ignoradas que no forman parte de un clon.
        if not path.exists() and subprocess.run(
            ['git', 'check-ignore', '--quiet', name], cwd=ROOT
        ).returncode == 0:
            continue
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    original = json.loads(subprocess.check_output(['git','show',f'{BASELINE_REF}:artifacts/metadata_modelo.json'], cwd=ROOT))
    current = load_metadata()
    assert {key: current[key] for key in original} == original
    assert current['etiquetas_visibles'] == DISPLAY_LABELS


def test_all_1189_predictions_probabilities_metrics_and_confusions():
    saved = np.load(AUDIT / 'test_previo.npz', allow_pickle=True)
    model = load_model()
    metadata = load_metadata()
    test = load_test_examples(metadata['variables'])
    x = test[metadata['variables']]
    assert len(test) == 1189
    np.testing.assert_array_equal(model.classes_, saved['classes'])
    np.testing.assert_array_equal(test[TARGET], saved['actual'])
    np.testing.assert_array_equal(predict(x, model, metadata), saved['pred'])
    np.testing.assert_allclose(predict_proba(x, model, metadata), saved['proba'], rtol=0, atol=1e-15)
    model.set_params(model__n_jobs=1)
    np.testing.assert_array_equal(predict_proba(x, model, metadata), saved['proba'])
    pred = predict(x, model, metadata)
    assert f1_score(test[TARGET], pred, average='macro') == pytest.approx(0.39672311525116466, abs=1e-15)
    assert balanced_accuracy_score(test[TARGET], pred) == pytest.approx(0.4137447185549167, abs=1e-15)
    observed = confusion_matrix(test[TARGET], pred, labels=INTERNAL_ORDER)
    table = pd.read_csv(ROOT / 'results/analisis_puntos_4_6_plus/tables/plus_matriz_confusion_k3.csv', index_col=0)
    np.testing.assert_array_equal(observed, table.to_numpy())
    assert list(table.index) == list(table.columns) == list(DISPLAY_ORDER)


def test_saved_tables_change_only_class_text():
    for p in (ROOT / 'results/analisis_puntos_4_6_plus/tables').glob('*.csv'):
        old = subprocess.check_output(['git','show',f'{BASELINE_REF}:{p.relative_to(ROOT)}'], cwd=ROOT).decode('utf-8')
        assert p.read_bytes().decode('utf-8') == rename_text(old), p.name


def test_notebook_numeric_outputs_unchanged_and_visible_labels_neutral():
    def clean(output):
        o = json.loads(json.dumps(output))
        o.get('data', {}).pop('image/png', None)
        return o
    for p in ROOT.glob('*.ipynb'):
        if subprocess.run(['git', 'cat-file', '-e', f'{BASELINE_REF}:{p.name}'], cwd=ROOT, capture_output=True).returncode:
            continue  # Los notebooks nuevos tienen su referencia en la auditoría de figuras.
        old = json.loads(subprocess.check_output(['git','show',f'{BASELINE_REF}:{p.name}'], cwd=ROOT))
        new = json.loads(p.read_text())
        assert len(old['cells']) == len(new['cells'])
        for before, after in zip(old['cells'],new['cells']):
            assert before.get('execution_count') == after.get('execution_count')
            assert len(before.get('outputs',[])) == len(after.get('outputs',[]))
            for a,b in zip(before.get('outputs',[]),after.get('outputs',[])):
                assert json.loads(rename_text(json.dumps(clean(a),ensure_ascii=False))) == clean(b)
            if after['cell_type'] == 'markdown':
                assert not re.search(r'\b(Bajo|Moderado|Alto|Sin actividad)\b', ''.join(after['source']))


def test_all_presentation_figures_have_neutral_labels_and_original_palette(monkeypatch):
    from matplotlib.text import Text
    from matplotlib.colors import to_hex
    from src import refresh_presentation as refresh
    captured = {}
    def inspect(fig, name, close=True):
        texts = [item.get_text() for item in fig.findobj(Text)]
        assert not any(re.search(r'\b(Bajo|Moderado|Alto|Sin actividad)\b', text) for text in texts), name
        captured[name] = texts
        if name == 'punto6_06_distribucion_niveles_departamento.png':
            patches = fig.axes[0].patches
            observed = [to_hex(p.get_facecolor()) for p in patches]
            for color in COLORS.values():
                assert color.lower() in observed
        import matplotlib.pyplot as plt
        plt.close(fig)
    monkeypatch.setattr(refresh.analysis, 'save_figure', inspect)
    refresh.main()
    assert len(captured) == 12
    assert all(label in captured['plus_matriz_confusion_k3.png'] for label in DISPLAY_ORDER)
