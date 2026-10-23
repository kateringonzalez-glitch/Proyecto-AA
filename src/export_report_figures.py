"""Exporta presentación desde datos/etiquetas y resultados persistidos, sin ajustes.

Ejecutar: python -m src.export_report_figures
El notebook figura_clusters.ipynb genera las figuras 1–3 y 6–9.
Este módulo genera las restantes y verifica los valores gráficos antes/después.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
from unittest.mock import patch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.text import Text
import numpy as np
import pandas as pd

from . import generar_puntos_4_6_plus as analysis
from .class_labels import DISPLAY_ORDER
from .refresh_presentation import saved_sensitivity
from .visual_style import COLORS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'results/figuras_informe_actualizadas'
AUDIT = OUTPUT / 'auditoria'
OLD_LABELS = re.compile(r'\b(Sin actividad|Bajo|Moderado|Alto)\b')
NAMES = {
    'punto4_distribucion_conteos_por_nivel.png': 'suplementaria_conteos_por_categoria_boxplots.png',
    'punto6_01_kmeans_inercia_silhouette.png': 'figura_04_inercia_silhouette.png',
    'punto6_02_boxplot_detecciones_positivas.png': 'suplementaria_conteos_clusters_positivos.png',
    'punto6_03_boxplot_temperatura_por_nivel.png': 'suplementaria_temperatura_boxplots.png',
    'punto6_04_boxplot_humedad_por_nivel.png': 'suplementaria_humedad_boxplots.png',
    'punto6_05_heatmap_meteo_medianas_estandarizadas.png': 'figura_05_medianas_meteorologicas_estandarizadas.png',
    'punto6_06_distribucion_niveles_departamento.png': 'suplementaria_porcentajes_departamento.png',
    'punto6_07_metricas_rf_por_clase_test.png': 'suplementaria_precision_recall_f1_por_clase.png',
    'plus_metricas_globales_k.png': 'figura_10_sensibilidad_metricas_k3_k4_k5.png',
    'plus_matriz_confusion_k3.png': 'suplementaria_matriz_confusion_k3.png',
    'plus_matriz_confusion_k4.png': 'suplementaria_matriz_confusion_k4.png',
    'plus_matriz_confusion_k5.png': 'suplementaria_matriz_confusion_k5.png',
    'plus_tamanos_clase_por_k.png': 'suplementaria_sensibilidad_tamanos_clase.png',
    'plus_f1_por_clase_k.png': 'suplementaria_sensibilidad_f1_por_clase.png',
}


def numeric_signature(fig):
    """Huella de valores y geometría; excluye nombres, colores y tipografía."""
    values = []
    def add(value):
        arr = np.ma.filled(np.ma.asarray(value, dtype=float), np.nan)
        values.append((list(arr.shape), sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()))
    for ax in fig.axes:
        add(ax.get_xlim()); add(ax.get_ylim())
        add(ax.get_xticks()); add(ax.get_yticks())
        for line in ax.lines:
            add(line.get_xdata()); add(line.get_ydata())
        for collection in ax.collections:
            add(collection.get_offsets())
            for path in collection.get_paths():
                add(path.vertices)
        for image in ax.images:
            add(image.get_array()); add(image.get_extent()); add(image.get_clim())
        for item in ax.patches:
            add(item.get_patch_transform().transform(item.get_path().vertices))
        # Las anotaciones numéricas forman parte de los datos representados.
        for text in ax.texts:
            if re.fullmatch(r'[-+\d.,% ]+', text.get_text()):
                values.append(text.get_text())
    return values


def check_labels(fig):
    texts = [item.get_text() for item in fig.findobj(Text)]
    assert not any(OLD_LABELS.search(t) for t in texts), texts
    return texts


def validate_new_notebook_coordinates():
    """Ejecuta sólo cargas/figuras y compara coordenadas con el notebook original."""
    original = json.loads((AUDIT / 'figura_clusters_original.ipynb').read_text())
    current = json.loads((ROOT / 'figura_clusters.ipynb').read_text())
    def execute(notebook, old):
        namespace = {'__name__': '__paa_visual_validation__'}
        result = {}
        with patch.object(Figure, 'savefig'), patch.object(plt, 'show'), redirect_stdout(StringIO()):
            for i in [1,2,8,16,17,18,19,20,21]:
                source = ''.join(notebook['cells'][i]['source'])
                if old and i == 16:
                    source = 'data = pd.read_parquet("data/processed/modelado/dataset_modelado_nivel_actividad_firms.parquet")'
                exec(compile(source, f'figura_clusters.ipynb:cell{i}', 'exec'), namespace)
                if i >= 17:
                    result[str(i)] = numeric_signature(plt.gcf())
                    if not old:
                        check_labels(plt.gcf())
                    plt.close('all')
        return result
    before = execute(original, True)
    after = execute(current, False)
    assert before == after, 'Las coordenadas o valores de una figura cambiaron'
    (AUDIT / 'coordenadas_antes_despues.json').write_text(json.dumps({
        'celdas': list(before), 'iguales': True, 'original': before, 'actualizado': after,
    }, indent=2))
    return before


def main():
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestClassifier
    from .refresh_presentation import main as refresh
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    def forbidden(*args, **kwargs):
        raise RuntimeError('Esta exportación no puede ajustar modelos ni reconstruir el target')
    def export(fig, original_name, close=True):
        name = NAMES[original_name]
        analysis.color_class_labels(fig)
        texts = check_labels(fig)
        fig.savefig(OUTPUT / name, dpi=300)
        manifest.append({'png': name, 'origen': original_name, 'dpi': 300, 'etiquetas': texts,
                         'datos_sha256': sha256(json.dumps(numeric_signature(fig)).encode()).hexdigest()})
        if close:
            plt.close(fig)
        return OUTPUT / name
    with patch.object(KMeans, 'fit', forbidden), patch.object(RandomForestClassifier, 'fit', forbidden):
        # Los datos oficiales y las tablas nunca se escriben en este proceso.
        with plt.rc_context(), patch.object(analysis, 'save_figure', export):
            refresh()
            analysis.plot_kmeans_metrics(pd.read_csv(analysis.TABLES / 'punto6_kmeans_metricas_k_2_5.csv'))
            analysis.plot_plus_global(saved_sensitivity()['global_metrics'])
        # Figura 11: composición y escala de valores de la matriz del Word.
        cm = saved_sensitivity()['confusion_matrices']['k3']
        with plt.rc_context():
            fig, ax = plt.subplots(figsize=(6, 5.5))
            ax.imshow(cm.to_numpy(), cmap='viridis')
            ax.set_xticks(range(4), DISPLAY_ORDER)
            ax.set_yticks(range(4), DISPLAY_ORDER)
            ax.set_xlabel('Clase estimada'); ax.set_ylabel('Clase real')
            ax.set_title('Matriz de confusión - Random Forest V1')
            for i in range(4):
                for j in range(4):
                    ax.text(j, i, str(int(cm.iloc[i,j])), ha='center', va='center', color='black')
            analysis.color_class_labels(fig); check_labels(fig)
            fig.tight_layout()
            fig.savefig(OUTPUT / 'figura_11_matriz_confusion_random_forest_v1.png', dpi=300, bbox_inches='tight')
            plt.close(fig)
        validate_new_notebook_coordinates()
    (AUDIT / 'exportaciones.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f'{len(manifest) + 1} figuras exportadas desde resultados guardados; coordenadas del notebook verificadas.')


if __name__ == '__main__':
    main()
