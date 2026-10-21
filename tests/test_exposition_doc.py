from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


def test_guion_docx_valido_y_coherente_con_resultados():
    path = Path(__file__).resolve().parents[1] / 'entregables/Guion_Exposicion_DengueML_UPN.docx'
    assert path.is_file() and path.stat().st_size > 5000
    with ZipFile(path) as doc:
        names = set(doc.namelist())
        assert {'[Content_Types].xml', 'word/document.xml', 'word/styles.xml'} <= names
        xml = doc.read('word/document.xml')
        root = ET.fromstring(xml)
    text = ''.join(node.text or '' for node in root.iter() if node.tag.endswith('}t'))
    for required in ('Guion de exposición DengueML-UPN', 'A Introducción', 'G Guion oral',
                     'H Preguntas posibles', 'XGBoost', '62.2%', '16.7%', 'no se alcanzó'):
        assert required in text
