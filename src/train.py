"""Entrena, evalúa y publica conjuntamente datos + modelo mediante un puntero atómico."""
import argparse
import json
from pathlib import Path
from uuid import uuid4
import pandas as pd
try:
    from .etl import BASE, sha256, guardar_json
    from .features import generar_features
    from .model import entrenar_xgboost, guardar_modelo
    from .validation import validar_modelos, metricas
except ImportError:
    from etl import BASE, sha256, guardar_json
    from features import generar_features
    from model import entrenar_xgboost, guardar_modelo
    from validation import validar_modelos, metricas


def publicar(metadata_path, base=BASE):
    base = Path(base).resolve()
    metadata_path = Path(metadata_path).resolve()
    ruta_datos = metadata_path.parent / 'datos.csv'
    meta = json.loads(metadata_path.read_text(encoding='utf-8'))
    if sha256(ruta_datos) != meta['sha256_datos']:
        raise ValueError('La huella de los datos no coincide.')
    datos = pd.read_csv(ruta_datos)
    resumen, val, test = validar_modelos(datos)
    release = base / 'models/releases' / (meta['version'] + '-' + uuid4().hex[:12])
    release.mkdir(parents=True)
    val.to_csv(release / 'validacion.csv', index=False)
    test.to_csv(release / 'test.csv', index=False)
    metricas(test, ('modelo', 'distrito', 'horizonte')).to_csv(release / 'metricas_distritales.csv', index=False)
    guardar_json(release / 'evaluacion.json', resumen)
    modelo_path = None
    if resumen['modelo_publicado'] != 'baseline':
        modelo = entrenar_xgboost(generar_features(datos), params=resumen['parametros'])
        modelo_path = release / 'modelo.json'
        guardar_modelo(modelo, str(modelo_path))
    bundle = dict(version=release.name, datos=ruta_datos.relative_to(base).as_posix(),
                  metadata=metadata_path.relative_to(base).as_posix(), sha256_datos=meta['sha256_datos'],
                  modelo=modelo_path.relative_to(base).as_posix() if modelo_path else None,
                  sha256_modelo=sha256(modelo_path) if modelo_path else None,
                  evaluacion=(release / 'evaluacion.json').relative_to(base).as_posix(),
                  metodo=resumen['modelo_publicado'], corte=meta['corte'])
    guardar_json(release / 'bundle.json', bundle)
    guardar_json(base / 'models/actual.json', bundle)  # único punto de activación
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(publicar(args.metadata), indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'No se activó la actualización: {exc}\n')


if __name__ == '__main__':
    main()
