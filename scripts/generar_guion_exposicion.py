"""Genera el guion editable desde reportes versionados del proyecto.

Usa python-docx cuando está disponible. Si no se instaló en el entorno aislado,
emite el mismo DOCX con OOXML estándar de la biblioteca estándar de Python.
"""
from __future__ import annotations

import json
import csv
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "entregables" / "Guion_Exposicion_DengueML_UPN.docx"


def leer_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def metricas_y_contenido():
    resumen = leer_json(BASE / "reports/evaluacion_holdout_final.json")
    bundle = leer_json(BASE / "models/actual.json")
    metadata = leer_json(BASE / bundle["metadata"])
    audit = leer_json(BASE / "reports/fuentes_auditadas.json")
    xgb, ganador = resumen["anterior_xgb"], resumen["seleccionado"]
    xgb_name = "XGBoost publicado (evaluado walk-forward)"
    new_name = resumen["modelo_elegido_solo_en_validacion"].capitalize() + " seleccionado en validación"
    rows_model = [
        ["WAPE", f"{xgb['WAPE_pct']:.1f}%", f"{ganador['WAPE_pct']:.1f}%"],
        ["MAE", f"{xgb['MAE']:.2f} casos", f"{ganador['MAE']:.2f} casos"],
        ["RMSE", f"{xgb['RMSE']:.2f} casos", f"{ganador['RMSE']:.2f} casos"],
        ["sMAPE", f"{xgb['sMAPE_pct']:.1f}%", f"{ganador['sMAPE_pct']:.1f}%"],
        ["Predicciones dentro de ±10%", f"{xgb['semanas_error_menor_10_pct']:.1f}%", f"{ganador['semanas_error_menor_10_pct']:.1f}%"],
    ]
    return resumen, bundle, metadata, audit, xgb, ganador, xgb_name, new_name, rows_model


