"""Walk-forward de un paso. Las semanas marcadas sin fuente nunca se tratan como cero."""
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics import mean_absolute_error, mean_squared_error

try:
    from .calendar_epi import fecha_semana
    from .features import obtener_feature_columns
    from .model import entrenar_xgboost
except ImportError:
    from calendar_epi import fecha_semana
    from features import obtener_feature_columns
    from model import entrenar_xgboost


def _ejemplo(historia, fecha, distrito, target):
    valores = list(historia)
    if len(valores) < 4:
        return None
    f = fecha_semana(*fecha)
    fila = {f"lag_{i}": valores[-i] for i in range(1, 5)}
    fila.update(media_movil_3=np.mean(valores[-3:]), media_movil_4=np.mean(valores[-4:]),
                crecimiento_semanal=(valores[-1] / valores[-2] - 1) if valores[-2] else 0,
                mes=f.month, trimestre=(f.month - 1) // 3 + 1,
                distrito=distrito, ano=fecha[0], semana=fecha[1], casos_notificados=target)
    return fila


def backtest_walk_forward(datos, minimo_entrenamiento=20):
    """Predice el siguiente dato observado con modelo reentrenado solo con fechas anteriores.

    Por conservadurismo, se construyen lags solo cuando las cuatro semanas previas
    tienen notificación en la fuente. No se rellenan semanas desconocidas.
    """
    datos = datos.copy()
    if "sin_registros_fuente" not in datos:
        raise ValueError("Falta la marca de cobertura; no es seguro evaluar esta serie.")
    datos["sin_registros_fuente"] = datos.sin_registros_fuente.astype(bool)
    panel = {}
    for distrito, g in datos.groupby("distrito"):
        panel[distrito] = {
            (int(r.ano), int(r.semana)): (None if r.sin_registros_fuente else float(r.casos_notificados))
            for r in g.itertuples()
        }
    fechas = sorted({k for valores in panel.values() for k in valores})
    por_dia = {fecha_semana(*k): k for k in fechas}
    ejemplos = []
    for distrito, serie in panel.items():
        for fecha in fechas:
            actual = serie.get(fecha)
            if actual is None:
                continue
            cursor = fecha
            previas = []
            for _ in range(4):
                d = fecha_semana(*cursor) - pd.Timedelta(days=7)
                candidata = por_dia.get(d)
                if candidata is None or serie.get(candidata) is None:
                    previas = []
                    break
                previas.append(serie[candidata])
                cursor = candidata
            if len(previas) == 4:
                ejemplos.append(_ejemplo(list(reversed(previas)), fecha, distrito, actual))
    if not ejemplos:
        return pd.DataFrame(columns=["distrito", "ano", "semana", "semana_epidemiologica", "real", "prediccion", "baseline", "error_absoluto", "error_pct", "estado", "version_modelo"])
    frame = pd.DataFrame(ejemplos).sort_values(["ano", "semana", "distrito"])
    predicciones = []
    cols = obtener_feature_columns()
    for (ano, semana), actuales in frame.groupby(["ano", "semana"], sort=True):
        train = frame[(frame.ano < ano) | ((frame.ano == ano) & (frame.semana < semana))]
        if len(train) < minimo_entrenamiento:
            continue
        modelo = entrenar_xgboost(train, feature_cols=cols, params={"n_estimators": 60, "max_depth": 2, "learning_rate": .04, "min_child_weight": 3, "reg_lambda": 5})
        p = np.clip(modelo.predict(actuales[cols]), 0, None)
        for r, v in zip(actuales.itertuples(), p):
            predicciones.append({"distrito": r.distrito, "ano": int(ano), "semana": int(semana),
                                 "semana_epidemiologica": f"{ano}-SE{semana:02d}", "real": float(r.casos_notificados),
                                 "prediccion": float(v), "baseline": float(r.lag_1),
                                 "error_absoluto": abs(float(r.casos_notificados)-float(v)),
                                 "error_pct": abs(float(r.casos_notificados)-float(v))/float(r.casos_notificados)*100 if r.casos_notificados else np.nan,
                                 "estado": ("No evaluable (real=0)" if not r.casos_notificados else
                                            "Dentro de ±10%" if abs(float(r.casos_notificados)-float(v))/float(r.casos_notificados) <= .10 else "Fuera de ±10%"),
                                 "version_modelo": "walk-forward-xgb-v1"})
    return pd.DataFrame(predicciones)


@st.cache_data(show_spinner="Calculando validación temporal sin semanas posteriores…")
def backtest_cache(datos, version):
    return backtest_walk_forward(datos)


def metricas_backtest(resultados):
    if resultados.empty:
        return {"n": 0}
    y, p = resultados.real.to_numpy(), resultados.prediccion.to_numpy()
    denom = np.abs(y).sum()
    return {"n": len(resultados), "mae": mean_absolute_error(y, p),
            "rmse": mean_squared_error(y, p) ** .5,
            "wape": np.abs(y-p).sum()/denom*100 if denom else np.nan,
            "smape": np.mean(200*np.abs(y-p)/(np.abs(y)+np.abs(p)+1e-9)),
            "dentro_10": (resultados.loc[resultados.real.gt(0), "estado"] == "Dentro de ±10%").mean()*100 if resultados.real.gt(0).any() else np.nan,
            "baseline_mae": mean_absolute_error(y, resultados.baseline)}


def metricas_por_grupo(resultados, columna):
    """Métricas comparables por distrito o año calendario epidemiológico."""
    filas = []
    for grupo, d in resultados.groupby(columna, sort=True):
        y, p = d.real.to_numpy(), d.prediccion.to_numpy()
        denom = np.abs(y).sum()
        positivos = d.real.gt(0)
        filas.append({columna: grupo, "n_predicciones": len(d),
                      "MAE_modelo": mean_absolute_error(y, p),
                      "MAE_baseline": mean_absolute_error(y, d.baseline),
                      "RMSE_modelo": mean_squared_error(y, p) ** .5,
                      "WAPE_pct": np.abs(y-p).sum()/denom*100 if denom else np.nan,
                      "dentro_10_pct": (d.loc[positivos, "estado"] == "Dentro de ±10%").mean()*100 if positivos.any() else np.nan})
    return pd.DataFrame(filas)
