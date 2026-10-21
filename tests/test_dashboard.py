from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_dashboard_publico_predice_y_filtra_automaticamente():
    p = Path(__file__).resolve().parents[1] / 'src/app.py'
    at = AppTest.from_file(str(p), default_timeout=30).run()
    assert not at.exception
    assert not at.error

    # La vista inicial demuestra resultados históricos y no presenta pronósticos como observaciones.
    assert len(at.metric) >= 5
    assert any('Predicciones evaluadas' == m.label for m in at.metric)
    assert any('MAE' == m.label for m in at.metric)

    # Cambia horizonte de proyección a 2 semanas
    at.sidebar.selectbox[1].select(2).run()
    assert not at.exception
    assert not at.error

    # Cambia ventana histórica a 'Últimas 12 semanas'
    at.sidebar.selectbox[0].select('Últimas 12 semanas').run()
    assert not at.exception
    assert not at.error


def test_dashboard_muestra_fuentes_y_descargas_reales():
    p = Path(__file__).resolve().parents[1] / 'src/app.py'
    at = AppTest.from_file(str(p), default_timeout=30).run()
    at.sidebar.radio[0].set_value('Fuentes de datos y transparencia').run()
    assert not at.exception
    assert any('Fuentes de datos y transparencia' in h.value for h in at.header)
    assert {b.label for b in at.download_button} >= {
        'Dataset procesado (CSV)', 'Resultados walk-forward (CSV)'
    }
    at.sidebar.radio[0].set_value('Cómo funciona').run()
    assert not at.exception
    at.sidebar.radio[0].set_value('Comparación real vs. predicho').run()
    assert not at.exception
    assert any('Casos reales frente a predicciones históricas' in h.value for h in at.header)
    at.sidebar.radio[0].set_value('Pronósticos futuros').run()
    assert not at.exception
    assert any('Pronósticos futuros' in h.value for h in at.header)
