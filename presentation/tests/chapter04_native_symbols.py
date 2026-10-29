"""Chapter 04 native Schemdraw provenance and topological consistency checks."""
from collections import Counter
from pathlib import Path
import json
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'presentation'/'assets'/'chapter04'
counts_expected={'SCR':6,'Transformer':3,'SourceSin':3,'Inductor':4,
                 'ResistorIEEE':3,'SourceI':1,'Ground':2,'Dot':3}

for variant in ('lcc','ccc','lcc_shunt','ccc_shunt'):
    svg=DIR/(variant+'.svg')
    manifest=DIR/(variant+'.manifest.json')
    assert svg.is_file() and manifest.is_file(),variant
    root=ET.parse(svg).getroot()
    assert root.get('data-native-symbols')=='true'
    assert root.get('data-library')=='schemdraw'
    elems=root.findall('.//*[@data-symbol]')
    counts=Counter(el.get('data-symbol').split('.')[-1] for el in elems)
    for kind,n in counts_expected.items():
        assert counts[kind]==n,(variant,kind,counts)
    cap_count=(3 if variant.startswith('ccc') else 0)+(3 if variant.endswith('_shunt') else 0)
    assert counts['Capacitor']==cap_count,(variant,counts)
    for node in elems:
        assert node.get('data-symbol-source')=='native-instance',(variant,node.attrib)
        assert len(node)>0,(variant,node.attrib)
    scr=root.findall('.//*[@data-valve]')
    assert {valve.get('data-valve') for valve in scr}=={'T1','T2','T3','T4','T5','T6'}
    assert all(x.get('data-terminal-start') and x.get('data-terminal-end') for x in scr)
    for phase in 'abc':
        for role in ('transformer','leakage','resistance','source','junction'):
            assert root.find(f".//*[@id='{role}-{phase}']") is not None,(variant,role,phase)
        assert root.find(f".//*[@id='feed-{phase}-post']") is not None
        assert root.find(f".//*[@id='live-current-{phase}']") is not None
        if variant.startswith('ccc'):
            el=root.find(f".//*[@id='series-{phase}']")
            assert el is not None and el.get('data-role')=='series-capacitor'
        else:
            assert root.find(f".//*[@id='series-{phase}']") is None
    p=root.find(".//*[@id='bus-dc-positive']")
    n=root.find(".//*[@id='bus-dc-negative']")
    assert p is not None and n is not None and p.get('d')!=n.get('d')
    meta=json.loads(manifest.read_text(encoding='utf-8'))
    assert meta['topology']==('CCC' if variant.startswith('ccc') else 'LCC')
    assert meta['series_capacitors']==(3 if variant.startswith('ccc') else 0)
    assert meta['shunt_capacitors']==(3 if variant.endswith('_shunt') else 0)
    assert meta['dc_positive_y']<meta['dc_negative_y']
print('PASS: 4 native Schemdraw variants, all electrical components and connections.')
