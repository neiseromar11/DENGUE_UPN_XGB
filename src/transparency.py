"""Metadatos públicos de procedencia y exportaciones disponibles en el proyecto."""
from pathlib import Path


FUENTES = [
    {
        "institucion": "Ministerio de Salud · CDC Perú",
        "nombre": "Vigilancia Epidemiológica de dengue",
        "url": "https://www.datosabiertos.gob.pe/dataset/vigilancia-epidemiol%C3%B3gica-de-dengue/resource/79e21c8d-3a94-4ac5-b234-bace71fe9675",
        "anios": "Fuente pública: 2000–2024; panel local integrado: 2023–2024",
        "actualizacion": "Catálogo indica modificación 17-12-2025; panel local generado 12-10-2026",
        "licencia": "Open Data Commons Attribution (según la ficha oficial)",
        "descripcion": "Registros de notificación del MINSA/CDC. El paquete conserva el panel procesado, no el CSV original; el tipo de diagnóstico no equivale por sí solo a una etiqueta de confirmación.",
        "estado": "Origen atribuido al panel local; archivo fuente original no está en el proyecto.",
    },
    {
        "institucion": "CDC Perú · MINSA",
        "nombre": "Observatorio de Clima y Salud · tendencias epidemiológicas",
        "url": "https://app7.dge.gob.pe/maps/clima-salud/",
        "anios": "Selector publicado 2018–2026; dengue semanal por departamento, provincia y distrito",
        "actualizacion": "Consulta 21-10-2026; página indica corte 2026-SE35 (05-09-2026), actualización 10-09-2026",
        "licencia": "No declarada en la ficha consultada",
        "descripcion": "El portal ofrece consulta y descarga de bases de vigilancia y clima; identifica SENAMHI como fuente meteorológica espacial. La definición de dengue puede seleccionarse como confirmados y probables.",
        "estado": "Integrado como candidato experimental desde XLSX local: clima rezagado y dengue TOTAL. No sustituye el modelo activo porque no mejor? la validaci?n temporal previa.",
    },
    {
        "institucion": "CDC Perú · MINSA",
        "nombre": "Sala Situacional Diaria de Dengue",
        "url": "https://app7.dge.gob.pe/maps2/sala_diaria_dengue.html",
        "anios": "Panel diario 2026; indicadores nacionales, DIRIS y distritales",
        "actualizacion": "Corte visible 20-10-2026 08:00 (hora de Perú)",
        "licencia": "No declarada en la página consultada",
        "descripcion": "Presenta casos confirmados y probables y anuncia descargas Excel por distrito. En el corte consultado, DIRIS Lima Centro mostraba 1.450 casos: 1.340 confirmados y 110 probables.",
        "estado": "Cifra agregada de corte para contexto; no integrada al histórico semanal ni al entrenamiento.",
    },
    {
        "institucion": "DIRIS Lima Centro",
        "nombre": "Dengue 2024 · salas integradas semanales",
        "url": "https://www.gob.pe/institucion/dirislimacentro/informes-publicaciones/7824541-dengue-2024",
        "anios": "2024 · informes semanales hasta SE52",
        "actualizacion": "Publicación 23-12-2024",
        "licencia": "No declarada en la ficha consultada",
        "descripcion": "Boletines PDF con cortes sucesivos; no se mezclaron con la serie MINSA por diferencias de formato y definiciones.",
        "estado": "Referencia oficial consultada; no integrada como filas semanales.",
    },
    {
        "institucion": "DIRIS Lima Centro",
        "nombre": "Dengue 2025 · salas integradas semanales",
        "url": "https://www.gob.pe/institucion/dirislimacentro/informes-publicaciones/7825010-dengue-2025",
        "anios": "2025 · reportes semanales publicados hasta SE53",
        "actualizacion": "Publicación del compendio: 29-12-2025",
        "licencia": "No declarada en la ficha consultada",
        "descripcion": "PDF oficiales con cortes sucesivos; útiles para contraste distrital, sujeto a extracción, cobertura y compatibilidad de definición.",
        "estado": "No integrado: los PDF no son una tabla de microdatos validada y no se mezclaron con conteos MINSA.",
    },
    {
        "institucion": "DIRIS Lima Centro",
        "nombre": "Boletines Epidemiológicos 2026",
        "url": "https://www.gob.pe/institucion/dirislimacentro/informes-publicaciones/7636617-boletines-epidemiologicos-2026",
        "anios": "2026 · boletines semanales visibles hasta SE29 en la ficha revisada",
        "actualizacion": "Publicación de la colección: 31-07-2026",
        "licencia": "No declarada en la ficha consultada",
        "descripcion": "Boletines institucionales PDF; la disponibilidad de una semana no garantiza una serie distrital homogénea ni un mismo corte de revisión.",
        "estado": "No integrado; requiere extracción y conciliación contra una serie fuente única.",
    },
]


def archivos_exportables(base, bundle):
    """Devuelve solo archivos reales existentes; nunca simula el CSV original."""
    base = Path(base)
    candidatos = {
        "Dataset procesado (CSV)": base / bundle["datos"],
        "Resultados walk-forward (CSV)": base / "reports/predicciones_modelos_walk_forward.csv",
        "Evaluación del tramo final (CSV)": base / "reports/predicciones_holdout_final.csv",
        "Panel distrital de dengue y clima (CSV)": base / "data/processed/dengue_clima_14d.csv",
        "Backtest candidato con clima (CSV)": base / "reports/predicciones_clima_walk_forward.csv",
        "Auditoria del experimento clima (JSON)": base / "reports/evaluacion_clima_walk_forward.json",
        "Fuente original clima TOTAL (XLSX)": base / "XLSX/clima_departamento (2).xlsx",
        "Fuente original clima CONFIRMADO (XLSX)": base / "XLSX/clima_departamento.xlsx",
    }
    return {nombre: ruta for nombre, ruta in candidatos.items() if ruta.is_file()}
