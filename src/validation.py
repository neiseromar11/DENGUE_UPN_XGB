"""Backtesting recursivo: ajuste hasta el origen; ningún observado futuro entra al modelo."""
import numpy as np
import pandas as pd
try:
    from .features import generar_features
    from .model import entrenar_xgboost, predecir_multistep
    from .config import DISTRITOS_DIRIS_DATASET, DISTRITOS_DATASET_MAP
except ImportError:
    from features import generar_features
    from model import entrenar_xgboost, predecir_multistep
    from config import DISTRITOS_DIRIS_DATASET, DISTRITOS_DATASET_MAP

CANDIDATOS = {
    'xgb_conservador': dict(max_depth=2, n_estimators=100, min_child_weight=5, reg_lambda=10),
    'xgb_moderado': dict(max_depth=3, n_estimators=150, min_child_weight=3, reg_lambda=5),
    'xgb_poisson': dict(max_depth=2, n_estimators=100, min_child_weight=3,
                        reg_lambda=10, objective='count:poisson'),
}


def validar_panel(datos):
    esperados = {DISTRITOS_DATASET_MAP[d] for d in DISTRITOS_DIRIS_DATASET}
    if set(datos.distrito.unique()) != esperados:
        raise ValueError('La evaluación requiere los 14 distritos del alcance.')
    features = generar_features(datos)  # valida fechas, duplicados, huecos y conteos
    cantidades = datos.groupby('semana_epidemiologica').distrito.nunique()
    if not cantidades.eq(14).all():
        raise ValueError('Cada semana debe contener los mismos 14 distritos.')
    return features


def plan_cortes(semanas, min_train=26, holdout=16, n_cortes=3, separacion=8):
    """Cuatro semanas por origen; el bloque final nunca selecciona hiperparámetros."""
    if min_train < 8 or holdout < 8 or holdout % 4 or n_cortes < 2 or separacion < 4:
        raise ValueError('Configuración temporal insuficiente o con bloques solapados.')
    inicio_test = len(semanas) - holdout
    ultimo = inicio_test - 5  # objetivos de validación terminan antes del test
    val = [ultimo - separacion * i for i in reversed(range(n_cortes))]
    test = list(range(inicio_test - 1, len(semanas) - 4, 4))
    if val[0] + 1 < min_train or not test:
        raise ValueError('Histórico insuficiente para separar selección y prueba final.')
    return [semanas[i] for i in val], [semanas[i] for i in test]


def evaluar_cortes(datos, cortes, candidatos=None, features=None):
    candidatos = CANDIDATOS if candidatos is None else candidatos
    features = validar_panel(datos) if features is None else features
    semanas = sorted(datos.semana_epidemiologica.unique())
    filas = []
    for corte in cortes:
        idx = semanas.index(corte)
        futuras = semanas[idx + 1:idx + 5]
        if len(futuras) != 4:
            raise ValueError('Cada corte debe tener cuatro semanas posteriores observadas.')
        train = features[features.semana_epidemiologica.le(corte)]
        if train.empty:
            raise ValueError('Entrenamiento vacío.')
        modelos = {nombre: entrenar_xgboost(train, params=params) for nombre, params in candidatos.items()}
        reales = datos.set_index(['distrito', 'semana_epidemiologica']).casos_notificados
        for distrito, grupo in train.groupby('distrito'):
            ultimo = grupo.sort_values(['ano', 'semana']).iloc[-1]
            if ultimo.semana_epidemiologica != corte:
                raise ValueError('El origen no coincide entre distritos.')
            pronosticos = {'baseline': [float(ultimo.casos_notificados)] * 4}
            pronosticos.update({nombre: predecir_multistep(modelo, ultimo, 4) for nombre, modelo in modelos.items()})
            for nombre, preds in pronosticos.items():
                for h, (semana, pred) in enumerate(zip(futuras, preds), 1):
                    filas.append(dict(modelo=nombre, corte=corte, distrito=distrito, horizonte=h,
                                      semana=semana, real=float(reales.loc[distrito, semana]), prediccion=pred))
    return pd.DataFrame(filas)


def metricas(detalle, por=('modelo', 'horizonte')):
    d = detalle.assign(error_abs=abs(detalle.real - detalle.prediccion),
                       error_cuadrado=(detalle.real - detalle.prediccion) ** 2)
    out = d.groupby(list(por), as_index=False).agg(mae=('error_abs', 'mean'),
        mse=('error_cuadrado', 'mean'), n=('real', 'size'))
    out['rmse'] = np.sqrt(out.pop('mse'))
    return out


def elegir_modelo(detalle, mejora_minima=0.02):
    """MAE macro balanceado (panel completo), pasos 2–4; sin regresión por horizonte."""
    if not 0 <= mejora_minima < 1:
        raise ValueError('Mejora mínima inválida.')
    tabla = metricas(detalle[detalle.horizonte.isin([2, 3, 4])])
    pivot = tabla.pivot(index='modelo', columns='horizonte', values='mae')
    if pivot.isna().any().any() or set(pivot.columns) != {2, 3, 4}:
        raise ValueError('Evaluación incompleta.')
    base = pivot.loc['baseline']
    elegibles = [nombre for nombre in pivot.index if nombre != 'baseline'
                 and (pivot.loc[nombre] <= base).all()
                 and pivot.loc[nombre].mean() < base.mean() * (1 - mejora_minima)]
    return min(elegibles, key=lambda n: pivot.loc[n].mean()) if elegibles else 'baseline'


def validar_modelos(datos, candidatos=None):
    candidatos = CANDIDATOS if candidatos is None else candidatos
    features = validar_panel(datos)
    cortes_val, cortes_test = plan_cortes(sorted(datos.semana_epidemiologica.unique()))
    validacion = evaluar_cortes(datos, cortes_val, candidatos, features)
    elegido = elegir_modelo(validacion)
    # Si el baseline gana, se evalúa solamente este. No se busca otro candidato en test.
    final = evaluar_cortes(datos, cortes_test,
                          {elegido: candidatos[elegido]} if elegido != 'baseline' else {}, features)
    aprobado = elegir_modelo(final) if elegido != 'baseline' else 'baseline'
    resumen = dict(candidato_validacion=elegido, modelo_publicado=aprobado,
                   parametros=candidatos.get(aprobado, {}), cortes_validacion=cortes_val,
                   cortes_test=cortes_test, mejora_minima_mae=0.02,
                   criterio='MAE medio de pasos 2, 3 y 4; mejora >2% y sin empeorar ningún horizonte.',
                   limites='Backtest retrospectivo; no garantiza precisión futura ni calibración sanitaria.',
                   validacion=metricas(validacion).to_dict('records'),
                   test=metricas(final).to_dict('records'))
    return resumen, validacion, final
