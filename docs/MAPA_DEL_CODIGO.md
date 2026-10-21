# Dónde está cada parte de DengueML UPN

El programa ejecutable está en `src/`. El archivo `DengueML_UPN_dashboard.html` es una maqueta anterior: editarlo no cambia el dashboard de Streamlit. La aplicación es pública y no contiene cuentas, login ni roles de acceso.

## Recorrido para entender o sustentar el sistema

1. `src/etl.py` recibe y valida un histórico completo. `src/data_pipeline.py` lo transforma en conteos por distrito y semana.
2. `src/features.py` construye las variables que utilizará XGBoost, sin incorporar información futura.
3. `src/validation.py` compara candidatos y baseline en cortes temporales. `src/model.py` entrena XGBoost y calcula sus proyecciones recursivas.
4. `src/train.py` guarda los resultados y activa datos y método conjuntamente mediante `models/actual.json`.
5. `src/app.py` muestra la interfaz. Solicita datos y predicciones a `src/services.py`, que reutiliza cálculos mediante caché.
6. `src/dashboard.py` aplica filtros, calcula KPI y pronostica los distritos solicitados. Cada proyección recibe un indicador de `src/risk.py`.

El entrenamiento ocurre durante el mantenimiento. Abrir el dashboard no vuelve a entrenar XGBoost. La publicación incluida selecciona el baseline porque los candidatos no cumplieron el criterio completo de mejora.

## Pantalla y comportamiento visible

| Lo que se ve o se hace | Archivo y punto del código | Qué hace |
|---|---|---|
| Título y distribución de pantalla | `src/app.py`: `st.set_page_config`, `st.title` | Configura página y textos principales. |
| Vista Global o Distrital | `src/app.py`: `st.sidebar.radio`, `selectbox` | Usa `distrito=None` para los 14; en vista distrital envía solamente el seleccionado. |
| Periodo histórico visible | `src/dashboard.py`: `filtrar` | Restringe filas por distrito y, opcionalmente, últimas 12 semanas. No cambia el corte del pronóstico. |
| Tarjetas KPI | `src/dashboard.py`: `indicadores`; `src/app.py`: `cols[].metric` | Agrupa por semana; calcula total, última semana, cantidad de semanas y semanas con suma cero. |
| Gráfico histórico y futuro | `src/app.py`: `hist`, `pred`, `st.line_chart` | Suma los distritos seleccionados por semana y presenta las dos series. |
| Horizonte 2, 3 o 4 | `src/app.py`: selector `horizonte`; `src/dashboard.py`: `pronosticar` | Genera pasos desde la última semana disponible. El gráfico no es una predicción desde la fecha actual. |
| Tabla de predicciones y riesgo | `src/dashboard.py`: `pronosticar`; `src/risk.py`: `evaluar_riesgo` | Calcula pronóstico y referencia de las últimas 12 semanas por distrito. |
| Descargar CSV | `src/app.py`: `st.download_button` | Exporta exactamente el resultado de la selección. |
| Tabla MAE y RMSE | `src/app.py`: `leer_test`; `src/validation.py`: `metricas` | Lee el bloque reservado y calcula métricas del distrito y horizontes seleccionados. |
| Información de versión y corte | `src/app.py`; `models/actual.json` | Muestra la publicación activa, su método y el corte del histórico. |

## Datos y actualización

| Archivo / función | Explicación |
|---|---|
| `src/etl.py`: `validar_fuente` | Comprueba columnas obligatorias, nulos, enteros y semanas válidas. Rechaza datos inválidos. |
| `src/etl.py`: `actualizar_datos` | Lee CSV, aplica periodo explícito si se solicita, calcula huellas SHA-256 y crea una versión inmutable. No concatena casos sin identificador. |
| `src/data_pipeline.py`: `preparar_datos` | Normaliza nombres, selecciona el ámbito territorial, agrupa registros y completa el calendario. Los ceros representan ausencia de registros en la fuente. |
| `src/calendar_epi.py`: `fecha_semana`, `siguiente_semana` | Define el calendario epidemiológico y los cambios de año. |
| `src/config.py` | Contiene el catálogo de los 14 distritos y equivalencias de nombres. |
| `src/train.py`: `publicar` | Comprueba la huella, evalúa métodos, guarda artefactos y cambia el puntero activo al finalizar. |
| `src/etl.py`: `guardar_json` | Escribe primero un temporal y reemplaza el archivo de forma atómica. Evita publicar JSON incompleto. |

