"""Regresiones de presentación sin reentrenar ni reescribir artefactos."""
import ast
import json
from pathlib import Path
import re
import subprocess

import pandas as pd
import pytest

from src.class_labels import present, DISPLAY_LABELS
from src.inference import load_model, load_metadata, predict_proba

ROOT = Path(__file__).resolve().parents[1]
BASE = '980ce6a18b4be88086b826dce91e6eccc17097a6'
OLD = re.compile(r'\b(?:Sin actividad|Bajo|Moderado|Alto)\b|\b(?:precision|recall|f1)_(?:sin_actividad|bajo|moderado|alto)\b')


def test_nested_results_and_metric_columns_are_presented_without_mutation():
    raw = {'distribucion': {'Bajo': 1237}, 'confusion': {'Bajo → Alto': 19}}
    assert present(raw) == {'distribucion': {'Clúster 1': 1237}, 'confusion': {'Clúster 1 → Clúster 3': 19}}
    assert raw['distribucion'] == {'Bajo': 1237}
    frame = pd.DataFrame({'f1_bajo': [0.25], 'clase': ['Bajo']}, index=['Alto'])
    pd.testing.assert_frame_equal(present(frame), pd.DataFrame({'f1_clúster_1': [0.25], 'clase': ['Clúster 1']}, index=['Clúster 3']))
    assert list(frame.columns) == ['f1_bajo', 'clase']
    assert present('temperatura alta') == 'temperatura alta'
    assert present('Ajuste moderado sobre mejor variante base') == 'Ajuste moderado sobre mejor variante base'


def test_probability_names_preserve_model_column_values_and_order():
    model = load_model()
    metadata = load_metadata()
    x = pd.read_parquet(ROOT / 'app/demo_examples.parquet')[metadata['variables']]
    probabilities = predict_proba(x, model, metadata)
    visible = present(probabilities)
    assert list(visible.columns) == [DISPLAY_LABELS[c] for c in model.classes_]
    pd.testing.assert_frame_equal(visible, probabilities.rename(columns=DISPLAY_LABELS))


@pytest.mark.parametrize('path', sorted((ROOT / 'experimentos').glob('*.ipynb')), ids=lambda p:p.name)
def test_experiment_outputs_have_only_label_changes_and_source_compiles(path):
    old = json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path.relative_to(ROOT)}'], cwd=ROOT))
    new = json.loads(path.read_text())
    assert len(old['cells']) == len(new['cells'])
    def translate(value):
        if isinstance(value, str):
            return OLD.sub(lambda m: present(m[0]), value)
        if isinstance(value, list):
            return [translate(v) for v in value]
        if isinstance(value, dict):
            return {k: v if k.startswith('image/') else translate(v) for k,v in value.items()}
        return value
    for before, after in zip(old['cells'], new['cells']):
        if after['cell_type'] == 'code':
            ast.parse(''.join(after['source']))
        assert before.get('execution_count') == after.get('execution_count')
        assert after.get('outputs', []) == translate(before.get('outputs', []))
        for output in after.get('outputs', []):
            assert not OLD.search(''.join(output.get('text', [])))
            for mime, value in output.get('data', {}).items():
                if mime.startswith('text/'):
                    assert not OLD.search(''.join(value))


def test_metadata_generation_keeps_display_contract():
    nb = json.loads((ROOT / 'experimentos/Comparacion_Modelos.ipynb').read_text())
    source = ''.join(nb['cells'][17]['source'])
    # Ejecutar sólo la construcción del contrato nuevo; ninguna escritura ni fit.
    tree = ast.parse(source)
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                   and isinstance(node.targets[0], ast.Subscript)
                   and isinstance(node.targets[0].value, ast.Name)
                   and node.targets[0].value.id == 'meta']
    namespace = {'meta': {}, 'DISPLAY_LABELS': DISPLAY_LABELS}
    exec(compile(ast.Module(body=assignments, type_ignores=[]), '<metadata>', 'exec'), namespace)
    assert namespace['meta']['etiquetas_visibles'] == load_metadata()['etiquetas_visibles']
    assert namespace['meta']['interpretacion_clases'] == load_metadata()['interpretacion_clases']
