"""Indicador relativo experimental; no es una alerta sanitaria calibrada."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Umbrales:
    medio: float = 0.8
    alto: float = 1.5
    min_semanas: int = 12

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.medio, self.alto)):
            raise ValueError('Los umbrales deben ser finitos.')
        if not 0 < self.medio < self.alto:
            raise ValueError('Se requiere 0 < medio < alto.')
        if not isinstance(self.min_semanas, int) or self.min_semanas < 4:
            raise ValueError('La ventana mínima debe ser un entero >= 4.')


def evaluar_riesgo(prediccion, referencia, n_semanas, umbrales=None):
    u = umbrales or Umbrales()
    if not all(math.isfinite(float(x)) and x >= 0 for x in (prediccion, referencia)):
        raise ValueError('Predicción y referencia deben ser finitas y no negativas.')
    if not isinstance(n_semanas, int) or n_semanas < 0:
        raise ValueError('Número de semanas inválido.')
    if n_semanas < u.min_semanas:
        return dict(nivel='Sin datos suficientes', razon=f'Se requieren {u.min_semanas} semanas.', razon_relativa=None)
    if referencia == 0:
        return dict(nivel='Evaluación especial', razon='Referencia cero: no se puede calcular una razón relativa.', razon_relativa=None)
    ratio = float(prediccion / referencia)
    nivel = 'ALTO' if ratio > u.alto else 'MEDIO' if ratio > u.medio else 'BAJO'
    return dict(nivel=nivel, razon='Umbrales experimentales, sin calibración sanitaria.', razon_relativa=ratio)
