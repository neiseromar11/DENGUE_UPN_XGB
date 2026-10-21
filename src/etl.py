"""Carga de un histórico completo y publicación inmutable; no concatena casos sin ID."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import pandas as pd
try:
    from .data_pipeline import preparar_datos
except ImportError:
    from data_pipeline import preparar_datos

BASE = Path(__file__).resolve().parents[1]
VERSION_ETL = 3


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def guardar_json(path, value):
    """Reemplazo atómico; el lector ve el archivo anterior o el nuevo completo."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def consultar_estado_fuente_oficial(base=BASE, timeout_segundos=10):
    """Resuelve el CSV desde la ficha oficial y consulta sus cabeceras con TLS validado."""
    import urllib.request
    base = Path(base)
    reporte_path = base / 'reports/fuente_oficial.json'
    local_raw = base / 'data/raw/datos_abiertos_vigilancia_dengue.csv'
    sha_local = sha256(local_raw) if local_raw.exists() else None
    tamano_local = local_raw.stat().st_size if local_raw.exists() else None

    resultado = {
        'fecha_consulta_utc': datetime.now(timezone.utc).isoformat(),
        'fuente': 'Plataforma Nacional de Datos Abiertos (datosabiertos.gob.pe)',
        'entidad': 'Centro Nacional de Epidemiología, Prevención y Control de Enfermedades (CDC Perú / MINSA)',
        'conjunto_datos': 'vigilancia-epidemiológica-de-dengue',
        'corte_consolidado': '2024-SE52',
        'archivo_local': str(local_raw.relative_to(base)) if local_raw.exists() else None,
        'sha256_local': sha_local,
        'tamano_bytes_local': tamano_local,
        'estado_sincronizacion': 'No verificado',
        'url_recurso_oficial': 'https://www.datosabiertos.gob.pe/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue/resource/79e21c8d-3a94-4ac5-b234-bace71fe9675',
        'notas_metodologicas': (
            'El recurso nacional publicado llega a 2024; fuentes oficiales adicionales recientes figuran en el manifiesto de cobertura. '
            'El sistema preserva cada versión local y no mezcla cortes acumulados con microdatos semanales; '
            'los archivos se identifican mediante hash SHA-256.'
        )
    }

    try:
        try:
            from .update_data import _source_url
        except ImportError:
            from update_data import _source_url
        url_archivo = _source_url(timeout=timeout_segundos)
        resultado['url_recurso_oficial'] = url_archivo
        req_head = urllib.request.Request(url_archivo, headers={'User-Agent': 'DengueML-UPN/1.0'})
        req_head.get_method = lambda: 'HEAD'
        with urllib.request.urlopen(req_head, timeout=timeout_segundos) as resp_head:
            tamano_remoto = int(resp_head.headers.get('Content-Length', 0))
            resultado['tamano_bytes_remoto'] = tamano_remoto
            resultado['etag_remoto'] = resp_head.headers.get('ETag', '').strip('"')
            if tamano_local == tamano_remoto:
                resultado['estado_sincronizacion'] = 'Completamente sincronizado con versión oficial consolidada'
            else:
                resultado['estado_sincronizacion'] = 'Existe una versión remota con diferente tamaño; requiere actualización manual/ETL'
    except Exception as e:
        resultado['estado_sincronizacion'] = f'Consulta remota no disponible ({type(e).__name__}); se mantiene versión local inmutable verificada'

    guardar_json(reporte_path, resultado)
    return resultado


