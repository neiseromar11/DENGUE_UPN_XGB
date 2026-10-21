# DengueML-UPN: revisión de coherencia (20/10/2026)

**Archivos revisados:** `Informe_Capstone_DengueML.docx` (20/10 23:35, 16,8 MB) y `BURNDOWN_DengueML.xlsx` (20/10 23:48). Son las únicas versiones con esos nombres dentro de `KAWSAY MARKET`; los informes anteriores (`Informe_Integral…T2`, `entrega_T2/`) son versiones previas y no se editaron.
**Copias revisadas:** `Informe_Capstone_DengueML_REVISADO_20261020.docx` y `BURNDOWN_DengueML_REVISADO_20261020.xlsx`. Originales en `respaldo_revision_20261020/`.
**Evidencia usada:** `models/actual.json` (xgb_moderado, corte 2024-SE52, panel 2023–2024; SHA-256 de datos y modelo coinciden), `pytest` (22 aprobadas), ETL reproducido en carpeta temporal (mismo SHA-256 del panel), `evaluacion.json`/`test.csv`, informes de los tres experimentos, navegador y AppTest.

## Hallazgo principal

El bloque de prueba de la versión publicada contiene **5 casos en 56 observaciones por horizonte** (92–93 % de ceros). Allí «siempre cero» (MAE 0,0893) supera al modelo en los horizontes 2 (0,1296) y 4 (0,1034) y solo pierde en el 3 (0,0717). Las «reducciones» de 19–55 % del informe frente a persistencia no son evidencia de que XGBoost sea mejor. El bloque de validación (SE16–SE32, con casos) da una ventaja moderada, pero se usó para elegir el modelo. El informe quedó corregido; la validación predictiva independiente sigue pendiente.

## Matriz de coherencia

Estados: **IC** implementado y comprobado · **IV** implementado con validación pendiente · **EXP** experimental · **PLAN** planificado · **NI** no implementado.

| Afirmación o requisito | Evidencia real | Estado | Inconsistencia | Corrección propuesta / aplicada |
|---|---|---|---|---|
| Alcance: 14 distritos DIRIS Lima Centro | `config.py`; panel 14×104; test del ETL | IC | Informe 2.5 decía periodo 2020-2026 | Aplicada: 2023-SE01 a 2024-SE52 |
| Panel y trazabilidad (SHA-256) | ETL reproducido → mismo hash `06a1e001…`; `actual.json` coincide | IC | Informe decía «no recalculado» | Aplicada |
| Fuente = casos confirmados | Responsable lo identifica; el CSV solo tiene tipo de dengue (3 categorías) | IV | Informe 2.6.1 hablaba de «confirmados y probables» | Aplicada: se atribuye a la revisión del responsable; no se inventa verificación |
| Cada fila = un registro; sin deduplicar | 2 256 coincidencias conservadas | IC | Informe 2.10.1 y CA HU-02/CA-001 pedían eliminar duplicados | Aplicada; CA queda «por reformular» |
| Ceros = ausencia de filas (862) | `metadata.json` | IC | — | Reforzada en informe y dashboard |
| Procedencia (URL, licencia, descarga) | `fuente_oficial.json`: URL, tamaño y ETag; falta licencia y fecha de descarga | IV | Informe F-01 decía «pendiente» sin matiz | Aplicada; licencia pendiente |
| Modelo publicado xgb_moderado | `actual.json`, `modelo.json` | IC | README decía «quedó seleccionado el baseline» | Aplicada en README (nota vigente) |
| «XGBoost mejora a persistencia» | Test: 5 casos; siempre-cero gana en h2 y h4; validación: ventaja moderada no independiente | IV | Informe 9.4 mostraba reducciones 19–55 % y 41 % | Aplicada: columnas reemplazadas, lectura prudente, Fig. 9-2 regenerada |
| MAE como precisión | `calidad_ui.py` ya lo aclara | IC | Informe lo mezclaba en «reducción» | Aplicada |
| R², MAE y RMSE (objetivo 3, pregunta 3) | `evaluacion.json` solo tiene MAE y RMSE | NI (R²) | Objetivo promete R² | Nota de coherencia 2.4 con redacción propuesta (no se cambió el texto original) |
| Fuentes complementarias / clima / demografía | No están en el modelo; solo experimentos | NI / EXP | Objetivo general y 2.10 las daban por integradas | Aplicada: texto aclarado; TA-05 sigue pendiente |
| Tasas de incidencia | No hay denominador | NI | Informe 2.10.2 listaba «cálculo de tasas» | Aplicada: marcado no implementado |
| KPI-01 casos semanales | `indicadores()`; 3 casos en SE52 | IC | «Cálculo real no reproducido» | Aplicada |
| KPI-02 nivel de riesgo | `risk.py` (0,8/1,5, 12 sem.) | IV | Sin calibración; 2025-SE01: 8 «Evaluación especial», 5 BAJO, 1 ALTO (2,34 casos) | Aplicada: indicador relativo experimental; pendiente aval |
| KPI-03 capacidad de anticipación | UI muestra «Pendiente de estimación» + horizonte | NI (medición) | Q-01 decía que mostraba el horizonte | Q-01 cerrada en UI; medición pendiente (no se sustituye por semanas proyectadas) |
| KPI-04 tendencia | `indicadores()`: base cero → diferencia absoluta | IC | Q-02 y manual decían 100 %/0 % | Aplicada; falta prueba unitaria específica |
| Horizonte 2–4 ≠ anticipación | App y guía lo dicen | IC | Informe 5.5.3.2 lo trataba como beneficio logrado | Aplicada |
| Estimaciones parten de 2024-SE52 | Aviso en app; 2025-SE01..04 | IC | — | Informe 7.4.3 lo documenta |
| Dashboard 4 vistas y filtros | AppTest y 4 vistas ejecutadas; navegador en escritorio | IC (escritorio) | Informe describía «Vista Global/Distrital» | Aplicada |
| Responsive multidispositivo | Sin prueba; ficha 5.1 decía «Cumple… cuatro resoluciones» | IV | Contradice CA HU-05/CA-005 | Aplicada: ficha pasa a autoevaluación; responsive «pendiente» |
| Ficha «validación» con conformidad | Evaluador = integrante del equipo, sin firma | — | Parecía validación independiente | Aplicada: «autoevaluación (no validación independiente)» |
| Instrumentos validados por expertos | No hay fichas firmadas | PLAN | — | Se mantiene «pendiente»; no se inventó nada |
| Sin login, usuarios ni roles | Código público | IC | Informe 6.3 y CA HU-06/CA-005 exigían RBAC; SECURITY.md lo planificaba | Aplicada: «excluido del alcance» en informe, SECURITY.md y Excel |
| Pruebas | 22 aprobadas hoy (14,8 s) | IC | Informe decía 18 (sin Streamlit) y 22 | Aplicada: 22 |
| Carga/estrés, restauración, usabilidad | Sin ejecutar | PLAN | — | Fuera de esta tarea; siguen pendientes |
| Experimento clima v3 | MAE 5,9681→4,7808 (−19,89 %); sensibilidad 82,40→80,58 % | EXP | Riesgo de leerse como mejora del producto | Nueva sección 9.6; no publicado |
| Experimento vacíos 0/1 | 15,9034 vs 15,6473 (567 obs.) | EXP | — | Sección 9.6 |
| Piloto provincial | XGB 31,8534 vs persistencia 27,1227; gana 22/110 | EXP | — | Sección 9.6; alcance no cambia |
| Burndown S1 | Histórico 55/21/34 | IV | Semanas S1 sin actas | Conservado; marcado «requiere actas» |
| Burndown S2 | Ideal/escenario/real | IV | «Desviación» comparaba escenario con ideal, no real; ideal dependía de `ROW()`; 36 pendientes escrito a mano; hoja «13 CONTROL REAL S2» y «06 RUBRICA T2» citadas no existían | Corregido en la copia (hoja 04, 08) |
| TA-26 y TA-27 «Hecho/Por hacer» | Alineación del informe aún no aceptada; KPI solo corregidos en UI | — | Parciales no acreditan | Ambas pasan a «En progreso»: **71/110, 39 pendientes** (antes 74/36) |
| Esfuerzo real | No existe ningún registro de horas | — | El burndown es de puntos estimados | Declarado en hojas 01, 08 y 10; no se inventaron horas ni fechas |
| Título | Cuatro variantes (T1 «predicción de incidencia y riesgo»; T2 «predictivo… en los 14 distritos»; informe «sistema web… por distrito»; app/README) | — | «Incidencia» contradice no usar población | No se cambió; ver pregunta abierta |

