# DengueML-UPN: guía para presentar y cerrar el avance

## Decisión de alcance

Mantener el producto en los 14 distritos de DIRIS Lima Centro. La alternativa provincial y los experimentos climáticos permanecen separados. No se modifica el modelo publicado con resultados exploratorios. El acceso continúa público, sin usuarios ni login.

El objetivo operativo es estimar el número semanal de casos por distrito para las semanas posteriores al corte de datos y presentar un indicador relativo experimental. No se promete predicción exacta, detección validada de brotes ni incidencia por población.

## Qué datos se muestran

La versión publicada usa un panel de 2023–2024 y tiene corte 2024-SE52. Las proyecciones de esa versión parten de ese corte, no de la fecha actual de consulta. Mostrar 2025 en el gráfico no significa disponer de datos observados de 2025 ni de un pronóstico actualizado.

El responsable del proyecto revisó la fuente `datos_abiertos_vigilancia_dengue_2000_2024.csv` e indicó que contiene casos confirmados. Esa identificación debe atribuirse a su revisión hasta adjuntar la documentación de la fuente. Las columnas del CSV permiten clasificar el tipo de dengue, pero no comprobar por separado la confirmación. Internamente el panel publicado conserva el nombre `casos_notificados`; la interfaz usa el término descriptivo «casos registrados» para evitar cambiar silenciosamente el contrato de datos.

Cada fila fuente se cuenta como un registro. No eliminar coincidencias sin identificador único de caso. Una semana completada con cero representa ausencia de filas en la fuente, no prueba de vigilancia completa ni ausencia de transmisión. El Excel de clima es una fuente distinta y no está incorporado al dashboard publicado.

## Qué hace el producto

1. Consulta históricos agregados y distritales.
2. Muestra gráficos de evolución, comparación de distritos y mapa de calor.
3. Genera estimaciones posteriores al corte usando el modelo publicado.
4. Calcula un indicador relativo respecto a una referencia histórica, con estados especiales cuando la referencia es cero o la historia es insuficiente.
5. Muestra evidencia retrospectiva del modelo activo, persistencia y siempre cero con los mismos objetivos y cortes.

## Cómo demostrarlo en cinco minutos

1. **Resumen (1 minuto):** señalar los 14 distritos, fuente, fecha de corte y periodo proyectado. Distinguir conteo de casos de tasa de incidencia.
2. **Comparación distrital (1 minuto):** mostrar barras y mapa de calor. Cambiar el periodo histórico y explicar que no cambia la fecha de origen del pronóstico.
3. **Detalle del distrito (1 minuto):** elegir un distrito y mostrar sus indicadores e histórico. Explicar la línea estimada y las cantidades decimales como valores esperados.
4. **Calidad y límites (1–2 minutos):** seleccionar horizonte y ámbito; comparar errores y mostrar puntos históricos registrados y estimados. Explicar que un error cero en pocas semanas sin casos no implica exactitud perfecta general.
5. **Cierre:** indicar qué está implementado y qué falta validar. No presentar los experimentos separados como resultados del modelo activo.

## Qué significa cada indicador

| Indicador | Qué se puede afirmar | Qué no se debe afirmar |
|---|---|---|
| Casos semanales | Conteo de registros del periodo y territorio seleccionados. | Incidencia poblacional sin denominador. |
| Nivel de riesgo | Indicador relativo experimental según referencia histórica y umbrales definidos. | Alerta sanitaria validada o detección de brotes. |
| Capacidad de anticipación | Está pendiente de medir frente a eventos previamente definidos. | Que proyectar cuatro semanas equivale a anticipar un brote cuatro semanas. |
| Tendencia | Cambio entre semanas observadas, con tratamiento especial de referencia cero. | Que la tendencia garantiza el comportamiento futuro. |

Los cuatro indicadores se conservan; un estado pendiente no se sustituye por una cifra inventada para aparentar cumplimiento.

## Explicación para el profesor

