"""Verifica la entrega trasladada, no solo la ubicación del repositorio."""
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from iniciar import verificar_publicacion
from empaquetar import empaquetar


def test_zip_trasladado_carga_dashboard(tmp_path):
    archivo = empaquetar()
    destino = tmp_path / 'Otra ubicación con espacios'
    with ZipFile(archivo) as z:
        nombres = z.namelist()
        assert not any('/.runtime-envs/' in n or n.endswith('/.env') for n in nombres)
        z.extractall(destino)
    proyecto = destino / 'DengueML_UPN'
    assert verificar_publicacion(proyecto)['version'] == verificar_publicacion(BASE)['version']
    # Otro proceso evita que imports/cachés del proyecto original falseen la prueba.
    codigo = '''
from pathlib import Path
from streamlit.testing.v1 import AppTest
app = AppTest.from_file('src/app.py').run(timeout=60)
assert not app.exception, app.exception
assert not app.error, app.error
app.sidebar.selectbox[1].select(2).run(timeout=60)
assert not app.exception, app.exception
assert not app.error, app.error
import etl
assert etl.BASE == Path.cwd()
print('Dashboard trasladado: pestañas y filtros operativos')
'''
    resultado = subprocess.run([sys.executable, '-c', codigo], cwd=proyecto,
                               capture_output=True, text=True, timeout=90)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_publicacion_rechaza_archivo_alterado(tmp_path):
    bundle = verificar_publicacion(BASE)
    for campo in ('datos', 'metadata', 'evaluacion', 'modelo'):
        if not bundle.get(campo):
            continue
        destino = tmp_path / bundle[campo]
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes((BASE / bundle[campo]).read_bytes())
    test_path = tmp_path / Path(bundle['evaluacion']).parent / 'test.csv'
    test_path.write_bytes((BASE / Path(bundle['evaluacion']).parent / 'test.csv').read_bytes())
    (tmp_path / 'models/actual.json').write_text(json.dumps(bundle), encoding='utf-8')
    with (tmp_path / bundle['datos']).open('ab') as f:
        f.write(b'\n')
    with pytest.raises(ValueError, match='huella'):
        verificar_publicacion(tmp_path)
