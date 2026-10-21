"""ETL auditable y experimento temporal de dengue + clima CDC/SENAMHI.

El Excel se lee con OOXML de la biblioteca estandar, sin dependencias nuevas.
Casos vacios se preservan como desconocidos; nunca se imputan a cero.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

try:
    from .calendar_epi import fecha_semana
except ImportError:
    from calendar_epi import fecha_semana

BASE = Path(__file__).resolve().parents[1]
CLIMATE_COLUMNS = ["tmean", "tmax", "tmin", "humr", "ptot"]
UBIGEO_DISTRICT = {
    "150101": "Cercado de Lima", "150105": "Breña", "150113": "Jesús María",
    "150115": "La Victoria", "150116": "Lince", "150120": "Magdalena",
    "150121": "Pueblo Libre", "150122": "Miraflores", "150130": "San Borja",
    "150131": "San Isidro", "150132": "San Juan de Lurigancho", "150134": "San Luis",
    "150136": "San Miguel", "150141": "Surquillo",
}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _col_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group()
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def read_district_sheet(path: Path) -> pd.DataFrame:
    """Extrae Distrito preservando celdas vacias y leyendo inline/shared strings."""
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheet = next(s for s in wb.findall("m:sheets/m:sheet", NS) if s.attrib["name"] == "Distrito")
        target = targets[sheet.attrib[f"{{{NS['r']}}}id"]].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ET.fromstring(z.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in si.findall(".//m:t", NS))
                       for si in shared.findall("m:si", NS)]
        root = ET.fromstring(z.read(target))
        rows = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            cells = {}
            for cell in row.findall("m:c", NS):
                val = cell.find("m:v", NS)
                inline = cell.find("m:is", NS)
                value = val.text if val is not None else None
                if cell.attrib.get("t") == "s" and value is not None:
                    value = strings[int(value)]
                elif inline is not None:
                    value = "".join(t.text or "" for t in inline.findall(".//m:t", NS))
                cells[_col_index(cell.attrib["r"])] = value
            rows.append(cells)
    if not rows:
        raise ValueError(f"Hoja Distrito vacia: {path}")
    header = [rows[0].get(i, "") for i in range(max(rows[0]) + 1)]
    frame = pd.DataFrame([{header[i]: row.get(i) for i in range(len(header))} for row in rows[1:]])
    return frame


def extract_climate(path: Path) -> tuple[pd.DataFrame, dict]:
    raw = read_district_sheet(path)
    required = {"UBIGEO", "Ano", "Semana", "Tipo caso", "Casos", *CLIMATE_COLUMNS}
    if not required.issubset(raw.columns):
        raise ValueError(f"Faltan columnas: {sorted(required - set(raw.columns))}")
    raw["UBIGEO"] = raw.UBIGEO.astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(6)
    frame = raw.loc[raw.UBIGEO.isin(UBIGEO_DISTRICT)].copy()
    frame["ano"] = pd.to_numeric(frame.Ano, errors="raise").astype(int)
    frame["semana"] = pd.to_numeric(frame.Semana, errors="raise").astype(int)
    for year, week in frame[["ano", "semana"]].drop_duplicates().itertuples(index=False, name=None):
        fecha_semana(year, week)
    # El total del observatorio es confirmados + probables; filas sin etiqueta/caso
    # aportan clima, pero el blanco de casos se preserva como desconocido.
    frame["casos"] = pd.to_numeric(frame.Casos.where(frame["Tipo caso"].eq("TOTAL")), errors="coerce")
    for col in CLIMATE_COLUMNS:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["ubigeo"] = frame.UBIGEO
    frame["distrito"] = frame.ubigeo.map(UBIGEO_DISTRICT)
    keys = ["ubigeo", "ano", "semana"]
    if frame.duplicated(keys).any():
        raise ValueError("Duplicados UBIGEO-año-semana en fuente clima")
    # Calendario semanal uniforme por cada distrito; los casos vacios siguen siendo NA.
    expected = frame.groupby("ubigeo").size()
    if expected.nunique() != 1:
        raise ValueError("Cobertura calendaria desigual entre distritos")
    for _, group in frame.groupby("ubigeo"):
        dates = [fecha_semana(y, w) for y, w in zip(group.ano, group.semana)]
        if any((dates[i] - dates[i-1]).days != 7 for i in range(1, len(dates))):
            raise ValueError("Hueco/duplicado en calendario epidemiologico del panel clima")
    out = frame[["ubigeo", "distrito", "ano", "semana", "casos", *CLIMATE_COLUMNS]].sort_values(keys)
    meta = {"filas_panel": len(out), "distritos": int(out.ubigeo.nunique()),
            "casos_observados": int(out.casos.notna().sum()),
            "casos_desconocidos": int(out.casos.isna().sum()),
            "clima_observado": {c: int(out[c].notna().sum()) for c in CLIMATE_COLUMNS},
            "casos_por_ano": {str(int(y)): int(g.casos.notna().sum()) for y, g in out.groupby("ano")},
            "semanas_casos_por_ano": {str(int(y)): sorted(g.loc[g.casos.notna(), "semana"].astype(int).unique().tolist())
                                       for y, g in out.groupby("ano")}}
    return out.reset_index(drop=True), meta


def make_features(panel: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    d = panel.sort_values(["ubigeo", "ano", "semana"]).copy()
    # Orden/calendario del CDC sheet; shift(1+) evita clima/casos de la semana objetivo.
    groups = d.groupby("ubigeo", sort=False)
    base = []
    climate = []
    for lag in range(1, 5):
        col = f"casos_lag_{lag}"
        d[col] = groups.casos.shift(lag)
        base.append(col)
    for lag in range(1, 5):
        for weather in CLIMATE_COLUMNS:
            wcol = f"{weather}_lag_{lag}"
            d[wcol] = groups[weather].shift(lag)
            climate.append(wcol)
    d["week_sin"] = np.sin(2 * np.pi * d.semana / 52.1775)
    d["week_cos"] = np.cos(2 * np.pi * d.semana / 52.1775)
    district_columns = pd.get_dummies(d.ubigeo, prefix="district", dtype=int)
    d = pd.concat([d, district_columns], axis=1)
    base += ["week_sin", "week_cos", *district_columns.columns.tolist()]
    climate_cols = base + climate
    return d, base, climate_cols


def _fit_predict(train: pd.DataFrame, target: pd.DataFrame, cols: list[str]) -> np.ndarray:
    model = XGBRegressor(n_estimators=100, max_depth=2, learning_rate=.035,
                         min_child_weight=4, reg_lambda=8, subsample=.9,
                         colsample_bytree=.9, objective="reg:squarederror",
                         random_state=42, n_jobs=1, missing=np.nan)
    model.fit(train[cols], np.log1p(train.casos.astype(float)))
    return np.maximum(0, np.expm1(model.predict(target[cols])))


def metrics(real, pred) -> dict:
    y, p = np.asarray(real, float), np.maximum(0, np.asarray(pred, float))
    err = np.abs(y - p)
    den = np.abs(y).sum()
    positive = y > 0
    return {"n": int(len(y)), "MAE": float(mean_absolute_error(y, p)),
            "RMSE": float(mean_squared_error(y, p) ** .5),
            "WAPE_pct": float(err.sum() / den * 100) if den else None,
            "sMAPE_pct": float(np.mean(200 * err / (np.abs(y) + np.abs(p) + 1e-9))) if len(y) else None,
            "dentro_10_pct": float(np.mean(err[positive] / y[positive] < .10) * 100) if positive.any() else None,
            "casos_reales_cero": int((~positive).sum())}


def _walk(panel: pd.DataFrame, first_year: int, last_year: int, min_train: int = 90):
    featured, base_cols, climate_cols = make_features(panel)
    keys = ["ano", "semana"]
    allweeks = sorted(set(zip(featured.ano.astype(int), featured.semana.astype(int))))
    rows = []
    for year, week in allweeks:
        if not first_year <= year <= last_year:
            continue
        train = featured.loc[(featured.casos.notna()) & ((featured.ano < year) | ((featured.ano == year) & (featured.semana < week)))]
        target = featured.loc[(featured.ano.eq(year)) & (featured.semana.eq(week)) & featured.casos.notna()]
        if len(train) < min_train or target.empty:
            continue
        # Dos modelos iguales, misma ventana/labels; unica diferencia son los meteo rezagados.
        p0 = _fit_predict(train, target, base_cols)
        p1 = _fit_predict(train, target, climate_cols)
        for idx, (_, r) in enumerate(target.iterrows()):
            rows.append({"ubigeo": r.ubigeo, "distrito": r.distrito, "ano": int(year), "semana": int(week),
                         "semana_epidemiologica": f"{year}-SE{week:02d}", "real": float(r.casos),
                         "prediccion_sin_clima": float(p0[idx]), "prediccion_con_clima": float(p1[idx]),
                         "fecha_corte": f"{year}-SE{week-1:02d}" if week > 1 else f"{year-1}-ultima-semana",
                         "version_modelo": "xgb-clima-lagged-v1"})
    return pd.DataFrame(rows)


def run(source: Path | None = None, base: Path = BASE) -> dict:
    source = source or base / "XLSX/clima_departamento (2).xlsx"
    frame, coverage = extract_climate(source)
    variants = []
    for candidate in sorted((base / "XLSX").glob("*.xlsx")):
        other, other_cov = extract_climate(candidate)
        raw_variant = read_district_sheet(candidate)
        raw_variant["UBIGEO"] = raw_variant.UBIGEO.astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(6)
        raw_variant = raw_variant.loc[raw_variant.UBIGEO.isin(UBIGEO_DISTRICT)]
        variants.append({"archivo": str(candidate.relative_to(base)), "sha256": sha256(candidate),
                         "filas_14_distritos": int(len(other)),
                         "filas_casos_14_distritos": int(pd.to_numeric(raw_variant.Casos, errors="coerce").notna().sum()),
                         "definicion": str(raw_variant["Tipo caso"].dropna().iloc[0])})
        if candidate.name.startswith("clima_departamento (1)"):
            same = frame[["ubigeo", "ano", "semana", "casos", *CLIMATE_COLUMNS]].reset_index(drop=True).equals(
                other[["ubigeo", "ano", "semana", "casos", *CLIMATE_COLUMNS]].reset_index(drop=True))
            if not same:
                raise ValueError("La variante (1) difiere del archivo TOTAL seleccionado; revisar revisiones.")
    processed = base / "data/processed/dengue_clima_14d.csv"
    report = base / "reports/evaluacion_clima_walk_forward.json"
    preds_path = base / "reports/predicciones_clima_walk_forward.csv"
    processed.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(processed, index=False, encoding="utf-8-sig")
    # Validacion (2023-24) solo selecciona si el clima ayuda; 2025+ queda reservado al final.
    validation = _walk(frame, 2023, 2024)
    final = _walk(frame, 2025, 2026)
    if validation.empty or final.empty:
        raise ValueError("No hay casos observados suficientes para validacion temporal y periodo final")
    score0, score1 = metrics(validation.real, validation.prediccion_sin_clima), metrics(validation.real, validation.prediccion_con_clima)
    selected = "con_clima" if score1["WAPE_pct"] < score0["WAPE_pct"] else "sin_clima"
    final["modelo_seleccionado"] = final[f"prediccion_{selected}"]
    final["error_absoluto"] = (final.real-final.modelo_seleccionado).abs()
    final["error_pct"] = np.where(final.real.gt(0), final.error_absoluto/final.real*100, np.nan)
    final.to_csv(preds_path, index=False, encoding="utf-8-sig")
    summary = {"fuente": {"institucion": "CDC Perú / MINSA; datos climáticos atribuidos a SENAMHI",
                           "url": "https://app7.dge.gob.pe/maps/clima-salud/",
                           "archivo": str(source.relative_to(base)), "sha256": sha256(source),
                           "fecha_modificacion_archivo_utc": pd.Timestamp(source.stat().st_mtime, unit="s", tz="UTC").isoformat(),
                           "definicion_casos": "TOTAL (confirmados + probables, etiqueta del archivo)",
                           "licencia": "No indicada en el archivo/página consultada; verificar con CDC",
                           "archivos_locales_auditados": variants,
                           "clima": CLIMATE_COLUMNS, "regla": "casos y clima rezagados 1-4; semana objetivo nunca usada"},
               "cobertura": coverage,
               "validacion_2023_2024": {"sin_clima": score0, "con_clima": score1,
                                         "eleccion_solo_validacion": selected},
               "prueba_final_2025_2026": {"sin_clima": metrics(final.real, final.prediccion_sin_clima),
                                           "con_clima": metrics(final.real, final.prediccion_con_clima),
                                           "seleccionado": metrics(final.real, final.modelo_seleccionado),
                                           "modelo_seleccionado_en_validacion": selected,
                                           "periodo": [int(final.ano.min()), int(final.ano.max())]},
               "mayores_errores": final.sort_values("error_absoluto", ascending=False).head(15)[
                   ["distrito", "semana_epidemiologica", "real", "modelo_seleccionado", "error_absoluto", "error_pct"]
               ].replace({np.nan: None}).to_dict(orient="records"),
               "archivos": {"panel": str(processed.relative_to(base)), "predicciones": str(preds_path.relative_to(base))},
               "advertencias": ["Celdas vacias de casos permanecen desconocidas y no se evaluan como cero.",
                                "Evaluacion condicionada a las semanas donde el archivo trae Casos explicitos.",
                                "El corte de publicacion de clima/casos por semana historica no esta archivado; se usa clima rezagado una semana.",
                                "TOTAL del archivo no se mezcla con el panel MINSA de 2023-24: definicion/corte de notificacion distintos."]}
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