«DengueML-UPN es un dashboard público que permite consultar el comportamiento histórico del dengue en 14 distritos de DIRIS Lima Centro y generar estimaciones semanales. Además de desarrollar el producto, evaluamos el error del modelo frente a referencias sencillas con cortes temporales. La versión presentada tiene una fecha de corte explícita; no la presentamos como información en tiempo real. La clasificación de riesgo es experimental y la anticipación de brotes aún no está validada. Los experimentos con clima y provincias se documentaron por separado y no se incorporaron automáticamente al producto».

## Explicación para los compañeros

«Una cosa es que el sistema funcione y otra que el modelo acierte mejor que una regla sencilla. El sistema ya muestra históricos y estimaciones. Para saber si esas estimaciones aportan valor, comparamos lo que habría predicho con lo que después se registró. El MAE mide cuántos casos se equivoca en promedio; no es un porcentaje de precisión. No vamos a cambiar datos ni elegir solo resultados favorables para decir que llegamos al 100%».

## Preguntas frecuentes durante la sustentación

**¿Por qué no predice al 100%?** Se estiman resultados futuros con información incompleta y variable. No existe una garantía de acierto perfecto. El compromiso es medir y comunicar el error.

**¿Para qué sirve si una referencia sencilla gana?** Sirve para consultar información y realizar una comparación reproducible de alternativas. No prueba superioridad de XGBoost. Si el objetivo académico exige demostrar esa superioridad, ese objetivo sigue pendiente y debe discutirse; no basta con mejorar el aspecto visual.

**¿Por qué no hacerlo nacional?** Se probó un piloto provincial. En 110 provincias el XGBoost ensayado no superó a persistencia. No se justificó ampliar el alcance buscando una mejora automática.

**¿Los experimentos contradicen el modelo publicado?** No se comparan directamente: cambian datos, periodos y, en algunos casos, el objetivo. La vista de calidad usa exclusivamente la evidencia archivada de la versión publicada.

**¿Se usó clima?** En experimentos aislados sí; en el modelo activo no. La mejora del 19,89% corresponde a un par de modelos experimentales con/sin clima y no es un porcentaje de exactitud ni una mejora certificada del dashboard.

## Plan para una siguiente validación independiente

1. Fijar antes de entrenar: objetivo de casos, fuente, territorios, política de ausencia de registros, horizontes y métricas principales.
2. Elaborar un inventario de semanas ya examinadas. Los periodos usados para seleccionar o ajustar alternativas no deben presentarse como un nuevo test independiente.
3. Elegir hiperparámetros y modelos con cortes internos cronológicos; entrenar cada corte usando únicamente información disponible hasta ese momento, incluidos los rezagos climáticos si corresponde.
4. Congelar la alternativa elegida y compararla con persistencia y siempre cero en semanas nuevas o un periodo realmente no utilizado para decidir. No hay un nuevo test independiente ejecutado en esta entrega.
5. Medir MAE, RMSE, error en semanas con casos, resultados por distrito y horizonte y la incertidumbre de las diferencias. Separar precisión de cantidad de capacidad de detectar eventos.
6. Antes de publicar intervalos, verificar su cobertura temporal. Antes de llamar alerta al indicador, definir el evento y medir sensibilidad, falsos positivos y anticipación.
7. Actualizar el modelo publicado solo con una decisión documentada basada en los criterios previamente fijados. Si no supera las referencias, conservar el resultado negativo y revisar el objetivo con el docente.

## Dónde está cada cosa

- `src/app.py`: navegación, filtros, indicadores, aviso de corte histórico y explicaciones.
- `src/calidad_ui.py`: comparación de errores, filtros de evaluación y gráfica retrospectiva.
- `src/charts.py`: gráficos del dashboard.
- `src/services.py`: caché de datos/modelos y predicción por versión y distrito.
- `models/actual.json`: versión publicada; no modificada en esta mejora.
- `reports/experimento_confirmados_clima_v3/RESULTADOS.md`: experimento climático.
- `reports/experimento_vacios_0_1/RESULTADOS.md`: sensibilidad al relleno 0/1.
- `reports/experimento_provincias_v1/RESULTADOS.md`: piloto provincial.

Esta guía prepara una presentación verificable; no garantiza aprobación académica ni sustituye los criterios del docente.
