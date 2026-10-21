import pandas as pd

from scripts.evaluar_ceros_confirmados import apply_blank_zero_hypothesis


def test_hypotesis_de_ceros_no_altera_observaciones_ni_periodo_previo():
    panel = pd.DataFrame({
        "ano": [2019, 2020, 2020],
        "casos": [None, None, 4.0],
    })
    candidate = apply_blank_zero_hypothesis(panel)
    assert pd.isna(candidate.loc[0, "casos"])
    assert candidate.loc[1, "casos"] == 0
    assert candidate.loc[2, "casos"] == 4.0
    assert pd.isna(panel.loc[1, "casos"])

