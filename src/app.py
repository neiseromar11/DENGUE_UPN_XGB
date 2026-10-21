"""
Sistema predictivo basado en XGBoost para la estimación semanal de casos de dengue
y la clasificación preliminar del nivel de riesgo en los 14 distritos de la DIRIS Lima Centro.

Dashboard público e informativo: sin autenticación, usuarios ni roles.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st
from config import DISTRITOS_VALIDOS
from calidad_ui import mostrar_calidad
from etl import BASE
from dashboard import filtrar, indicadores
from services import leer_bundle, preparar_version, leer_json_version, predecir_version
from charts import (barras_acumulado_distrital, barras_pronostico_semana,
                    heatmap_distrital, comparador_distritos,
                    curva_historico_pronostico, resumen_riesgo_distrital,
                    estilizar, colorear_riesgo)
from backtesting import metricas_backtest
from model_benchmark import load_benchmark, comparar_metricas, comparar_por_grupo
from transparency import FUENTES, archivos_exportables

# ── Configuración ───────────────────────────────────────────
st.set_page_config(page_title='DengueML - DIRIS Lima Centro',
                   page_icon='🦟', layout='wide',
                   initial_sidebar_state='expanded')

st.markdown("""
<style>
.stApp {background: #0b1120; color: #e5e7eb;}
[data-testid="stAppViewContainer"] {background: radial-gradient(ellipse at 50% 0%, #172554 0%, #0b1120 52%);}
[data-testid="stHeader"] {background: rgba(11,17,32,.82);}
[data-testid="stSidebar"] {background: #101827; border-right: 1px solid rgba(148,163,184,.16);}
.block-container {max-width: 1480px; padding-top: 1.35rem; padding-bottom: 3rem;}
h1, h2, h3, p, label {color: #e5e7eb;}
h1 {letter-spacing: -.03em; font-weight: 700;}
h2, h3 {letter-spacing: -.02em; font-weight: 600; margin-top: 1.1rem; margin-bottom: 0.4rem;}

/* Hero Banner */
.hero {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
  color: #ffffff;
  border-radius: 16px;
  padding: 26px 30px;
  margin-bottom: 14px;
  box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.hero small {letter-spacing: .12em; text-transform: uppercase; opacity: .85; font-weight: 700; font-size: 0.78rem;}
.hero h1 {color: #ffffff; margin: 6px 0 8px 0; padding: 0; font-size: clamp(1.6rem, 2.8vw, 2.2rem); font-weight: 800;}
.hero p {margin: 0 0 16px 0; opacity: .92; max-width: 62rem; font-size: 0.98rem; line-height: 1.5;}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.26);
  backdrop-filter: blur(8px);
  border-radius: 999px;
  padding: 5px 14px;
  margin: 0 8px 8px 0;
  font-size: .84rem;
  font-weight: 500;
  color: #ffffff;
}

/* Metric Cards Layout & Visuals */
[data-testid="stHorizontalBlock"] {flex-wrap: wrap; gap: .85rem;}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width: 210px; flex: 1 1 210px;}

[data-testid="stMetric"] {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: var(--secondary-background-color);
  border-radius: 14px;
  padding: 16px 20px;
  min-height: 125px;
  box-shadow: 0 2px 6px -1px rgba(15, 23, 42, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px -2px rgba(15, 23, 42, 0.08);
}
[data-testid="stMetricLabel"] {font-weight: 600; font-size: 0.88rem; letter-spacing: .01em; color: var(--text-color); opacity: 0.85;}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
  font-size: clamp(1.15rem, 1.8vw, 1.6rem);
  font-weight: 700;
  white-space: normal;
  overflow: visible;
  line-height: 1.25;
}
[data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * {
  white-space: normal;
  overflow: visible;
  line-height: 1.35;
  font-size: 0.84rem;
}

/* Colored accent borders for the 4 KPI cards */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) [data-testid="stMetric"] { border-left: 5px solid #2563eb; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] { border-left: 5px solid #7c3aed; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] { border-left: 5px solid #059669; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] { border-left: 5px solid #0284c7; }

/* Plotly, expanders, tables */
[data-testid="stPlotlyChart"] {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.15);
  background: var(--secondary-background-color);
  padding: 8px 8px 2px 8px;
}
[data-testid="stExpander"] {border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.25);}
[data-testid="stDataFrame"] {border-radius: 12px; overflow: hidden;}
[data-testid="stAlert"] {border-radius: 12px;}
[data-testid="stSidebar"] h2 {font-size: 1.15rem;}
[data-testid="stRadio"] {padding: .6rem 0;}
.stButton > button, .stLinkButton > a, [data-testid="stDownloadButton"] button {border-radius: 10px; border: 1px solid #475569; background: linear-gradient(135deg,#1d4ed8,#2563eb); color: white; font-weight: 650; min-height: 2.65rem; transition: transform .15s ease, filter .15s ease;}
.stButton > button:hover, .stLinkButton > a:hover, [data-testid="stDownloadButton"] button:hover {filter: brightness(1.12); transform: translateY(-1px); border-color: #93c5fd;}
[data-testid="stMetric"] {background: rgba(17,24,39,.82); border-color: rgba(148,163,184,.22);}
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {background: rgba(15,23,42,.65);}
@media (max-width: 720px) { .block-container {padding: .9rem .8rem 2rem;} [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width: 145px;} .hero {padding: 20px 18px;} }
</style>
""", unsafe_allow_html=True)

# ── Datos y modelo ──────────────────────────────────────────
try:
    bundle = leer_bundle()
    datos, _ = preparar_version(str(BASE / bundle['datos']), bundle['sha256_datos'])
    evaluacion = leer_json_version(str(BASE / bundle['evaluacion']), bundle['version'])
except (OSError, ValueError, KeyError):
    st.error('No hay una versión operativa válida. Se requiere completar el ETL y la validación.')
    st.stop()

CORTE_SE = bundle['corte']       # e.g. "2024-SE52"
DISTRITOS_14 = sorted(DISTRITOS_VALIDOS[:-1])  # sin "Todos los distritos ..."

# ── Barra lateral ───────────────────────────────────────────
st.sidebar.header('⚙️ Parámetros de consulta')
periodo = st.sidebar.selectbox(
    'Periodo histórico visible',
    ['Todo el histórico', 'Últimas 12 semanas'], index=0,
    help='Controla los gráficos y resúmenes históricos. No modifica el pronóstico.')
horizonte = st.sidebar.selectbox(
    'Horizonte de estimación', [2, 3, 4], index=2,
    format_func=lambda n: f'{n} semanas',
    help='Controla cuántas semanas futuras se estiman.')

st.sidebar.markdown('---')
st.sidebar.markdown('**Cobertura:** 14 distritos de DIRIS Lima Centro')
st.sidebar.caption(f'Método activo: {bundle["metodo"]}')
st.sidebar.caption(f'Versión: {bundle["version"][:20]}…')
st.sidebar.caption(f'Corte histórico: {CORTE_SE}')

# ── Datos filtrados (para vistas globales) ──────────────────
ultimas_n = 12 if periodo == 'Últimas 12 semanas' else None
hist_global = filtrar(datos, None, ultimas_n)
periodo_label = 'Últimas 12 semanas' if ultimas_n else f'{datos.semana_epidemiologica.min()} a {CORTE_SE}'

secciones = {
    'Inicio y objetivo': 'Resumen',
    'Predicciones históricas': 'Evaluación histórica',
    'Comparación real vs. predicho': 'Comparación distrital',
    'Indicadores y evaluación': 'Calidad y límites',
    'Pronósticos futuros': 'Detalle del distrito',
    'Fuentes de datos y transparencia': 'Fuentes de datos y transparencia',
    'Cómo funciona': 'Cómo funciona',
}
seccion = st.sidebar.radio('Sección', list(secciones), index=1)
vista = secciones[seccion]
distrito_sel = st.sidebar.selectbox('Distrito', DISTRITOS_14, key='distrito_detalle') if vista == 'Detalle del distrito' else None

# La caché del servicio incluye versión, distrito y horizonte.
try:
    resultado_global = predecir_version(bundle, distrito_sel, horizonte)
except (OSError, ValueError, KeyError):
    st.error('No se pudo cargar el pronóstico de esta versión de datos.')
    st.stop()
if resultado_global.empty:
    st.info('No hay estimaciones disponibles para esta versión.')
    st.stop()
semanas_futuras = sorted(resultado_global.semana_epidemiologica.unique())
modelo_label = 'Persistencia' if bundle['metodo'] == 'baseline' else 'XGBoost'

# ── Encabezado ──────────────────────────────────────────────
st.markdown(
    f'''<div class="hero"><small>DENGUEML · OBSERVATORIO DISTRITAL</small>
<h1>Dengue: evolución y pronóstico</h1>
<p>Estimación semanal de casos registrados y clasificación preliminar del nivel de riesgo · 14 distritos de DIRIS Lima Centro.
Sistema informativo: no es diagnóstico médico ni alerta sanitaria oficial.</p>
<span class="chip">📊 Fuente: CDC Perú / MINSA (Datos Abiertos)</span>
<span class="chip">📍 Última semana observada: {CORTE_SE}</span>
<span class="chip">🔮 Estimación: {semanas_futuras[0]} a {semanas_futuras[-1]}</span>
<span class="chip">🧠 Modelo: {modelo_label}</span></div>''', unsafe_allow_html=True)

st.warning(f'Esta versión tiene corte en {CORTE_SE}. Las estimaciones parten de ese corte histórico; '
           'no representan un pronóstico actualizado a la fecha de consulta.')
st.info('La evaluacion walk-forward selecciona persistencia como campeon por MAE; el XGBoost del pronostico futuro es la version heredada y no supera al baseline. En 2024-SE52 solo 2 de 14 distritos tienen registro observado, por lo que los pronosticos futuros heredados son exploratorios.')

# ══════════════════════════════════════════════════════════════
#  PESTAÑAS
# ══════════════════════════════════════════════════════════════
st.caption(f'VISTA: {vista.upper()} · ÁMBITO: {distrito_sel or "14 distritos de Lima Centro"}')
with st.expander('Cómo leer este dashboard'):
    st.markdown('**1. Histórico:** registros disponibles hasta la fecha de corte. '
                '**2. Estimación:** cantidad esperada después del corte, no un dato observado. '
                '**3. Calidad:** error histórico frente a referencias sencillas. '
                '**4. Riesgo:** indicador relativo experimental, no diagnóstico ni alerta oficial.')
    st.caption('Una estimación decimal representa un valor esperado, no una fracción de persona. '
               'No se muestran intervalos porque todavía no se ha validado su cobertura.')
if vista == 'Calidad y límites':
    mostrar_calidad(BASE, bundle, DISTRITOS_14)

if vista == 'Fuentes de datos y transparencia':
    st.header('Fuentes de datos y transparencia')
    st.caption('Separamos el origen del panel local de las fuentes oficiales consultadas que todavía no forman parte del entrenamiento.')
    for fuente in FUENTES:
        with st.container(border=True):
            st.subheader(fuente['nombre'])
            st.markdown(f"**Institución:** {fuente['institucion']}  ·  **Años:** {fuente['anios']}")
            st.markdown(f"**Actualización:** {fuente['actualizacion']}")
            st.markdown(f"**Licencia:** {fuente['licencia']}")
            st.write(fuente['descripcion'])
            st.info(fuente['estado'])
            st.link_button('Abrir fuente oficial', fuente['url'], use_container_width=False)
    cobertura_path = BASE / 'reports/cobertura_disponibilidad_2020_2026.json'
    if cobertura_path.is_file():
        cobertura = json.loads(cobertura_path.read_text(encoding='utf-8'))
        st.markdown('#### Cobertura por año · disponibilidad no equivale a integración')
        filas = []
        for anio in range(2020, 2027):
            filas.append({
                'Año': anio,
                'Integrado al modelo': 'Sí' if cobertura['integrado_en_modelo'][str(anio)] else 'No',
                'Disponibilidad verificada': (
                    'MINSA/CDC, microdatos públicos hasta 2024' if anio <= 2024 else
                    'DIRIS PDF / CDC Observatorio semanal' if anio == 2025 else
                    'CDC Observatorio hasta SE35; sala diaria al 20-oct'
                ),
            })
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
        st.caption(cobertura['cobertura_local']['advertencia'])
    st.markdown('#### Descargas del proyecto')
    st.caption(f"Versión local {bundle['version']} · cobertura {datos.semana_epidemiologica.min()} a {CORTE_SE} · 14 distritos. El CSV original de 2000–2024 no está archivado aquí; usa el enlace oficial del MINSA para obtenerlo.")
    tipos_mime = {'.csv': 'text/csv', '.json': 'application/json',
                  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
    for nombre, ruta in archivos_exportables(BASE, bundle).items():
        st.download_button(nombre, data=ruta.read_bytes(), file_name=ruta.name,
                           mime=tipos_mime.get(ruta.suffix.lower(), 'application/octet-stream'),
                           key=f'download_{ruta.name}', use_container_width=True)
    if cobertura_path.is_file():
        st.download_button('Manifiesto de cobertura 2020–2026', data=cobertura_path.read_bytes(),
                           file_name=cobertura_path.name, mime='application/json', key='download_coverage_manifest')
    st.markdown('#### Reglas de lectura')
    st.markdown('- Los casos del panel son **registros notificados**, no una tasa de incidencia ni necesariamente personas únicas.\n'
                '- Las 862 combinaciones distrito-semana marcadas sin registros se excluyen del backtest; no significan cero transmisión.\n'
                '- Los boletines DIRIS y el portal DGE se presentan como fuentes de contraste y consulta. No se agregaron a la serie porque su formato, corte o definición no fue conciliado con el CSV semanal del MINSA.')

if vista == 'Cómo funciona':
    st.header('Cómo funciona DengueML-UPN')
    st.write('El sistema transforma registros epidemiológicos semanales en una consulta histórica y una estimación exploratoria. Está dirigido a estudiantes, docentes y equipos que revisan tendencias; no reemplaza la vigilancia oficial ni el criterio sanitario.')
    with st.expander('1 · Datos y características', expanded=True):
        st.write('El panel consolida el periodo 2023–2024 para 14 distritos. Para cada distrito y semana evaluable construye rezagos de casos, promedios móviles y características de calendario. Los rezagos se calculan solo con semanas anteriores y no se rellena cobertura desconocida con casos inventados.')
    with st.expander('2 · XGBoost y el pronóstico futuro'):
        st.write('XGBoost combina muchos árboles pequeños. Cada árbol corrige parte del error que dejaron los anteriores; el conjunto produce una estimación semanal. La versión publicada entrena con datos disponibles hasta 2024-SE52 y proyecta semanas posteriores. Por eso sus resultados futuros no son observaciones actuales y requieren datos recientes para actualizarse.')
    with st.expander('3 · Predicciones históricas y control de fuga'):
        st.write('En walk-forward, se toma una semana como objetivo, se entrena únicamente con semanas previas y se compara la estimación con el registro observado. Las características usan rezagos anteriores. Las semanas sin fuente o sin historia suficiente se excluyen y se identifican como no evaluables.')
    with st.expander('Clima como factor epidemiologico'):
        st.write('Temperatura, humedad y lluvia pueden favorecer condiciones para el mosquito y cambiar el riesgo de transmision, con retrasos de varias semanas. Son factores de riesgo, no causas unicas ni una prediccion determinista. El experimento usa unicamente clima de semanas anteriores; aun no demuestra mejora consistente y por eso no reemplaza el modelo activo.')
    with st.expander('4 · Cómo leer el error'):
        st.write('Error absoluto = |real − predicho|. Error porcentual = error absoluto / real × 100; no se define cuando real = 0. MAE resume el error absoluto medio; RMSE penaliza más los fallos grandes; WAPE divide la suma de errores absolutos entre la suma de casos reales; sMAPE usa una escala simétrica. El objetivo ±10 % es una meta, no una precisión garantizada.')
    with st.expander('5 · Riesgo y límites'):
        st.write('El nivel de riesgo compara la estimación con el promedio histórico reciente de 12 semanas y aplica umbrales experimentales. No es un canal endémico oficial ni una alerta validada. La capacidad de anticipación de brotes sigue pendiente de evaluación empírica.')
    st.info('El mejor resultado walk-forward observado fue persistencia, no XGBoost. El pronóstico publicado se conserva como referencia heredada; la evidencia disponible no permite afirmar que XGBoost supere de forma general a una regla sencilla.')

if vista == 'Evaluación histórica':
    st.header('Predicciones históricas verificables')
    st.caption('Walk-forward de un paso: cada semana se predice con un modelo ajustado solo con semanas anteriores. Las semanas sin registros se excluyen, nunca se convierten en cero.')
    try:
        bt = load_benchmark(BASE, datos, bundle['version'])
    except (ValueError, KeyError) as exc:
        st.error(f'No se pudo construir la evaluación: {exc}')
        bt = pd.DataFrame()
    if bt.empty:
        st.warning('Predicción no evaluable: la cobertura no aporta suficientes semanas observadas consecutivas para formar lags y 20 ejemplos previos para entrenar.')
        st.caption('En esta versión, 862 de 1.456 combinaciones distrito-semana están marcadas sin registros. No se imputan para fabricar una evaluación.')
    else:
        clima_json = BASE / "reports/evaluacion_clima_walk_forward.json"
        clima_csv = BASE / "reports/predicciones_clima_walk_forward.csv"
        if clima_json.is_file() and clima_csv.is_file():
            clima_result = json.loads(clima_json.read_text(encoding="utf-8"))
            clima_pred = pd.read_csv(clima_csv)
            st.subheader("Casos observados y predicciones con clima")
            st.caption("El grafico compara casos semanales con XGBoost sin clima y con clima observado de semanas anteriores.")
            val = clima_result["validacion_2023_2024"]
            final = clima_result["prueba_final_2025_2026"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Validacion sin clima", f"{val['sin_clima']['WAPE_pct']:.1f}% WAPE")
            c2.metric("Validacion con clima", f"{val['con_clima']['WAPE_pct']:.1f}% WAPE")
            c3.metric("Prueba final sin clima", f"{final['sin_clima']['WAPE_pct']:.1f}% WAPE")
            c4.metric("Prueba final con clima", f"{final['con_clima']['WAPE_pct']:.1f}% WAPE")
            st.info("El clima mejora en esta prueba final, pero no en la validacion previa; por rigor, el candidato climatico aun no reemplaza al modelo activo.")
            curva_clima = clima_pred.groupby("semana_epidemiologica", as_index=False).agg(
                real=("real", "sum"), sin_clima=("prediccion_sin_clima", "sum"),
                con_clima=("prediccion_con_clima", "sum"))
            import plotly.graph_objects as go
            fig_clima = go.Figure()
            fig_clima.add_trace(go.Scatter(x=curva_clima.semana_epidemiologica, y=curva_clima.real,
                name="Casos observados", mode="lines+markers", line=dict(color="#3b82f6", width=3)))
            fig_clima.add_trace(go.Scatter(x=curva_clima.semana_epidemiologica, y=curva_clima.sin_clima,
                name="XGBoost sin clima", mode="lines+markers", line=dict(color="#a78bfa", dash="dot")))
            fig_clima.add_trace(go.Scatter(x=curva_clima.semana_epidemiologica, y=curva_clima.con_clima,
                name="XGBoost con clima", mode="lines+markers", line=dict(color="#f59e0b", dash="dash")))
            fig_clima.update_layout(template="plotly_dark", height=370, hovermode="x unified",
                margin=dict(l=15, r=15, t=15, b=15), xaxis_title="Semana epidemiologica",
                yaxis_title="Casos de dengue")
            st.plotly_chart(fig_clima, use_container_width=True)
            st.caption(f"Prueba final {int(clima_pred.ano.min())}-{int(clima_pred.ano.max())}: {len(clima_pred)} distrito-semanas con casos explicitos. Semanas vacias no se cuentan como cero.")
            st.subheader("Evaluacion del modelo con clima (prueba final)")
            elegido = final["con_clima"]
            e1, e2, e3, e4, e5 = st.columns(5)
            e1.metric("Predicciones evaluadas", f"{elegido['n']}")
            e2.metric("MAE", f"{elegido['MAE']:.2f} casos")
            e3.metric("RMSE", f"{elegido['RMSE']:.2f} casos")
            e4.metric("WAPE", f"{elegido['WAPE_pct']:.1f}%")
            e5.metric("Dentro de +/-10%", f"{elegido['dentro_10_pct']:.1f}%")
            st.caption("Metricas del candidato con clima en la prueba final 2025-2026. Aunque mejora en esta prueba, no reemplaza al modelo activo porque no supero la validacion previa.")
            with st.expander("Descargar resultados del experimento climatico", expanded=False):
                st.download_button("Predicciones con y sin clima (CSV)", clima_csv.read_bytes(),
                    file_name=clima_csv.name, mime="text/csv", key="download_climate_bt")

    # ──────────────────────────────────────────────────────────────
#  TAB 1: RESUMEN
# ──────────────────────────────────────────────────────────────
if vista == 'Resumen':
    st.header('Inicio y objetivo del sistema')
    st.write('DengueML-UPN organiza registros semanales de dengue y ofrece estimaciones exploratorias para apoyar el aprendizaje y la revisión de tendencias en los 14 distritos de DIRIS Lima Centro. Su objetivo es facilitar la consulta y evaluar el modelo con evidencia temporal; no sustituye la vigilancia epidemiológica oficial.')
    kpi_global = indicadores(hist_global)

    # ── Los 4 KPI (agregado de 14 distritos) ─────────────
    st.subheader('Indicadores clave · Agregado de 14 distritos')
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            '1. Casos semanales',
            f'{kpi_global["ultima"]:,} casos',
            help=(f'Casos registrados en la última semana observada ({CORTE_SE}). '
                  'Conteo absoluto; no es tasa de incidencia (sin denominador poblacional).'))

    with c2:
        # Vista global: mostrar conteo de distritos por nivel de riesgo
        sem1 = semanas_futuras[0]
        r1 = resultado_global[resultado_global.semana_epidemiologica == sem1]
        niveles_conteo = r1.riesgo_relativo.value_counts()
        resumen_txt = ' · '.join(f'{n}: {c}' for n, c in niveles_conteo.items())
        st.metric('2. Riesgo distrital', f'{len(r1)} distritos',
                  help=(f'Distribución de los 14 distritos por nivel de riesgo '
                        f'para la primera semana estimada ({sem1}). '
                        'Clasificación experimental: BAJO (≤80%), MEDIO (>80–150%), ALTO (>150%) '
                        'respecto a la media de las últimas 12 semanas. '
                        'No constituye una alerta sanitaria oficial.'))
        st.caption(f'{resumen_txt} (semana {sem1})')

    with c3:
        st.metric('3. Anticipación',
                  'Pendiente de estimación',
                  delta=f'Horizonte: {horizonte} sem. (parámetro)',
                  delta_color='off',
                  help=('El horizonte de proyección (2-4 semanas) es un parámetro del modelo. '
                        'La capacidad real de anticipación requiere medición retrospectiva '
                        'frente a eventos definidos, aún no realizada.'))

    with c4:
        if kpi_global['tendencia_pct'] is not None:
            st.metric('4. Tendencia de casos',
                      kpi_global['tendencia_texto'],
                      delta=f'{kpi_global["diferencia_absoluta"]:+d} casos vs sem. anterior',
                      delta_color='inverse' if kpi_global['diferencia_absoluta'] else 'off',
                      help=('Variación porcentual: (Casos actuales − Casos anteriores) / '
                            'Casos anteriores × 100. Última semana observada del periodo visible.'))
        else:
            st.metric('4. Tendencia de casos',
                      kpi_global['tendencia_texto'],
                      delta=f'{kpi_global["diferencia_absoluta"]:+d} casos (ref. anterior = 0)',
                      delta_color='off',
                      help=('Porcentaje no calculable: la semana anterior registró 0 casos. '
                            'Se muestra la diferencia absoluta.'))

    st.markdown('---')

    # ── Curva histórica + pronóstico ─────────────────────
    st.subheader('Curva epidemiológica: observado vs. estimación futura')
    hist_s = hist_global.groupby('semana_epidemiologica').casos_notificados.sum()
    hist_s = hist_s.mask(hist_global.groupby('semana_epidemiologica').sin_registros_fuente.all())
    pred_s = resultado_global.groupby('semana_epidemiologica').prediccion.sum()
    fig_curva = curva_historico_pronostico(
        hist_s, pred_s, CORTE_SE,
        titulo=f'14 distritos agregados · {periodo_label}')
    st.plotly_chart(estilizar(fig_curva), use_container_width=True)
    st.caption(
        '**Línea sólida azul:** casos registrados observados (fuente oficial). '
        f'**Línea discontinua ámbar:** estimación {modelo_label}. '
        '**Línea punteada gris:** corte entre datos históricos y proyección. '
        'En la vista global, los valores son la suma de los 14 distritos.')

    # ── Barras acumuladas por distrito ───────────────────
    st.subheader('Casos acumulados por distrito')
    fig_barras = barras_acumulado_distrital(hist_global, periodo_label)
    st.plotly_chart(estilizar(fig_barras), use_container_width=True)
    st.caption('Conteo absoluto de casos registrados acumulados en el periodo visible. '
               'Los 14 distritos se muestran aunque tengan 0 casos. '
               'Gris = sin registros en la fuente (no equivale a confirmación de cero transmisión).')

    # ── Riesgo por distrito para una semana seleccionada ─
    st.subheader('Distribución de riesgo por distrito')
    sem_riesgo = st.selectbox('Semana estimada a evaluar', semanas_futuras,
                               index=0, key='sem_riesgo_resumen')
    resumen_r, tabla_r = resumen_riesgo_distrital(resultado_global, sem_riesgo)
    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        st.dataframe(colorear_riesgo(resumen_r[['Nivel de riesgo', 'Distritos']], 'Nivel de riesgo'), hide_index=True)
    with col_r2:
        st.dataframe(colorear_riesgo(tabla_r, 'Nivel'), hide_index=True)
    st.caption(
        'Clasificación experimental por distrito para la semana seleccionada. '
        'BAJO: ≤80% de la referencia. MEDIO: >80% y ≤150%. ALTO: >150%. '
        '"Evaluación especial": referencia histórica igual a 0. '
        '"Sin datos suficientes": menos de 12 semanas de historia. '
        'No constituye una alerta sanitaria oficial.')

    # ── Tabla de predicciones ────────────────────────────
    with st.expander('Tabla completa de estimaciones'):
        cols_tabla = ['distrito', 'semana_epidemiologica', 'horizonte',
                      'prediccion', 'riesgo_relativo', 'umbral_referencia', 'explicacion']
        st.dataframe(resultado_global[cols_tabla], hide_index=True)
        csv_dl = resultado_global[cols_tabla].to_csv(index=False).encode('utf-8-sig')
        st.download_button('📥 Descargar CSV', csv_dl,
                          f'estimaciones_DIRIS_{CORTE_SE}.csv', 'text/csv')


# ──────────────────────────────────────────────────────────────
#  TAB 2: COMPARACIÓN DISTRITAL
# ──────────────────────────────────────────────────────────────
if vista == 'Comparación distrital':
    st.header('Casos reales frente a predicciones históricas')
    st.caption('Curvas calculadas con los mismos resultados out-of-sample que aparecen en la tabla; no incluye pronósticos posteriores al corte.')
    comparacion_bt = load_benchmark(BASE, datos, bundle['version'])
    if not comparacion_bt.empty:
        bc1, bc2 = st.columns(2)
        distritos_comp = ['Todos los distritos'] + sorted(comparacion_bt.distrito.unique().tolist())
        distrito_comp = bc1.selectbox('Distrito para la curva', distritos_comp, key='comparacion_bt_distrito')
        anios_comp = sorted(comparacion_bt.ano.unique().tolist())
        anio_comp = bc2.selectbox('Año para la curva', anios_comp, index=len(anios_comp)-1, key='comparacion_bt_anio')
        parte = comparacion_bt[comparacion_bt.ano.eq(anio_comp)]
        if distrito_comp != 'Todos los distritos':
            parte = parte[parte.distrito.eq(distrito_comp)]
        curva_bt = parte.groupby('semana_epidemiologica', as_index=False).agg(
            real=('real','sum'), xgb=('prediccion_xgb','sum'), seleccion=('prediccion','sum'))
        import plotly.graph_objects as go
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=curva_bt.semana_epidemiologica, y=curva_bt.real, name='Casos reales', mode='lines+markers', line=dict(color='#60a5fa',width=3)))
        fig_bt.add_trace(go.Scatter(x=curva_bt.semana_epidemiologica, y=curva_bt.xgb, name='XGBoost histórico', mode='lines+markers', line=dict(color='#fb923c',width=2,dash='dash')))
        fig_bt.add_trace(go.Scatter(x=curva_bt.semana_epidemiologica, y=curva_bt.seleccion, name='Persistencia', mode='lines+markers', line=dict(color='#34d399',width=2,dash='dot')))
        fig_bt.update_layout(template='plotly_dark', height=410, hovermode='x unified', xaxis_title='Semana epidemiológica', yaxis_title='Registros', margin=dict(l=15,r=15,t=15,b=15))
        st.plotly_chart(fig_bt, use_container_width=True, key='comparacion_oos_plot')
        st.dataframe(parte[['ano','semana','distrito','real','prediccion_xgb','prediccion','error_pct','estado']], hide_index=True, use_container_width=True)
        st.download_button('Descargar comparación histórica (CSV)', parte.to_csv(index=False).encode('utf-8-sig'), 'comparacion_historica_dengueml.csv', 'text/csv', key='download_comparison_oos')
    st.subheader('Mapa de calor: distritos × semanas')
    fig_heat = heatmap_distrital(hist_global, periodo_label)
    st.plotly_chart(estilizar(fig_heat), use_container_width=True)
    st.caption('Color = casos registrados por semana. Escala azul = registros observados; gris = sin registros. '
               '"Sin registros" = la semana no tiene datos en la fuente oficial.')

    st.markdown('---')

    st.subheader('Comparación de pronósticos por distrito (semana individual)')
    sem_comp = st.selectbox('Semana futura a comparar', semanas_futuras,
                             index=0, key='sem_comp_tab2')
    fig_comp = barras_pronostico_semana(resultado_global, sem_comp)
    if fig_comp:
        st.plotly_chart(estilizar(fig_comp), use_container_width=True)
        st.caption(
            f'Estimación para la semana {sem_comp} únicamente (no acumulado). '
            'Color = nivel de riesgo: 🟢 Bajo, 🟡 Medio, 🔴 Alto, 🟣 Evaluación especial.')
    else:
        st.info('No hay estimaciones para la semana seleccionada.')

    st.markdown('---')

    st.subheader('Comparador de curvas históricas')
    distritos_comp = st.multiselect(
        'Selecciona entre 2 y 4 distritos',
        DISTRITOS_14, default=DISTRITOS_14[:2],
        max_selections=4, key='comp_multi')
    if len(distritos_comp) >= 2:
        fig_cmp = comparador_distritos(hist_global, distritos_comp)
        if fig_cmp:
            st.plotly_chart(estilizar(fig_cmp), use_container_width=True)
            st.caption('Curvas históricas en el mismo periodo. Las interrupciones indican semanas sin registros en la fuente; no se interpolan.')
    elif len(distritos_comp) == 1:
        st.warning('Selecciona al menos 2 distritos para comparar.')
    else:
        st.info('Selecciona distritos en el menú superior.')

# ──────────────────────────────────────────────────────────────
#  TAB 3: DETALLE DEL DISTRITO
# ──────────────────────────────────────────────────────────────
if vista == 'Detalle del distrito':

    st.header('Pronósticos futuros · estimaciones aún no verificables')
    st.warning(f"Este pronóstico se origina en el corte {CORTE_SE}; no está actualizado con reportes posteriores. Solo podrá verificarse cuando existan observaciones compatibles para las semanas proyectadas.")
    st.caption(f"Método publicado: {modelo_label}. Las evaluaciones walk-forward muestran mejor resultado de persistencia; el pronóstico futuro XGBoost se mantiene como referencia exploratoria.")

    hist_dist = filtrar(datos, distrito_sel, ultimas_n)
    kpi_dist = indicadores(hist_dist)

    # Predicción distrital (reutiliza caché global)
    res_dist = resultado_global[resultado_global.distrito == distrito_sel].copy()

    # ── KPI distritales ──────────────────────────────────
    st.subheader(f'Indicadores clave · {distrito_sel}')
    d1, d2, d3, d4 = st.columns(4)

    with d1:
        st.metric('1. Casos semanales',
                  f'{kpi_dist["ultima"]:,} casos',
                  help=f'Casos registrados en la última semana observada ({CORTE_SE}) '
                       f'para {distrito_sel}. Conteo absoluto.')

    with d2:
        if not res_dist.empty:
            fila1 = res_dist.iloc[0]
            indice = fila1['indice_riesgo']
            st.metric('2. Nivel de riesgo',
                      fila1['riesgo_relativo'],
                      delta=f'Índice: {indice} (Ref: {fila1["umbral_referencia"]})',
                      delta_color='off',
                      help=f'Riesgo para {distrito_sel} en {fila1["semana_epidemiologica"]}. '
                           'Clasificación experimental.')
        else:
            st.metric('2. Nivel de riesgo', 'No disponible')

    with d3:
        st.metric('3. Anticipación',
                  'Pendiente de estimación',
                  delta=f'Horizonte: {horizonte} sem.',
                  delta_color='off',
                  help='Medición retrospectiva aún no realizada para este distrito.')

    with d4:
        if kpi_dist['tendencia_pct'] is not None:
            st.metric('4. Tendencia',
                      kpi_dist['tendencia_texto'],
                      delta=f'{kpi_dist["diferencia_absoluta"]:+d} casos',
                      delta_color='inverse',
                      help=f'Variación en la última semana observada de {distrito_sel}.')
        else:
            st.metric('4. Tendencia',
                      kpi_dist['tendencia_texto'],
                      delta=f'{kpi_dist["diferencia_absoluta"]:+d} casos',
                      delta_color='off',
                      help='Porcentaje no calculable (referencia anterior = 0).')

    st.markdown('---')

    # ── Curva distrital ──────────────────────────────────
    st.subheader(f'Curva epidemiológica · {distrito_sel}')
    hist_d_s = hist_dist.groupby('semana_epidemiologica').casos_notificados.sum()
    hist_d_s = hist_d_s.mask(
        hist_dist.groupby('semana_epidemiologica').sin_registros_fuente.all())
    pred_d_s = res_dist.groupby('semana_epidemiologica').prediccion.sum()
    fig_dist = curva_historico_pronostico(
        hist_d_s, pred_d_s, CORTE_SE,
        titulo=f'{distrito_sel} · {periodo_label}')
    st.plotly_chart(estilizar(fig_dist), use_container_width=True)
    st.caption(
        f'Casos registrados observados y estimación {modelo_label} para {distrito_sel}. '
        f'Las predicciones parten de {CORTE_SE}, no de la fecha actual.')

    # ── Tabla distrital ──────────────────────────────────
    st.subheader(f'Estimaciones semanales · {distrito_sel}')
    cols_det = ['semana_epidemiologica', 'horizonte', 'prediccion',
                'riesgo_relativo', 'umbral_referencia', 'explicacion']
    st.dataframe(colorear_riesgo(res_dist[cols_det], 'riesgo_relativo'), hide_index=True)

    # ── Resumen histórico ────────────────────────────────
    with st.expander(f'Resumen histórico · {distrito_sel}'):
        st.write(f'**Total acumulado en el periodo visible:** {kpi_dist["total"]:,} casos')
        st.write(f'**Semanas incluidas:** {kpi_dist["semanas"]}')
        st.write(f'**Semanas con 0 casos:** {kpi_dist["semanas_sin_registros"]}')
        st.write(f'**Semanas sin registros en fuente:** {kpi_dist["combinaciones_sin_registros"]}')


# ══════════════════════════════════════════════════════════════
#  SECCIONES DESPLEGABLES COMUNES (fuera de las pestañas)
# ══════════════════════════════════════════════════════════════
st.markdown('---')

with st.expander('🏛️ Procedencia de datos y metodología'):
    fuente_path = BASE / 'reports/fuente_oficial.json'
    if fuente_path.exists():
        try:
            info = json.loads(fuente_path.read_text(encoding='utf-8'))
            st.write(f'**Entidad:** {info.get("entidad")}')
            st.write(f'**Plataforma:** {info.get("fuente")}')
            st.write(f'**Sincronización:** {info.get("estado_sincronizacion")}')
            st.write(f'**SHA-256:** `{info.get("sha256_local")}`')
            st.caption(info.get('notas_metodologicas', ''))
        except Exception:
            pass
    st.write(f'**Versión activa:** `{bundle["version"]}`')
    st.write(
        '**Variable analizada:** Casos registrados semanales de dengue (registros Notiweb / CDC Perú). '
        'El responsable del proyecto identifica la fuente como casos confirmados. '
        'Esta condición procede de su revisión de la fuente; no se verifica mediante un campo de confirmación en el CSV. '
        'La versión activa conserva su procesamiento y no se ha mezclado con la base climática.')
    st.write(
        '**Clasificación de riesgo:** Experimental, basada en umbrales sobre la media móvil '
        'de 12 semanas. BAJO: ratio ≤ 0.8. MEDIO: ratio > 0.8 y ≤ 1.5. ALTO: ratio > 1.5. '
        'No sustituye al canal endémico del CDC Perú.')
