from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib

if os.environ.get("MPLBACKEND") is None and os.environ.get("JPY_PARENT_PID") is None:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    silhouette_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/modelado/dataset_modelado_nivel_actividad_firms.parquet"
SPLITS = ROOT / "data/processed/modelado/splits"
EXPERIMENTOS = ROOT / "results/experimentos_entregable3.csv"
METADATA = ROOT / "artifacts/metadata_modelo.json"
OUT = ROOT / "results/analisis_puntos_4_6_plus"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"

KEY = ["departamento", "fecha_inicio_semana"]
TARGET = "nivel_actividad_firms"
COUNT = "cantidad_detecciones"
ORDER = ["Sin detecciones", "Clúster 1", "Clúster 2", "Clúster 3"]
RS = 42
FEATURES = [
    "departamento",
    "mes",
    "temperature_2m_max_mean_weekly",
    "relative_humidity_2m_min_mean_weekly",
    "wind_speed_10m_max_mean_weekly",
    "precipitation_sum_weekly",
]
METEO = FEATURES[2:]
METEO_LABELS = {
    "temperature_2m_max_mean_weekly": "Temp. max media semanal (C)",
    "relative_humidity_2m_min_mean_weekly": "Humedad relativa min media semanal (%)",
    "wind_speed_10m_max_mean_weekly": "Viento max medio semanal (m/s)",
    "precipitation_sum_weekly": "Precipitacion semanal (mm)",
}
try:
    from src.visual_style import COLORS, CLASS_COLORS
except ModuleNotFoundError:
    from visual_style import COLORS, CLASS_COLORS



def ensure_dirs() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    from src.class_labels import display_frame
    data = display_frame(pd.read_parquet(DATA))
    data["fecha_inicio_semana"] = pd.to_datetime(data["fecha_inicio_semana"])
    assert not data.duplicated(KEY).any(), "Hay claves departamento-semana duplicadas."
    assert set(ORDER).issubset(set(data[TARGET].unique())), "Faltan clases del target vigente."
    assert data.loc[data[COUNT].eq(0), TARGET].eq("Sin detecciones").all()
    assert data.loc[data[COUNT].gt(0), TARGET].ne("Sin detecciones").all()
    return data


def read_rf_params() -> dict:
    results = pd.read_csv(EXPERIMENTOS)
    selected = results.set_index("experiment_id").loc["rf_tuned_v1"]
    params = json.loads(selected["hiperparametros"])

    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    expected = metadata.get("hiperparametros", {})
    for key in ["n_estimators", "min_samples_leaf", "max_features", "class_weight", "random_state"]:
        assert params.get(key) == expected.get(key), f"Hiperparametro inconsistente: {key}"
    assert selected["modelo"] == "RandomForest"
    assert selected["variante_variables"] == "V1"
    assert metadata.get("variables") == FEATURES
    return params


def subset_by_keys(data: pd.DataFrame, split: str) -> pd.DataFrame:
    keys = pd.read_parquet(SPLITS / f"{split}_keys.parquet").copy()
    keys["fecha_inicio_semana"] = pd.to_datetime(keys["fecha_inicio_semana"])
    part = data.merge(keys, on=KEY, how="inner", validate="one_to_one")
    assert len(part) == len(keys), f"Split {split} no conserva todas las claves."
    return part


def make_rf(params: dict) -> Pipeline:
    model_params = dict(params)
    model_params["random_state"] = RS
    model_params.setdefault("n_jobs", -1)
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["departamento", "mes"]),
            ("num", "passthrough", FEATURES[2:]),
        ]
    )
    return Pipeline(
        [
            ("preprocess", pre),
            ("model", RandomForestClassifier(**model_params)),
        ]
    )


def save_csv(df: pd.DataFrame, name: str, **kwargs) -> Path:
    path = TABLES / name
    df.to_csv(path, index=kwargs.pop("index", False), encoding="utf-8-sig", **kwargs)
    return path


def save_json(obj: dict, name: str) -> Path:
    path = OUT / name
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_figure(fig: plt.Figure, name: str, close: bool = True) -> Path:
    path = FIGURES / name
    fig.savefig(path, dpi=180)
    if close:
        plt.close(fig)
    return path


def quantile(q: float):
    return lambda s: s.quantile(q)


def point4_summary(data: pd.DataFrame) -> pd.DataFrame:
    summary = (
        data.groupby(TARGET, observed=False)[COUNT]
        .agg(
            observaciones="size",
            minimo="min",
            q1=quantile(0.25),
            mediana="median",
            q3=quantile(0.75),
            maximo="max",
            media="mean",
        )
        .reindex(ORDER)
        .reset_index()
    )
    summary["porcentaje_dataset"] = summary["observaciones"] / len(data) * 100
    summary = summary[
        [
            TARGET,
            "observaciones",
            "porcentaje_dataset",
            "minimo",
            "q1",
            "mediana",
            "q3",
            "maximo",
            "media",
        ]
    ]
    save_csv(summary.round(4), "punto4_resumen_estadistico_niveles.csv")
    return summary


def boxplot_by_class(
    ax: plt.Axes,
    data: pd.DataFrame,
    y: str,
    order: list[str],
    title: str,
    ylabel: str,
    log_scale: bool = False,
    showfliers: bool = True,
) -> None:
    values = [data.loc[data[TARGET].eq(label), y].dropna().to_numpy() for label in order]
    bp = ax.boxplot(
        values,
        tick_labels=order,
        patch_artist=True,
        showfliers=showfliers,
        medianprops={"color": "black", "linewidth": 1.3},
        flierprops={"marker": "o", "markersize": 2.2, "alpha": 0.35},
    )
    for patch, label in zip(bp["boxes"], order):
        patch.set_facecolor(CLASS_COLORS[label])
        patch.set_alpha(1.0)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    if log_scale:
        ax.set_yscale("log")
    ax.tick_params(axis="x", rotation=15)


