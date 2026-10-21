import os, sys, json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import obtener_feature_columns, TARGET

def separar_temporal(df, ratio_test=0.2):
    """Partición por semanas completas, nunca por filas de distritos."""
    if not 0 < ratio_test < 1:
        raise ValueError('ratio_test debe estar entre 0 y 1.')
    df = df.sort_values(['ano', 'semana']).copy()
    semanas = sorted(set(zip(df.ano, df.semana)))
    if len(semanas) < 2:
        raise ValueError('Se necesitan al menos dos semanas distintas.')
    n_test = max(1, int(np.ceil(len(semanas) * ratio_test)))
    corte = semanas[-n_test]
    mask = pd.Series([tuple(x) >= corte for x in zip(df.ano, df.semana)], index=df.index)
    return df[~mask].copy(), df[mask].copy(), {'semana_epidemiologica': f'{corte[0]}-SE{corte[1]:02d}'}

def entrenar_xgboost(df_train, feature_cols=None, params=None):
    """
    Entrena un modelo XGBoost con los datos de entrenamiento.
    """
    if feature_cols is None:
        feature_cols = obtener_feature_columns()
        
    X_train = df_train[feature_cols]
    y_train = df_train[TARGET]
    
    opciones = dict(n_estimators=200, max_depth=5, learning_rate=0.05,
                    subsample=0.8, colsample_bytree=0.8,
                    objective='reg:squarederror', random_state=42, n_jobs=1)
    opciones.update(params or {})
    modelo = xgb.XGBRegressor(**opciones)
    
    modelo.fit(X_train, y_train)
    return modelo

def evaluar_modelo(modelo, df_test, feature_cols=None):
    """
    Evalúa el modelo usando R2, MAE y RMSE.
    Corta las predicciones para que no sean negativas.
    """
    if feature_cols is None:
        feature_cols = obtener_feature_columns()
        
    X_test = df_test[feature_cols]
    y_test = df_test[TARGET]
    
    y_pred = modelo.predict(X_test)
    y_pred = np.clip(y_pred, 0, None)
    
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    return {
        'metricas': {'r2': r2, 'mae': mae, 'rmse': rmse},
        'y_pred': y_pred
    }

def calcular_baseline(df_test):
    """
    Calcula el MAE y RMSE usando el valor de la semana anterior como predicción.
    """
    y_test = df_test[TARGET]
    y_pred_baseline = df_test['lag_1']
    
    mae = mean_absolute_error(y_test, y_pred_baseline)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_baseline))
    
    return {'mae': mae, 'rmse': rmse}

def guardar_modelo(modelo, ruta):
    """
    Guarda el modelo entrenado en la ruta especificada.
    """
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    modelo.save_model(ruta)

def cargar_modelo(ruta):
    """
    Carga un modelo guardado desde la ruta especificada.
    """
    modelo = xgb.XGBRegressor()
    from pathlib import Path
    modelo.load_model(bytearray(Path(ruta).read_bytes()))
    modelo.set_params(n_jobs=1)
    return modelo

def predecir_multistep(modelo, ultimo_registro, horizonte=4, feature_cols=None):
    """Pronostica desde t+1 usando el observado en t y actualiza todos los rezagos.
    
    Implementa arquitectura híbrida epidemiológica (Hurdle / Umbral Basal):
    1. Si los 2 últimos rezagos observados son 0, la transmisión local está inactiva y se infiere 0.
    2. Las predicciones fraccionarias de ruido residual (< 0.5 casos) se truncan a 0.
    3. En presencia de brote o transmisión activa, infiere la dinámica completa mediante XGBoost.
    """
    from calendar_epi import siguiente_semana, fecha_semana
    if horizonte not in (1, 2, 3, 4):
        raise ValueError('Horizonte permitido: 1 a 4 semanas.')
    feature_cols = feature_cols or obtener_feature_columns()
    fila = ultimo_registro
    historia = [float(fila['lag_3']), float(fila['lag_2']), float(fila['lag_1']), float(fila[TARGET])]
    if not np.isfinite(historia).all() or min(historia) < 0:
        raise ValueError('Historia inválida para pronosticar.')
    ano, semana = int(fila['ano']), int(fila['semana'])
    predicciones = []
    for _ in range(horizonte):
        ano, semana = siguiente_semana(ano, semana)
        fecha = fecha_semana(ano, semana)
        
        # Umbral basal epidemiológico: 2 semanas consecutivas en 0 indican ausencia de transmisión local
        if historia[-1] == 0.0 and historia[-2] == 0.0:
            pred = 0.0
        else:
            valores = {f'lag_{i}': historia[-i] for i in range(1, 5)}
            valores.update(media_movil_3=np.mean(historia[-3:]), media_movil_4=np.mean(historia[-4:]),
                           crecimiento_semanal=(historia[-1] / historia[-2] - 1) if historia[-2] else 0,
                           mes=fecha.month, trimestre=(fecha.month - 1) // 3 + 1)
            p_raw = float(modelo.predict(pd.DataFrame([valores])[feature_cols])[0])
            if not np.isfinite(p_raw):
                raise ValueError('El modelo devolvió una predicción no finita.')
            # Amortiguación epidemiológica autorregresiva: previene explosión en proyecciones iteradas a varias semanas
            if historia[-1] > 20:
                p_raw = min(p_raw, historia[-1] * 1.3)
            # Truncamiento de ruido residual continuo (< 0.5 casos esperados se redondea a nivel basal 0)
            pred = 0.0 if p_raw < 0.5 else max(0.0, p_raw)
            
        predicciones.append(pred)
        historia.append(pred)
    return predicciones

def clasificar_riesgo(prediccion, referencia_historica, n_semanas=0):
    from risk import evaluar_riesgo
    return evaluar_riesgo(prediccion, referencia_historica, n_semanas)['nivel']
