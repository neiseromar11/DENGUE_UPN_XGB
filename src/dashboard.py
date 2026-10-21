"""Transformaciones puras compartidas por interfaz y pruebas."""
import pandas as pd
try:
    from .calendar_epi import siguiente_semana
    from .model import predecir_multistep
    from .risk import evaluar_riesgo
except ImportError:
    from calendar_epi import siguiente_semana
    from model import predecir_multistep
    from risk import evaluar_riesgo


def filtrar(datos, distrito=None, ultimas=None):
    d = datos if distrito is None else datos[datos.distrito.eq(distrito)]
    if ultimas:
        semanas = sorted(d.semana_epidemiologica.unique())[-ultimas:]
        d = d[d.semana_epidemiologica.isin(semanas)]
    return d.copy()


def indicadores(datos):
    semanal = datos.groupby('semana_epidemiologica').casos_notificados.sum().sort_index()
    ultima = int(semanal.iloc[-1])
    anterior = int(semanal.iloc[-2]) if len(semanal) >= 2 else None
    diferencia_absoluta = (ultima - anterior) if anterior is not None else 0
    if anterior is not None and anterior > 0:
        tendencia_pct = ((ultima - anterior) / anterior) * 100.0
        tendencia_texto = f"{tendencia_pct:+.1f}%"
    elif anterior == 0 and ultima > 0:
        tendencia_pct = None
        tendencia_texto = f"+{ultima} casos (ref. anterior 0)"
    elif anterior == 0 and ultima == 0:
        tendencia_pct = 0.0
        tendencia_texto = "0.0% (sin casos)"
    else:
        tendencia_pct = None
        tendencia_texto = "Sin datos previos"
        
    return dict(ultima=ultima, anterior=anterior, diferencia_absoluta=diferencia_absoluta,
                tendencia_pct=tendencia_pct, tendencia_texto=tendencia_texto,
                total=int(semanal.sum()), semanas=len(semanal),
                semanas_sin_registros=int(semanal.eq(0).sum()),
                combinaciones_sin_registros=int(datos.sin_registros_fuente.sum()))


def pronosticar(features, distrito, horizonte, modelo=None, datos=None):
    if horizonte not in (2, 3, 4):
        raise ValueError('Horizonte permitido: 2, 3 o 4 semanas.')
    seleccion = filtrar(features, distrito)
    if seleccion.empty:
        raise ValueError('No hay historia suficiente para el distrito seleccionado.')
    filas = []
    for nombre, grupo in seleccion.groupby('distrito'):
        grupo = grupo.sort_values(['ano', 'semana'])
        ultimo = grupo.iloc[-1]
        valores = predecir_multistep(modelo, ultimo, horizonte) if modelo is not None else [float(ultimo.casos_notificados)] * horizonte
        observado = datos[datos.distrito.eq(nombre)] if datos is not None else grupo
        ventana = observado.sort_values(['ano', 'semana']).tail(12)
        referencia = float(ventana.casos_notificados.mean())
        a, s = int(ultimo.ano), int(ultimo.semana)
        for paso, valor in enumerate(valores, 1):
            a, s = siguiente_semana(a, s)
            riesgo = evaluar_riesgo(valor, referencia, len(ventana))
            ratio = riesgo.get('razon_relativa')
            indice_pct = f"{ratio * 100:.1f}%" if ratio is not None else "No calculable"
            filas.append(dict(distrito=nombre, semana_epidemiologica=f'{a}-SE{s:02d}',
                              horizonte=paso, prediccion=round(valor, 2), 
                              indice_riesgo=indice_pct, riesgo_relativo=riesgo['nivel'],
                              explicacion=riesgo['razon'], umbral_referencia=round(referencia, 2)))
    return pd.DataFrame(filas)
