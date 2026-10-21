# Material de sustentación DengueML-UPN (20/10/2026)

## 1. Explicación breve para el profesor

DengueML-UPN es un dashboard público e informativo que permite consultar el histórico de registros de dengue de 14 distritos de DIRIS Lima Centro y obtener estimaciones semanales con un modelo XGBoost. El panel llega a 2024-SE52 y las estimaciones (2025-SE01 a SE04) parten de ese corte; no son pronósticos actuales. La fuente la identificamos como casos confirmados por nuestra revisión, aunque el CSV no trae un campo que lo compruebe. Evaluamos el modelo con cortes temporales frente a «repetir la última semana» y «siempre cero». El resultado es honesto pero no favorable: en el bloque de prueba hay solo 5 casos y una regla de ceros iguala o supera al modelo en dos de tres horizontes, así que no podemos afirmar superioridad. El nivel de riesgo es un indicador relativo experimental y la capacidad de anticipación de brotes aún no está medida. Probamos clima y provincias en experimentos aislados que no se publicaron. Lo que falta es una validación predictiva en semanas nuevas, medir anticipación y validar con usuarios.

## 2. Explicación sencilla para los compañeros

* Lo que sí funciona: el sistema carga datos, calcula, muestra gráficos y estimaciones, y las pruebas automáticas pasan (22).
* Lo que no sabemos: si el modelo acierta mejor que una regla simple. En las semanas de prueba casi no hubo casos, y adivinar «cero» ya da poco error.
* MAE = cuántos casos se equivoca en promedio. No es un porcentaje de acierto.
* El número 19,89 % del clima es de un experimento aparte; no es la precisión del dashboard.
* Las estimaciones «del futuro» arrancan en 2025-SE01 porque los datos terminan en 2024.
* No decimos «alerta», «diagnóstico» ni «incidencia». Decimos «casos registrados» y «riesgo relativo experimental».

## 3. Guion de demostración (5 minutos)

1. **0:00–1:00 Resumen.** Abrir la app. Señalar: 14 distritos, fuente, última semana observada 2024-SE52, periodo estimado 2025-SE01–SE04, aviso de corte. Los 4 indicadores: casos (conteo, no tasa), riesgo (experimental), anticipación («Pendiente de estimación»), tendencia. Cambiar el periodo a **Todo el histórico** para que se vean 2023–2024 (con 12 semanas el gráfico queda casi plano).
2. **1:00–2:00 Comparación distrital.** Mapa de calor: gris = sin registros, no cero de transmisión. Cambiar la semana estimada.
3. **2:00–3:00 Detalle del distrito.** Elegir San Juan de Lurigancho (el distrito con más casos). Mostrar línea continua = registrado; discontinua = estimado; tabla con riesgo y «Evaluación especial».
4. **3:00–4:30 Calidad y límites.** Elegir horizonte 3 y luego 2: comparar error del modelo, de repetir la última semana y de «siempre cero». Mostrar la advertencia automática y que hay solo 5 casos en la muestra. Abrir «descargar evidencia».
5. **4:30–5:00 Cierre.** Implementado: ETL reproducible, modelo publicado, dashboard, pruebas. Pendiente: validación independiente, anticipación, aval del riesgo, usuarios. Experimentos separados.

Antes de empezar: ejecutar `INICIAR_WINDOWS.bat`, abrir la app y probar una vez cada sección.

## 4. Respuestas preparadas

**¿Cuál es la precisión del modelo?** No hay un porcentaje de precisión. Usamos MAE y RMSE en casos. En la prueba, el MAE del modelo es 0,13; 0,07 y 0,10 casos (horizontes 2, 3 y 4), pero «siempre cero» da 0,089, y todo ocurre sobre 5 casos. Un error bajo con muchos ceros no es acierto.

**¿Por qué no llegó al 100 %?** Es una estimación con información incompleta; nadie puede garantizarlo. Nuestro compromiso es medir y comunicar el error.

**¿Gana XGBoost a la línea base?** No está demostrado. En la validación (SE16–SE32) mejora a persistencia de forma moderada (8,78 vs 9,10 en h2; 10,61 vs 12,24 en h3; 15,81 vs 19,55 en h4), pero ese bloque sirvió para elegir el modelo. En la prueba, «siempre cero» gana en h2 y h4. Si el objetivo exige demostrarlo, queda pendiente con semanas nuevas.

**¿Y el clima?** En el experimento aislado, el mismo XGBoost con clima redujo el MAE 19,89 % (5,9681 → 4,7808) frente a sin clima, pero la sensibilidad bajó (82,40 % → 80,58 %), no cumplió todos los criterios previos y frente a las reglas actuales la ventaja no fue concluyente. No se publicó.

**¿Por qué no todo el Perú?** El piloto provincial (110 provincias) dio MAE 31,85 para XGBoost y 27,12 para persistencia; ganó en 22 de 110. No justifica ampliar. Tampoco se comparan esos MAE con los distritales: cambian escala y objetivo.

**¿Los datos son confirmados?** Es la identificación de nuestra revisión de la fuente. El CSV solo trae el tipo de dengue (sin alarma, con alarma, grave); no hay campo de confirmación.

**¿Cada fila es un caso distinto?** Cada fila se cuenta como un registro; sin identificador no eliminamos filas parecidas (2 256 coincidencias).

**¿Los ceros son ausencia de dengue?** No. Son semanas sin filas (862 combinaciones); no prueban ausencia de transmisión ni vigilancia completa.

**¿Es un sistema de alerta?** No. El riesgo es un indicador relativo con umbrales 0,8 y 1,5 sin calibración sanitaria. La anticipación no está medida: proyectar 4 semanas no es anticipar un brote.

**¿Por qué no hay login?** Decisión de alcance: dashboard público e informativo, solo con datos agregados.

**¿Por qué el pronóstico llega a 2025?** Porque parte del corte 2024-SE52; no es un pronóstico a hoy.

**¿Hay validación de instrumentos?** No tenemos fichas firmadas; no las inventamos.

## 5. Pendientes para cerrar

| # | Pendiente | Por qué | Quién decide / aporta |
|---|---|---|---|
| 1 | Confirmar (commit/PR) los cambios locales (70 archivos) | El informe cita evidencia versionada | Equipo |
| 2 | Validación predictiva independiente (semanas nuevas, protocolo previo, vs persistencia y siempre cero) | Los periodos actuales ya se examinaron | Equipo + docente |
| 3 | Medir anticipación (definir evento, alertas, falsos positivos) | KPI-03 sin dato | Equipo + referente |
| 4 | Aval o ajuste del indicador de riesgo | Umbrales sin calibración; ALTO con 2,34 casos | Decisión con evidencia |
| 5 | Prueba visual en móvil/tablet | CA HU-05/CA-005 | Equipo |
| 6 | Licencia y fecha de descarga de la fuente | Ficha F-01 | Responsable de datos |
| 7 | Decisión escrita sobre el clima (excluir o evaluación futura) | TA-05 | Equipo |
| 8 | Fichas de validación firmadas y aceptación de usuario | No existen | Docente/expertos |
| 9 | Revisar y aceptar el informe y el burndown revisados; regenerar figuras de semana 6 | TA-26 en progreso | Equipo |
| 10 | Decidir título final y redacción de objetivos 2–3 | Contradicciones listadas | Equipo + docente |
| 11 | Estimar puntos de la hoja 09 del Excel | No se inventaron | Equipo |
| 12 | Carga/estrés, restauración, declaración de IA | Fuera de esta tarea o sin registro | Equipo |
