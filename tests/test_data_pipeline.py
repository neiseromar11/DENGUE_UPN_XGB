import pandas as pd
import pytest
from src.data_pipeline import normalize_district_name, match_district, preparar_datos

def test_normalizacion():
    assert normalize_district_name(' Breña ') == 'BRENA'
    assert match_district('BRE\ufffdA', ['BREÑA']) == 'BREÑA'
    assert match_district('BREA', ['BREÑA']) is None

def fuente():
    return pd.DataFrame({'departamento':['LIMA']*5,'provincia':['LIMA']*4+['OTRA'], 'distrito':['SAN BORJA','SAN BORJA','RIMAC','SAN BORJA','SAN BORJA'], 'ano':[2023]*5,'semana':[1,1,1,3,1]})

def test_alcance_coincidencias_y_huecos():
    d, r = preparar_datos(fuente())
    sb = d[d.distrito.eq('San Borja')]
    assert sb.casos_notificados.tolist() == [2,0,1]
    assert sb.sin_registros_fuente.tolist() == [False,True,False]
    assert 'Rímac' not in d.distrito.tolist()
    assert r['coincidencias_exactas_conservadas'] == 1
    assert d.casos_notificados.sum() == 3
    assert d.distrito.nunique() == 14

def test_fecha_invalida_y_columnas():
    f=fuente(); f.loc[0,'semana']=54
    _,r=preparar_datos(f)
    assert r['filas_fecha_invalida'] == 1
    with pytest.raises(ValueError): preparar_datos(f.drop(columns='provincia'))
