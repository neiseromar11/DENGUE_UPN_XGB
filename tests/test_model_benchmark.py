import numpy as np
import pandas as pd

from src import model_benchmark


def test_nested_benchmark_usa_solo_el_pasado(monkeypatch):
    limites = []

    def fake_fit_predict(nombre, train, test, cols):
        ultimo_train = max(zip(train.ano, train.semana))
        primer_test = min(zip(test.ano, test.semana))
        limites.append((ultimo_train, primer_test))
        return test.lag_1.to_numpy(dtype=float)

    monkeypatch.setattr(model_benchmark, "_fit_predict", fake_fit_predict)
    d = pd.DataFrame([
        {"distrito": f"D{i}", "ano": 2023, "semana": w,
         "casos_notificados": float(w+i), "sin_registros_fuente": False}
        for i in range(3) for w in range(1, 42)
    ])
    a = model_benchmark.benchmark_walk_forward(d, minimo=10)
    assert not a.empty
    assert all(train < test for train, test in limites)

    d.loc[d.semana.eq(30), "casos_notificados"] = 9000
    b = model_benchmark.benchmark_walk_forward(d, minimo=10)
    pa = a.loc[a.semana.eq(30), "prediccion"].to_numpy()
    pb = b.loc[b.semana.eq(30), "prediccion"].to_numpy()
    np.testing.assert_array_equal(pa, pb)


def test_comparacion_incluye_seleccion_y_margenes_cero():
    d = pd.DataFrame({"real": [0, 10], "prediccion": [1., 10.],
                      "persistencia": [0., 9.], "media_3": [0., 11.],
                      "xgb_actual": [1., 12.], "xgb_log1p": [1., 10.],
                      "xgb_regularizado": [1., 10.], "poisson": [1., 10.]})
    metricas = model_benchmark.comparar_metricas(d)
    assert "seleccion_temporal" in metricas.modelo.values
    assert metricas.loc[metricas.modelo.eq("seleccion_temporal"), "dentro_10_pct"].iloc[0] == 100
