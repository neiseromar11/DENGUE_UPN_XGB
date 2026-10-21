import pandas as pd

from src.update_data import _consolidar_por_ubigeo


def test_update_usa_ubigeo_y_conserva_casos_duplicados_exactos():
    raw = pd.DataFrame([
        {"departamento":"OTRO", "provincia":"OTRA", "distrito":"nombre erróneo", "ano":2023, "semana":1, "ubigeo":"150132", "tipo_dx":"C"},
        {"departamento":"LIMA", "provincia":"LIMA", "distrito":"nombre erróneo", "ano":2023, "semana":1, "ubigeo":"150132", "tipo_dx":"C"},
        {"departamento":"LIMA", "provincia":"LIMA", "distrito":"San Luis", "ano":2023, "semana":1, "ubigeo":"150134", "tipo_dx":"P"},
    ])
    out, _ = _consolidar_por_ubigeo(raw)
    sl = out[(out.ano == 2023) & (out.semana == 1)].set_index("distrito")
    assert sl.loc["San Juan de Lurigancho", "casos_notificados"] == 2
    assert sl.loc["San Luis", "casos_notificados"] == 1
    assert bool(sl.loc["Miraflores", "sin_registros_fuente"])
