# DengueML-UPN: qué hace cada parte y qué tanto cumple el informe

## 1. Flujo completo en una frase

CSV del CDC → **ETL** (cuenta registros por distrito y semana) → **panel** versionado con hash → **características** (rezagos, medias) → **evaluación** por cortes temporales → **modelo** XGBoost publicado (`models/actual.json`) → **dashboard** que lee lo publicado y muestra histórico, estimación y riesgo.

## 2. Parte por parte

| Parte | Archivo | Qué hace | ¿Hace el trabajo? |
|---|---|---|---|
| Configuración | `src/config.py` | Lista los 14 distritos válidos y su nombre en el CSV; lee variables de entorno (sin secretos en el código). | Sí. |
| Calendario | `src/calendar_epi.py` | Semanas epidemiológicas domingo–sábado (semana 1 contiene el 4 de enero). Valida semanas y calcula la siguiente. | Sí; probado. |
| ETL | `src/etl.py`, `src/data_pipeline.py` | Lee el CSV, valida columnas/fechas, filtra 14 distritos y desde 2023, **cuenta filas** por distrito-semana, completa con 0 las semanas sin filas (marcadas `sin_registros_fuente`), guarda `datos.csv` + `metadata.json` con SHA-256. No publica si hay error y conserva la versión anterior. | Sí. Reproduje el panel: mismo hash. |
| Características | `src/features.py` | Para cada distrito: rezagos 1–4, medias móviles de 3 y 4 semanas, crecimiento semanal, mes y trimestre. Solo usa el pasado. | Sí; hay prueba anti-fuga. |
| Modelo y pronóstico | `src/model.py` | Entrena XGBoost y pronostica **recursivamente** (usa su propia predicción para la semana siguiente). Añade reglas: si las 2 últimas semanas son 0, predice 0; valores < 0,5 pasan a 0; si la última semana > 20, limita a 1,3× lo anterior. | Funciona. Ojo: lo publicado es **XGBoost + reglas**, no XGBoost puro; esas reglas no tienen validación independiente (Q-03). |
| Evaluación | `src/validation.py` | Define 3 cortes de validación (SE16, 24, 32) y 4 de prueba (SE36, 40, 44, 48 de 2024), reentrena en cada corte, compara 3 XGBoost con «repetir la última semana», elige con MAE (mejora > 2 % sin empeorar ningún horizonte). | Funciona y no filtra el futuro. Limitación: el bloque de prueba casi no tiene casos. |
| Publicación | `src/train.py` | Ejecuta la evaluación, guarda modelo y resultados en `models/releases/…` y escribe `models/actual.json` como único punto de activación. | Sí. |
| Servicios | `src/services.py` | Comprueba hashes, cachea datos/modelo y calcula la predicción por distrito y horizonte. | Sí. |
| Riesgo | `src/risk.py` | Compara la estimación con la media de las 12 semanas previas: BAJO ≤ 0,8; MEDIO ≤ 1,5; ALTO > 1,5; «Evaluación especial» si la referencia es 0; «Sin datos suficientes» con < 12 semanas. | Calcula bien, pero es **experimental** y poco discriminante hoy. |
| KPI | `src/dashboard.py` | Casos de la última semana, tendencia (con base cero muestra diferencia absoluta), pronóstico por distrito. | Sí. |
| Dashboard | `src/app.py`, `src/charts.py`, `src/calidad_ui.py` | 4 secciones: Resumen, Comparación distrital, Detalle del distrito, Calidad y límites. Avisos de corte, procedencia y definiciones. | Sí. |
| Auditoría | `src/audit.py` | Registra eventos en `logs/audit.log`. | Sí (cobertura total sin auditar). |
| Portabilidad | `iniciar.py`, `empaquetar.py`, `INICIAR_WINDOWS.bat` | Crea entorno, comprueba integridad y abre Streamlit. | Sí (probado con test; no en otro PC). |
| Experimentos | `scripts/`, `reports/experimento_*` | Clima, vacíos 0/1 y provincias, aislados. | No son producción. |
| Legado | `src/app_avance.py`, `src/train_model.py` | Versiones anteriores del primer avance. | No se usan en el flujo actual. |

## 3. ¿Está haciendo el trabajo?

**Sí como sistema:** carga datos reproducibles, calcula, muestra históricos y estimaciones, y las 22 pruebas pasan.
**No demostrado como modelo predictivo:**
* En la prueba hay 5 casos; «siempre cero» (0,089) supera al modelo en h2 (0,130) y h4 (0,103).
* En la validación el modelo mejora a persistencia, pero ese bloque se usó para elegirlo.
* Desde SE33 de 2024 casi no hay casos, así que el modelo se evalúa sobre todo en "quedarse en cero".
* La estimación futura a 2025 sale casi plana (suma ≈ 2–4 casos por semana) por esa misma razón.

## 4. Qué falta para que informe y proyecto estén a la par

| # | Brecha | Qué hacer | Tipo |
|---|---|---|---|
| 1 | El informe ya está corregido en texto y cifras, pero **no lo han leído ni aceptado ustedes** (TA-26 en progreso) | Revisar la copia `…_REVISADO_20261020.docx` y copiarla como versión final | Revisión |
| 2 | Figuras con contenido de semana 6 (Kanban, EDT, Fig. 9-1) y diagramas con la palabra «ZIP» | Regenerarlas o rotularlas como históricas | Documento |
| 3 | Objetivo 3 promete R²; el sistema solo calcula MAE y RMSE | Cambiar el texto del objetivo (propuesta ya redactada en 2.4) **o** calcular R² | Decisión |
| 4 | Objetivo general/2 mencionan clima y demografía; no están en el modelo | Cambiar el texto **o** decidir una evaluación futura congelada del clima | Decisión |
| 5 | KPI-03 «Capacidad de anticipación» no medido | Definir evento (p. ej. aumento > X % sobre la referencia), registrar alertas y medir | Trabajo nuevo |
| 6 | Riesgo sin aval | Revisión con un referente epidemiológico y análisis de sensibilidad | Trabajo nuevo |
| 7 | Validación predictiva independiente | Congelar configuración y comparar en semanas nuevas con persistencia y siempre cero | Trabajo nuevo |
| 8 | Reglas de ceros/amortiguación (en `model.py`) sin validar ni explicar en el informe | Documentarlas y medir su efecto con y sin reglas | Trabajo nuevo |
| 9 | Responsive en tablet/móvil (CA HU-05/CA-005) | Probar y guardar capturas | Prueba |
| 10 | Licencia y fecha de descarga de la fuente | Completar ficha F-01 | Documento |
| 11 | Git: 70+ cambios sin confirmar | Commit y PR | Repositorio |
| 12 | Pruebas de carga, restauración, usabilidad con usuarios; fichas firmadas | Fuera de esta tarea; siguen pendientes | Pendiente |
| 13 | Título con 4 variantes | Se mantuvo el de la portada actual | Cerrado |

Lo que **ya está a la par** (informe = proyecto): 14 distritos, panel 2023–2024 con cifras y hashes, XGBoost moderado publicado, métricas, 4 KPI y sus límites, sin login, 22 pruebas, experimentos como no publicados, burndown 71/110.
