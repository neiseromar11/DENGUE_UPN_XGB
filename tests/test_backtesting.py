import pandas as pd
import numpy as np

from src import backtesting


def test_walk_forward_no_usa_semana_objetivo_ni_futuro(monkeypatch):
    """Una alteración del valor real objetivo no puede cambiar su predicción."""
    trained_cuts = []

    class Modelo:
        def predict(self, x):
            return x.lag_1.to_numpy()

    def entrenar(train, feature_cols=None, params=None):
        trained_cuts.append((int(train.ano.max()), int(train.loc[train.ano.eq(train.ano.max()), 'semana'].max())))
        return Modelo()

    monkeypatch.setattr(backtesting, "entrenar_xgboost", entrenar)
    base = pd.DataFrame([
        {"distrito": d, "ano": 2023, "semana": w, "casos_notificados": float(w+d), "sin_registros_fuente": False}
        for d in range(3) for w in range(1, 36)
    ])
    first = backtesting.backtest_walk_forward(base, minimo_entrenamiento=10)
    objetivo = first[(first.ano == 2023) & (first.semana == 25)]
    assert not objetivo.empty
    assert (2023, 24) in trained_cuts

    changed = base.copy()
    changed.loc[changed.semana.eq(25), "casos_notificados"] = 9999
    second = backtesting.backtest_walk_forward(changed, minimo_entrenamiento=10)
    p1 = first[(first.ano == 2023) & (first.semana == 25)].prediccion.to_numpy()
    p2 = second[(second.ano == 2023) & (second.semana == 25)].prediccion.to_numpy()
    np.testing.assert_array_equal(p1, p2)


def test_semana_sin_registro_no_se_imputa_como_cero():
    d = pd.DataFrame([
        {"distrito": "A", "ano": 2023, "semana": w,
         "casos_notificados": 0 if w == 4 else w,
         "sin_registros_fuente": w == 4}
        for w in range(1, 8)
    ])
    out = backtesting.backtest_walk_forward(d, minimo_entrenamiento=1)
    assert not ((out.ano == 2023) & (out.semana == 5)).any()
