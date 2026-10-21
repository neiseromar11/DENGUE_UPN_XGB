"""Funciones de gráficos Plotly para el dashboard DengueML-UPN.

Módulo separado del app.py principal para mantener legibilidad
y facilitar pruebas. Todas las funciones devuelven objetos
plotly.graph_objects.Figure listos para st.plotly_chart().
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


# Paleta accesible y consistente
COLOR_OBSERVADO = '#2563eb'   # azul
COLOR_PREDICCION = '#f59e0b'  # ámbar
COLOR_CORTE = '#6b7280'       # gris
COLORES_RIESGO = {
    'BAJO': '#16a34a',
    'MEDIO': '#eab308',
    'ALTO': '#dc2626',
    'Evaluación especial': '#7c3aed',
    'Sin datos suficientes': '#9ca3af'
}
PALETA_DISTRITOS = px.colors.qualitative.Set2 + px.colors.qualitative.Pastel2


def barras_acumulado_distrital(datos, periodo_label):
    """A. Barras horizontales: casos acumulados por distrito en el periodo visible."""
    resumen = datos.groupby('distrito', as_index=False).agg(
        casos=('casos_notificados', 'sum'),
        sin_fuente=('sin_registros_fuente', 'all')
    ).sort_values('casos', ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=resumen.distrito, x=resumen.casos,
        orientation='h',
        marker=dict(
            color=[COLOR_OBSERVADO if not sf else '#cbd5e1' for sf in resumen.sin_fuente],
            cornerradius=5
        ),
        text=[f'{c:,}' if c > 0 else ('0 (sin registros)' if sf else '0 casos')
              for c, sf in zip(resumen.casos, resumen.sin_fuente)],
        textposition='outside', cliponaxis=False,
        hovertemplate='<b>%{y}</b><br>Casos acumulados: %{x:,}<extra></extra>'
    ))
    fig.update_layout(
        xaxis=dict(title='Casos registrados (conteo absoluto)', automargin=True),
        yaxis=dict(automargin=True),
        height=max(420, len(resumen) * 32),
        margin=dict(l=15, r=45, t=25, b=45),
        showlegend=False,
        autosize=True
    )
    return fig


def barras_pronostico_semana(resultado, semana_sel):
    """B. Barras de pronóstico para una semana futura seleccionada."""
    df = resultado[resultado.semana_epidemiologica == semana_sel].sort_values('prediccion', ascending=True)
    if df.empty:
        return None

    colores = [COLORES_RIESGO.get(r, '#9ca3af') for r in df.riesgo_relativo]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df.distrito, x=df.prediccion,
        orientation='h',
        marker=dict(color=colores, cornerradius=5),
        text=[f'{p:.1f}' for p in df.prediccion],
        textposition='outside', cliponaxis=False,
        hovertemplate='<b>%{y}</b><br>Estimación: %{x:.2f} casos<br>Riesgo preliminar: %{customdata}<extra></extra>',
        customdata=df.riesgo_relativo
    ))
    fig.update_layout(
        xaxis=dict(title='Casos estimados', automargin=True),
        yaxis=dict(automargin=True),
        height=max(420, len(df) * 32),
        margin=dict(l=15, r=45, t=25, b=45),
        showlegend=False,
        autosize=True
    )
    return fig


def heatmap_distrital(datos, periodo_label):
    """C. Mapa de calor: distritos × semanas epidemiológicas."""
    pivot = datos.pivot_table(
        index='distrito', columns='semana_epidemiologica',
        values='casos_notificados', aggfunc='sum'
    )
    # Ordenar distritos por total descendente para legibilidad
    orden = pivot.sum(axis=1).sort_values(ascending=True).index.tolist()
    pivot = pivot.loc[orden]

    # Detectar celdas donde sin_registros_fuente es True (datos ausentes)
    ausentes = datos.pivot_table(
        index='distrito', columns='semana_epidemiologica',
        values='sin_registros_fuente', aggfunc='all'
    ).reindex(index=orden, columns=pivot.columns).fillna(False)

    # Crear texto con distinción cero vs ausente
    textos = []
    for d in pivot.index:
        fila = []
        for s in pivot.columns:
            val = pivot.loc[d, s]
            if ausentes.loc[d, s]:
                fila.append('Sin registros')
            elif pd.isna(val):
                fila.append('Sin datos')
            else:
                fila.append(str(int(val)))
        textos.append(fila)

    fig = go.Figure(data=go.Heatmap(
        z=pivot.mask(ausentes).values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        text=textos,
        hovertemplate='<b>%{y}</b><br>%{x}<br>Casos registrados: %{text}<extra></extra>',
        colorscale='Blues',
        colorbar_title='Casos',
        zmin=0,
        xgap=2, ygap=2
    ))
    # Capa gris independiente para no confundir ausencia de registro con cero
    fig.add_trace(go.Heatmap(
        z=np.where(ausentes | pivot.isna(), 1.0, np.nan),
        x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale=[[0, '#cbd5e1'], [1, '#cbd5e1']], showscale=False,
        hovertemplate='<b>%{y}</b><br>%{x}<br>Sin registros en fuente<extra></extra>',
        xgap=2, ygap=2
    ))
    fig.update_layout(
        xaxis=dict(title='Semana epidemiológica', automargin=True, tickangle=-45, dtick=4),
        yaxis=dict(automargin=True),
        height=max(450, len(pivot) * 28),
        margin=dict(l=15, r=45, t=25, b=45),
        autosize=True
    )
    return fig


def comparador_distritos(datos, distritos_sel):
    """D. Curvas históricas de 2-4 distritos seleccionados."""
    if not distritos_sel or len(distritos_sel) < 2:
        return None

    fig = go.Figure()
    for i, dist in enumerate(distritos_sel):
        sub = datos[datos.distrito == dist].sort_values('semana_epidemiologica')
        serie = sub.groupby('semana_epidemiologica').casos_notificados.sum()
        sin_fuente = sub.groupby('semana_epidemiologica').sin_registros_fuente.all()
        serie = serie.mask(sin_fuente)
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values,
            mode='lines+markers',
            connectgaps=False,
            name=dist,
            marker_size=4,
            line_color=PALETA_DISTRITOS[i % len(PALETA_DISTRITOS)],
            hovertemplate=f'{dist}<br>%{{x}}<br>Casos: %{{y:,}}<extra></extra>'
        ))

    # Diseño responsivo: leyenda horizontal holgada arriba sin solapamiento
    fig.update_layout(
        xaxis=dict(title='Semana epidemiológica', automargin=True, tickangle=-45, dtick=8),
        yaxis=dict(title='Casos registrados', automargin=True),
        height=420,
        margin=dict(l=55, r=25, t=35, b=45),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0.0, font=dict(size=11)),
        autosize=True
    )
    return fig


def curva_historico_pronostico(hist_series, pred_series, corte_se, titulo=None):
    """E. Curva con línea de corte y pronóstico diferenciado."""
    fig = go.Figure()

    # Histórico: línea sólida azul con relleno sutil
    fig.add_trace(go.Scatter(
        x=hist_series.index, y=hist_series.values,
        mode='lines+markers',
        name='Observado (histórico)',
        line=dict(color=COLOR_OBSERVADO, width=2.5),
        marker=dict(size=3),
        fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.07)',
        hovertemplate='<b>%{x}</b><br>Observado: %{y:,} casos<extra></extra>'
    ))

    # Predicción: línea discontinua ámbar con diamantes
    fig.add_trace(go.Scatter(
        x=pred_series.index, y=pred_series.values,
        mode='lines+markers',
        name='Estimación (XGBoost)',
        line=dict(color=COLOR_PREDICCION, width=2.5, dash='dash'),
        marker=dict(size=6, symbol='diamond', color=COLOR_PREDICCION, line=dict(width=1, color='#ffffff')),
        hovertemplate='<b>%{x}</b><br>Estimado: %{y:.2f} casos<extra></extra>'
    ))

    # Zona sombreada: semanas estimadas (no observadas)
    if len(pred_series):
        fig.add_vrect(x0=corte_se, x1=pred_series.index[-1], fillcolor=COLOR_PREDICCION,
                      opacity=0.08, line_width=0, layer='below')

    # Línea vertical de corte (usando shape y annotation para soportar ejes categóricos)
    fig.add_shape(
        type='line', x0=corte_se, x1=corte_se, y0=0, y1=1, yref='paper',
        line=dict(color=COLOR_CORTE, width=2, dash='dot')
    )
    fig.add_annotation(
        x=corte_se, y=1, yref='paper',
        text='Corte histórico · a la derecha: estimación, no observado',
        showarrow=False,
        font=dict(size=10, color=COLOR_CORTE),
        yanchor='bottom'
    )

    # Layout limpio y 100% responsivo: leyenda situada arriba sin competir con títulos
    fig.update_layout(
        xaxis=dict(title='Semana epidemiológica', automargin=True, tickangle=-45, dtick=8),
        yaxis=dict(title='Casos registrados', automargin=True),
        height=420,
        margin=dict(l=55, r=25, t=35, b=45),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0.0, font=dict(size=11)),
        autosize=True
    )
    return fig


def resumen_riesgo_distrital(resultado, semana_sel):
    """Tabla resumen de niveles de riesgo para una semana pronosticada (vista global)."""
    df = resultado[resultado.semana_epidemiologica == semana_sel].copy()
    if df.empty:
        return (pd.DataFrame(columns=['Nivel de riesgo', 'Distritos']),
                pd.DataFrame(columns=['Distrito', 'Casos estimados', 'Nivel', 'Ref. 12 sem.', 'Nota']))

    niveles = ['BAJO', 'MEDIO', 'ALTO', 'Evaluación especial', 'Sin datos suficientes']
    conteo = {n: 0 for n in niveles}
    for n in df.riesgo_relativo:
        if n in conteo:
            conteo[n] += 1

    resumen = pd.DataFrame([
        {'Nivel de riesgo': k, 'Distritos': v, 'Etiqueta': f'{k} ({v})'}
        for k, v in conteo.items() if v > 0
    ])
    tabla = df[['distrito', 'prediccion', 'riesgo_relativo', 'umbral_referencia', 'explicacion']].rename(
        columns={'distrito': 'Distrito', 'prediccion': 'Casos estimados',
                 'riesgo_relativo': 'Nivel', 'umbral_referencia': 'Ref. 12 sem.',
                 'explicacion': 'Nota'})
    return resumen, tabla


FONDO_RIESGO = {
    'BAJO': '#dcfce7', 'MEDIO': '#fef9c3', 'ALTO': '#fee2e2',
    'Evaluación especial': '#ede9fe', 'Sin datos suficientes': '#e5e7eb',
}


def estilizar(fig):
    """Estilo común: fondo transparente, rejilla suave y tipografía legible."""
    if fig is None:
        return None
    fig.update_layout(
        font=dict(family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size=12, color='#334155'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hoverlabel=dict(
            bgcolor='rgba(15, 23, 42, 0.92)',
            font_size=12,
            font_color='#ffffff',
            bordercolor='rgba(0,0,0,0)'
        ),
    )
    fig.update_xaxes(showgrid=False, linecolor='rgba(148, 163, 184, 0.4)')
    fig.update_yaxes(gridcolor='rgba(148, 163, 184, 0.2)', zeroline=False)
    return fig


def colorear_riesgo(df, columna):
    """Styler que pinta la columna de nivel de riesgo (solo presentación)."""
    def f(v):
        c = FONDO_RIESGO.get(v)
        return f'background-color: {c}; color: #111827; font-weight: 600' if c else ''
    fmt = {c: '{:.2f}' for c in df.select_dtypes('float').columns}
    return df.style.map(f, subset=[columna]).format(fmt)
