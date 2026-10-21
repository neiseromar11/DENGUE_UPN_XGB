"""Exporta código, documentación y publicación activa; excluye entornos y secretos."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from iniciar import BASE, verificar_publicacion, archivo_publicado


def empaquetar(base=BASE, incluir_fuente=False, incluir_dependencias=False):
    bundle = verificar_publicacion(base)
    archivos = set()
    for carpeta in ('src', 'docs', 'tests'):
        archivos.update(p for p in (base / carpeta).rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    for nombre in ('iniciar.py', 'INICIAR_WINDOWS.bat', 'empaquetar.py', 'README.md',
                   'requirements.txt', 'requirements-lock.txt', '.env.example', '.gitignore',
                   'INICIAR_MAC_LINUX.sh', 'Dockerfile', '.dockerignore', 'INICIO_RAPIDO.md'):
        if (base / nombre).is_file():
            archivos.add(base / nombre)
    if incluir_dependencias:
        rueda = base / 'wheelhouse'
        if not rueda.is_dir() or not any(rueda.iterdir()):
            raise ValueError('Falta wheelhouse/. Ejecute: python -m pip download --only-binary=:all: -r requirements-lock.txt -d wheelhouse')
        archivos.update(p for p in rueda.iterdir() if p.is_file())
    archivos.add(base / 'models/actual.json')
    for campo in ('datos', 'metadata', 'evaluacion', 'modelo'):
        if bundle.get(campo):
            archivos.add(archivo_publicado(base, bundle[campo]))
    release = archivo_publicado(base, bundle['evaluacion']).parent
    archivos.update(p for p in release.iterdir() if p.is_file() and p.suffix in ('.json', '.csv'))
    if incluir_fuente:
        archivos.add(base / 'datos_abiertos_vigilancia_dengue.csv')
    destino = base / ('dist/DengueML_UPN_completo.zip' if incluir_dependencias else 'dist/DengueML_UPN_trasladable.zip')
    destino.parent.mkdir(exist_ok=True)
    with ZipFile(destino, 'w', ZIP_DEFLATED) as z:
        for archivo in sorted(archivos):
            z.write(archivo, 'DengueML_UPN/' + archivo.relative_to(base).as_posix())
    return destino


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--incluir-fuente', action='store_true', help='Incluye también el CSV crudo de 108 MB')
    parser.add_argument('--con-dependencias', action='store_true', help='Incluye wheelhouse/ para instalar sin Internet (mismo sistema y Python)')
    args = parser.parse_args()
    print(empaquetar(incluir_fuente=args.incluir_fuente, incluir_dependencias=args.con_dependencias))
