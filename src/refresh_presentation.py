"""Actualiza figuras desde datos y resultados guardados, sin ajustar modelos."""
from . import generar_puntos_4_6_plus as analysis


def saved_sensitivity():
    import pandas as pd
    def read(name):
        return pd.read_csv(analysis.TABLES / name)
    return {
        'global_metrics': read('plus_metricas_globales_test.csv'),
        'class_summary': read('plus_distribucion_clases_por_k.csv'),
        'per_class': read('plus_metricas_por_clase_test.csv'),
        'confusion_matrices': {s: read(f'plus_matriz_confusion_{s}.csv').set_index('real') for s in ('k3','k4','k5')},
    }


def main():
    import pandas as pd
    # Impide que este flujo documental ejecute ajustes accidentalmente.
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestClassifier
    from unittest.mock import patch
    def forbidden(*args, **kwargs):
        raise RuntimeError('La actualización de presentación no permite ajustar modelos')
    with patch.object(KMeans, 'fit', forbidden), patch.object(RandomForestClassifier, 'fit', forbidden):
        data = analysis.load_data()
        summary = pd.read_csv(analysis.TABLES / 'punto4_resumen_estadistico_niveles.csv')
        analysis.plot_point4_distribution(data, summary)
        analysis.plot_positive_boxplot(data)
        # Funciones descriptivas que también escriben tablas: deshabilitar escritura.
        with patch.object(analysis, 'save_csv', lambda *a, **kw: None):
            analysis.plot_meteo_boxplot(data, analysis.METEO[0], 'punto6_03_boxplot_temperatura_por_nivel.png', 'Temperatura maxima media semanal por categoría FIRMS')
            analysis.plot_meteo_boxplot(data, analysis.METEO[1], 'punto6_04_boxplot_humedad_por_nivel.png', 'Humedad relativa minima media semanal por categoría FIRMS')
            analysis.heatmap_meteo(data)
            analysis.department_distribution(data)
        saved = saved_sensitivity()
        analysis.plot_rf_class_metrics(saved['per_class'].query("escenario == 'k3'"))
        for scenario, matrix in saved['confusion_matrices'].items():
            analysis.plot_confusion(matrix, scenario)
        analysis.plot_plus_class_sizes(saved['class_summary'])
        analysis.plot_plus_f1(saved['per_class'])


if __name__ == '__main__':
    main()