def plot_point4_distribution(data: pd.DataFrame, summary: pd.DataFrame, close: bool = True) -> plt.Figure:
    plot_data = data.copy()
    plot_data["log1p_detecciones"] = np.log1p(plot_data[COUNT])
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    boxplot_by_class(
        axes[0],
        plot_data,
        "log1p_detecciones",
        ORDER,
        "Distribucion de detecciones por nivel final",
        "log1p(cantidad de detecciones)",
        showfliers=True,
    )
    positives = data[data[COUNT].gt(0)].copy()
    boxplot_by_class(
        axes[1],
        positives,
        COUNT,
        ORDER[1:],
        "Clases positivas en escala original",
        "Cantidad de detecciones (escala log)",
        log_scale=True,
        showfliers=True,
    )
    axes[0].text(
        0.01,
        -0.22,
        "La escala log1p permite incluir los ceros sin ocultar la asimetria de las clases positivas.",
        transform=axes[0].transAxes,
        fontsize=9,
    )
    alto = summary.loc[summary[TARGET].eq("Clúster 3")].iloc[0]
    axes[1].text(
        0.01,
        -0.22,
        f"Clúster 3: min={alto['minimo']:.0f}, Q1={alto['q1']:.0f}, mediana={alto['mediana']:.0f}, Q3={alto['q3']:.0f}, max={alto['maximo']:.0f}.",
        transform=axes[1].transAxes,
        fontsize=9,
    )
    save_figure(fig, "punto4_distribucion_conteos_por_nivel.png", close=close)
    return fig


def kmeans_targets(data: pd.DataFrame, k: int) -> tuple[pd.Series, pd.DataFrame, KMeans]:
    positive_mask = data[COUNT].gt(0)
    x = np.log1p(data.loc[positive_mask, [COUNT]].to_numpy())
    model = KMeans(n_clusters=k, random_state=RS, n_init=50).fit(x)
    centers = pd.DataFrame(
        {
            "cluster_original": range(k),
            "centroide_log1p": model.cluster_centers_.ravel(),
        }
    )
    centers["centroide_original"] = np.expm1(centers["centroide_log1p"])
    centers = centers.sort_values("centroide_original").reset_index(drop=True)
    if k == 3:
        labels = ["Clúster 1", "Clúster 2", "Clúster 3"]
    else:
        labels = [f"Perfil positivo {i}" for i in range(1, k + 1)]
    centers["etiqueta"] = labels
    mapping = centers.set_index("cluster_original")["etiqueta"].to_dict()
    target = pd.Series("Sin detecciones", index=data.index, dtype="object")
    target.loc[positive_mask] = pd.Series(model.labels_, index=data.index[positive_mask]).map(mapping)
    ranges = (
        data.assign(target_alt=target)
        .groupby("target_alt", observed=False)[COUNT]
        .agg(observaciones="size", minimo="min", maximo="max", media="mean", mediana="median")
        .reset_index()
        .rename(columns={"target_alt": "clase"})
    )
    ranges["k"] = k
    ranges["porcentaje_dataset"] = ranges["observaciones"] / len(data) * 100
    order = ["Sin detecciones"] + labels
    ranges["orden"] = ranges["clase"].map({label: i for i, label in enumerate(order)})
    ranges = ranges.sort_values("orden").drop(columns="orden")
    return target, ranges, model


def kmeans_metrics(data: pd.DataFrame) -> pd.DataFrame:
    positive = data.loc[data[COUNT].gt(0), [COUNT]].copy()
    x = np.log1p(positive[[COUNT]].to_numpy())
    rows = []
    for k in range(2, 6):
        model = KMeans(n_clusters=k, random_state=RS, n_init=50).fit(x)
        counts = np.bincount(model.labels_)
        rows.append(
            {
                "k": k,
                "inertia": model.inertia_,
                "silhouette": silhouette_score(x, model.labels_),
                "cluster_minimo": counts.min(),
                "porcentaje_minimo_positivas": counts.min() / len(positive) * 100,
            }
        )
    metrics = pd.DataFrame(rows)
    save_csv(metrics.round(6), "punto6_kmeans_metricas_k_2_5.csv")
    return metrics


