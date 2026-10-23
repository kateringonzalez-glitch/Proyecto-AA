"""Figuras listas para el informe y conservación de sus datos originales."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'results/figuras_informe_actualizadas'
AUDIT = OUTPUT / 'auditoria'


def test_datasets_model_and_previous_figures_untouched():
    for name, expected in json.loads((AUDIT/'hashes_previos.json').read_text()).items():
        path = ROOT / name
        # Las fuentes ignoradas sólo se verifican cuando están disponibles localmente.
        if not path.exists() and subprocess.run(
            ['git', 'check-ignore', '--quiet', name], cwd=ROOT
        ).returncode == 0:
            continue
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name


def test_coordinates_and_numeric_graph_values_identical():
    for name in ['coordenadas_antes_despues.json','coordenadas_figuras_guardadas.json']:
        record = json.loads((AUDIT/name).read_text())
        assert record['iguales'] is True
        assert record['original'] == record['actualizado']


@pytest.mark.parametrize('number', [3,5,6,7,8,9,11])
def test_required_report_figures_are_high_resolution(number):
    files = list(OUTPUT.glob(f'figura_{number:02d}_*.png'))
    assert len(files) == 1
    with Image.open(files[0]) as im:
        assert im.width >= 1600 and im.height >= 1200
        assert im.info['dpi'] == pytest.approx((300,300),abs=.001)


def test_new_notebook_has_only_neutral_visible_names_and_no_execution_errors():
    notebook = json.loads((ROOT/'figura_clusters.ipynb').read_text())
    from src.export_report_figures import OLD_LABELS
    for cell in notebook['cells']:
        source = ''.join(cell['source'])
        assert not OLD_LABELS.search(source)
        assert '/Users/' not in source
        if cell['cell_type'] == 'code':
            tree = ast.parse(source)
            for node in ast.walk(tree):
                assert not (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
                            and node.func.attr in ['fit','fit_predict','to_parquet']), source
            if source.strip():
                assert cell['execution_count'] is not None
            for output in cell.get('outputs',[]):
                assert output['output_type'] != 'error'
                for mime, value in output.get('data',{}).items():
                    if mime.startswith('text/'):
                        assert not OLD_LABELS.search(''.join(value))


def test_rendered_labels_are_neutral_and_scenarios_remain_distinct():
    from src.export_report_figures import OLD_LABELS
    manifest = json.loads((AUDIT/'exportaciones.json').read_text())
    assert len(manifest) == 14
    for item in manifest:
        assert not any(OLD_LABELS.search(t) for t in item['etiquetas'])
    sensitivity = next(x for x in manifest if x['origen']=='plus_f1_por_clase_k.png')
    assert 'k3 | Clúster 1' in sensitivity['etiquetas']
    assert 'k4 | Perfil positivo 1' in sensitivity['etiquetas']
    assert 'k5 | Perfil positivo 1' in sensitivity['etiquetas']
