"""Lectura y presentación de la evaluación publicada, sin reentrenar modelos."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


@st.cache_data(max_entries=8, show_spinner=False)
def leer_evidencia(ruta, version):
    return pd.read_csv(ruta)


def comparar(detalle, metodo, distrito=None, horizonte=2):
    d = detalle[detalle.horizonte.eq(horizonte) & detalle.modelo.isin([metodo, 'baseline'])].copy()
    if distrito:
        d = d[d.distrito.eq(distrito)]
    keys = ['corte', 'distrito', 'horizonte', 'semana']
    activo = d[d.modelo.eq(metodo)].set_index(keys).sort_index()
    base = d[d.modelo.eq('baseline')].set_index(keys).sort_index()
    if activo.empty or not activo.index.equals(base.index) or not activo.real.equals(base.real):
        raise ValueError('La comparación requiere los mismos objetivos y cortes.')
    cero = base.reset_index().copy()
    cero['modelo'] = 'cero'
    cero['prediccion'] = 0.
    d = pd.concat([d, cero], ignore_index=True)
    rows = []
    for name, g in d.groupby('modelo'):
        error = (g.real-g.prediccion).abs()
        positive = g.real.gt(0)
        rows.append({'Método': name, 'MAE (casos)': error.mean(),
                     'RMSE (casos)': ((error**2).mean())**.5,
                     'MAE en semanas con casos': error[positive].mean(),
                     'Observaciones': len(g), 'Observaciones con casos': int(positive.sum())})
    return d, pd.DataFrame(rows)


def mostrar_calidad(base, bundle, distritos):
    st.subheader('Calidad y límites de las estimaciones')
    st.write('Consulta cuánto se equivocó el modelo al estimar semanas históricas posteriores '
             'a cada corte de entrenamiento. Esta evaluación no garantiza el desempeño futuro.')
    c1, c2 = st.columns(2)
    scope = c1.selectbox('Ámbito de la evaluación', ['Los 14 distritos'] + distritos, key='calidad_distrito')
    h = c2.selectbox('Horizonte retrospectivo', [2, 3, 4], format_func=lambda x: f'{x} semanas', key='calidad_h')
    district = None if scope == 'Los 14 distritos' else scope
    try:
        evidence = leer_evidencia(str(base / bundle['evaluacion']).replace('evaluacion.json', 'test.csv'), bundle['version'])
        d, table = comparar(evidence, bundle['metodo'], district, h)
    except (OSError, ValueError, KeyError) as exc:
        st.info(f'No hay una comparación válida disponible: {exc}')
        return
    labels = {'baseline': 'Repetir última semana', 'cero': 'Siempre cero', bundle['metodo']: 'Modelo activo'}
    selected = d[d.modelo.eq(bundle['metodo'])]
    active_mae = (selected.real-selected.prediccion).abs().mean()
    baseline = d[d.modelo.eq('baseline')]
    base_mae = (baseline.real-baseline.prediccion).abs().mean()
    a, b, z, c = st.columns(4)
    a.metric('Error medio del modelo', f'{active_mae:.3f} casos')
    b.metric('Error de repetir la última semana', f'{base_mae:.3f} casos')
    z.metric('Error de «siempre cero»', f'{selected.real.abs().mean():.3f} casos')
    c.metric('Observaciones con cero casos', f'{100*selected.real.eq(0).mean():.1f}%')
    st.caption(f'Casos registrados en las observaciones evaluadas: {int(selected.real.sum())} en {len(selected)} observaciones '
               f'({int(selected.real.gt(0).sum())} con al menos un caso). Con tan pocos casos, diferencias de décimas en el MAE no son concluyentes.')
    st.caption('MAE: promedio de las diferencias absolutas entre lo estimado y lo registrado. '
               'Menor es mejor. No es un porcentaje de precisión. Cada observación es un distrito, corte y horizonte.')
    zero_mae = selected.real.abs().mean()
    if active_mae > min(base_mae, zero_mae):
        st.warning('En esta selección, una referencia sencilla tiene menor MAE que el modelo activo. '
                   'Un promedio bajo en semanas con muchos ceros no demuestra buena detección de aumentos.')
    else:
        st.info('El modelo activo iguala o mejora estas referencias en esta selección histórica. '
                'Esto no demuestra exactitud perfecta ni anticipación de brotes.')
    table['Método'] = table['Método'].map(lambda x: labels.get(x, x))
    st.dataframe(table, hide_index=True)
    st.caption(f'Cortes evaluados: {", ".join(sorted(d.corte.unique()))}. '
               f'Semanas objetivo: {d.semana.min()} a {d.semana.max()}. '
               'Son resultados archivados de la versión publicada, ya examinados durante el proyecto; '
               'no constituyen una nueva evaluación independiente. El periodo visible de las otras vistas no modifica estos cortes.')
    st.subheader('Comprobación histórica: estimación frente a registro')
    st.caption('La gráfica muestra un horizonte fijo para evitar mezclar predicciones de distinta anticipación. '
               'Solo aparecen semanas evaluadas; las líneas no representan semanas intermedias no evaluadas.')
    fig = go.Figure()
    observed = selected.groupby('semana').real.sum().sort_index()
    fig.add_trace(go.Scatter(x=observed.index, y=observed.values, name='Registrado', mode='markers', marker=dict(color='#2563eb', size=11)))
    for method, color in [(bundle['metodo'], '#f59e0b'), ('baseline', '#64748b')]:
        g = d[d.modelo.eq(method)].groupby('semana').prediccion.sum().sort_index()
        fig.add_trace(go.Scatter(x=g.index, y=g.values, name=labels[method], mode='markers', marker=dict(color=color, size=9, symbol='diamond')))
    fig.update_layout(height=390, yaxis_title='Casos por semana', xaxis_title='Semana objetivo', legend=dict(orientation='h'))
    try:
        from charts import estilizar
    except ImportError:
        from .charts import estilizar
    st.plotly_chart(estilizar(fig), use_container_width=True)
    st.caption('Vista global: la gráfica suma los distritos; el MAE de arriba se calcula por distrito, sin compensar errores entre territorios.')
    with st.expander('Ver predicciones históricas y descargar evidencia'):
        st.dataframe(d, hide_index=True)
        st.download_button('Descargar evaluación seleccionada', d.to_csv(index=False).encode('utf-8-sig'), 'evaluacion_seleccionada.csv', 'text/csv')
    st.info('Los experimentos con clima y provincias están separados. No se han incorporado a este modelo ni se utilizan para estas proyecciones.')
