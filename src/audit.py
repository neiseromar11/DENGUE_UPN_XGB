"""
DengueML-UPN - Módulo de Auditoría y Trazabilidad
==================================================
Registra eventos relevantes del sistema en logs locales.
NO registra: contraseñas, tokens, claves, DNI, datos personales.
"""

import os
import logging
from datetime import datetime

# Configurar directorio de logs
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_BASE_DIR, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_LOG_FILE = os.path.join(_LOG_DIR, "audit.log")

# Configurar logger de auditoría
_logger = logging.getLogger("dengueml_audit")
_logger.setLevel(logging.INFO)

# Evitar duplicar handlers si el módulo se recarga
if not _logger.handlers:
    _file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    _file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    _logger.addHandler(_file_handler)


# ---------------------------------------------------------
# Tipos de eventos permitidos
# ---------------------------------------------------------
EVENTOS = {
    "APP_INICIO": "Inicio de la aplicación",
    "FILTROS_ACTUALIZADOS": "Actualización de filtros",
    "CARGA_DATOS": "Carga de dataset epidemiológico",
    "PROCESAMIENTO_ETL": "Ejecución del procesamiento ETL",
    "PREPARACION_MODELADO": "Preparación de datos para modelado",
    "ENTRENAMIENTO_MODELO": "Entrenamiento del modelo predictivo",
    "EVALUACION_MODELO": "Evaluación del modelo predictivo",
    "PREDICCION_GENERADA": "Generación de predicciones",
    "EXPORTACION_REPORTE": "Exportación de reporte",
    "ERROR": "Error del sistema",
}


def registrar_evento(tipo_evento: str, descripcion: str = "", nivel: str = "INFO"):
    """
    Registra un evento de auditoría.

    Args:
        tipo_evento: Clave del tipo de evento (ver EVENTOS).
        descripcion: Descripción adicional del evento.
        nivel: Nivel del log (INFO, WARNING, ERROR).
    """
    etiqueta = EVENTOS.get(tipo_evento, tipo_evento)
    mensaje = f"[{tipo_evento}] {etiqueta}"
    if descripcion:
        mensaje += f" | {descripcion}"

    nivel_upper = nivel.upper()
    if nivel_upper == "ERROR":
        _logger.error(mensaje)
    elif nivel_upper == "WARNING":
        _logger.warning(mensaje)
    else:
        _logger.info(mensaje)


def obtener_eventos_recientes(max_eventos: int = 5) -> list:
    """
    Lee los últimos eventos del archivo de auditoría para mostrar en el dashboard.

    Returns:
        Lista de diccionarios con 'fecha' y 'descripcion'.
    """
    eventos = []
    try:
        if os.path.exists(_LOG_FILE):
            with open(_LOG_FILE, "r", encoding="utf-8") as f:
                lineas = f.readlines()
            for linea in lineas[-max_eventos:]:
                partes = linea.strip().split(" | ", 2)
                if len(partes) >= 3:
                    eventos.append({
                        "fecha": partes[0],
                        "descripcion": partes[2]
                    })
    except Exception:
        # No exponer detalles del error al dashboard
        pass
    eventos.reverse()
    return eventos
