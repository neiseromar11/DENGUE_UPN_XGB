# DengueML-UPN: sistema público modular

```text
capstone_dengue/
├── src/
│   ├── app.py             # Interfaz pública y filtros automáticos
│   ├── app_avance.py      # Entrada compatible con el comando anterior
│   ├── dashboard.py       # KPI, filtros e inferencia selectiva
│   ├── services.py        # Cachés por versión y recurso XGBoost compartido
│   ├── etl.py             # Validación, versiones y carga de histórico
│   ├── validation.py      # Selección temporal y prueba final reservada
│   ├── train.py           # Publicación conjunta de datos y modelo
│   ├── risk.py            # Casos especiales y umbrales relativos
│   ├── model.py           # XGBoost y predicción recursiva
│   ├── features.py        # Rezagos sin fuga de información
│   ├── calendar_epi.py    # Calendario epidemiológico
│   └── config.py          # Catálogo de 14 distritos
├── data/versions/<version>/datos.csv, metadata.json
├── models/actual.json     # Puntero a la versión activa
├── models/releases/<version>/
│   ├── evaluacion.json
│   ├── validacion.csv
│   ├── test.csv
│   ├── metricas_distritales.csv
│   ├── bundle.json
│   └── modelo.json        # Solo si XGBoost supera el criterio
└── tests/
```

## Ejecutar

Desde `capstone_dengue`, con Python 3.11 y dependencias de `requirements.txt`:

```powershell
python -m streamlit run src/app.py
```

La versión activa ya está preparada. El dashboard genera resultados automáticamente. Es público y no tiene usuarios, roles ni login. La actualización del histórico se ejecuta desde consola por quien mantiene la instalación; no se ofrece escritura pública del dataset.

## Actualizar el histórico

```powershell
python src/etl.py data/raw/datos_abiertos_vigilancia_dengue.csv --desde 2023
# Copiar la ruta metadata.json devuelta por el ETL:
python src/train.py data/versions/<version>/metadata.json
```

La fuente debe ser un histórico completo con una fila por registro, separado por `;`, con departamento, provincia, distrito, ano y semana. Se pueden configurar `--sep` y `--encoding`. No concatena archivos sin un identificador de caso: eso duplicaría registros en actualizaciones solapadas. Las coincidencias exactas se conservan porque no existe un ID único fiable.

No hay año final fijo. `--desde` y `--hasta` son opcionales; al omitir ambos se intenta validar todo el histórico. La migración inicial usa explícitamente `--desde 2023` para mantener el alcance anterior: la fuente contiene semanas antiguas como 2009-SE53 que el calendario implementado rechaza. No se descartan silenciosamente errores dentro del periodo solicitado. Los registros fuera del periodo quedan contabilizados en metadata.

El ETL valida nulos obligatorios, columnas, formatos enteros y calendario. Identifica versiones por la fuente, configuración temporal y versión de ETL; registra fecha UTC, corte y SHA-256. Los datos preparados se guardan en una carpeta nueva. Si falla la validación o el entrenamiento, se conserva el puntero activo. Solo al terminar se reemplaza atómicamente `models/actual.json`. Las carpetas versionadas son inmutables: para modificar datos hay que crear una nueva versión. Un único proceso de mantenimiento debe publicar a la vez.

Los ceros completan semanas sin registros en el archivo. No prueban cobertura de notificación ni ausencia de transmisión. El sistema pronostica conteos, no tasas de incidencia: no contiene denominadores poblacionales.

## Evaluación y elección del modelo

`validation.py` compara persistencia (última semana) con tres XGBoost: conservador, moderado y objetivo Poisson. `CANDIDATOS` permite configurar la búsqueda antes de ejecutar la evaluación.

Se usan tres orígenes de validación separados por ocho semanas y un bloque final de 16 semanas reservado. En cada origen se reentrena únicamente con observaciones disponibles hasta ese momento. La recursión a cuatro semanas incorpora predicciones, nunca observaciones futuras. Se evalúan los 14 distritos, cada paso y cada corte. Los pasos 2, 3 y 4 deciden la selección; el paso 1 se conserva como diagnóstico.

