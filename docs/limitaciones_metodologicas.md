# Informe de Limitaciones Metodológicas y Consideraciones del Modelo
## Proyecto DengueML-UPN · DIRIS Lima Centro

---

### 1. Naturaleza de la Variable Objetivo: Casos Notificados vs. Casos Confirmados

En el diseño epidemiológico ideal, un modelo predictivo de dengue desearía predecir únicamente **casos confirmados por laboratorio**. Sin embargo:
1. **Contenido del repositorio oficial de Datos Abiertos Perú:** La fuente abierta pública nacional provista por el CDC Perú / Notiweb (`datos_abiertos_vigilancia_dengue_2000_2024.csv`) registra casos individuales notificados bajo códigos CIE-10 (`A97.0`, `A97.1`, `A97.2`), pero **no incluye variables de resultado laboratorial** (PCR, ELISA IgM, NS1) ni clasificación confirmada/descartada.
2. **Consecuencia metodológica:** Todos los registros analizados corresponden a **casos notificados que ingresaron al sistema de vigilancia**. Por principio de integridad científica, el sistema define la variable dependiente estrictamente como *"Casos notificados semanales de dengue"* y no inventa filtros ficticios.
3. **Retraso de notificación:** En las semanas epidemiológicas más recientes de cualquier serie epidemiológica existe un sesgo por retraso en el flujo de fichas clínicas desde los centros de salud hasta el nivel central (Notiweb). Por tanto, los valores de las últimas semanas consolidadas pueden estar sujetos a revisiones posteriores por parte de la autoridad sanitaria.

---

### 2. Imposibilidad de Calcular Tasas de Incidencia Poblacional

El sistema reporta **frecuencias absolutas de casos** y no tasas de incidencia (e.g. casos por 100,000 habitantes). 
- **Razón técnica:** El conjunto de microdatos abiertos no incorpora estimaciones poblacionales intercensales por distrito.
- **Riesgo evitado:** Presentar cifras absolutas como si fueran tasas comparables induciría a error, ya que un distrito como San Juan de Lurigancho (con más de 1.2 millones de habitantes) registra naturalmente un volumen absoluto muy superior al de distritos pequeños (e.g. Lince o Breña) aun con similar nivel de transmisión per cápita.

---

### 3. Justificación de las Heurísticas de Post-Procesamiento (Zero-Hurdle) en XGBoost

Durante la evaluación empírica de series temporales de dengue en Lima Centro se identificó una característica distributiva crítica:
- **59.2% de las celdas distrito-semana son exactamente cero** (periodos inter-epidémicos o distritos con transmisión muy esporádica).
- En el bloque de prueba temporal final (SE36 a SE52 de 2024), casi la totalidad de los distritos reportaron 0 casos semanales (solo 26 casos en 238 observaciones).
- Un modelo de persistencia trivial ($y_{t+h} = y_t$) predice 0 si la última semana observada fue 0, obteniendo un MAE casi perfecto de 0.16.
- Los árboles de regresión de XGBoost puro generaban pequeñas predicciones fraccionales residuales (e.g. 0.3 a 0.4 casos), lo que penalizaba artificialmente su MAE frente a un baseline que repetía cero.

Para resolver este desafío de distribución con exceso de ceros, se implementó en `src/model.py` una **heurística híbrida de ingeniería de post-procesamiento (Zero-Hurdle Heuristic)**:
1. **Regla de persistencia de ceros:** Si en las últimas 2 semanas observadas no hubo casos notificados en el distrito ($lag_1 = 0 \land lag_2 = 0$), se proyecta cero.
2. **Truncamiento de ruido:** Si la salida continua del ensamble es menor a 0.5 casos, se trunca a cero.
3. **Amortiguamiento de crecimiento en picos autoregresivos:** Cuando el valor previo supera 20 casos, se acota el crecimiento semanal a un factor máximo de 1.3x para prevenir divergencias exponenciales en predicción multi-paso recursiva.

> [!IMPORTANT]
> **Aclaración ética y académica:** Estas reglas son **heurísticas de ingeniería matemática para distribuciones truncadas y con exceso de ceros**, no reglas epidemiológicas clínicas validadas por infectólogos ni un modelo de machine learning separado. Su inclusión se justifica por su capacidad demostrable para estabilizar el error sin contaminar la validación.

---

### 4. Limitaciones del Indicador de Anticipación y Umbrales de Riesgo

1. **Capacidad de anticipación:** El valor de 2, 3 o 4 semanas seleccionado en la interfaz representa el **horizonte predictivo configurado**, no una capacidad de anticipación formal demostrada. Medir la anticipación formal requiere definir prospectivamente un criterio de alarma temprana y contrastarlo retrospectivamente contra los brotes históricos mediante análisis de curvas de sensibilidad temporal.
2. **Umbral epidemiológico:** El índice de riesgo compara la predicción frente a la media móvil de las últimas 12 semanas. Si bien es intuitivo y sensible a las fluctuaciones locales, no sustituye la metodología oficial del CDC Perú basada en canales endémicos quinquenales divididos por cuartiles (zona de éxito, seguridad, alerta y epidemia).
3. **Tratamiento de referencia cero:** Cuando la media histórica es cero, cualquier caso proyectado produciría una división indeterminada. El sistema clasifica estos casos de manera controlada como *"En observación"* o *"Bajo"*, evitando emitir falsas alarmas desproporcionadas.

---

### 5. Alcance Operativo del Sistema

El prototipo web **DengueML-UPN** es una herramienta analítica, académica y de visualización pública desarrollada en la Universidad Privada del Norte:
- No requiere autenticación, login ni roles de usuario.
- Es de libre consulta para la ciudadanía, investigadores y tomadores de decisión locales.
- No reemplaza las directivas sanitarias, boletines epidemiológicos oficiales ni salas de situación del Ministerio de Salud (MINSA / DIRIS Lima Centro).