def contenido():
    r, bundle, meta, audit, xgb, ganador, xgb_name, new_name, rows_model = metricas_y_contenido()
    rows_model.insert(0, ["Métrica", xgb_name, new_name])
    n= int(r["n_prueba"])
    semanas=int(r["semanas_prueba"])
    with (BASE / "reports/predicciones_holdout_final.csv").open(encoding="utf-8-sig", newline="") as f:
        last = max((int(row["ano"]), int(row["semana"])) for row in csv.DictReader(f))
    periodo=f"{r['periodo_prueba_desde']} a {last[0]}-SE{last[1]:02d}"
    coverage=meta["cobertura"] if "cobertura" in meta else "2023-SE01 a 2024-SE52"
    data_quality=meta.get("calidad", {})
    nobs=1456-int(data_quality.get("semanas_sin_registros",862))
    xs, ps = xgb["WAPE_pct"], ganador["WAPE_pct"]
    change=(xs-ps)/xs*100 if xs else 0
    source_note=("No se encontró KPI.docx ni archivo Capstone editable/PDF dentro de la carpeta revisada. "
                 "Se respetan los cuatro KPI de docs/fichas_kpis.md y la descripción vigente del código; "
                 "el informe académico original no se modificó.")
    blocks=[]
    def p(text, style="Normal"): blocks.append(("p",style,text))
    def h(text, level=1): blocks.append(("h",f"Heading{level}",text))
    def table(headers, rows): blocks.append(("table",headers,rows))
    def page(): blocks.append(("page",))
    def bullet(text): blocks.append(("p","Bullet",text))

    blocks += [("p","Title","Guion de exposición DengueML-UPN"),
               ("p","Subtitle","Sistema de consulta epidemiológica y evaluación de predicciones semanales"),
               ("p","Normal",f"Guion universitario · DIRIS Lima Centro · {date.today().strftime('%d-%m-%Y')}"),
               ("p","Normal",f"Cobertura local: {coverage} · 14 distritos · archivo procesado {bundle['version']}"),
               ("p","Normal","Lectura principal: la evidencia disponible no demuestra que XGBoost supere a una referencia sencilla; el resultado más favorable en validación fue persistencia. La meta de error menor o igual a 10% no se alcanzó."),
               ("p","Normal",source_note)]
    page()

    h("Resultados que deben comunicarse",1)
    p(f"La evaluación walk-forward comparó {n} predicciones distrito-semana correspondientes a {semanas} semanas epidemiológicas entre {periodo}. El modelo se eligió usando solamente la parte previa, hasta {r['periodo_validacion_hasta']}. La serie local cuenta con {nobs} combinaciones distrito-semana con registros y 862 marcadas sin registros.")
    table(["Resultado en tramo evaluado",xgb_name,new_name],rows_model[1:])
    p(f"Persistencia redujo el WAPE frente a XGBoost en {change:.1f}% en este tramo. Es un resultado retrospectivo exploratorio, no una prueba nueva e independiente: reportes walk-forward anteriores ya incluían semanas de la serie completa. Además, el conjunto evaluado es pequeño y termina en 2024.")
    p("El método seleccionado para la evaluación histórica no reemplazó el modelo publicado para pronósticos futuros. La estimación XGBoost vigente parte del corte 2024-SE52 y no está actualizada con datos posteriores.")

    h("A Introducción",1)
    p("Buenos días. Presentamos DengueML-UPN, un dashboard educativo que consulta registros semanales de dengue en los 14 distritos de DIRIS Lima Centro. El dengue puede producir brotes que exigen vigilancia y coordinación. Anticipar cambios en los registros ayudaría a revisar tendencias y preparar preguntas para la gestión, pero una estimación automática no reemplaza el trabajo epidemiológico.")
    p("El proyecto organiza una serie temporal, ofrece gráficos distritales y compara predicciones históricas con observaciones posteriores. Su valor es hacer visible la evidencia y sus límites. Las cifras representan registros notificados, no una tasa poblacional ni personas necesariamente únicas.")

    h("B Objetivo del sistema",1)
    p("Objetivo general: brindar una consulta y estimación semanal, reproducible y explicable para los 14 distritos de DIRIS Lima Centro, junto con una evaluación temporal del error.")
    p("Objetivos específicos: consolidar los registros por distrito y semana; mostrar la curva histórica; generar estimaciones de corto plazo con XGBoost; contrastar el modelo con referencias simples mediante walk-forward; y exponer procedencia, cobertura y limitaciones.")
    p("El público principal son estudiantes, profesores y personas que necesitan explorar el comportamiento registrado. El beneficio esperado es facilitar la lectura y la explicación de datos, no declarar brotes ni emitir alertas oficiales.")

    h("C Funcionamiento de la página",1)
    steps=[
        "Abre el dashboard desde INICIAR_WINDOWS.bat o con streamlit run src/app.py.",
        "En el menú lateral, entra a Predicciones históricas para evaluar semanas pasadas; elige Comparación real vs. predicho para superponer curvas.",
        "Selecciona distrito, año epidemiológico y semana. La opción Todos los distritos agrega los registros disponibles, pero no convierte semanas ausentes en casos cero.",
        "Lee Casos reales como registros del panel procesado para esa semana y distrito. Un campo sin observación no debe interpretarse como ausencia de transmisión.",
        "Lee Casos predichos como una estimación fuera de muestra, generada entrenando con semanas anteriores al objetivo. Revisa el error absoluto, el error porcentual y el estado del margen ±10%.",
        "En la curva, azul representa observaciones, naranja XGBoost histórico y verde persistencia. Las curvas históricas son evaluaciones retrospectivas; el pronóstico futuro aparece en su sección y no está confirmado.",
        "Consulta Indicadores y evaluación para MAE, RMSE, WAPE, sMAPE y resultados por distrito. El tramo final muestra la comparación congelada para este informe.",
        "En Fuentes de datos y transparencia revisa las instituciones y usa los botones para descargar el panel procesado y los CSV de resultados. Para el CSV original, abre el recurso oficial del MINSA; el original no está guardado dentro del proyecto.",
    ]
    for s in steps: bullet("• " + s)

    h("D KPI e indicadores",1)
    h("D.1 KPI oficiales del proyecto",2)
    p("El repositorio define cuatro KPI oficiales en docs/fichas_kpis.md. No se sustituyen por métricas de aprendizaje automático.")
    table(["KPI oficial · fórmula", "Qué indica", "Ejemplo y lectura favorable"],[
        ["Casos semanales por distrito. Total = suma de registros de la semana.","Magnitud absoluta observada; no es incidencia por habitantes.","8 + 10 + 7 = 25 registros. No existe un número universalmente favorable; se interpreta con territorio y periodo."],
        ["Nivel preliminar de riesgo. Índice = predicción / referencia histórica × 100.","Compara el pronóstico con la media móvil de 12 semanas. Bajo <80%; medio 80–150%; alto >150%; referencia cero puede dar evaluación especial.","60 / 50 ×100 =120%: medio. Menor no equivale a riesgo sanitario validado; los umbrales son experimentales."],
        ["Capacidad de anticipación. Semana del evento − semana de alerta.","Mide cuántas semanas antes habría señalado un evento definido.","Alerta SE20 y pico SE23 = 3 semanas. Más anticipación útil sería mejor, pero el KPI está pendiente de validación empírica."],
        ["Tendencia de casos. (actual − anterior) / anterior ×100.","Cambio relativo entre semanas consecutivas; si el anterior es cero, el porcentaje no se define.","De 40 a 50 = +25% y +10 casos. Un aumento no es favorable; describe dirección y escala."],
    ])
    h("D.2 Métricas técnicas complementarias de Machine Learning",2)
    table(["Métrica · fórmula", "Qué mide e interpretación", "Ejemplo y valor deseable"],[
        ["Casos reales / predichos", "Valor observado y estimación para una combinación distrito-semana.", "Real 60 y estimado 54: diferencia 6 casos. Cuanto menor sea la diferencia, mejor, sin prometer acierto exacto."],
        ["Error absoluto = |real − predicho|", "Distancia en número de casos; evita cancelación de errores.", "|60−54| = 6 casos. Menor es mejor."],
        ["Error porcentual = |real−predicho| / real ×100", "Error relativo; no se define si real = 0 y puede crecer mucho con valores bajos.", "6/60 ×100 = 10%. Menor es mejor; la meta del proyecto es ±10%."],
        ["MAE = promedio(|real−predicho|)", "Error absoluto medio, expresado en casos.", "Errores 2, 2 y 3: MAE=2,33 casos. Menor es mejor."],
        ["RMSE = raíz(promedio((real−predicho)²))", "Error en casos que castiga especialmente los fallos grandes y picos.", "Errores 2, 2 y 3: RMSE=2,24 casos. Menor es mejor."],
        ["WAPE = suma(|real−predicho|) / suma(real) ×100", "Error absoluto ponderado por el volumen total. Evita interpretar porcentajes por semana sin mirar el tamaño de la serie.", "Suma de errores 7 y suma real 60: WAPE=11,7%. Menor es mejor; meta complementaria <10%."],
        ["sMAPE = promedio(200×|real−predicho| / (|real|+|predicho|))", "Error porcentual simétrico; se reporta como porcentaje y requiere tratar real=predicho=0 con valor cero.", "Para 10 vs 12 y 20 vs 18: sMAPE≈14,4%. Menor es mejor."],
        ["Porcentaje dentro de ±10% = predicciones con |error|/real ≤0,10 / predicciones con real>0 ×100", "Proporción de observaciones distrito-semana que cumple el umbral. Los reales cero se excluyen del denominador porcentual.", "Si 8 de 40 predicciones cumplen: 20%. Más alto es mejor; la meta 100% no está demostrada."],
        ["Semanas evaluadas", "Número de semanas con al menos una observación evaluable; se reporta aparte el número de filas distrito-semana.", f"En el tramo: {semanas} semanas y {n} predicciones distrito-semana. Mayor cobertura útil, sin sacrificar calidad."],
    ])
    p("El holdout no tuvo objetivos reales iguales a cero en sus 48 filas. Por ello, el error porcentual se calculó en todas las predicciones evaluadas. Los porcentajes con casos muy bajos siguen siendo inestables y deben leerse junto con el error absoluto.")

    h("E Explicación de XGBoost y validación",1)
    p("XGBoost es un método de aprendizaje automático que construye árboles de decisión en secuencia. Cada árbol aprende a corregir parte de los errores acumulados, y el conjunto produce la estimación. En este proyecto recibe la historia de casos por distrito: rezagos semanales, promedios móviles, cambios recientes y calendario epidemiológico.")
    p("El backtesting walk-forward simula el uso real en fechas pasadas. Para cada semana objetivo, el entrenamiento y las características solo usan datos anteriores. Se predice, se guarda la salida y luego se compara con el dato observado. No se incorporó clima al modelo desplegado; los experimentos climáticos permanecen separados.")
    p("La fuga temporal se evita ordenando por año y semana, creando rezagos dentro de cada distrito y cortando el entrenamiento antes de la semana evaluada. Un valor de una semana posterior no puede actuar como característica o formar parte del entrenamiento de esa predicción. La prueba de regresión comprueba que cambiar la semana objetivo no cambia la predicción generada desde el pasado.")
    p("Las referencias comparadas fueron persistencia (repetir el último dato), media móvil, XGBoost directo, XGBoost con objetivo logarítmico, una variante regularizada y Poisson. Se eligió el método por MAE en validación temporal anterior. Persistencia ganó; por eso no se afirma que optimizar XGBoost haya conseguido el objetivo.")

    h("F Resultados reales del proyecto",1)
    table(["Métrica",xgb_name,new_name],rows_model[1:])
    p(f"Periodo de validación: hasta {r['periodo_validacion_hasta']}. Periodo de evaluación: desde {r['periodo_prueba_desde']}, {semanas} semanas con {n} predicciones distrito-semana. El método escogido en validación fue {r['modelo_elegido_solo_en_validacion']}.")
    p(f"En estas observaciones, persistencia bajó MAE de {xgb['MAE']:.2f} a {ganador['MAE']:.2f} casos y WAPE de {xgb['WAPE_pct']:.1f}% a {ganador['WAPE_pct']:.1f}%. La proporción dentro de ±10% fue {ganador['semanas_error_menor_10_pct']:.1f}% para persistencia y {xgb['semanas_error_menor_10_pct']:.1f}% para XGBoost. La meta no se alcanzó.")
    worst=r["errores_mayores"][0]
    p(f"El mayor error absoluto del método elegido fue {worst['error_absoluto_seleccionado']:.0f} casos en {worst['distrito']}, {worst['ano']}-SE{worst['semana']:02d}. Los errores relativos son particularmente altos en distritos-semanas con pocos casos.")
    p("Limitaciones: serie local integrada 2023–2024, solo 594 combinaciones con registros y 862 sin filas; el archivo raw no está disponible localmente. La auditoría encontró microdatos MINSA/CDC publicados hasta 2024, un observatorio CDC con consulta semanal distrital hasta 2026-SE35, una sala diaria hasta 20-10-2026 y boletines DIRIS 2025–2026. No se descargaron ni integraron: la conexión de red local fue rechazada y los cortes, formatos y definiciones requieren conciliación. Pocas semanas permiten evaluar los 14 distritos. Los resultados no son un test virgen: evaluaciones walk-forward previas ya habían utilizado toda la serie. Se requiere protocolo congelado y datos nuevos para confirmar generalización.")

    h("Fuentes oficiales y disponibilidad",2)
    table(["Fuente", "Cobertura y uso", "Estado local"],[
        ["MINSA / CDC Perú · Vigilancia Epidemiológica de dengue · datosabiertos.gob.pe", "Fuente pública 2000–2024; modificación indicada 17-12-2025; licencia ODC Attribution.", "Panel local 2023–2024; CSV original no está archivado. Recurso enlazado en el dashboard."],
        ["CDC Perú · Observatorio de Clima y Salud", "Selector 2018–2026; serie semanal detallada por departamento, provincia y distrito; corte 2026-SE35 (05-09-2026).", "Descarga anunciada por el portal; no obtenida desde este entorno. No integrada."],
        ["CDC Perú · Sala Situacional Diaria", "Indicadores diarios al 20-10-2026 08:00; confirma/probable; ofrece indicadores por distrito.", "DIRIS Lima Centro: 1.450 agregados, 1.340 confirmados y 110 probables; cifra de corte, no serie semanal, no integrada."],
        ["DIRIS Lima Centro · Dengue 2024", "Boletines PDF semanales hasta SE52; publicación 23-12-2024.", "Fuente de contexto; no agregada a la serie para evitar mezclar cortes/definiciones."],
        ["DIRIS Lima Centro · Dengue 2025", "PDF semanales hasta SE53; publicación 29-12-2025.", "No integrado; cortes sucesivos en PDF."],
        ["DIRIS Lima Centro · Boletines Epidemiológicos 2026", "PDF semanales visibles hasta SE29 en ficha revisada (31-07-2026).", "No integrado; requiere extracción y conciliación."],
    ])
    p("URLs oficiales: https://www.datosabiertos.gob.pe/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue · https://app7.dge.gob.pe/maps/clima-salud/ · https://app7.dge.gob.pe/maps2/sala_diaria_dengue.html · https://www.gob.pe/institucion/dirislimacentro/informes-publicaciones/7824541-dengue-2024 · https://www.gob.pe/institucion/dirislimacentro/informes-publicaciones/7825010-dengue-2025 · https://www.gob.pe/institucion/dirislimacentro/informes-publicaciones/7636617-boletines-epidemiologicos-2026")

    page()
    h("G Guion oral para exposición de 5 a 7 minutos",1)
    h("1. Presentación e introducción · 40 segundos",2)
    p("Buenos días. Somos el equipo de DengueML-UPN. Presentamos una herramienta educativa para explorar casos notificados de dengue y revisar estimaciones semanales en 14 distritos de DIRIS Lima Centro. El sistema busca facilitar la lectura de los datos y demostrar cómo se evalúa una predicción. No es un sistema de diagnóstico ni una alerta oficial.")
    h("2. Problema y objetivos · 45 segundos",2)
    p("El dengue cambia en el tiempo y entre distritos. Si solo vemos una cifra aislada, perdemos la tendencia. Nuestro objetivo fue consolidar registros por semana, presentar su evolución y probar XGBoost con validación temporal. También comparamos el modelo con reglas sencillas, porque un modelo complejo solo es útil si generaliza mejor.")
    h("3. Funcionamiento del dashboard · 55 segundos",2)
    p("Ahora observamos la pantalla de inicio: el periodo local llega a 2024-SE52. El menú permite explorar predicciones históricas, comparar curvas, revisar indicadores, consultar pronósticos futuros y abrir las fuentes. La cobertura es de 14 distritos. Las semanas sin filas se identifican como sin registros; no las interpretamos como cero transmisión.")
    h("4. Demostración de una predicción histórica · 60 segundos",2)
    p("Ahora seleccionamos la sección de predicciones históricas. Elegimos el año, la semana epidemiológica y el distrito. El valor real corresponde al registro observado posteriormente. La predicción de walk-forward se construyó usando solo semanas anteriores. En la curva, azul representa lo observado y naranja la predicción histórica de XGBoost. La línea verde muestra persistencia. El error absoluto expresa casos; el porcentual no se calcula si el valor real es cero.")
    h("5. KPI y métricas · 50 segundos",2)
    p("Los cuatro KPI oficiales son casos semanales, nivel preliminar de riesgo, capacidad de anticipación y tendencia. Riesgo y anticipación tienen límites importantes: el riesgo es experimental y la anticipación todavía no está validada ante brotes definidos. Para medir el modelo usamos MAE, RMSE, WAPE, sMAPE y la proporción dentro de diez por ciento. MAE indica el error medio en casos; WAPE resume el error relativo global.")
    h("6. Resultados obtenidos · 55 segundos",2)
    p(f"En el tramo evaluado, que contiene {n} predicciones de {semanas} semanas, persistencia fue elegida en la validación anterior. Su WAPE fue {ganador['WAPE_pct']:.1f}%, frente a {xgb['WAPE_pct']:.1f}% para XGBoost; el MAE fue {ganador['MAE']:.2f} frente a {xgb['MAE']:.2f} casos. Solo {ganador['semanas_error_menor_10_pct']:.1f}% de sus predicciones quedó dentro de diez por ciento. Por tanto, no alcanzamos la meta y no afirmamos superioridad general. El tramo ya había aparecido en reportes anteriores, así que lo presentamos como evidencia retrospectiva, no como una prueba virgen.")
    h("7. Conclusiones · 35 segundos",2)
    p("El dashboard funciona como herramienta de consulta y evaluación, pero los resultados muestran que XGBoost todavía no supera a persistencia de forma convincente. Faltan más datos compatibles, validación en semanas nuevas y evaluación epidemiológica del indicador de riesgo. Gracias; podemos revisar una semana o una métrica del sistema.")

    h("H Preguntas posibles del profesor",1)
    qa=[
        ("¿Por qué utilizar XGBoost?","Porque puede aprender relaciones no lineales entre rezagos y calendario, ofrece un modelo reproducible y es apropiado para datos tabulares. Eso no significa que siempre venza a una regla simple."),
        ("¿De dónde salen los datos?","El panel local atribuye su origen a vigilancia MINSA/CDC y cubre 2023–2024. La auditoría encontró fuentes oficiales hasta 2026, pero el archivo original nacional y los cortes recientes no están archivados ni integrados en el proyecto."),
        ("¿Qué significa un error del 10%?","Que la diferencia absoluta representa como máximo 10% del valor real. Si el real es 50, el margen es 5 casos. Con real cero, el porcentaje no se define."),
        ("¿Cómo comprueban que funciona?","Con walk-forward: cada objetivo se pronostica usando solo semanas previas, y después se compara con lo observado. También se contrasta con persistencia y otras referencias."),
        ("¿Qué pasa si faltan datos?","La semana aparece sin registros y se excluye cuando no se puede formar historia válida. No inventamos cero ni imputamos un caso para evaluar."),
        ("¿Qué diferencia hay entre predicción histórica y futura?","La histórica ya tiene un real para compararse; la futura aún no puede verificarse y se origina en el corte 2024-SE52."),
        ("¿Cómo evitan que el modelo conozca resultados futuros?","Se ordena la serie, se entrena solo con fechas anteriores y los rezagos se construyen dentro del distrito con información pasada. Hay pruebas de consistencia temporal."),
        ("¿Qué significa MAE?","Es el promedio de la diferencia absoluta entre la predicción y el valor real, expresada en casos. No es porcentaje de acierto."),
        ("¿Cuáles son las limitaciones?","Cobertura escasa e incompleta, periodo local corto, original no archivado, pocas evaluaciones y ausencia de una validación completamente nueva. Riesgo experimental y anticipación pendiente."),
        ("¿Qué mejoras siguen?","Conseguir una serie oficial semanal más larga y comparable; congelar un protocolo; validar en semanas futuras; evaluar riesgo con especialistas y solo sumar clima si existe una variable disponible en el momento de predecir."),
        ("¿Ya se alcanzó menos de 10% de error?","No. En el tramo reportado, el método elegido quedó dentro del margen en 16,7% de las predicciones distrito-semana."),
        ("¿Se puede tratar como alerta de salud?","No. Es una herramienta educativa y sus etiquetas de riesgo no han sido calibradas como alertas sanitarias oficiales."),
    ]
    for q,a in qa:
        h(q,3); p(a)
    h("Referencias de implementación",1)
    p("Código y métricas: src/app.py, src/model.py, src/backtesting.py, src/model_benchmark.py, reports/evaluacion_holdout_final.json, reports/predicciones_holdout_final.csv y reports/fuentes_auditadas.json. KPI: docs/fichas_kpis.md. No se alteró el informe Capstone.")
    return blocks