def validar_fuente(df):
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace('\ufeff', '', regex=False)
    campos = ['departamento', 'provincia', 'distrito', 'ano', 'semana']
    if df.columns.duplicated().any() or not set(campos).issubset(df.columns):
        raise ValueError('Columnas duplicadas o faltantes: se requieren ' + ', '.join(campos))
    if df.empty or df[campos].replace(r'^\s*$', pd.NA, regex=True).isna().any().any():
        raise ValueError('La fuente está vacía o contiene nulos en campos obligatorios.')
    for campo in ('ano', 'semana'):
        valores = pd.to_numeric(df[campo], errors='raise')
        if not valores.between(1, 9998).all() or (valores % 1 != 0).any():
            raise ValueError(f'Formato inválido en {campo}.')
        df[campo] = valores.astype(int)
    try:
        from .calendar_epi import fecha_semana
    except ImportError:
        from calendar_epi import fecha_semana
    for a, s in df[['ano', 'semana']].drop_duplicates().itertuples(index=False, name=None):
        fecha_semana(a, s)
    return df


def actualizar_datos(fuente, base=BASE, sep=';', encoding='utf-8-sig', desde=None, hasta=None):
    """El CSV debe contener el histórico completo, una fila por registro de caso.

    La versión candidata no cambia el dashboard hasta validar y publicar su modelo.
    Los ceros son ausencia de registros, no cobertura confirmada.
    """
    base, fuente = Path(base), Path(fuente)
    firma = sha256(fuente)
    df = pd.read_csv(fuente, sep=sep, encoding=encoding, low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace('\ufeff', '', regex=False)
    total_fuente = len(df)
    if desde is not None or hasta is not None:
        if 'ano' not in df or (desde is not None and hasta is not None and desde > hasta):
            raise ValueError('Periodo solicitado inválido o columna ano ausente.')
        anos = pd.to_numeric(df.ano, errors='raise')
        if anos.isna().any() or (anos % 1 != 0).any():
            raise ValueError('Años nulos o no enteros.')
        df = df[anos.between(desde if desde is not None else anos.min(),
                             hasta if hasta is not None else anos.max())]
    df = validar_fuente(df)
    if sha256(fuente) != firma:
        raise ValueError('La fuente cambió durante la lectura. Reintente con una copia estable.')
    datos, calidad = preparar_datos(df)
    if calidad['filas_fecha_invalida']:
        raise ValueError('Hay fechas inválidas; no se publica el lote.')
    identidad = json.dumps([firma, VERSION_ETL, desde, hasta], sort_keys=True).encode()
    version = f'v{VERSION_ETL}-' + hashlib.sha256(identidad).hexdigest()[:16]
    carpeta = base / 'data/versions' / version
    meta_path = carpeta / 'metadata.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if sha256(carpeta / 'datos.csv') != meta['sha256_datos']:
            raise ValueError('La versión almacenada fue alterada.')
        return meta_path
    temporal = carpeta.with_name(carpeta.name + '.pending-' + uuid4().hex)
    temporal.mkdir(parents=True, exist_ok=False)
    datos.to_csv(temporal / 'datos.csv', index=False)
    meta = dict(version=version, version_etl=VERSION_ETL, corte=calidad['fin'],
                generado_utc=datetime.now(timezone.utc).isoformat(),
                sha256_fuente=firma, sha256_datos=sha256(temporal / 'datos.csv'),
                calidad=calidad, modo='reemplazo de histórico completo',
                periodo_solicitado=dict(desde=desde, hasta=hasta),
                filas_fuera_periodo=total_fuente-len(df))
    guardar_json(temporal / 'metadata.json', meta)
    os.replace(temporal, carpeta)
    return meta_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fuente', type=Path)
    parser.add_argument('--sep', default=';')
    parser.add_argument('--encoding', default='utf-8-sig')
    parser.add_argument('--desde', type=int, help='Inicio opcional y explícito del histórico.')
    parser.add_argument('--hasta', type=int, help='Fin opcional; por defecto incluye todos los años nuevos.')
    args = parser.parse_args()
    try:
        print(actualizar_datos(args.fuente, sep=args.sep, encoding=args.encoding, desde=args.desde, hasta=args.hasta))
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, f'ETL rechazado: {exc}\n')


if __name__ == '__main__':
    main()
