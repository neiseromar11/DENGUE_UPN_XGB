"""Cachés públicas, acotadas y vinculadas a versiones inmutables."""
import json
from pathlib import Path
from threading import RLock
import streamlit as st
import pandas as pd
try:
    from .etl import BASE, sha256
    from .features import generar_features
    from .model import cargar_modelo
    from .dashboard import pronosticar
except ImportError:
    from etl import BASE, sha256
    from features import generar_features
    from model import cargar_modelo
    from dashboard import pronosticar


def leer_bundle(base=BASE):
    # El puntero es pequeño y se lee en cada rerun para detectar publicaciones.
    return json.loads((Path(base) / 'models/actual.json').read_text(encoding='utf-8'))


@st.cache_data(max_entries=4, show_spinner=False)
def preparar_version(ruta, firma):
    if sha256(ruta) != firma:
        raise ValueError('Los datos publicados fueron alterados.')
    datos = pd.read_csv(ruta)
    return datos, generar_features(datos)


@st.cache_resource(max_entries=4, show_spinner=False)
def recurso_modelo(ruta, firma):
    if sha256(ruta) != firma:
        raise ValueError('El modelo publicado fue alterado.')
    # El recurso es compartido: se evita mutarlo y se serializa su inferencia.
    return cargar_modelo(ruta), RLock()


@st.cache_data(max_entries=8, show_spinner=False)
def leer_json_version(ruta, version):
    return json.loads(Path(ruta).read_text(encoding='utf-8'))


@st.cache_data(max_entries=180, show_spinner=False)
def predecir_version(bundle, distrito, horizonte, base=str(BASE)):
    base = Path(base)
    datos, features = preparar_version(str(base / bundle['datos']), bundle['sha256_datos'])
    if bundle['metodo'] == 'baseline':
        return pronosticar(features, distrito, horizonte, datos=datos)
    modelo, lock = recurso_modelo(str(base / bundle['modelo']), bundle['sha256_modelo'])
    with lock:
        return pronosticar(features, distrito, horizonte, modelo, datos)
