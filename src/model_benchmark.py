"""Comparacion walk-forward anidada de XGBoost y baselines sobre semanas observadas."""
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from .backtesting import _ejemplo
    from .calendar_epi import fecha_semana
    from .features import obtener_feature_columns
    from .model import entrenar_xgboost
except ImportError:
    from backtesting import _ejemplo
    from calendar_epi import fecha_semana
    from features import obtener_feature_columns
    from model import entrenar_xgboost

MODELOS = ("persistencia", "media_3", "xgb_actual", "xgb_log1p", "xgb_regularizado", "poisson")
BENCHMARK_VERSION = "walk-forward-nested-v3-district-effects"


def _ejemplos(datos):
    if "sin_registros_fuente" not in datos:
        raise ValueError("Se requiere sin_registros_fuente para excluir cobertura desconocida.")
    panel = {}
    for distrito, g in datos.groupby("distrito"):
        panel[distrito] = {(int(r.ano), int(r.semana)): (None if bool(r.sin_registros_fuente) else float(r.casos_notificados)) for r in g.itertuples()}
    fechas = sorted(set(k for s in panel.values() for k in s))
    por_dia = {fecha_semana(*k): k for k in fechas}
    rows = []
    for distrito, serie in panel.items():
        for semana in fechas:
            y = serie.get(semana)
            if y is None:
                continue
            hist, cursor = [], semana
            for _ in range(4):
                prev = por_dia.get(fecha_semana(*cursor) - pd.Timedelta(days=7))
                if prev is None or serie.get(prev) is None:
                    hist = []
                    break
                hist.append(serie[prev]); cursor = prev
            if len(hist) == 4:
                rows.append(_ejemplo(hist[::-1], semana, distrito, y))
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).sort_values(["ano", "semana", "distrito"])
    districts = sorted(datos.distrito.dropna().astype(str).unique())
    one_hot = pd.get_dummies(pd.Categorical(frame.distrito, categories=districts), prefix="district", dtype=float)
    one_hot.index = frame.index
    return pd.concat([frame, one_hot], axis=1)


def _fit_predict(nombre, train, test, cols):
    if nombre in ("persistencia", "media_3"):
        col = "lag_1" if nombre == "persistencia" else "media_movil_3"
        return np.maximum(0, test[col].to_numpy(dtype=float))
    if nombre == "poisson":
        model = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1.0, max_iter=500))
        model.fit(train[cols], train.casos_notificados)
        return np.maximum(0, model.predict(test[cols]))
    params = {"n_estimators": 60, "max_depth": 2, "learning_rate": .04, "min_child_weight": 3, "reg_lambda": 5}
    fit = train
    if nombre == "xgb_log1p":
        fit = train.copy(); fit["casos_notificados"] = np.log1p(fit.casos_notificados)
    elif nombre == "xgb_regularizado":
        params = {"n_estimators": 80, "max_depth": 1, "learning_rate": .03, "min_child_weight": 5, "reg_lambda": 10, "reg_alpha": 1}
    model = entrenar_xgboost(fit, feature_cols=cols, params=params)
    pred = model.predict(test[cols])
    return np.maximum(0, np.expm1(pred) if nombre == "xgb_log1p" else pred)


