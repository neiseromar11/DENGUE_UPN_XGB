# Fichas Técnicas de los 4 Indicadores Clave de Desempeño (KPI)
## Sistema Predictivo DengueML · DIRIS Lima Centro

---

### KPI 1: Casos Semanales de Dengue por Distrito

| Atributo | Especificación Técnica |
| :--- | :--- |
| **Nombre** | Casos semanales observados de dengue por distrito |
| **Definición** | Frecuencia absoluta de registros individuales de dengue notificados al sistema de vigilancia Notiweb para un distrito y semana epidemiológica determinada. |
| **Fórmula de Negocio** | $$\text{Total de casos} = \sum_{i=1}^{n} \text{casos registrados en el distrito } d \text{ durante la semana epidemiológica } s$$ |
| **Ejemplo de Cálculo** | Si durante la Semana Epidemiológica 20 en San Juan de Lurigancho se registran notificaciones de 8, 10 y 7 casos en distintos reportes clínicos: $8 + 10 + 7 = 25\text{ casos}$. |
| **Fuente de Datos** | Plataforma Nacional de Datos Abiertos (`datosabiertos.gob.pe`) / Centro Nacional de Epidemiología, Prevención y Control de Enfermedades (CDC Perú / MINSA). |
| **Unidad de Medida** | Casos notificados (número entero $\ge 0$). |
| **Ámbito Temporal** | Semana epidemiológica (SE 01 a SE 52/53). En el dashboard responde al selector de periodo y semana de corte. |
| **Interpretación** | Permite conocer la magnitud real de casos notificados observados en el territorio. |
| **Limitaciones y Advertencias** | **No representa tasa de incidencia:** Al no contar con proyecciones poblacionales censales oficiales en el registro abierto, el indicador refleja conteo absoluto y no riesgo por cada 100,000 habitantes. Sujeto a retraso de notificación epidemiológica. |

---

### KPI 2: Nivel de Riesgo por Distrito

| Atributo | Especificación Técnica |
| :--- | :--- |
| **Nombre** | Nivel preliminar de riesgo por distrito |
| **Definición** | Relación porcentual entre la estimación esperada de casos para una semana futura y un umbral epidemiológico histórico de referencia distrital. |
| **Fórmula de Negocio** | $$\text{Índice de riesgo (\%)} = \left(\frac{\text{Casos predichos}}{\text{Umbral epidemiológico de referencia}}\right) \times 100$$ |
| **Criterio de Clasificación** | • **BAJO:** $\text{Índice} < 80\%$ (o predicción $= 0$ con referencia $= 0$).<br>• **MEDIO:** $80\% \le \text{Índice} \le 150\%$.<br>• **ALTO:** $\text{Índice} > 150\%$.<br>• **En observación / Evaluación especial:** Referencia $= 0$ y predicción $> 0$. |
| **Ejemplo de Cálculo** | Si la predicción para la semana $t+1$ en Cercado de Lima es de 60 casos y el umbral histórico promedio de las últimas 12 semanas es de 50 casos: $\frac{60}{50} \times 100 = 120\%$ (Clasificación: **MEDIO**). |
| **Fuente de Datos** | Estimación generada por el modelo XGBoost (`src/model.py`) y ventana móvil de 12 semanas de datos observados. |
| **Unidad de Medida** | Porcentaje (\%) y categoría cualitativa (Bajo, Medio, Alto, En observación). |
| **Ámbito Temporal** | Proyección semanal en horizonte de 2, 3 o 4 semanas hacia el futuro. |
| **Interpretación** | Determina si la transmisión esperada supera o se aproxima al comportamiento basal reciente del distrito. |
| **Limitaciones y Advertencias** | **Umbral de referencia experimental:** Emplea la media móvil histórica reciente de 12 semanas; no constituye un canal endémico oficial de cuartiles ni una declaratoria oficial de brote sanitario por parte de DIRIS Lima Centro. Tratamiento explícito para evitar división por cero. |

---

### KPI 3: Capacidad de Anticipación

| Atributo | Especificación Técnica |
| :--- | :--- |
| **Nombre** | Capacidad de anticipación del sistema predictivo |
| **Definición** | Intervalo temporal medido en semanas epidemiológicas entre la emisión de una alerta por incremento de casos y la ocurrencia observada del evento en los datos reales. |
| **Fórmula de Negocio** | $$\text{Anticipación} = \text{Semana del evento real} - \text{Semana de la alerta emitida}$$ |
| **Ejemplo de Cálculo** | Si el modelo proyecta un incremento sostenido (alerta) en la Semana 20 y el pico del brote ocurre efectivamente en la Semana 23: $23 - 20 = 3\text{ semanas de anticipación}$. |
| **Estado Operativo Actual** | **Horizonte activo:** Se evalúan proyecciones a 2, 3 y 4 semanas hacia el futuro. La capacidad formal de anticipación frente a brotes históricos se reporta como *"En fase de validación empírica retrospectiva"*. |
| **Fuente de Datos** | Módulo de validación temporal recursiva (`src/validation.py`). |
| **Unidad de Medida** | Semanas epidemiológicas (entero de 2 a 4). |
| **Ámbito Temporal** | Horizontes predictivos $h \in \{2, 3, 4\}$. |
| **Interpretación** | Cuantifica la ventana temporal previa con la que el modelo advierte aumentos en la curva epidemiológica. |
| **Limitaciones y Advertencias** | El horizonte técnico configurado no debe confundirse con una capacidad demostrada de detección de brotes sin un estudio formal de curvas ROC / sensibilidad temporal retrospectiva. |

---

### KPI 4: Tendencia de Casos

| Atributo | Especificación Técnica |
| :--- | :--- |
| **Nombre** | Tendencia de casos notificados |
| **Definición** | Variación relativa o absoluta de casos notificados entre la semana epidemiológica analizada y la semana inmediata anterior. |
| **Fórmula de Negocio** | $$\text{Variación (\%)} = \left(\frac{\text{Casos actual} - \text{Casos anterior}}{\text{Casos anterior}}\right) \times 100$$ |
| **Tratamiento de Casos Borde** | • Si $\text{Casos anterior} > 0$: Se calcula el porcentaje exacto y la diferencia absoluta ($\pm \Delta$).<br>• Si $\text{Casos anterior} = 0$ y $\text{Casos actual} > 0$: Porcentaje no calculable; se reporta la diferencia absoluta: $+N\text{ casos (ref. 0)}$.<br>• Si $\text{Casos anterior} = 0$ y $\text{Casos actual} = 0$: $0.0\%\text{ (sin casos)}$. |
| **Ejemplo de Cálculo** | Semana previa = 40 casos; semana actual = 50 casos: $\frac{50 - 40}{40} \times 100 = +25.0\%$ ($+10\text{ casos}$). |
| **Fuente de Datos** | Serie observada filtrada (`src/dashboard.py`). |
| **Unidad de Medida** | Porcentaje (\%) y delta de casos ($\Delta$). |
| **Ámbito Temporal** | Comparación entre semanas epidemiológicas contiguas ($t$ vs $t-1$). |
| **Interpretación** | Identifica si la curva epidémica local está acelerando, desacelerando o manteniéndose estable. |
| **Limitaciones y Advertencias** | Una variación porcentual alta en distritos con pocos casos (e.g. de 1 a 3 casos = $+200\%$) debe interpretarse en conjunto con la magnitud absoluta para evitar falsas alarmas de escala. |
