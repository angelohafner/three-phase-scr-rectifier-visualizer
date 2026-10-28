"""Checks for the HTML bundle and JavaScript source (no network required)."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'dist'/'lcc_hvdc_interactive.html'


def test_standalone_html_present():
    assert HTML.exists()
    text=HTML.read_text(encoding='utf-8')
    assert '<!doctype html>' in text
    assert 'id="presentation-data"' in text
    assert text.count('id="presentation-data"') == 1
    assert not re.search(r'<(?:script|link)\b[^>]+(?:src|href)=["\']https?://', text)


def test_48_reference_states_available():
    text=HTML.read_text(encoding='utf-8')
    import json
    m=re.search(r'<script id="presentation-data" type="application/json">(.*?)</script>',text,re.S)
    assert m is not None
    data=json.loads(m.group(1))
    assert sum(map(len,data['references'].values()))==48
    assert len(data['diagrams']['hvdc'])==144
    assert 'window.LCCPresentationTest' in text
    assert len(data['load_figures'])==28
    assert 'RectifierLoads' not in text or 'LoadModel' in text
    assert 'RECTIFIER · Normal conduction with R load' in text
    assert 'RECTIFIER · Normal conduction with RL load' in text


def test_source_functions_are_not_placeholders():
    s=(ROOT/'presentation/src/waveforms.js').read_text(encoding='utf-8')
    for name in ('jointSchedule','function sample(','stateInfo','function windows('):
        assert name in s


def test_four_loads_scr_voltages_and_light_document_theme():
    html=HTML.read_text(encoding='utf-8')
    for label in ('SCR voltages','RLE','LE','TechnicalMath','SCRVoltage','Independent educational material'):
        assert label in html
    assert '<!--INLINE_PTI_CSS-->' not in html
