import pandas as pd

from src.climate_experiment import extract_climate, make_features, metrics
from src.etl import BASE


def test_xlsx_clima_se_filtra_por_ubigeo_y_blancos_no_son_cero():
    frame, coverage = extract_climate(BASE / "XLSX/clima_departamento (2).xlsx")
    assert coverage["filas_panel"] == 14 * 470
    assert coverage["distritos"] == 14
    assert coverage["casos_observados"] == 837
    assert coverage["casos_desconocidos"] == len(frame) - 837
    assert frame.casos.isna().any()
    assert frame.loc[frame.casos.isna(), "casos"].eq(0).sum() == 0
    assert not frame.duplicated(["ubigeo", "ano", "semana"]).any()


def test_features_clima_y_casos_solo_semanas_previas():
    panel = pd.DataFrame({
        "ubigeo": ["150101"] * 8,
        "distrito": ["Lima"] * 8,
        "ano": [2024] * 8,
        "semana": list(range(1, 9)),
        "casos": [1, 2, None, 4, 5, 6, 7, 8],
        "tmean": [20, 21, 22, 23, 24, 25, 26, 999],
        "tmax": [25] * 8, "tmin": [15] * 8, "humr": [80] * 8, "ptot": [1] * 8,
    })
    first, _, cols = make_features(panel)
    changed = panel.copy()
    changed.loc[7, ["casos", "tmean", "tmax", "tmin", "humr", "ptot"]] = [9999, 999, 999, 999, 999, 999]
    second, _, _ = make_features(changed)
    # La fila de SE08 solo usa clima/casos de SE07 o anteriores.
    a = first.loc[first.semana.eq(8)].iloc[0]
    b = second.loc[second.semana.eq(8)].iloc[0]
    assert a["tmean_lag_1"] == b["tmean_lag_1"] == 26
    assert a["casos_lag_1"] == b["casos_lag_1"] == 7
    # La semana objetivo no aparece entre sus variables meteorológicas.
    assert all("lag_" in c for c in cols if c.startswith(("tmean", "tmax", "tmin", "humr", "ptot")))
    assert pd.isna(first.loc[first.semana.eq(4), "casos_lag_1"]).all()


def test_metricas_clima_manejan_real_cero():
    result = metrics([0, 10], [0, 11])
    assert result["n"] == 2
    assert result["casos_reales_cero"] == 1
    assert result["WAPE_pct"] == 10
    assert result["dentro_10_pct"] == 0