def build_with_python_docx(blocks, output):
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc=Document()
    sec=doc.sections[0]
    sec.top_margin=Inches(.68); sec.bottom_margin=Inches(.68)
    sec.left_margin=Inches(.75); sec.right_margin=Inches(.75)
    normal=doc.styles['Normal']; normal.font.name='Aptos'; normal.font.size=Pt(9.5); normal.font.color.rgb=RGBColor(31,41,55)
    normal.paragraph_format.space_after=Pt(5)
    for name,size in [('Title',27),('Heading 1',17),('Heading 2',12),('Heading 3',10)]:
        s=doc.styles[name]; s.font.name='Aptos Display'; s.font.size=Pt(size); s.font.bold=True; s.font.color.rgb=RGBColor(0,0,0)
    for block in blocks:
        if block[0]=='page': doc.add_page_break()
        elif block[0]=='p': doc.add_paragraph(block[2],style='List Bullet' if block[1]=='Bullet' else block[1])
        elif block[0]=='h': doc.add_paragraph(block[2],style=block[1])
        elif block[0]=='table':
            headers, rows=block[1],block[2]
            tb=doc.add_table(rows=1, cols=len(headers)); tb.alignment=WD_TABLE_ALIGNMENT.CENTER; tb.style='Table Grid'
            for i,text in enumerate(headers):
                cell=tb.rows[0].cells[i]; cell.text=text; cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),'123B5D'); cell._tc.get_or_add_tcPr().append(shd)
                for run in cell.paragraphs[0].runs: run.font.bold=True; run.font.color.rgb=RGBColor(255,255,255); run.font.size=Pt(8)
            for row in rows:
                cells=tb.add_row().cells
                for i,text in enumerate(row):
                    cells[i].text=str(text); cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.TOP
                    for para in cells[i].paragraphs:
                        para.paragraph_format.space_after=Pt(2)
                        for run in para.runs: run.font.name='Aptos'; run.font.size=Pt(7.7)
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run('DengueML-UPN · Guion de exposición  |  ')
    fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); footer._p.append(fld)
    doc.save(output)


