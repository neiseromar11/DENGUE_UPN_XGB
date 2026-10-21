import pandas as pd
import pytest
from src.features import generar_features

def datos():
    return pd.DataFrame({'distrito':['A']*6+['B']*6, 'ano':[2023]*12, 'semana':list(range(1,7))*2,'casos_notificados':[10,20,15,30,25,40]+[1,2,3,4,5,6]})

def test_lags_aislados_sin_fuga():
    f=datos(); d=generar_features(f)
    a=d[d.distrito.eq('A')].iloc[0]
    assert a.lag_1 == 30
    assert a.media_movil_3 == pytest.approx(65/3)
    assert a.crecimiento_semanal == 1
    f.loc[4,'casos_notificados']=999
    mod=generar_features(f)
    assert mod.iloc[0].media_movil_4 == d.iloc[0].media_movil_4
    assert d[d.distrito.eq('B')].iloc[0].lag_4 == 1

def test_rechaza_huecos_duplicados_y_negativos():
    f=datos()
    for invalido in [f.drop(index=2), pd.concat([f,f.iloc[:1]]), f.assign(casos_notificados=-1)]:
        with pytest.raises(ValueError): generar_features(invalido)
