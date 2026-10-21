import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.risk import Umbrales, evaluar_riesgo
from src.etl import actualizar_datos
from src.dashboard import filtrar, indicadores, pronosticar
from src.validation import plan_cortes, elegir_modelo, evaluar_cortes
from src.features import generar_features
from src.config import DISTRITOS_VALIDOS


def panel(n=20):
    return pd.DataFrame([dict(distrito=d, ano=2024, semana=s,
        semana_epidemiologica=f'2024-SE{s:02d}', casos_notificados=s,
        sin_registros_fuente=False) for d in DISTRITOS_VALIDOS[:-1] for s in range(1,n+1)])


def test_riesgo_cero_insuficiente_y_limites():
    assert evaluar_riesgo(.001, 0, 12)['nivel'] == 'Evaluación especial'
    assert evaluar_riesgo(10, 2, 4)['nivel'] == 'Sin datos suficientes'
    assert evaluar_riesgo(1.5, 1, 12)['nivel'] == 'MEDIO'
    assert evaluar_riesgo(.8, 1, 12)['nivel'] == 'BAJO'
    for args in [(2,1), (float('nan'),2), (-1,2)]:
        with pytest.raises(ValueError): Umbrales(*args)
    with pytest.raises(ValueError): evaluar_riesgo(float('nan'), 1, 12)


def test_etl_nuevos_anos_version_y_rechazo(tmp_path):
    fuente=tmp_path/'fuente.csv'
    df=pd.DataFrame(dict(departamento=['LIMA']*2,provincia=['LIMA']*2,
                        distrito=['SAN BORJA']*2,ano=[2025]*2,semana=[1,3]))
    df.to_csv(fuente,sep=';',index=False)
    meta_path=actualizar_datos(fuente,tmp_path)
    meta=json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['corte']=='2025-SE03'
    assert actualizar_datos(fuente,tmp_path)==meta_path
    assert not (tmp_path/'models/actual.json').exists()
    df.loc[0,'semana']=54; df.to_csv(fuente,sep=';',index=False)
    with pytest.raises(ValueError): actualizar_datos(fuente,tmp_path)
    assert meta_path.exists()
    df.loc[0,'semana']=None; df.to_csv(fuente,sep=';',index=False)
    with pytest.raises(ValueError): actualizar_datos(fuente,tmp_path)


def test_kpis_globales_y_distritales_y_calculo_selectivo():
    d=panel()
    d.loc[(d.distrito=='San Borja') & (d.semana==20),'casos_notificados']=0
    d.loc[(d.distrito=='San Borja') & (d.semana==20),'sin_registros_fuente']=True
    assert indicadores(d)['semanas_sin_registros']==0
    assert indicadores(filtrar(d,'San Borja',12))['semanas_sin_registros']==1
    llamadas=[]
    class Modelo:
        def predict(self,x): llamadas.append(len(x)); return [1.]
    r=pronosticar(generar_features(d),'San Borja',4,Modelo())
    assert len(llamadas)==4 and len(r)==4 and r.distrito.unique().tolist()==['San Borja']
    assert len(pronosticar(generar_features(d),None,2))==28


def test_cortes_reservan_test_y_baseline_no_mira_futuro():
    semanas=list(range(104))
    val,test=plan_cortes(semanas)
    assert max(val)+4 < min(test)+1
    d=panel()
    detalle=evaluar_cortes(d,['2024-SE16'],{})
    assert detalle.prediccion.eq(16).all() and len(detalle)==56
    mod=d.copy(); mod.loc[mod.semana.gt(16),'casos_notificados']=999
    futuro=evaluar_cortes(mod,['2024-SE16'],{})
    assert futuro.prediccion.equals(detalle.prediccion)


def test_seleccion_rechaza_regresion_en_un_horizonte():
    rows=[]
    for h in [2,3,4]:
        rows.extend([dict(modelo='baseline',horizonte=h,real=0,prediccion=1),
                     dict(modelo='xgb',horizonte=h,real=0,prediccion=1.1 if h==4 else .1)])
    assert elegir_modelo(pd.DataFrame(rows))=='baseline'
    rows[-1]['prediccion']=.2
    assert elegir_modelo(pd.DataFrame(rows))=='xgb'


def test_xgb_no_entrena_con_objetivos_futuros(monkeypatch):
    from src import validation
    cortes=[]
    class Modelo:
        def predict(self,x): return np.asarray(x.lag_1)
    def entrenar(train, params):
        cortes.append(train.semana.max())
        assert train.casos_notificados.max()==16
        return Modelo()
    monkeypatch.setattr(validation,'entrenar_xgboost',entrenar)
    d=panel(); d.loc[d.semana.gt(16),'casos_notificados']=999
    r=validation.evaluar_cortes(d,['2024-SE16'],{'xgb':{}})
    assert cortes==[16]
    assert r[r.modelo.eq('xgb')].prediccion.eq(16).all()


def test_cache_reusa_e_invalida_por_firma(tmp_path,monkeypatch):
    from src import services
    from src.etl import sha256
    path=tmp_path/'datos.csv'; panel().to_csv(path,index=False)
    llamadas=[]
    original=services.generar_features
    def generar(d): llamadas.append(1); return original(d)
    monkeypatch.setattr(services,'generar_features',generar)
    services.preparar_version.clear()
    firma=sha256(path)
    services.preparar_version(str(path),firma)
    services.preparar_version(str(path),firma)
    assert len(llamadas)==1
    panel().assign(casos_notificados=2).to_csv(path,index=False)
    services.preparar_version(str(path),sha256(path))
    assert len(llamadas)==2
    services.preparar_version.clear()


def test_publicacion_fallida_conserva_version_activa(tmp_path,monkeypatch):
    from src import train
    from src.etl import sha256, guardar_json
    folder=tmp_path/'data/versions/prueba';folder.mkdir(parents=True)
    panel().to_csv(folder/'datos.csv',index=False)
    guardar_json(folder/'metadata.json',dict(sha256_datos=sha256(folder/'datos.csv')))
    guardar_json(tmp_path/'models/actual.json',{'version':'anterior'})
    def fallar(datos): raise ValueError('Evaluación incompleta')
    monkeypatch.setattr(train,'validar_modelos',fallar)
    with pytest.raises(ValueError): train.publicar(folder/'metadata.json',tmp_path)
    assert json.loads((tmp_path/'models/actual.json').read_text())=={'version':'anterior'}


def test_recurso_xgb_compartido_y_prediccion_de_version(tmp_path,monkeypatch):
    from src import services
    from src.etl import sha256
    from src.model import entrenar_xgboost, guardar_modelo
    path=tmp_path/'datos.csv'; panel().to_csv(path,index=False)
    modelo=entrenar_xgboost(generar_features(panel()),params={'n_estimators':5})
    modelpath=tmp_path/'modelo.json'; guardar_modelo(modelo,str(modelpath))
    services.recurso_modelo.clear()
    recurso1=services.recurso_modelo(str(modelpath),sha256(modelpath))
    recurso2=services.recurso_modelo(str(modelpath),sha256(modelpath))
    assert recurso1 is recurso2
    bundle=dict(version='prueba',datos='datos.csv',modelo='modelo.json',
                sha256_datos=sha256(path),sha256_modelo=sha256(modelpath),metodo='xgb')
    r=services.predecir_version(bundle,'San Borja',2,str(tmp_path))
    assert len(r)==2 and np.isfinite(r.prediccion).all()
    assert r.distrito.eq('San Borja').all()
    services.recurso_modelo.clear()
    services.predecir_version.clear()