def _xml_text(text):
    return escape(str(text)).replace("\n"," ")


def _paragraph(text, style="Normal", pagebreak=False):
    run=f'<w:r><w:t xml:space="preserve">{_xml_text(text)}</w:t></w:r>' if text else ''
    if pagebreak: run='<w:r><w:br w:type="page"/></w:r>'
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>{run}</w:p>'


def _table(headers, rows):
    all_rows=[headers]+rows
    col_width=10080//len(headers)
    s=['<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>']
    for edge in ('top','left','bottom','right','insideH','insideV'):
        s.append(f'<w:{edge} w:val="single" w:sz="4" w:color="CBD5E1"/>')
    s.append('</w:tblBorders><w:tblCellMar><w:top w:w="85" w:type="dxa"/><w:start w:w="90" w:type="dxa"/><w:bottom w:w="85" w:type="dxa"/><w:end w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>')
    s.extend(f'<w:gridCol w:w="{col_width}"/>' for _ in headers)
    s.append('</w:tblGrid>')
    for ri,row in enumerate(all_rows):
        s.append('<w:tr>')
        if ri==0: s.append('<w:trPr><w:tblHeader/></w:trPr>')
        for value in row:
            fill='123B5D' if ri==0 else ('F1F5F9' if ri%2==0 else 'FFFFFF')
            color='FFFFFF' if ri==0 else '1F2937'
            s.append(f'<w:tc><w:tcPr><w:shd w:fill="{fill}"/><w:tcW w:w="{col_width}" w:type="dxa"/></w:tcPr>')
            s.append(f'<w:p><w:pPr><w:spacing w:after="40"/></w:pPr><w:r><w:rPr><w:color w:val="{color}"/><w:sz w:val="16"/>{"<w:b/>" if ri==0 else ""}</w:rPr><w:t xml:space="preserve">{_xml_text(value)}</w:t></w:r></w:p></w:tc>')
        s.append('</w:tr>')
    s.append('</w:tbl>')
    return ''.join(s)


