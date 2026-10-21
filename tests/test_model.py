import numpy as np
import pandas as pd
import pytest
from src.model import separar_temporal, entrenar_xgboost, predecir_multistep, guardar_modelo, cargar_modelo
from src.features import generar_features
from src.calendar_epi import siguiente_semana, fecha_semana

def test_corte_no_comparte_semana():
    d=pd.DataFrame({'ano':[2023]*15,'semana':list(range(1,6))*3})
    tr,te,_=separar_temporal(d, .3)
    assert len(te)==6
    assert tr.semana.max() < te.semana.min()
    with pytest.raises(ValueError): separar_temporal(d, 0)
    with pytest.raises(ValueError): separar_temporal(d.iloc[:1])

def test_recursion_usa_ultimo_observado_y_medias_correctas():
    entradas=[]
    class Modelo:
        def predict(self,x):
            entradas.append(x.iloc[0].copy())
            return np.array([50.0])
    ultimo={'ano':2024,'semana':52,'lag_3':10,'lag_2':20,'lag_1':30,'casos_notificados':40}
    assert predecir_multistep(Modelo(),ultimo,2)==[50,50]
    assert entradas[0].lag_1==40
    assert entradas[0].media_movil_4==25
    assert entradas[1].media_movil_3==40
    assert entradas[1].crecimiento_semanal==pytest.approx(.25)
    assert entradas[1].mes==1

def test_calendario_53_semanas():
    assert siguiente_semana(2020,52)==(2020,53)
    assert siguiente_semana(2020,53)==(2021,1)
    assert str(fecha_semana(2024,1))=='2023-12-31'
    with pytest.raises(ValueError): fecha_semana(2024,53)

def test_entrenamiento_persistencia(tmp_path):
    d=pd.DataFrame({'distrito':['A']*20,'ano':[2023]*20,'semana':range(1,21),'casos_notificados':np.arange(20)})
    d=generar_features(d)
    modelo=entrenar_xgboost(d)
    ruta=str(tmp_path/'modelo.json'); guardar_modelo(modelo,ruta)
    p=predecir_multistep(cargar_modelo(ruta),d.iloc[-1],4)
    assert len(p)==4 and all(np.isfinite(p)) and min(p)>=0

def test_prediccion_no_finita_y_horizonte():
    class Malo:
        def predict(self,x): return [np.nan]
    r={'ano':2024,'semana':1,'lag_3':1,'lag_2':2,'lag_1':3,'casos_notificados':4}
    with pytest.raises(ValueError): predecir_multistep(Malo(),r,4)
    with pytest.raises(ValueError): predecir_multistep(Malo(),r,0)
