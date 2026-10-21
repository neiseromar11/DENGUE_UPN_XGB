"""Reproduce y persiste el walk-forward de la versión activa del proyecto."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    from .etl import BASE, sha256
    from .backtesting import metricas_backtest, metricas_por_grupo
    from .model_benchmark import benchmark_walk_forward, comparar_metricas
except ImportError:
    from etl import BASE, sha256
    from backtesting import metricas_backtest, metricas_por_grupo
    from model_benchmark import benchmark_walk_forward, comparar_metricas


def main():
    bundle = json.loads((BASE / "models/actual.json").read_text(encoding="utf-8"))
    data_path = BASE / bundle["datos"]
    datos = pd.read_csv(data_path)
    data_metadata = json.loads((BASE / bundle["metadata"]).read_text(encoding="utf-8"))
    benchmark = benchmark_walk_forward(datos)
    reports = BASE / "reports"
    reports.mkdir(exist_ok=True)
    benchmark.to_csv(reports / "predicciones_modelos_walk_forward.csv", index=False, encoding="utf-8-sig")
    benchmark.to_csv(reports / "predicciones_walk_forward_v2.csv", index=False, encoding="utf-8-sig")
    modelos = comparar_metricas(benchmark)
    metricas_xgb = modelos.loc[modelos.modelo.eq("xgb_actual")].iloc[0].to_dict()
    metricas_temporal = modelos.loc[modelos.modelo.eq("seleccion_temporal")].iloc[0].to_dict()
    metadata = {
        "version_datos": bundle["version"],
        "sha256_datos": sha256(data_path),
        "version_modelo_walk_forward": "walk-forward-nested-v3-district-effects",
        "horizonte_semanas": 1,
        "fecha_calculo_utc": datetime.now(timezone.utc).isoformat(),
        "fecha_version_datos_utc": data_metadata.get("generado_utc"),
        "fecha_descarga_fuente": None,
        "muestras_oos": len(benchmark),
        "metricas_xgb_actual": metricas_xgb,
        "metricas": metricas_backtest(benchmark),
        "metricas_seleccion_temporal": metricas_temporal,
        "comparacion_modelos": modelos.to_dict(orient="records"),
        "seleccion_modelos": benchmark.modelo_seleccionado.value_counts().to_dict(),
        "metricas_por_distrito": metricas_por_grupo(benchmark, "distrito").to_dict(orient="records"),
        "metricas_por_ano": metricas_por_grupo(benchmark, "ano").to_dict(orient="records"),
        "politica_faltantes": "Semanas sin registros excluidas; no interpretadas como cero.",
        "fuente": "MINSA / CDC Perú, Vigilancia Epidemiológica de dengue",
        "url": "https://www.datosabiertos.gob.pe/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue",
        "licencia": "Open Data Commons Attribution License",
        "cobertura": "Versión local: 2023-SE01 a 2024-SE52; 14 distritos DIRIS Lima Centro.",
        "notas": "El archivo fuente original no está presente en la carpeta; no se descargaron datos nuevos. SHA-256 de la versión consolidada: el campo sha256_datos permite reproducirla. Estimaciones evaluables solo con cuatro lags semanales consecutivos observados y 20 ejemplos de entrenamiento previos. El CSV contiene únicamente predicciones out-of-sample.",
    }
    (reports / "predicciones_walk_forward_v2.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
