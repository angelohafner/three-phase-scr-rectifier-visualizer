"""Static validation for the generated standalone HTML."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / 'dist' / 'lcc_hvdc_interactive.html'

def test_standalone_html():
    assert FILE.exists()
    html = FILE.read_text(encoding='utf-8')
    assert '<!doctype html>' in html
    assert '<script src="https://' not in html
    assert '<script src="http://' not in html
    assert '<link href="https://' not in html

def test_embedded_reference_figures():
    html = FILE.read_text(encoding='utf-8')
    match = re.search(r'<script id="presentation-data" type="application/json">(.*?)</script>', html, re.S)
    assert match is not None
    data = json.loads(match.group(1))
    assert sum(len(v) for v in data['references'].values()) == 48
    assert len(data['diagrams']['hvdc']) == 144
