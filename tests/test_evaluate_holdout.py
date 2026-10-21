import pandas as pd

from src.evaluate_holdout import split_temporal, metricas


def test_split_temporal_separa_semanas_completas_y_ordenadas():
    frame = pd.DataFrame([
        {"ano": 2024, "semana": w, "distrito": f"D{i}"}
        for w in range(1, 11) for i in range(2)
    ])
    train, test, start = split_temporal(frame, .2)
    assert start == (2024, 9)
    assert set(zip(train.ano, train.semana)).isdisjoint(set(zip(test.ano, test.semana)))
    assert max(zip(train.ano, train.semana)) < min(zip(test.ano, test.semana))
    assert len(test) == 4


def test_metricas_cero_real_no_define_error_porcentual():
    result = metricas([0, 100], [8, 105])
    assert result["semanas_con_real_cero"] == 1
    assert result["WAPE_pct"] == 13
    assert result["semanas_error_menor_10_pct"] == 100
