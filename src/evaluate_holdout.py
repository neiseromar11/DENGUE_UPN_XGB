"""Evaluación temporal final: modelo elegido en validación y probado en el tramo final."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .etl import BASE
    from .model_benchmark import MODELOS, comparar_metricas
except ImportError:
    from etl import BASE
    from model_benchmark import MODELOS, comparar_metricas


def split_temporal(frame: pd.DataFrame, fraccion_test: float = 0.20):
    """Corta por semana completa, nunca mezcla distritos de la misma semana."""
    semanas = sorted(set(zip(frame.ano.astype(int), frame.semana.astype(int))))
    if len(semanas) < 5 or not 0 < fraccion_test < 0.5:
        raise ValueError("Insuficientes semanas o fracción de prueba inválida")
    n_test = max(1, int(np.ceil(len(semanas) * fraccion_test)))
    inicio = semanas[-n_test]
    test_mask = [(int(y), int(s)) >= inicio for y, s in zip(frame.ano, frame.semana)]
    return frame.loc[~np.asarray(test_mask)].copy(), frame.loc[np.asarray(test_mask)].copy(), inicio


def metricas(y, p):
    y, p = np.asarray(y, float), np.maximum(0, np.asarray(p, float))
    err = np.abs(y-p)
    nonzero = y > 0
    return {
        "n": int(len(y)),
        "WAPE_pct": float(err.sum()/np.abs(y).sum()*100) if np.abs(y).sum() else None,
        "MAE": float(err.mean()) if len(err) else None,
        "RMSE": float(np.sqrt(np.mean((y-p)**2))) if len(err) else None,
        "sMAPE_pct": float(np.mean(200*err/(np.abs(y)+np.abs(p)+1e-9))) if len(err) else None,
        "semanas_error_menor_10_pct": float(np.mean(err[nonzero]/y[nonzero] <= .10)*100) if nonzero.any() else None,
        "semanas_con_real_cero": int((~nonzero).sum()),
    }


def evaluar(frame: pd.DataFrame, fraccion_test: float = 0.20):
    validacion, test, inicio = split_temporal(frame, fraccion_test)
    # La decisión se congela usando solo la porción anterior al tramo final.
    candidatos = [c for c in MODELOS if c in validacion]
    elegido = min(candidatos, key=lambda c: float(np.abs(validacion.real-validacion[c]).sum()/len(validacion)))
    test = test.copy()
    test["modelo_anterior_xgb"] = test["xgb_actual"].clip(lower=0)
    test["modelo_seleccionado"] = test[elegido].clip(lower=0)
    test["modelo_ganador_validacion"] = elegido
    test["fecha_inicio_test"] = f"{inicio[0]}-SE{inicio[1]:02d}"
    salida = {
        "periodo_validacion_hasta": f"{max(zip(validacion.ano, validacion.semana))[0]}-SE{max(zip(validacion.ano, validacion.semana))[1]:02d}",
        "periodo_prueba_desde": f"{inicio[0]}-SE{inicio[1]:02d}",
        "semanas_validacion": int(validacion.groupby(["ano", "semana"]).ngroups),
        "semanas_prueba": int(test.groupby(["ano", "semana"]).ngroups),
        "n_validacion": len(validacion), "n_prueba": len(test),
        "modelo_elegido_solo_en_validacion": elegido,
        "anterior_xgb": metricas(test.real, test.modelo_anterior_xgb),
        "seleccionado": metricas(test.real, test.modelo_seleccionado),
        "nota": "Prueba temporal final reportada sin ajustar el modelo tras inspeccionar sus resultados. Predicciones OOS: cada semana se entrenó usando solo semanas anteriores.",
    }
    err = np.abs(test.real-test.modelo_seleccionado)
    test["error_absoluto_seleccionado"] = err
    test["error_pct_seleccionado"] = np.where(test.real > 0, err/test.real*100, np.nan)
    return salida, test


def main():
    csv = BASE / "reports/predicciones_modelos_walk_forward.csv"
    if not csv.exists():
        raise FileNotFoundError(f"Falta {csv}; ejecute src.run_backtest primero")
    full = pd.read_csv(csv)
    summary, test = evaluar(full)
    reports = BASE / "reports"
    test.to_csv(reports / "predicciones_holdout_final.csv", index=False, encoding="utf-8-sig")
    summary["errores_mayores"] = test.sort_values("error_absoluto_seleccionado", ascending=False).head(10)[
        ["ano", "semana", "distrito", "real", "modelo_anterior_xgb", "modelo_seleccionado", "error_absoluto_seleccionado", "error_pct_seleccionado"]
    ].replace({np.nan: None}).to_dict(orient="records")
    summary["errores_porcentuales_mayores"] = test.loc[test.real.gt(0)].sort_values(
        "error_pct_seleccionado", ascending=False).head(10)[
        ["ano", "semana", "distrito", "real", "modelo_seleccionado", "error_pct_seleccionado"]
    ].replace({np.nan: None}).to_dict(orient="records")
    summary["metricas_por_distrito"] = [{
        "distrito": distrito,
        "modelo_anterior_xgb": metricas(parte.real, parte.modelo_anterior_xgb),
        "modelo_seleccionado": metricas(parte.real, parte.modelo_seleccionado),
    } for distrito, parte in test.groupby("distrito", sort=True)]
    (reports / "evaluacion_holdout_final.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