El criterio previo exige una reducción superior al 2% del MAE promedio de los pasos 2–4 y no empeorar ninguno de esos horizontes frente al baseline. Esta es una decisión técnica conservadora configurable, no un umbral clínico. El panel balanceado da el mismo peso a cada distrito; los conteos de distritos grandes pueden dominar la magnitud del error.

Solo el candidato seleccionado y el baseline pasan al bloque final, con reentrenamiento progresivo al avanzar los orígenes. Si el candidato no confirma la mejora, se publica el baseline; no se prueba otro candidato sobre ese mismo bloque. Si ningún XGBoost supera la validación, se evalúa el baseline en el bloque final. No ajustar candidatos repetidamente mirando el test: para una nueva búsqueda informada por ese resultado se necesita un nuevo bloque independiente.

Resultado de la ejecución inicial: quedó seleccionado el baseline. Ninguno de los tres XGBoost cumplió el criterio completo, aunque algunos mejoraron determinados horizontes. El MAE final del baseline fue 0,160714 a dos semanas, 0,160714 a tres y 0,196429 a cuatro. Estos valores no son comparables directamente con el MAE 0,1821 anterior, porque cambiaron los cortes y la evaluación recursiva. La selección no demuestra generalización a brotes futuros.

## Rendimiento y filtros

- `preparar_version`, con `st.cache_data`, reutiliza CSV y características; comprueba SHA-256 al cargar una versión.
- `recurso_modelo`, con `st.cache_resource`, reutiliza el modelo y un bloqueo para proteger la inferencia compartida. XGBoost usa `n_jobs=1` para limitar competencia por CPU.
- `predecir_version` almacena resultados por versión, distrito y horizonte; todas las cachés tienen límites de entradas.
- El puntero pequeño se relee en cada interacción. Una publicación cambia la clave de las cachés; no se recorre todo el CSV en cada rerun.
- Vista Distrital calcula solo ese distrito. Vista Global calcula 14 y suma sus pronósticos.
- Los KPI y el histórico respetan distrito y periodo. El pronóstico siempre parte del último dato; cambiar el periodo visible no hace un backtest.
- Semanas sin registros cuenta semanas únicas con total cero en la selección; no suma combinaciones distrito-semana.
- Las métricas de evaluación se filtran por distrito y por los horizontes mostrados; corresponden al bloque reservado, no al periodo visual del histórico.

## Indicador relativo

`risk.py` valida valores finitos no negativos, al menos 12 semanas y `0 < medio < alto`. Con historia insuficiente muestra **Sin datos suficientes**; con referencia cero, **Evaluación especial**. En los demás casos usa la razón contra el promedio observado de las últimas 12 semanas, con límites 0,8 y 1,5 y comparación estricta `>`.

La validación numérica de umbrales no es calibración sanitaria. Los niveles siguen siendo experimentales. El indicador se calcula por semana y distrito; no se convierte la suma global en una alerta.

## Pruebas

```powershell
python -m pytest tests -q --basetemp=reports/pytest_local
```

Cubren recursión y calendario, entrenamiento y persistencia, aislamiento de datos futuros, selección por horizonte, cache e invalidación, inferencia XGBoost compartida, actualización con años nuevos y nulos, conservación de la versión ante fallos, KPI y navegación automática del dashboard.

La optimización no implica haber demostrado soporte para 5000 usuarios. Se debe repetir una campaña de carga sobre esta versión antes de atribuirle una nueva capacidad. Los resultados de estrés anteriores corresponden a la implementación previa.

## Referencias técnicas

- Streamlit: https://docs.streamlit.io/develop/concepts/architecture/caching
- XGBoost: https://xgboost.readthedocs.io/en/stable/python/python_api.html