def plot_kmeans_metrics(metrics: pd.DataFrame, close: bool = True) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    axes[0].plot(metrics["k"], metrics["inertia"], marker="o", color="#2563EB")
    axes[0].set_title("Inercia de K-Means segun K")
    axes[0].set_xlabel("K positivo")
    axes[0].set_ylabel("Inercia")
    axes[0].grid(alpha=0.25)
    for _, row in metrics.iterrows():
        axes[0].annotate(f"{row['inertia']:.1f}", (row["k"], row["inertia"]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)

    axes[1].plot(metrics["k"], metrics["silhouette"], marker="o", color="#DC2626")
    axes[1].set_title("Silhouette de K-Means segun K")
    axes[1].set_xlabel("K positivo")
    axes[1].set_ylabel("Silhouette")
    axes[1].grid(alpha=0.25)
    for _, row in metrics.iterrows():
        axes[1].annotate(f"{row['silhouette']:.3f}", (row["k"], row["silhouette"]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    save_figure(fig, "punto6_01_kmeans_inercia_silhouette.png", close=close)
    return fig


def plot_positive_boxplot(data: pd.DataFrame, close: bool = True) -> plt.Figure:
    positives = data[data[COUNT].gt(0)].copy()
    fig, ax = plt.subplots(figsize=(7.8, 5), constrained_layout=True)
    boxplot_by_class(
        ax,
        positives,
        COUNT,
        ORDER[1:],
        "Detecciones semanales por perfil positivo",
        "Cantidad de detecciones (escala log)",
        log_scale=True,
        showfliers=True,
    )
    ax.text(
        0.01,
        -0.18,
        "Se muestran los valores extremos; la escala logaritmica evita que los conteos altos compriman las cajas.",
        transform=ax.transAxes,
        fontsize=9,
    )
    save_figure(fig, "punto6_02_boxplot_detecciones_positivas.png", close=close)
    return fig


def plot_meteo_boxplot(data: pd.DataFrame, variable: str, filename: str, title: str, close: bool = True) -> plt.Figure:
    valid = data[[TARGET, variable]].dropna().copy()
    counts = valid.groupby(TARGET, observed=False).size().reindex(ORDER).reset_index(name=f"validos_{variable}")
    save_csv(counts, f"{filename.replace('.png', '')}_observaciones_validas.csv")
    fig, ax = plt.subplots(figsize=(8.4, 5), constrained_layout=True)
    boxplot_by_class(
        ax,
        valid,
        variable,
        ORDER,
        title,
        METEO_LABELS.get(variable, variable),
        showfliers=True,
    )
    save_figure(fig, filename, close=close)
    return fig


def heatmap_meteo(data: pd.DataFrame, close: bool = True) -> tuple[pd.DataFrame, plt.Figure]:
    medians = data.groupby(TARGET, observed=False)[METEO].median().reindex(ORDER)
    means = data[METEO].mean()
    stds = data[METEO].std(ddof=0).replace(0, np.nan)
    standardized = (medians - means) / stds
    save_csv(medians.reset_index().round(4), "punto6_heatmap_meteo_medianas_originales.csv")
    save_csv(standardized.reset_index().round(4), "punto6_heatmap_meteo_medianas_estandarizadas.csv")
    missing = (
        data.groupby(TARGET, observed=False)[METEO]
        .apply(lambda df: df.isna().sum())
        .reset_index()
        .rename(columns={"level_1": "variable", 0: "nulos"})
    )
    save_csv(missing, "punto6_meteo_nulos_por_clase.csv")

    fig, ax = plt.subplots(figsize=(9.2, 4.8), constrained_layout=True)
    im = ax.imshow(standardized.to_numpy(), cmap="RdBu_r", aspect="auto", vmin=-1.2, vmax=1.2)
    ax.set_xticks(range(len(METEO)))
    ax.set_xticklabels([METEO_LABELS[c] for c in METEO], rotation=25, ha="right")
    ax.set_yticks(range(len(ORDER)))
    ax.set_yticklabels(ORDER)
    ax.set_title("Medianas meteorologicas por nivel, estandarizadas")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Desvios estandar respecto al promedio de la variable")
    for i in range(len(ORDER)):
        for j in range(len(METEO)):
            ax.text(j, i, f"{standardized.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    save_figure(fig, "punto6_05_heatmap_meteo_medianas_estandarizadas.png", close=close)
    return medians, fig


def department_distribution(data: pd.DataFrame, close: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, plt.Figure]:
    counts = pd.crosstab(data["departamento"], data[TARGET]).reindex(columns=ORDER, fill_value=0)
    proportions = counts.div(counts.sum(axis=1), axis=0) * 100
    sort_index = proportions[["Clúster 3", "Clúster 2", "Clúster 1"]].sum(axis=1).sort_values(ascending=False).index
    counts = counts.loc[sort_index]
    proportions = proportions.loc[sort_index]
    save_csv(counts.reset_index(), "punto6_departamento_recuentos_por_nivel.csv")
    save_csv(proportions.reset_index().round(4), "punto6_departamento_porcentajes_por_nivel.csv")

    fig, ax = plt.subplots(figsize=(11.5, 6.5), constrained_layout=True)
    bottom = np.zeros(len(proportions))
    x = np.arange(len(proportions))
    for label in ORDER:
        vals = proportions[label].to_numpy()
        ax.bar(x, vals, bottom=bottom, label=label, color=COLORS[label])
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(proportions.index, rotation=55, ha="right")
    ax.set_ylabel("Porcentaje dentro del departamento")
    ax.set_title("Distribucion porcentual de niveles FIRMS por departamento")
    ax.set_ylim(0, 100)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.20))
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "punto6_06_distribucion_niveles_departamento.png", close=close)
    return counts, proportions, fig


def evaluate_rf_for_target(
    data: pd.DataFrame,
    target_values: pd.Series,
    class_order: list[str],
    params: dict,
    scenario: str,
    close: bool = True,
) -> tuple[dict, pd.DataFrame, pd.DataFrame, plt.Figure]:
    work = data.copy()
    work["target_sensibilidad"] = target_values
    train = subset_by_keys(work, "train")
    validation = subset_by_keys(work, "validation")
    test = subset_by_keys(work, "test")
    development = pd.concat([train, validation], ignore_index=True)

    assert len(development) + len(test) == len(work)
    assert set(FEATURES).issubset(work.columns)
    assert not work[FEATURES].isna().any().any()

    model = make_rf(params).fit(development[FEATURES], development["target_sensibilidad"])
    pred = model.predict(test[FEATURES])

    report = classification_report(
        test["target_sensibilidad"],
        pred,
        labels=class_order,
        output_dict=True,
        zero_division=0,
    )
    global_metrics = {
        "escenario": scenario,
        "n_clases": len(class_order),
        "train_validation": len(development),
        "test": len(test),
        "f1_macro_test": f1_score(test["target_sensibilidad"], pred, labels=class_order, average="macro", zero_division=0),
        "balanced_accuracy_test": balanced_accuracy_score(test["target_sensibilidad"], pred),
    }
    per_class = (
        pd.DataFrame(report)
        .T.loc[class_order, ["precision", "recall", "f1-score", "support"]]
        .reset_index()
        .rename(columns={"index": "clase", "f1-score": "f1"})
    )
    per_class.insert(0, "escenario", scenario)

    cm = pd.DataFrame(
        confusion_matrix(test["target_sensibilidad"], pred, labels=class_order),
        index=class_order,
        columns=class_order,
    )
    cm.index.name = "real"
    cm.columns.name = "predicho"
    cm.to_csv(TABLES / f"plus_matriz_confusion_{scenario}.csv", encoding="utf-8-sig")
    cm_fig = plot_confusion(cm, scenario, close=close)
    if scenario == "k3":
        save_csv(per_class.round(6), "punto6_metricas_rf_final_test_por_clase.csv")
        plot_rf_class_metrics(per_class, close=close)
    return global_metrics, per_class, cm, cm_fig


def plot_rf_class_metrics(per_class: pd.DataFrame, close: bool = True) -> plt.Figure:
    metrics = ["precision", "recall", "f1"]
    x = np.arange(len(per_class))
    width = 0.24
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    palette = ["#2563EB", "#F59E0B", "#10B981"]
    for i, metric in enumerate(metrics):
        vals = per_class[metric].to_numpy()
        ax.bar(x + (i - 1) * width, vals, width=width, label=metric.title(), color=palette[i])
        for xi, val in zip(x + (i - 1) * width, vals):
            ax.text(xi, val + 0.015, f"{val:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(per_class["clase"], rotation=15)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Valor de metrica en test")
    ax.set_title("Precision, Recall y F1 por clase - Random Forest V1")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "punto6_07_metricas_rf_por_clase_test.png", close=close)
    return fig