`data/versions/<versión>/datos.csv` contiene el panel preparado. `metadata.json` conserva fecha de creación, corte, calidad y huellas. `models/releases/<versión>/` guarda evaluación, predicciones de validación/test y, cuando corresponde, el modelo. No modificar estos archivos a mano: publicar una nueva versión.

## Modelo y evaluación

- `src/features.py`, `generar_features`: rezagos de 1 a 4 semanas, medias móviles de 3 y 4 semanas, crecimiento, mes y trimestre. Las medias se desplazan antes de calcularse para no utilizar el objetivo de la misma fila.
- `src/model.py`, `entrenar_xgboost`: configura y ajusta el regresor. `guardar_modelo` / `cargar_modelo` usan el formato del modelo XGBoost. `predecir_multistep` incorpora sus predicciones al avanzar, sin leer los valores futuros reales.
- `src/validation.py`, `CANDIDATOS`: hiperparámetros a comparar. `plan_cortes` separa selección y prueba reservada; `evaluar_cortes` entrena con el pasado y evalúa los 14 distritos.
- `metricas` calcula MAE y RMSE. `elegir_modelo` exige mejora media superior al 2% en horizontes 2–4 y que ninguno empeore frente al baseline. `validar_modelos` coordina selección y comprobación final.
- Si XGBoost no cumple, `dashboard.pronosticar` repite el último conteo observado. No debe describirse como una predicción XGBoost activa en ese caso.

Para cambiar la búsqueda se edita `CANDIDATOS` y se vuelve a ejecutar el flujo de publicación. No ajustar hiperparámetros repetidamente observando el mismo test: se perdería la independencia de la evaluación.

## Riesgo y rendimiento

`src/risk.py` contiene `Umbrales` y `evaluar_riesgo`. Se validan umbrales y entradas finitas/no negativas. Menos de 12 semanas produce “Sin datos suficientes”; referencia cero produce “Evaluación especial”. Con referencia positiva se compara la razón predicción/promedio con los umbrales. Son indicadores experimentales, no alertas sanitarias calibradas.

`src/services.py` contiene cuatro cachés:

| Función | Tipo | Qué evita repetir |
|---|---|---|
| `preparar_version` | `st.cache_data` | Lectura CSV y construcción de características. Verifica la huella al cargar. |
| `recurso_modelo` | `st.cache_resource` | Carga del modelo; comparte un bloqueo para su inferencia. |
| `leer_json_version` | `st.cache_data` | Lectura de evaluación de una versión. |
| `predecir_version` | `st.cache_data` | Pronósticos de una versión, distrito y horizonte. |

`leer_bundle` vuelve a leer el puntero pequeño en cada interacción. Una publicación nueva cambia las claves de caché. En modo baseline no se carga un XGBoost innecesariamente.

## Pruebas y archivos anteriores

`tests/test_refactor.py` cubre el flujo modular; `test_dashboard.py` comprueba la interfaz; los otros archivos verifican datos, características y modelo. `test_portabilidad.py` comprueba un traslado a una ruta con espacios y acentos, integridad de publicación y carga de la interfaz trasladada.

`src/app_avance.py` redirige a la interfaz actual. `src/train_model.py` conserva el entrenamiento anterior de un paso; no activa el flujo modular actual. `src/audit.py` ofrece registro de eventos usado por código anterior: no supone que todas las interacciones actuales estén auditadas. Para mantener la publicación actual se usan `etl.py` y `train.py`.

## Archivos nuevos para trasladar el sistema

- `INICIAR_WINDOWS.bat`: busca Python y llama al iniciador, aunque la carpeta tenga espacios.
- `iniciar.py`: comprueba la publicación, crea un entorno aislado para la ubicación actual, instala las versiones fijadas y abre Streamlit.
- `requirements-lock.txt`: versiones concretas del entorno de referencia. `requirements.txt` conserva rangos para desarrollo.
- `empaquetar.py`: crea el ZIP con código, documentación y datos/modelo activos, sin copiar entornos ni credenciales.
- `docs/PORTABILIDAD.md`: instrucciones de instalación, traslado, ejecución y mantenimiento.
