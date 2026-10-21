"""Prepara un entorno propio y ejecuta DengueML desde cualquier carpeta."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

BASE = Path(__file__).resolve().parent


def archivo_publicado(base, nombre):
    ruta = (base / nombre).resolve()
    if not ruta.is_relative_to(base.resolve()) or not ruta.is_file():
        raise ValueError(f'Falta un archivo publicado o su ruta no es local: {nombre}')
    return ruta


def verificar_publicacion(base=BASE):
    bundle = json.loads((base / 'models/actual.json').read_text(encoding='utf-8'))
    for campo in ('datos', 'metadata', 'evaluacion'):
        archivo_publicado(base, bundle[campo])
    archivo_publicado(base, str(Path(bundle['evaluacion']).parent / 'test.csv'))
    for campo in ('datos', 'modelo'):
        if bundle.get(campo):
            ruta = archivo_publicado(base, bundle[campo])
            if hashlib.sha256(ruta.read_bytes()).hexdigest() != bundle['sha256_' + campo]:
                raise ValueError(f'La huella de {campo} no coincide con la publicación.')
    return bundle


def preparar_entorno(base=BASE, offline=False):
    if sys.version_info[:2] not in ((3, 11), (3, 12)):
        raise ValueError('Utilice Python 3.11 o 3.12 de 64 bits.')
    if sys.maxsize <= 2**32:
        raise ValueError('Se necesita Python de 64 bits.')
    requisitos = base / 'requirements-lock.txt'
    identidad = str(base.resolve()) + sys.executable + sys.version + requisitos.read_text()
    clave = hashlib.sha256(identidad.encode()).hexdigest()[:16]
    # Una nueva ubicación obtiene un entorno nuevo; nunca reutiliza el venv movido.
    entorno = base / '.runtime-envs' / clave
    python = entorno / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    listo = entorno / 'instalacion-completa.txt'
    if not python.exists():
        print('Creando entorno aislado...', flush=True)
        venv.EnvBuilder(with_pip=True).create(entorno)
    if not listo.exists():
        comando = [str(python), '-m', 'pip', 'install', '-r', str(requisitos)]
        local = comando + ['--no-index', '--find-links', str(base / 'wheelhouse')]
        print('Instalando dependencias. La primera ejecución puede tardar varios minutos.', flush=True)
        if offline or (base / 'wheelhouse').is_dir():
            # Si existe wheelhouse/ se usa primero (no requiere Internet); si falla y no es obligatorio, se intenta en línea.
            try:
                subprocess.run(local, check=True, cwd=base)
            except subprocess.CalledProcessError:
                if offline:
                    raise
                print('wheelhouse/ no sirve para este equipo; se intenta instalar desde Internet.', flush=True)
                subprocess.run(comando, check=True, cwd=base)
        else:
            subprocess.run(comando, check=True, cwd=base)
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True, cwd=base)
        listo.write_text(clave, encoding='utf-8')
    return python


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solo-instalar', action='store_true')
    parser.add_argument('--offline', action='store_true', help='Instala solamente desde wheelhouse/')
    parser.add_argument('--puerto', type=int, default=8501)
    args = parser.parse_args()
    try:
        if not 1 <= args.puerto <= 65535:
            raise ValueError('Puerto inválido.')
        bundle = verificar_publicacion()
        python = preparar_entorno(offline=args.offline)
        print(f"Publicación válida: {bundle['version']} | Corte: {bundle['corte']}", flush=True)
        print(f'Python del proyecto: {python}', flush=True)
        if not args.solo_instalar:
            return subprocess.call([str(python), '-m', 'streamlit', 'run', str(BASE / 'src/app.py'),
                                    '--server.address=127.0.0.1', f'--server.port={args.puerto}',
                                    '--browser.gatherUsageStats=false'], cwd=BASE)
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f'No se pudo iniciar: {exc}', file=sys.stderr)
        print('Revise docs/PORTABILIDAD.md. No se cambió la publicación de datos/modelo.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