def plot_confusion(cm: pd.DataFrame, scenario: str, close: bool = True) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6.8, 5.8), constrained_layout=True)
    im = ax.imshow(cm.to_numpy(), cmap="Blues")
    ax.set_xticks(range(cm.shape[1]))
    ax.set_yticks(range(cm.shape[0]))
    ax.set_xticklabels(cm.columns, rotation=35, ha="right")
    ax.set_yticklabels(cm.index)
    ax.set_xlabel("Clase predicha")
    ax.set_ylabel("Clase real")
    ax.set_title(f"Matriz de confusion test - {scenario}")
    fig.colorbar(im, ax=ax, label="Observaciones")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            val = int(cm.iloc[i, j])
            color = "white" if val > cm.to_numpy().max() * 0.55 else "black"
            ax.text(j, i, str(val), ha="center", va="center", color=color, fontsize=8)
    save_figure(fig, f"plus_matriz_confusion_{scenario}.png", close=close)
    return fig


def plot_plus_global(metrics: pd.DataFrame, close: bool = True) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.5, 4.8), constrained_layout=True)
    x = np.arange(len(metrics))
    width = 0.34
    ax.bar(x - width / 2, metrics["f1_macro_test"], width=width, label="F1 macro", color="#2563EB")
    ax.bar(x + width / 2, metrics["balanced_accuracy_test"], width=width, label="Balanced Accuracy", color="#F59E0B")
    for xi, f1, ba in zip(x, metrics["f1_macro_test"], metrics["balanced_accuracy_test"]):
        ax.text(xi - width / 2, f1 + 0.012, f"{f1:.3f}", ha="center", va="bottom", fontsize=8)
        ax.text(xi + width / 2, ba + 0.012, f"{ba:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics["escenario"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Metrica en test")
    ax.set_title("Sensibilidad del Random Forest al numero de perfiles positivos")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "plus_metricas_globales_k.png", close=close)
    return fig


def plot_plus_class_sizes(class_summary: pd.DataFrame, close: bool = True) -> plt.Figure:
    pivot = class_summary.pivot(index="escenario", columns="clase", values="porcentaje_dataset").fillna(0)
    fig, ax = plt.subplots(figsize=(10, 5.4), constrained_layout=True)
    bottom = np.zeros(len(pivot))
    x = np.arange(len(pivot))
    for label in pivot.columns:
        color = CLASS_COLORS[label]
        ax.bar(x, pivot[label], bottom=bottom, label=label, color=color)
        bottom += pivot[label].to_numpy()
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index)
    ax.set_ylabel("Porcentaje del dataset")
    ax.set_title("Tamanos de clase por escenario K")
    ax.legend(ncol=3, bbox_to_anchor=(0.5, -0.18), loc="upper center")
    ax.grid(axis="y", alpha=0.25)
    save_figure(fig, "plus_tamanos_clase_por_k.png", close=close)
    return fig


