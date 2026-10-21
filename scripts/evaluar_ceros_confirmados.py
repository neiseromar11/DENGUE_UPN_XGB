"""Controlled walk-forward experiment: confirmed-case blanks as zero.

Scoring always uses explicit CDC CONFIRMADO values. Only the candidate's
training labels convert blank weekly cells to zero, and only from 2020 onward.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.climate_experiment import (
    BASE,
    CLIMATE_COLUMNS,
    UBIGEO_DISTRICT,
    _fit_predict,
    make_features,
    metrics,
    read_district_sheet,
    sha256,
)
from src.calendar_epi import fecha_semana


SOURCE = BASE.parent / "clima_departamento LIMA METROPOLITANA.xlsx"
FIRST_YEAR = 2020
VALIDATION = (2023, 2024)
FINAL_TEST = (2025, 2026)


def apply_blank_zero_hypothesis(panel: pd.DataFrame) -> pd.DataFrame:
    """Return an isolated candidate copy; preserve pre-2020 unknowns."""
    candidate = panel.copy()
    mask = candidate.ano.ge(FIRST_YEAR)
    candidate.loc[mask, "casos"] = candidate.loc[mask, "casos"].fillna(0)
    return candidate


def load_confirmed(path: Path = SOURCE) -> tuple[pd.DataFrame, dict]:
    raw = read_district_sheet(path)
    raw["UBIGEO"] = raw.UBIGEO.astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(6)
    d = raw.loc[raw.UBIGEO.isin(UBIGEO_DISTRICT)].copy()
    d["ano"] = pd.to_numeric(d.Ano, errors="raise").astype(int)
    d["semana"] = pd.to_numeric(d.Semana, errors="raise").astype(int)
    for year, week in d[["ano", "semana"]].drop_duplicates().itertuples(index=False, name=None):
        fecha_semana(year, week)
    d["casos"] = pd.to_numeric(d.Casos.where(d["Tipo caso"].eq("CONFIRMADO")), errors="coerce")
    for col in CLIMATE_COLUMNS:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d["ubigeo"] = d.UBIGEO
    d["distrito"] = d.ubigeo.map(UBIGEO_DISTRICT)
    key = ["ubigeo", "ano", "semana"]
    if d.duplicated(key).any():
        raise ValueError("Duplicados UBIGEO-ano-semana")
    expected = len(UBIGEO_DISTRICT) * (52 * 9 + 2)
    if len(d) != expected or d.ubigeo.nunique() != 14:
        raise ValueError(f"Cobertura inesperada: {len(d)} filas, se esperaban {expected}")
    panel = d[["ubigeo", "distrito", "ano", "semana", "casos", *CLIMATE_COLUMNS]].sort_values(key).reset_index(drop=True)
    usable = panel.loc[panel.ano.between(FIRST_YEAR, 2026)]
    coverage = {
        "filas_2020_2026": int(len(usable)),
        "filas_casos_explicitos": int(usable.casos.notna().sum()),
        "semanas_calendario": int(usable[["ano", "semana"]].drop_duplicates().shape[0]),
        "semanas_con_casos_observados": int(usable.loc[usable.casos.notna(), ["ano", "semana"]].drop_duplicates().shape[0]),
        "positivos": int(usable.casos.gt(0).sum()),
        "ceros_explicitos": int(usable.casos.eq(0).sum()),
        "vacios": int(usable.casos.isna().sum()),
        "ultima_semana_con_casos": f"{int(usable.loc[usable.casos.notna(), 'ano'].max())}-SE{int(usable.loc[usable.casos.notna()].sort_values(['ano','semana']).iloc[-1].semana):02d}",
        "casos_explicitos_por_ano": {str(int(y)): int(g.casos.notna().sum()) for y, g in usable.groupby("ano")},
    }
    return panel, coverage


def evaluate(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    observed_features, base_cols, climate_cols = make_features(panel)
    zero_panel = apply_blank_zero_hypothesis(panel)
    zero_features, _, zero_climate_cols = make_features(zero_panel)
    rows = []
    weeks = sorted(set(zip(panel.ano.astype(int), panel.semana.astype(int))))
    for year, week in weeks:
        if year < VALIDATION[0] or year > FINAL_TEST[1]:
            continue
        before_obs = (observed_features.ano < year) | (observed_features.ano.eq(year) & observed_features.semana.lt(week))
        before_zero = (zero_features.ano < year) | (zero_features.ano.eq(year) & zero_features.semana.lt(week))
        train_known = observed_features.loc[before_obs & observed_features.ano.ge(FIRST_YEAR) & observed_features.casos.notna()]
        train_zero = zero_features.loc[before_zero & zero_features.ano.ge(FIRST_YEAR) & zero_features.casos.notna()]
        target_mask = (panel.ano.eq(year) & panel.semana.eq(week) & panel.casos.notna())
        if int(target_mask.sum()) == 0 or len(train_known) < 90 or len(train_zero) < 90:
            continue
        target_known = observed_features.loc[target_mask]
        target_zero = zero_features.loc[target_mask]
        p_current = _fit_predict(train_known, target_known, base_cols)
        p_known_climate = _fit_predict(train_known, target_known, climate_cols)
        p_zero_climate = _fit_predict(train_zero, target_zero, zero_climate_cols)
        for i, (_, r) in enumerate(target_known.iterrows()):
            rows.append({
                "ubigeo": r.ubigeo, "distrito": r.distrito, "ano": year, "semana": week,
                "semana_epidemiologica": f"{year}-SE{week:02d}", "real_confirmado": float(r.casos),
                "prediccion_actual_sin_clima": float(p_current[i]),
                "prediccion_actual_con_clima_sin_ceros": float(p_known_climate[i]),
                "prediccion_ceros_mas_clima": float(p_zero_climate[i]),
                "fecha_corte": f"{year}-SE{week-1:02d}" if week > 1 else f"{year-1}-ultima-semana",
                "entrenamiento_candidato_incluye_ceros": int(len(train_zero)),
            })
    pred = pd.DataFrame(rows)
    if pred.empty:
        raise ValueError("No hay observaciones suficientes para backtesting")

    def summary(part: pd.DataFrame) -> dict:
        y = part.real_confirmado
        return {
            "actual_sin_clima": metrics(y, part.prediccion_actual_sin_clima),
            "actual_con_clima_sin_ceros": metrics(y, part.prediccion_actual_con_clima_sin_ceros),
            "candidato_ceros_mas_clima": metrics(y, part.prediccion_ceros_mas_clima),
        }

    validation = pred[pred.ano.between(*VALIDATION)]
    final = pred[pred.ano.between(*FINAL_TEST)]
    if validation.empty or final.empty:
        raise ValueError("Validacion o prueba final vacia")
    # Selection is fixed on validation only. Final is checked once against the existing baseline.
    selected = "candidato_ceros_mas_clima" if (
        metrics(validation.real_confirmado, validation.prediccion_ceros_mas_clima)["WAPE_pct"]
        < metrics(validation.real_confirmado, validation.prediccion_actual_sin_clima)["WAPE_pct"]
    ) else "actual_sin_clima"
    return pred, {
        "validacion_2023_2024": summary(validation),
        "prueba_final_2025_2026": summary(final),
        "seleccion_solo_validacion": selected,
        "regla_adopcion": "Adoptar solo si gana en validacion y reduce WAPE y MAE en prueba final frente al actual.",
        "adoptar": bool(
            selected == "candidato_ceros_mas_clima"
            and metrics(final.real_confirmado, final.prediccion_ceros_mas_clima)["WAPE_pct"]
            < metrics(final.real_confirmado, final.prediccion_actual_sin_clima)["WAPE_pct"]
            and metrics(final.real_confirmado, final.prediccion_ceros_mas_clima)["MAE"]
            < metrics(final.real_confirmado, final.prediccion_actual_sin_clima)["MAE"]
        ),
    }


def run() -> dict:
    panel, coverage = load_confirmed()
    pred, result = evaluate(panel)
    report = {
        "fuente": {"archivo": str(SOURCE.relative_to(BASE.parent)), "sha256": sha256(SOURCE),
                   "definicion": "CONFIRMADO", "ubigeos": 14},
        "cobertura": coverage,
        **result,
        "errores_mayores_candidato": pred.assign(
            error_abs=(pred.real_confirmado - pred.prediccion_ceros_mas_clima).abs(),
            error_pct=np.where(pred.real_confirmado.gt(0),
                               (pred.real_confirmado - pred.prediccion_ceros_mas_clima).abs() / pred.real_confirmado * 100,
                               np.nan),
        ).sort_values("error_abs", ascending=False).head(15).replace({np.nan: None})[
            ["distrito", "semana_epidemiologica", "real_confirmado", "prediccion_ceros_mas_clima", "error_abs", "error_pct"]
        ].to_dict("records"),
    }
    report_path = BASE / "reports/evaluacion_ceros_confirmados.json"
    pred_path = BASE / "reports/predicciones_ceros_confirmados.csv"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    pred.to_csv(pred_path, index=False, encoding="utf-8-sig")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