def benchmark_walk_forward(datos, minimo=20):
    """Retorna OOS para candidatos y selección por validación interna exclusivamente pasada."""
    frame = _ejemplos(datos)
    if frame.empty:
        return pd.DataFrame()
    cols = obtener_feature_columns() + [c for c in frame.columns if c.startswith("district_")]
    results = []
    for (year, week), test in frame.groupby(["ano", "semana"], sort=True):
        train = frame[(frame.ano < year) | ((frame.ano == year) & (frame.semana < week))]
        if len(train) < minimo:
            continue
        preds = {}
        for name in MODELOS:
            try:
                preds[name] = _fit_predict(name, train, test, cols)
            except (ValueError, FloatingPointError):
                preds[name] = preds.get("persistencia", test.lag_1.to_numpy(dtype=float))

        # Hyperparametro/algoritmo elegido solo con un fold temporal dentro del pasado.
        train_weeks = sorted(set(zip(train.ano, train.semana)))
        scores = {"persistencia": float("inf"), "media_3": float("inf")}
        selected = "persistencia"
        if len(train_weeks) >= 8 and len(train) >= minimo * 2:
            nval = max(2, int(np.ceil(.2 * len(train_weeks))))
            val_start = train_weeks[-nval]
            itrain = train[(train.ano < val_start[0]) | ((train.ano == val_start[0]) & (train.semana < val_start[1]))]
            valid = train[(train.ano > val_start[0]) | ((train.ano == val_start[0]) & (train.semana >= val_start[1]))]
            for name in MODELOS:
                try:
                    pv = _fit_predict(name, itrain, valid, cols)
                    scores[name] = mean_absolute_error(valid.casos_notificados, pv)
                except (ValueError, FloatingPointError):
                    continue
            selected = min(scores, key=scores.get)

        for pos, r in enumerate(test.itertuples()):
            chosen_pred = float(preds["persistencia"][pos])
            temporal_pred = float(preds[selected][pos])
            err = abs(float(r.casos_notificados)-chosen_pred)
            pct = err/float(r.casos_notificados)*100 if r.casos_notificados else np.nan
            item = {"distrito": r.distrito, "ano": int(year), "semana": int(week),
                    "semana_epidemiologica": f"{year}-SE{week:02d}", "real": float(r.casos_notificados),
                    "prediccion": chosen_pred, "prediccion_temporal": temporal_pred,
                    "prediccion_xgb": float(preds["xgb_actual"][pos]),
                    "baseline": float(preds["persistencia"][pos]), "error_absoluto": err,
                    "error_pct": pct,
                    "estado": ("No evaluable (real=0)" if not r.casos_notificados else "Dentro de ±10%" if pct <= 10 else "Fuera de ±10%"),
                    "version_modelo": BENCHMARK_VERSION, "modelo_seleccionado": selected}
            for name in MODELOS:
                item[name] = float(preds[name][pos])
            results.append(item)
    return pd.DataFrame(results)


@st.cache_data(show_spinner="Comparando modelos con validación temporal anidada…")
def benchmark_cache(datos, version):
    return benchmark_walk_forward(datos)


def load_benchmark(base, datos, version):
    """Usa el resultado versionado si corresponde; si falta, calcula una vez y cachea."""
    from pathlib import Path
    import json
    base = Path(base)
    path = base / "reports/predicciones_walk_forward_v2.csv"
    meta = base / "reports/predicciones_walk_forward_v2.json"
    if path.exists() and meta.exists():
        info = json.loads(meta.read_text(encoding="utf-8"))
        if info.get("version_datos") == version and info.get("version_modelo_walk_forward") == BENCHMARK_VERSION:
            return pd.read_csv(path)
    return benchmark_cache(datos, version)


def comparar_metricas(frame):
    if frame.empty:
        return pd.DataFrame()
    rows = []
    y = frame.real.to_numpy()
    candidates = list(MODELOS) + ["seleccion_temporal"]
    for name in candidates:
        col = "prediccion_temporal" if name == "seleccion_temporal" and "prediccion_temporal" in frame else "prediccion" if name == "seleccion_temporal" else name
        p = frame[col].to_numpy()
        valid = y > 0
        rows.append({"modelo": name, "n": len(y), "MAE": mean_absolute_error(y, p),
                     "RMSE": float(np.mean((y-p)**2)**.5),
                     "WAPE_pct": float(np.abs(y-p).sum()/np.abs(y).sum()*100) if np.abs(y).sum() else np.nan,
                     "sMAPE_pct": float(np.mean(200*np.abs(y-p)/(np.abs(y)+np.abs(p)+1e-9))),
                     "dentro_10_pct": float(np.mean(np.abs(y[valid]-p[valid])/y[valid] <= .10)*100) if valid.any() else np.nan})
    return pd.DataFrame(rows).sort_values("MAE")


def comparar_por_grupo(frame, columna):
    """Mismas métricas por distrito o año para no ocultar heterogeneidad."""
    parts = []
    for grupo, subset in frame.groupby(columna, sort=True):
        metricas = comparar_metricas(subset)
        metricas.insert(0, columna, grupo)
        parts.append(metricas)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