def plot_plus_f1(per_class: pd.DataFrame, close: bool = True) -> plt.Figure:
    plot = per_class.copy()
    plot["clase_escenario"] = plot["escenario"] + " | " + plot["clase"]
    fig, ax = plt.subplots(figsize=(12, 5.8), constrained_layout=True)
    x = np.arange(len(plot))
    ax.bar(x, plot["f1"], color=[CLASS_COLORS[label] for label in plot["clase"]])
    ax.set_xticks(x)
    ax.set_xticklabels(plot["clase_escenario"], rotation=55, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("F1-score en test")
    ax.set_title("F1 por clase en cada escenario de sensibilidad")
    ax.grid(axis="y", alpha=0.25)
    for xi, val in zip(x, plot["f1"]):
        ax.text(xi, val + 0.012, f"{val:.2f}", ha="center", va="bottom", fontsize=7)
    save_figure(fig, "plus_f1_por_clase_k.png", close=close)
    return fig


def run_sensitivity(data: pd.DataFrame, params: dict, close: bool = True) -> dict:
    class_summaries = []
    global_metrics = []
    per_class_metrics = []
    confusion_matrices = {}
    confusion_figures = {}

    for k in [3, 4, 5]:
        target, ranges, _ = kmeans_targets(data, k)
        scenario = f"k{k}"
        ranges.insert(0, "escenario", scenario)
        class_summaries.append(ranges)
        class_order = ["Sin detecciones"] + (["Clúster 1", "Clúster 2", "Clúster 3"] if k == 3 else [f"Perfil positivo {i}" for i in range(1, k + 1)])
        if k == 3:
            assert int((target != data[TARGET]).sum()) == 0, "El target k=3 reconstruido no coincide con el vigente."
        gm, pc, cm, cm_fig = evaluate_rf_for_target(data, target, class_order, params, scenario, close=close)
        global_metrics.append(gm)
        per_class_metrics.append(pc)
        confusion_matrices[scenario] = cm
        confusion_figures[scenario] = cm_fig

    class_summary = pd.concat(class_summaries, ignore_index=True)
    global_df = pd.DataFrame(global_metrics)
    per_class_df = pd.concat(per_class_metrics, ignore_index=True)

    save_csv(class_summary.round(6), "plus_distribucion_clases_por_k.csv")
    save_csv(global_df.round(6), "plus_metricas_globales_test.csv")
    save_csv(per_class_df.round(6), "plus_metricas_por_clase_test.csv")

    figures = {
        "global": plot_plus_global(global_df, close=close),
        "class_sizes": plot_plus_class_sizes(class_summary, close=close),
        "f1_class": plot_plus_f1(per_class_df, close=close),
        "confusion": confusion_figures,
    }
    return {
        "class_summary": class_summary,
        "global_metrics": global_df,
        "per_class": per_class_df,
        "confusion_matrices": confusion_matrices,
        "figures": figures,
    }


def make_notebook() -> None:
    notebook_path = ROOT / "Analisis_Puntos_4_6_Plus.ipynb"
    point4 = pd.read_csv(TABLES / "punto4_resumen_estadistico_niveles.csv")
    kmetrics = pd.read_csv(TABLES / "punto6_kmeans_metricas_k_2_5.csv")
    global_metrics = pd.read_csv(TABLES / "plus_metricas_globales_test.csv")
    class_summary = pd.read_csv(TABLES / "plus_distribucion_clases_por_k.csv")
    per_class = pd.read_csv(TABLES / "plus_metricas_por_clase_test.csv")
    meteo_medians = pd.read_csv(TABLES / "punto6_heatmap_meteo_medianas_originales.csv")
    dept_props = pd.read_csv(TABLES / "punto6_departamento_porcentajes_por_nivel.csv")

    alto = point4.loc[point4[TARGET].eq("Clúster 3")].iloc[0]
    sin = point4.loc[point4[TARGET].eq("Sin detecciones")].iloc[0]
    bajo = point4.loc[point4[TARGET].eq("Clúster 1")].iloc[0]
    moderado = point4.loc[point4[TARGET].eq("Clúster 2")].iloc[0]
    k3 = global_metrics.loc[global_metrics["escenario"].eq("k3")].iloc[0]
    k4 = global_metrics.loc[global_metrics["escenario"].eq("k4")].iloc[0]
    k5 = global_metrics.loc[global_metrics["escenario"].eq("k5")].iloc[0]
    worst_k3 = per_class.loc[per_class["escenario"].eq("k3")].sort_values("f1").iloc[0]
    temp_max_class = meteo_medians.sort_values("temperature_2m_max_mean_weekly", ascending=False).iloc[0]
    precip_min_class = meteo_medians.sort_values("precipitation_sum_weekly").iloc[0]
    dept_high = dept_props.assign(positivas=dept_props[["Clúster 1", "Clúster 2", "Clúster 3"]].sum(axis=1)).sort_values("positivas", ascending=False).iloc[0]
    small_k5 = class_summary.loc[class_summary["escenario"].eq("k5")].sort_values("observaciones").iloc[0]

    def md(source: str) -> dict:
        return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}

    def code(source: str) -> dict:
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": source.splitlines(keepends=True),
        }

    cells = [
        md(
            """# Puntos 4 y 6 + plus del proyecto FIRMS

Este notebook es el documento principal del análisis complementario. Ejecuta cálculos locales, renderiza tablas y gráficos directamente debajo de cada celda, y además guarda copias reproducibles en `results/analisis_puntos_4_6_plus/`.

La metodología conserva los ceros como `Sin detecciones`, aplica K-Means solamente sobre observaciones positivas con `log1p(cantidad_detecciones)` y usa el Random Forest V1 ya seleccionado para el análisis supervisado."""
        ),
        code(
            """from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from src import generar_puntos_4_6_plus as firms

pd.set_option("display.max_columns", 80)
pd.set_option("display.width", 140)

firms.ensure_dirs()
data = firms.load_data()
params = firms.read_rf_params()

print(f"Dataset: {firms.DATA.relative_to(firms.ROOT)}")
print(f"Filas: {len(data):,}")
print("Variables del Random Forest V1:", firms.FEATURES)
print("Hiperparametros confirmados:", params)"""
        ),
        md(
            """## Punto 4: distribución interna de los niveles de actividad

Objetivo: describir la distribución real de `cantidad_detecciones` dentro de las cuatro clases finales, incluyendo correctamente la masa de ceros."""
        ),
        code(
            """point4 = firms.point4_summary(data)
display(point4.round(4))

fig = firms.plot_point4_distribution(data, point4, close=False)
plt.show()"""
        ),
        md(
            f"""**Interpretación.** `Sin detecciones` concentra {sin['observaciones']:.0f} observaciones ({sin['porcentaje_dataset']:.2f}% del total) y todos sus valores son cero. `Clúster 1` queda fijado en una detección; `Clúster 2` agrupa semanas de {moderado['minimo']:.0f} a {moderado['maximo']:.0f} detecciones. `Clúster 3` conserva el rango {alto['minimo']:.0f}-{alto['maximo']:.0f}, pero su mediana es {alto['mediana']:.0f}, Q3 es {alto['q3']:.0f} y la media es {alto['media']:.2f}; esto muestra una clase con muchas semanas relativamente cercanas al umbral inferior y una cola de eventos excepcionalmente altos."""
        ),
        code(
            """alto = point4.loc[point4[firms.TARGET].eq("Clúster 3")].iloc[0]
bajo = point4.loc[point4[firms.TARGET].eq("Clúster 1")].iloc[0]
moderado = point4.loc[point4[firms.TARGET].eq("Clúster 2")].iloc[0]
print(
    f"Interpretacion: Clúster 1 queda concentrado en {bajo['minimo']:.0f} deteccion. "
    f"Clúster 2 cubre {moderado['minimo']:.0f}-{moderado['maximo']:.0f}. "
    f"Clúster 3 conserva el rango {alto['minimo']:.0f}-{alto['maximo']:.0f}, "
    f"pero su mediana es {alto['mediana']:.0f} y Q3={alto['q3']:.0f}; "
    "por tanto, el maximo representa una cola alta, no el caso tipico."
)"""
        ),
        md(
            """## Punto 6.1: método del codo e inercia de K-Means

Objetivo: comparar K=2,3,4,5 sobre la misma población positiva y la misma transformación `log1p(cantidad_detecciones)`."""
        ),
        code(
            """kmetrics = firms.kmeans_metrics(data)
display(kmetrics.round(4))

fig = firms.plot_kmeans_metrics(kmetrics, close=False)
plt.show()"""
        ),
        md(
            f"""**Interpretación.** La inercia cae de {kmetrics.loc[kmetrics.k.eq(2), 'inertia'].iloc[0]:.2f} con k=2 a {kmetrics.loc[kmetrics.k.eq(5), 'inertia'].iloc[0]:.2f} con k=5, y Silhouette sube de {kmetrics.loc[kmetrics.k.eq(2), 'silhouette'].iloc[0]:.3f} a {kmetrics.loc[kmetrics.k.eq(5), 'silhouette'].iloc[0]:.3f}. Sin embargo, el cluster positivo menor baja de {kmetrics.loc[kmetrics.k.eq(3), 'cluster_minimo'].iloc[0]:.0f} casos con k=3 a {kmetrics.loc[kmetrics.k.eq(5), 'cluster_minimo'].iloc[0]:.0f} con k=5. Por eso k mayores separan mejor algunos conteos en sentido geométrico, pero fragmentan la señal en clases más pequeñas."""
        ),
        code(
            """print(
    "Interpretacion: la inercia baja al aumentar K, pero la mejora debe leerse junto "
    "con Silhouette y el tamano minimo de los grupos. Silhouette no decide sola, "
    "porque K mayores fragmentan los conteos positivos en clases mas pequenas."
)"""
        ),
        md(
            """## Punto 6.2: boxplot de detecciones por perfil positivo

Objetivo: visualizar la dispersión de `Clúster 1`, `Clúster 2` y `Clúster 3` sin que la cola alta vuelva ilegible el gráfico."""
        ),
        code(
            """fig = firms.plot_positive_boxplot(data, close=False)
plt.show()"""
        ),
        md(
            f"""**Interpretación.** El gráfico confirma que `Clúster 1` no tiene dispersión porque corresponde a una detección. `Clúster 2` concentra valores entre {moderado['minimo']:.0f} y {moderado['maximo']:.0f}. `Clúster 3` tiene una mediana baja dentro de su rango ({alto['mediana']:.0f}), pero incluye valores extremos hasta {alto['maximo']:.0f}; por eso la escala logarítmica ayuda a ver la caja sin ocultar la cola."""
        ),
        code(
            """print(
    "Interpretacion: se muestran valores extremos y se usa escala logaritmica en la escala original "
    "de conteos. Esto permite ver simultaneamente la concentracion de cada clase y la cola de Clúster 3."
)"""
        ),
        md(
            """## Punto 6.3: boxplot de temperatura por nivel

Objetivo: comparar la temperatura máxima media semanal entre las cuatro clases finales."""
        ),
        code(
            """fig = firms.plot_meteo_boxplot(
    data,
    "temperature_2m_max_mean_weekly",
    "punto6_03_boxplot_temperatura_por_nivel.png",
    "Temperatura maxima media semanal por nivel FIRMS",
    close=False,
)
display(pd.read_csv(firms.TABLES / "punto6_03_boxplot_temperatura_por_nivel_observaciones_validas.csv"))
plt.show()"""
        ),
        md(
            f"""**Interpretación.** En medianas, la temperatura máxima media semanal más alta aparece en `{temp_max_class[TARGET]}` ({temp_max_class['temperature_2m_max_mean_weekly']:.2f} °C). Las distribuciones se solapan, de modo que el gráfico sugiere asociación descriptiva, no una regla suficiente para separar las clases ni evidencia causal."""
        ),
        code(
            """print(
    "Interpretacion: el grafico compara medianas, dispersion y extremos de temperatura por clase. "
    "Es evidencia descriptiva; no implica causalidad ni significacion estadistica."
)"""
        ),
        md(
            """## Punto 6.4: boxplot de humedad por nivel

Objetivo: comparar la humedad relativa mínima media semanal entre las cuatro clases finales, con la misma organización visual que temperatura."""
        ),
        code(
            """fig = firms.plot_meteo_boxplot(
    data,
    "relative_humidity_2m_min_mean_weekly",
    "punto6_04_boxplot_humedad_por_nivel.png",
    "Humedad relativa minima media semanal por nivel FIRMS",
    close=False,
)
display(pd.read_csv(firms.TABLES / "punto6_04_boxplot_humedad_por_nivel_observaciones_validas.csv"))
plt.show()"""
        ),
        md(
            """**Interpretación.** La humedad presenta diferencias de posición entre clases, pero también solapamiento. No se observan nulos en las variables meteorológicas usadas, por lo que las comparaciones mantienen el mismo conjunto de observaciones por clase."""
        ),
        code(
            """print(
    "Interpretacion: el grafico resume diferencias descriptivas de humedad entre niveles. "
    "Las observaciones validas permiten verificar que no hay cambios de denominador por nulos."
)"""
        ),
        md(
            """## Punto 6.5: heatmap de variables meteorológicas

Objetivo: resumir temperatura, humedad, viento y precipitación por clase sin mezclar escalas heterogéneas."""
        ),
        code(
            """meteo_medians, fig = firms.heatmap_meteo(data, close=False)
display(meteo_medians.round(3))
display(pd.read_csv(firms.TABLES / "punto6_meteo_nulos_por_clase.csv"))
plt.show()"""
        ),
        md(
            f"""**Interpretación.** El heatmap estandariza las medianas para comparar variables con unidades distintas. La precipitación semanal mediana más baja aparece en `{precip_min_class[TARGET]}` ({precip_min_class['precipitation_sum_weekly']:.2f} mm). Esta lectura es descriptiva: permite ver perfiles relativos, no afirmar que una variable meteorológica cause el nivel de actividad."""
        ),
        code(
            """print(
    "Interpretacion: el heatmap usa medianas por clase estandarizadas por variable. "
    "Los colores indican desvios respecto al promedio de cada variable, no valores absolutos comparables entre magnitudes."
)"""
        ),
        md(
            """## Punto 6.6: distribución de niveles por departamento

Objetivo: comparar la composición porcentual de niveles FIRMS en los 19 departamentos, usando como denominador el total de observaciones de cada departamento."""
        ),
        code(
            """dept_counts, dept_props, fig = firms.department_distribution(data, close=False)
display(dept_counts)
display(dept_props.round(2))
plt.show()"""
        ),
        md(
            f"""**Interpretación.** Las barras usan porcentajes dentro de cada departamento. El mayor porcentaje combinado de clases positivas aparece en `{dept_high['departamento']}` ({dept_high['positivas']:.2f}%). Esto permite comparar composición territorial sin que un departamento parezca más activo solo por tener más filas."""
        ),
        code(
            """row_sums = dept_props[firms.ORDER].sum(axis=1).round(6)
print(f"Validacion: minimo={row_sums.min():.6f}, maximo={row_sums.max():.6f}; las proporciones por departamento suman 100%.")
print(
    "Interpretacion: las barras apiladas al 100% comparan perfiles territoriales sin confundir mayor cantidad total de filas "
    "con mayor actividad relativa."
)"""
        ),
        md(
            """## Punto 6.7: Precision, Recall y F1 por clase del Random Forest

Objetivo: mostrar el desempeño por clase del Random Forest V1 final en el split de test ya definido."""
        ),
        code(
            """target_k3, _, _ = firms.kmeans_targets(data, 3)
global_k3, rf_class_metrics, cm_k3, cm_fig_k3 = firms.evaluate_rf_for_target(
    data,
    target_k3,
    firms.ORDER,
    params,
    "k3",
    close=True,
)
display(pd.DataFrame([global_k3]).round(4))
display(rf_class_metrics.round(4))

fig = firms.plot_rf_class_metrics(rf_class_metrics, close=False)
plt.show()"""
        ),
        md(
            f"""**Interpretación.** En test, el modelo reconoce mejor `Sin detecciones` (F1={per_class[(per_class.escenario == 'k3') & (per_class.clase == 'Sin detecciones')]['f1'].iloc[0]:.3f}) que las clases positivas. La clase más débil en k=3 es `{worst_k3['clase']}` (F1={worst_k3['f1']:.3f}). Esto indica que el modelo capta parte de la diferencia entre semanas sin actividad y con actividad, pero tiene dificultades para separar niveles positivos cercanos."""
        ),
        code(
            """worst = rf_class_metrics.sort_values("f1").iloc[0]
print(
    f"Interpretacion: la clase con menor F1 en test es {worst['clase']} "
    f"(F1={worst['f1']:.3f}). Las clases positivas son mas dificiles que Sin detecciones."
)"""
        ),
        md(
            """## Plus: análisis de sensibilidad con k=3, k=4 y k=5

Objetivo: aislar el efecto de cambiar la discretización del target positivo. Se mantienen las mismas observaciones, claves departamento-semana, variables V1, splits e hiperparámetros del Random Forest."""
        ),
        code(
            """sensitivity = firms.run_sensitivity(data, params, close=True)
global_metrics = sensitivity["global_metrics"]
class_summary = sensitivity["class_summary"]
per_class = sensitivity["per_class"]
confusion_matrices = sensitivity["confusion_matrices"]

display(global_metrics.round(4))
display(class_summary.round(4))
fig = firms.plot_plus_global(global_metrics, close=False)
plt.show()"""
        ),
        md(
            f"""**Interpretación.** La sensibilidad no mejora al aumentar K: k=3 obtiene F1 macro={k3['f1_macro_test']:.4f} y Balanced Accuracy={k3['balanced_accuracy_test']:.4f}; k=4 baja a {k4['f1_macro_test']:.4f}/{k4['balanced_accuracy_test']:.4f}; k=5 baja a {k5['f1_macro_test']:.4f}/{k5['balanced_accuracy_test']:.4f}. Además, con k=5 aparece una clase de solo {small_k5['observaciones']:.0f} observaciones ({small_k5['porcentaje_dataset']:.2f}% del dataset)."""
        ),
        code(
            """fig = firms.plot_plus_class_sizes(class_summary, close=False)
plt.show()"""
        ),
        md(
            """**Interpretación.** El aumento de K no crea solamente más detalle semántico: divide grupos positivos existentes en clases progresivamente más chicas. Esa fragmentación puede ser útil para describir conteos, pero dificulta el aprendizaje supervisado porque cada clase aporta menos ejemplos."""
        ),
        code(
            """display(per_class.round(4))
fig = firms.plot_plus_f1(per_class, close=False)
plt.show()"""
        ),
        md(
            """**Interpretación.** Los F1 por clase muestran que las nuevas clases de k=4 y k=5 no se reconocen de manera uniforme. Las clases más pequeñas, especialmente el perfil positivo más alto de k=5, tienen pocos casos de test y F1 bajo, por lo que una métrica global no debe leerse como mejora general de todas las categorías."""
        ),
        code(
            """for scenario, cm in confusion_matrices.items():
    print(f"Matriz de confusion - {scenario}")
    display(cm)
    fig = firms.plot_confusion(cm, scenario, close=False)
    plt.show()"""
        ),
        md(
            """**Interpretación.** Las matrices de confusión muestran que muchas semanas positivas se reparten entre clases vecinas o se predicen como `Sin detecciones`. En términos del problema, confundir `Clúster 3` con `Clúster 2` implica subestimar el orden del grupo según sus centroides de conteos; confundir `Sin detecciones` con `Clúster 1` implica marcar actividad donde no hubo detecciones."""
        ),
        code(
            """best = global_metrics.sort_values(["f1_macro_test", "balanced_accuracy_test"], ascending=False).iloc[0]
smallest = class_summary.sort_values(["escenario", "observaciones"]).groupby("escenario").first().reset_index()
display(smallest[["escenario", "clase", "observaciones", "porcentaje_dataset"]].round(4))
print(
    f"Conclusion: dentro de esta sensibilidad, el mayor F1 macro de test queda en {best['escenario']} "
    f"({best['f1_macro_test']:.3f}). Al aumentar K, aparecen clases positivas mas chicas y el desempeno global baja; "
    "esto respalda que k=3 ofrece una particion mas simple e interpretable para este proyecto, sin usar test para redisenar el modelo."
)"""
        ),
    ]
    # Actualizar las interpretaciones desde las tablas, sin conservar cifras antiguas.
    # Las celdas de código sin cambios mantienen sus salidas: generar el documento
    # no debe ejecutar ni volver a ajustar los modelos del análisis.
    previous_notebook = None
    if notebook_path.exists():
        previous_notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        previous = previous_notebook["cells"]
        if len(previous) == len(cells) and all(
            old["cell_type"] == new["cell_type"] for old, new in zip(previous, cells)
        ):
            for old, new in zip(previous, cells):
                if new["cell_type"] == "code" or old["source"] == new["source"]:
                    new.update(old)
                elif new["cell_type"] == "markdown":
                    new.update({key: value for key, value in old.items() if key != "source"})
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    if previous_notebook is not None:
        notebook["metadata"] = previous_notebook.get("metadata", notebook["metadata"])
    notebook_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def make_interpretation(
    point4: pd.DataFrame,
    kmetrics: pd.DataFrame,
    global_metrics: pd.DataFrame,
    class_summary: pd.DataFrame,
    per_class: pd.DataFrame,
) -> None:
    alto = point4.loc[point4[TARGET].eq("Clúster 3")].iloc[0]
    sin = point4.loc[point4[TARGET].eq("Sin detecciones")].iloc[0]
    best = global_metrics.sort_values(["f1_macro_test", "balanced_accuracy_test"], ascending=False).iloc[0]
    rf_k3 = per_class[per_class["escenario"].eq("k3")].sort_values("f1").iloc[0]
    min_classes = class_summary.sort_values(["escenario", "observaciones"]).groupby("escenario").first().reset_index()
    lines = [
        "# Interpretaciones sinteticas",
        "",
        "## Punto 4",
        f"- `Sin detecciones` concentra {sin['observaciones']:.0f} observaciones ({sin['porcentaje_dataset']:.2f}% del dataset) y todos sus conteos son cero.",
        f"- `Clúster 3` conserva en los datos locales el rango {alto['minimo']:.0f}-{alto['maximo']:.0f}, pero su mediana es {alto['mediana']:.0f} y el tercer cuartil es {alto['q3']:.0f}; el maximo representa una cola extrema, no el comportamiento tipico.",
        "- Los cuartiles se calcularon sobre observaciones reales agrupadas por la etiqueta final; no se eliminaron valores extremos.",
        "",
        "## Punto 6",
        f"- La inercia baja de {kmetrics.loc[kmetrics.k.eq(2), 'inertia'].iloc[0]:.2f} con k=2 a {kmetrics.loc[kmetrics.k.eq(5), 'inertia'].iloc[0]:.2f} con k=5. La mejora se desacelera, y Silhouette por si sola no define la solucion porque al aumentar K se fragmentan los conteos positivos.",
        "- Los boxplots meteorologicos comparan distribuciones por clase; son evidencia descriptiva y no prueban causalidad ni significacion estadistica.",
        f"- En el Random Forest V1 evaluado en test, la clase con menor F1 en k=3 es `{rf_k3['clase']}` (F1={rf_k3['f1']:.3f}).",
        "",
        "## Plus",
        f"- El mejor F1 macro de test dentro de la sensibilidad fue {best['f1_macro_test']:.4f} en {best['escenario']}; esto no reabre la seleccion del modelo, solo documenta sensibilidad al target.",
        "- Al aumentar K, las clases positivas representan particiones distintas del conteo, por lo que sus F1 por clase no son comparables como si fueran las mismas categorias.",
        "- Clase mas pequena por escenario:",
    ]
    for row in min_classes.itertuples():
        lines.append(f"  - {row.escenario}: {row.clase}, {row.observaciones:.0f} observaciones ({row.porcentaje_dataset:.2f}%).")
    lines.append("")
    lines.append("Todas las ejecuciones usaron las mismas claves departamento-semana, variables V1 permitidas, splits guardados e hiperparametros del Random Forest seleccionado.")
    (OUT / "interpretaciones.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Reproduce solamente la presentación de resultados ya guardados."""
    from src.refresh_presentation import main as refresh
    refresh()


if __name__ == "__main__":
    main()