def build_ooxml(blocks, output):
    body=[]
    for item in blocks:
        if item[0]=='p': body.append(_paragraph(item[2],item[1]))
        elif item[0]=='h': body.append(_paragraph(item[2],item[1]))
        elif item[0]=='table': body.append(_table(item[1],item[2]))
        elif item[0]=='page': body.append(_paragraph('',pagebreak=True))
    sect='<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="980" w:right="1080" w:bottom="980" w:left="1080" w:header="450" w:footer="450" w:gutter="0"/></w:sectPr>'
    document=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{''.join(body)}{sect}</w:body></w:document>'''
    styles='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="19"/><w:color w:val="1F2937"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="280" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:sz w:val="54"/><w:color w:val="000000"/></w:rPr><w:pPr><w:spacing w:after="180"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:rPr><w:sz w:val="28"/><w:color w:val="334155"/></w:rPr><w:pPr><w:spacing w:after="220"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="250" w:after="100"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:sz w:val="34"/><w:color w:val="000000"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="180" w:after="70"/></w:pPr><w:rPr><w:b/><w:sz w:val="25"/><w:color w:val="000000"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="90" w:after="30"/></w:pPr><w:rPr><w:b/><w:sz w:val="21"/><w:color w:val="000000"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Bullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360"/><w:contextualSpacing/></w:pPr></w:style></w:styles>'''
    content_types='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'''
    root_rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''
    doc_rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
    core=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Guion de exposición DengueML-UPN</dc:title><dc:subject>Evaluación y demostración del sistema DengueML-UPN</dc:subject><dc:creator>Equipo DengueML-UPN</dc:creator><cp:keywords>epidemiología, dengue, XGBoost, validación temporal</cp:keywords></cp:coreProperties>'''
    app='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Word</Application></Properties>'''
    with ZipFile(output,'w',ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',content_types)
        z.writestr('_rels/.rels',root_rels)
        z.writestr('word/document.xml',document)
        z.writestr('word/styles.xml',styles)
        z.writestr('word/_rels/document.xml.rels',doc_rels)
        z.writestr('docProps/core.xml',core)
        z.writestr('docProps/app.xml',app)


def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    blocks=contenido()
    try:
        import docx  # noqa: F401
    except ImportError:
        build_ooxml(blocks,OUT)
        print(f"DOCX creado con OOXML estándar (python-docx no está instalado): {OUT}")
    else:
        build_with_python_docx(blocks,OUT)
        print(f"DOCX creado con python-docx: {OUT}")


if __name__=='__main__':
    main()
