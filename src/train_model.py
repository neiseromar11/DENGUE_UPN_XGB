import os
import sys
import json
from datetime import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import generar_features, obtener_feature_columns
from model import separar_temporal, entrenar_xgboost, evaluar_modelo, calcular_baseline, guardar_modelo
from audit import registrar_evento

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, 'data', 'processed', 'dengue_processed.csv')
    models_dir = os.path.join(base_dir, 'models')
    reports_dir = os.path.join(base_dir, 'reports')
    
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    # 1. Cargar datos
    print("Cargando datos...")
    df = pd.read_csv(data_path)
    
    # 2. Generar features
    print("Generando features...")
    df_features = generar_features(df)
    feature_cols = obtener_feature_columns()
    
    # 3. Separar temporalmente
    print("Separando conjuntos de train y test temporalmente...")
    df_train, df_test, cutoff_info = separar_temporal(df_features, ratio_test=0.2)
    
    # 4. Entrenar modelo
    print("Entrenando modelo XGBoost...")
    registrar_evento("ENTRENAMIENTO_MODELO", "Iniciando entrenamiento de XGBoost")
    modelo = entrenar_xgboost(df_train, feature_cols)
    registrar_evento("ENTRENAMIENTO_MODELO", "Modelo XGBoost entrenado exitosamente")
    
    # 5. Evaluar modelo
    print("Evaluando modelo...")
    registrar_evento("EVALUACION_MODELO", "Evaluando modelo en conjunto de prueba")
    eval_resultados = evaluar_modelo(modelo, df_test, feature_cols)
    metricas_xgb = eval_resultados['metricas']
    
    # 6. Calcular baseline
    print("Calculando baseline...")
    metricas_baseline = calcular_baseline(df_test)
    
    # 7. Comparación
    print("\n--------------------------")
    print("Métricas XGBoost:")
    print(f"R2: {metricas_xgb['r2']:.4f}")
    print(f"MAE: {metricas_xgb['mae']:.4f}")
    print(f"RMSE: {metricas_xgb['rmse']:.4f}")
    print("\nMétricas Baseline (lag_1):")
    print(f"MAE: {metricas_baseline['mae']:.4f}")
    print(f"RMSE: {metricas_baseline['rmse']:.4f}")
    
    superacion = metricas_xgb['mae'] < metricas_baseline['mae']
    print(f"\nSupera baseline en MAE: {'Sí' if superacion else 'No'}")
    print("--------------------------\n")
    
    # 8. Guardar modelo
    print("Guardando modelo y métricas...")
    modelo_path = os.path.join(models_dir, 'xgboost_dengue.json')
    guardar_modelo(modelo, modelo_path)
    
    # 9. Guardar métricas
    metricas_completas = {
        'r2': float(metricas_xgb['r2']),
        'mae': float(metricas_xgb['mae']),
        'rmse': float(metricas_xgb['rmse']),
        'baseline_mae': float(metricas_baseline['mae']),
        'baseline_rmse': float(metricas_baseline['rmse']),
        'features_used': feature_cols,
        'cutoff_info': cutoff_info,
        'fecha_entrenamiento': datetime.now().isoformat(),
        'superacion_baseline': bool(superacion),
        'n_train': len(df_train), 'n_test': len(df_test),
        'train_hasta': df_train['semana_epidemiologica'].max(),
        'test_hasta': df_test['semana_epidemiologica'].max(),
        'evaluacion': 'Un paso con observaciones previas del test; no mide horizonte recursivo 2 a 4 semanas',
        'version_pipeline': 2
    }
    
    metricas_path = os.path.join(reports_dir, 'metricas_modelo.json')
    with open(metricas_path, 'w', encoding='utf-8') as f:
        json.dump(metricas_completas, f, indent=4)
        
    registrar_evento("EVALUACION_MODELO", "Métricas y modelo guardados exitosamente")
    # Modelo operativo reentrenado con todo el histórico; las métricas anteriores son del holdout.
    operativo = entrenar_xgboost(df_features, feature_cols)
    guardar_modelo(operativo, os.path.join(models_dir, 'xgboost_operativo.json'))
    metadata = {'version_pipeline': 2, 'datos_hasta': df_features['semana_epidemiologica'].max(),
                'sha256_datos': __import__('hashlib').sha256(open(data_path, 'rb').read()).hexdigest(),
                'uso': 'Solo posterior al corte de datos; no backtesting con modelo operativo'}
    with open(os.path.join(models_dir, 'metadata_operativo.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    pred_test = df_test[['distrito', 'semana_epidemiologica', 'casos_notificados', 'lag_1']].copy()
    pred_test['prediccion'] = eval_resultados['y_pred']
    pred_test.to_csv(os.path.join(reports_dir, 'evaluacion_temporal.csv'), index=False)
    print("Proceso finalizado con éxito.")

if __name__ == '__main__':
    main()
