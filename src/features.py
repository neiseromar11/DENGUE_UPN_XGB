import pandas as pd
import numpy as np
try:
    from .calendar_epi import fecha_semana
except ImportError:
    from calendar_epi import fecha_semana

TARGET = 'casos_notificados'

def obtener_feature_columns():
    return ['lag_1', 'lag_2', 'lag_3', 'lag_4', 'media_movil_3', 'media_movil_4', 'crecimiento_semanal', 'mes', 'trimestre']

def generar_features(df):
    df = df.sort_values(['distrito', 'ano', 'semana']).copy()
    if df.duplicated(['distrito', 'ano', 'semana']).any():
        raise ValueError('Hay más de una fila por distrito y semana.')
    df['fecha'] = pd.to_datetime([fecha_semana(a, s) for a, s in zip(df.ano, df.semana)])
    pasos = df.groupby('distrito')['fecha'].diff().dropna().dt.days
    if (pasos != 7).any():
        raise ValueError('La serie tiene huecos; complete el calendario en el ETL.')
    casos = pd.to_numeric(df[TARGET], errors='raise')
    if not np.isfinite(casos).all() or (casos < 0).any():
        raise ValueError('Los conteos deben ser finitos y no negativos.')
    df[TARGET] = casos
    grupo = df.groupby('distrito')[TARGET]
    for lag in range(1, 5):
        df[f'lag_{lag}'] = grupo.shift(lag)
    for ventana in (3, 4):
        df[f'media_movil_{ventana}'] = grupo.transform(lambda s: s.shift(1).rolling(ventana).mean())
    df['crecimiento_semanal'] = ((df.lag_1 - df.lag_2) / df.lag_2.replace(0, np.nan)).fillna(0)
    df['mes'] = df.fecha.dt.month
    df['trimestre'] = df.fecha.dt.quarter
    return df.dropna(subset=obtener_feature_columns()).reset_index(drop=True)
