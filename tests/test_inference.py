import pandas as pd
import pytest

from src.inference import load_metadata, load_model, predict, predict_proba, validate_input


@pytest.fixture(scope="module")
def resources():
    metadata = load_metadata()
    model = load_model()
    example = pd.DataFrame(
        [{
            "departamento": "Montevideo",
            "mes": 1,
            "temperature_2m_max_mean_weekly": 28.0,
            "relative_humidity_2m_min_mean_weekly": 45.0,
            "wind_speed_10m_max_mean_weekly": 22.0,
            "precipitation_sum_weekly": 4.0,
        }]
    )
    return metadata, model, example


def test_loads_pipeline(resources):
    metadata, model, _ = resources
    assert metadata["nombre_modelo"] == "RandomForestClassifier V1"
    assert hasattr(model, "predict")


def test_predicts_one_and_many_rows(resources):
    metadata, model, example = resources
    one = predict(example, model, metadata)
    many = predict(pd.concat([example, example], ignore_index=True), model, metadata)
    assert len(one) == 1
    assert len(many) == 2
    assert set(many).issubset(metadata["clases"])


def test_probabilities_sum_to_one(resources):
    metadata, model, example = resources
    probabilities = predict_proba(example, model, metadata)
    assert list(probabilities.columns) == list(model.classes_)
    assert probabilities.sum(axis=1).iloc[0] == pytest.approx(1.0)


def test_missing_variable_has_clear_error(resources):
    metadata, _, example = resources
    with pytest.raises(ValueError, match="Faltan variables requeridas"):
        validate_input(example.drop(columns=["mes"]), metadata)


def test_known_and_unknown_department_are_supported(resources):
    metadata, model, example = resources
    assert len(predict(example, model, metadata)) == 1
    unknown = example.assign(departamento="Departamento no observado")
    assert len(predict(unknown, model, metadata)) == 1


def test_rejects_contemporary_detection_count(resources):
    metadata, _, example = resources
    with pytest.raises(ValueError, match="No se permiten"):
        validate_input(example.assign(cantidad_detecciones=3), metadata)