## Observaciones pendientes (no resueltas en esta revisión)

1. **Título.** Se recomienda: «Sistema web basado en XGBoost para la estimación semanal de casos de dengue y la clasificación preliminar del nivel de riesgo en los 14 distritos de DIRIS Lima Centro». Requiere decisión del equipo/docente.
2. **Figuras con contenido de semana 6** (Kanban del corte 1, EDT, Fig. 9-1 «pendiente de reejecución») y diagramas 7-1/7-4 que hablan de «ZIP»: no se regeneraron. Los textos que las acompañan están rotulados como históricos.
3. **Citas.** Se conservaron las del informe. No se verificó el boletín CDC Perú 2026 (SE25) ni la cifra «14 a 21 días de desfase» atribuida a él; conviene que el equipo la confirme o la retire. No se añadieron fuentes nuevas.
4. **Repositorio.** Hay 70 cambios sin confirmar (código, modelos, experimentos); el informe cita «commit/PR» como evidencia. Falta confirmar y subir.
5. **Revisión visual.** Solo escritorio (1400 px) y en el navegador integrado; no se probó tablet/móvil. El navegador se agotó al comprobar el último cambio de la vista Calidad (se verificó con AppTest).
6. **Riesgo experimental.** Con baja incidencia clasifica 8 de 14 distritos como «Evaluación especial» y asigna ALTO a 2,34 casos. No se cambiaron umbrales (requiere decisión con evidencia).
7. **Declaración de IA y fichas de instrumentos:** siguen pendientes de completar por el equipo.
8. **Los puntos de la hoja 09 del Excel no tienen estimación**; el equipo debe estimarlos antes de que entren al burndown.

## Cambios en el código (reversibles)

* `src/calidad_ui.py`: se añadió la métrica «Error de siempre cero» y la línea «casos registrados en las observaciones evaluadas» (respaldo: `respaldo_revision_20261020/calidad_ui.py.antes`).
* `README.md` y `SECURITY.md`: notas de estado vigente (respaldos `.antes`).
* No se tocó la lógica predictiva, los umbrales, `models/actual.json`, datos ni modelos. 22 pruebas aprobadas después del cambio.
