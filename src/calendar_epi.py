"""Semanas domingo–sábado; semana 1 contiene el 4 de enero (convención CDC)."""
from datetime import date, timedelta


def inicio_ano(ano):
    enero4 = date(int(ano), 1, 4)
    return enero4 - timedelta(days=(enero4.weekday() + 1) % 7)


def fecha_semana(ano, semana):
    ano, semana = int(ano), int(semana)
    total = (inicio_ano(ano + 1) - inicio_ano(ano)).days // 7
    if not 1 <= semana <= total:
        raise ValueError(f"Semana inválida: {ano}-SE{semana}")
    return inicio_ano(ano) + timedelta(weeks=semana - 1)


def siguiente_semana(ano, semana):
    fecha = fecha_semana(ano, semana) + timedelta(weeks=1)
    if fecha >= inicio_ano(int(ano) + 1):
        return int(ano) + 1, 1
    return int(ano), int(semana) + 1
