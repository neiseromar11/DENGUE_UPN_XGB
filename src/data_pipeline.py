"""Conteos de registros, sin eliminar casos por atributos coincidentes."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import unicodedata
import pandas as pd
try:
    from .config import DISTRITOS_DATASET_MAP, DISTRITOS_DIRIS_DATASET
    from .calendar_epi import fecha_semana, siguiente_semana
    from .audit import registrar_evento
except ImportError:
    from config import DISTRITOS_DATASET_MAP, DISTRITOS_DIRIS_DATASET
    from calendar_epi import fecha_semana, siguiente_semana
    from audit import registrar_evento

def normalize_district_name(name):
    if pd.isna(name):
        return ''
    value = str(name).strip().upper().replace('\ufffd', 'N')
    return ''.join(c for c in unicodedata.normalize('NFD', value) if unicodedata.category(c) != 'Mn')

def match_district(raw_name, valid_districts):
    return next((x for x in valid_districts if normalize_district_name(x) == normalize_district_name(raw_name)), None)

def preparar_datos(df, ano_inicio=None, ano_fin=None):
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace('\ufeff', '', regex=False)
    requeridas = {'departamento', 'provincia', 'distrito', 'ano', 'semana'}
    if not requeridas.issubset(df.columns):
        raise ValueError(f'Faltan columnas: {sorted(requeridas - set(df.columns))}')
    total_raw = len(df)
    lima = df.departamento.map(normalize_district_name).eq('LIMA') & df.provincia.map(normalize_district_name).eq('LIMA')
    df = df[lima].copy()
    df['distrito'] = df.distrito.map(lambda x: match_district(x, DISTRITOS_DIRIS_DATASET))
    df = df[df.distrito.notna()].copy()
    for col in ('ano', 'semana'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    def valida(row):
        a, s = row
        try:
            if pd.isna(a) or pd.isna(s) or a != int(a) or s != int(s):
                return False
            fecha_semana(a, s)
            return True
        except (ValueError, OverflowError):
            return False
    validos = df[['ano', 'semana']].apply(valida, axis=1)
    invalidos = int((~validos).sum())
    if not validos.any():
        raise ValueError('No hay fechas válidas en el alcance.')
    ano_inicio = int(df.loc[validos, 'ano'].min()) if ano_inicio is None else ano_inicio
    ano_fin = int(df.loc[validos, 'ano'].max()) if ano_fin is None else ano_fin
    df = df[validos & df.ano.between(ano_inicio, ano_fin)].copy()
    if df.empty:
        raise ValueError('No hay registros válidos en el alcance y periodo seleccionados.')
    df[['ano', 'semana']] = df[['ano', 'semana']].astype(int)
    coincidencias = int(df.duplicated().sum())
    faltantes = {c: int(n) for c, n in df.isna().sum().items()}
    conteos = df.groupby(['distrito', 'ano', 'semana']).size()
    fin = max(zip(df.ano, df.semana))
    semanas = []
    par = (ano_inicio, 1)
    while par <= fin:
        semanas.append(par)
        par = siguiente_semana(*par)
    indice = pd.MultiIndex.from_tuples([(d, a, s) for d in DISTRITOS_DIRIS_DATASET for a, s in semanas], names=['distrito', 'ano', 'semana'])
    out = conteos.reindex(indice).rename('casos_notificados').reset_index()
    out['sin_registros_fuente'] = out.casos_notificados.isna()
    out['casos_notificados'] = out.casos_notificados.fillna(0).astype(int)
    out['distrito'] = out.distrito.map(DISTRITOS_DATASET_MAP)
    out['semana_epidemiologica'] = out.ano.astype(str) + '-SE' + out.semana.astype(str).str.zfill(2)
    reporte = dict(total_raw=total_raw, registros_fuente_en_periodo=len(df), registros_finales=len(out),
                   filas_fecha_invalida=invalidos, coincidencias_exactas_conservadas=coincidencias,
                   faltantes=faltantes, completitud_pct=100 * (1 - sum(faltantes.values()) / df.size),
                   semanas_sin_registros=int(out.sin_registros_fuente.sum()),
                   inicio=out.semana_epidemiologica.min(), fin=out.semana_epidemiologica.max(),
                   politica_ceros='Cero significa ausencia de registros en el archivo, no ausencia confirmada de transmisión. Cobertura de notificación pendiente de validar.',
                   politica_duplicados='Se conservan coincidencias sin identificador único de caso.',
                   fecha_procesamiento=datetime.now().isoformat())
    return out, reporte

def ejecutar_etl_calidad():
    base = Path(__file__).resolve().parents[1]
    raw = base / 'data/raw/datos_abiertos_vigilancia_dengue.csv'
    if not raw.exists():
        raw = base / 'datos_abiertos_vigilancia_dengue.csv'
    try:
        df = pd.read_csv(raw, sep=';', encoding='utf-8-sig', low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(raw, sep=';', encoding='latin-1', low_memory=False)
    out, reporte = preparar_datos(df)
    reporte['sha256_fuente'] = hashlib.sha256(raw.read_bytes()).hexdigest()
    for folder in ('data/processed', 'reports'):
        (base / folder).mkdir(parents=True, exist_ok=True)
    out.to_csv(base / 'data/processed/dengue_processed.csv', index=False, encoding='utf-8')
    for nombre in ('calidad_datos.json', 'calidad_datos.txt'):
        (base / 'reports' / nombre).write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding='utf-8')
    registrar_evento('PROCESAMIENTO_ETL', f'Generadas {len(out)} filas distrito-semana')
    print(json.dumps(reporte, ensure_ascii=False, indent=2))
    return out

if __name__ == '__main__':
    ejecutar_etl_calidad()
