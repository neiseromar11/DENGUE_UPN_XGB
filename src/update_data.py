"""Descarga opcional y validada de la serie oficial MINSA/CDC; conserva toda versión previa.

Uso explícito: python src/update_data.py. No se ejecuta al abrir Streamlit.
Resuelve el enlace CSV desde la ficha oficial; no codifica ni adivina endpoints de descarga.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import json
import os
import hashlib
import tempfile

import pandas as pd

try:
    from .calendar_epi import fecha_semana
    from .data_pipeline import preparar_datos
except ImportError:
    from calendar_epi import fecha_semana
    from data_pipeline import preparar_datos

BASE = Path(__file__).resolve().parents[1]
RESOURCE_PAGE = "https://www.datosabiertos.gob.pe/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue/resource/79e21c8d-3a94-4ac5-b234-bace71fe9675"
FILENAME = "datos_abiertos_vigilancia_dengue_2000_2024.csv"
LICENSE = "Open Data Commons Attribution License"
UBIGEO_DIRIS = {
    "150101": "LIMA", "150105": "BREÃ‘A", "150113": "JESUS MARIA",
    "150115": "LA VICTORIA", "150116": "LINCE", "150120": "MAGDALENA DEL MAR",
    "150121": "PUEBLO LIBRE", "150122": "MIRAFLORES", "150130": "SAN BORJA",
    "150131": "SAN ISIDRO", "150132": "SAN JUAN DE LURIGANCHO", "150134": "SAN LUIS",
    "150136": "SAN MIGUEL", "150141": "SURQUILLO",
}


class _CsvLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href and FILENAME in href:
                self.links.append(href)


def _source_url(timeout=30):
    req = Request(RESOURCE_PAGE, headers={"User-Agent": "DengueML-UPN/1.0 (research; contact project owner)"})
    with urlopen(req, timeout=timeout) as response:
        page_url = response.geturl()
        if urlparse(page_url).hostname not in {"www.datosabiertos.gob.pe", "datosabiertos.gob.pe"}:
            raise ValueError("La ficha redirigió fuera del dominio oficial.")
        parser = _CsvLinkParser(); parser.feed(response.read().decode("utf-8", "replace"))
    for href in parser.links:
        resolved = urljoin(page_url, href)
        parsed = urlparse(resolved)
        if parsed.scheme == "https" and parsed.hostname in {"www.datosabiertos.gob.pe", "datosabiertos.gob.pe"}:
            return resolved
    raise ValueError("La ficha no publica un enlace CSV directo con el nombre esperado.")


def _download(url, target, timeout=180):
    req = Request(url, headers={"User-Agent": "DengueML-UPN/1.0 (research; contact project owner)"})
    total = 0
    with urlopen(req, timeout=timeout) as response, target.open("wb") as out:
        if urlparse(response.geturl()).hostname not in {"www.datosabiertos.gob.pe", "datosabiertos.gob.pe"}:
            raise ValueError("La descarga redirigió fuera del dominio oficial.")
        while block := response.read(1024 * 1024):
            total += len(block)
            if total > 500 * 1024**2:
                raise ValueError("Archivo supera límite preventivo de 500 MB.")
            out.write(block)
    if total < 1024:
        raise ValueError("Descarga vacía o demasiado pequeña.")


def _sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _validate(path):
    try:
        sample = pd.read_csv(path, nrows=100, sep=None, engine="python", encoding="utf-8-sig")
        reader = lambda: pd.read_csv(path, chunksize=250_000, sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        sample = pd.read_csv(path, nrows=100, sep=None, engine="python", encoding="latin-1")
        reader = lambda: pd.read_csv(path, chunksize=250_000, sep=None, engine="python", encoding="latin-1")
    sample.columns = sample.columns.str.strip().str.lower().str.replace("\ufeff", "", regex=False)
    needed = {"departamento", "provincia", "distrito", "ano", "semana", "ubigeo"}
    if not needed.issubset(sample.columns):
        raise ValueError(f"Esquema fuente incompatible; faltan {sorted(needed-set(sample.columns))}.")
    if "tipo_dx" not in sample:
        raise ValueError("La fuente no distingue confirmado/probable; no se puede validar su definición.")
    years, bad_dates, cases_by_dx = set(), 0, {}
    duplicates_exact = 0
    for chunk in reader():
        chunk.columns = chunk.columns.str.strip().str.lower().str.replace("\ufeff", "", regex=False)
        years.update(pd.to_numeric(chunk.ano, errors="coerce").dropna().astype(int).unique())
        for a, s in zip(pd.to_numeric(chunk.ano, errors="coerce"), pd.to_numeric(chunk.semana, errors="coerce")):
            try:
                if pd.isna(a) or pd.isna(s) or a != int(a) or s != int(s):
                    bad_dates += 1
                else:
                    fecha_semana(int(a), int(s))
            except (ValueError, OverflowError):
                bad_dates += 1
        types = chunk.tipo_dx.astype(str).str.strip().str.upper().value_counts()
        for key, value in types.items():
            cases_by_dx[key] = cases_by_dx.get(key, 0) + int(value)
        duplicates_exact += int(chunk.duplicated().sum())
    if bad_dates:
        raise ValueError(f"Fuente rechazada: {bad_dates} filas tienen año/SE inválidos.")
    if not years or min(years) > 2020 or max(years) < 2024:
        raise ValueError(f"Cobertura inesperada: años {min(years) if years else None}–{max(years) if years else None}.")
    if set(cases_by_dx) - {"C", "P", "S", "NAN", "", "NONE"}:
        raise ValueError(f"La fuente incorporó categorías tipo_dx nuevas: {sorted(cases_by_dx)}.")
    return {"cobertura_anos": [min(years), max(years)], "filas_duplicadas_exactas_no_eliminadas": duplicates_exact,
            "filas_fecha_semana_invalida": bad_dates, "registros_por_tipo_dx": cases_by_dx,
            "nota": "Las filas idénticas no se eliminan: el recurso es de registros de casos y puede carecer de ID único."}


def _consolidar_por_ubigeo(raw):
    """Normaliza distrito usando UBIGEO INEI (Lima Metropolitana) antes de agregar casos."""
    raw = raw.copy()
    raw.columns = raw.columns.str.strip().str.lower().str.replace("\ufeff", "", regex=False)
    codes = raw.ubigeo.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(6)
    raw["ubigeo"] = codes
    target = raw.ubigeo.isin(UBIGEO_DIRIS)
    if not target.any():
        raise ValueError("No hay ubigeos del alcance DIRIS Lima Centro en la fuente descargada.")
    raw = raw.loc[target].copy()
    raw["departamento"] = "LIMA"
    raw["provincia"] = "LIMA"
    raw["distrito"] = raw.ubigeo.map(UBIGEO_DIRIS)
    if raw.distrito.isna().any():
        raise ValueError("Hay UBIGEO de DIRIS sin correspondencia en el mapa validado.")
    return preparar_datos(raw)


def actualizar():
    url = _source_url()
    raw_dir = BASE / "data/raw/official_versions"; raw_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="dengue_download_", suffix=".csv", dir=raw_dir); os.close(fd)
    tmp = Path(tmp_name)
    try:
        _download(url, tmp)
        validacion = _validate(tmp)
        digest = _sha256_file(tmp)
        raw_path = raw_dir / f"{digest[:16]}_{FILENAME}"
        if raw_path.exists():
            tmp.unlink()
        else:
            os.replace(tmp, raw_path)
        try:
            raw = pd.read_csv(raw_path, sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            raw = pd.read_csv(raw_path, sep=None, engine="python", encoding="latin-1")
        consolidado, calidad = _consolidar_por_ubigeo(raw)
        version = f"cdc-{validacion['cobertura_anos'][0]}-{validacion['cobertura_anos'][1]}-{digest[:12]}"
        outdir = BASE / "data/versions" / version
        if outdir.exists():
            existing = outdir / "metadata.json"
            if existing.exists():
                meta_existing = json.loads(existing.read_text(encoding="utf-8"))
                if meta_existing.get("sha256_fuente") == digest:
                    return meta_existing
            raise FileExistsError(f"Version existente distinta o incompleta: {outdir}")
        outdir.mkdir(parents=True, exist_ok=False)
        output = outdir / "datos.csv"
        consolidado.to_csv(output, index=False, encoding="utf-8")
        metadata = {"version": version, "fecha_descarga_utc": datetime.now(timezone.utc).isoformat(),
                    "fuente_url": RESOURCE_PAGE, "archivo_descarga_url": url, "licencia": LICENSE,
                    "archivo_original": str(raw_path.relative_to(BASE)), "sha256_fuente": digest,
                    "sha256_consolidado": _sha256_file(output),
                    "calidad_fuente": validacion, "calidad_consolidado": calidad,
                    "definicion": "Notificaciones dengue del recurso MINSA/CDC; C=confirmado, P=probable, S=sospechoso. No combinar tipos sin declarar el estimando.",
                    "clave_geografica": "UBIGEO de 6 dígitos, correspondencia INEI; se agregan los 14 UBIGEO DIRIS antes de generar panel semanal.",
                    "estado": "candidato; no activa en models/actual.json"}
        (outdir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    print(json.dumps(actualizar(), ensure_ascii=False, indent=2))
