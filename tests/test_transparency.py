import json
from pathlib import Path

from src.transparency import FUENTES, archivos_exportables


def test_transparencia_no_promete_original_ausente():
    base = Path(__file__).resolve().parents[1]
    bundle = json.loads((base / 'models/actual.json').read_text(encoding='utf-8'))
    exports = archivos_exportables(base, bundle)
    assert 'Dataset procesado (CSV)' in exports
    assert 'Resultados walk-forward (CSV)' in exports
    assert all(path.is_file() for path in exports.values())
    assert not any('original' in path.name.lower() for path in exports.values())
    assert any('datosabiertos.gob.pe' in source['url'] for source in FUENTES)
    assert any('dge.gob.pe' in source['url'] for source in FUENTES)
    assert any('gob.pe' in source['url'] for source in FUENTES)


def test_cobertura_separa_disponibilidad_oficial_de_integracion():
    base = Path(__file__).resolve().parents[1]
    cobertura = json.loads((base / 'reports/cobertura_disponibilidad_2020_2026.json').read_text(encoding='utf-8'))
    assert cobertura['integrado_en_modelo'] == {
        '2020': False, '2021': False, '2022': False, '2023': True,
        '2024': True, '2025': False, '2026': False,
    }
    assert cobertura['cobertura_local']['celdas_distrito_semana'] == 1456
    assert cobertura['cobertura_local']['celdas_con_registros'] + cobertura['cobertura_local']['celdas_sin_registros'] == 1456
    assert 'no equivalen a cero' in cobertura['cobertura_local']['advertencia']
    assert any('clima-salud' in source['url'] for source in FUENTES)
