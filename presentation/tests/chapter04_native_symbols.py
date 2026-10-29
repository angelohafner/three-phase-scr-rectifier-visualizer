"""Chapter 04 native Schemdraw provenance and topological consistency checks."""
from collections import Counter
import math
from pathlib import Path
import json
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'presentation'/'assets'/'chapter04'
counts_expected={'SCR':6,'Transformer':3,'SourceSin':3,'Inductor':3,
                 'ResistorIEEE':3,'Ground':2,'Dot':5}

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
    # Ensure the current-source label does not intersect the native source circle.
    current_label=root.find(".//*[@id='dc-current-label']")
    assert current_label is not None and float(current_label.get('x'))>1040
    p=root.find(".//*[@id='bus-dc-positive']")
    n=root.find(".//*[@id='bus-dc-negative']")
    assert p is not None and n is not None and p.get('d')!=n.get('d')
    assert root.find(".//*[@id='dc-positive-terminal']") is not None
    assert root.find(".//*[@id='dc-negative-terminal']") is not None
    assert root.find(".//*[@id='dc-current-source']") is None
    assert root.find(".//*[@id='smoothing-inductor']") is None
    assert counts['SourceI']==0,(variant,counts)

    # Every native capacitor plate must be joined to each branch terminal.
    # Verify the actual SVG conductor geometry, not only nominal metadata.
    for cap in root.findall('.//*[@data-symbol="schemdraw.elements.Capacitor"]'):
        key=cap.get('id')
        left=tuple(float(v) for v in cap.get('data-contact-left').split(','))
        right=tuple(float(v) for v in cap.get('data-contact-right').split(','))
        start=tuple(float(v) for v in cap.get('data-terminal-start').split(','))
        end=tuple(float(v) for v in cap.get('data-terminal-end').split(','))
        for suffix,a,b in (('-lead-in',start,left),('-lead-out',right,end)):
            lead=root.find(f".//*[@id='{key+suffix}']")
            assert lead is not None,(variant,key,suffix)
            points=[tuple(float(v) for v in xy.split(','))
                    for xy in lead.get('d').replace('M ','').split(' L ')]
            assert len(points)==2
            assert all(math.dist(points[k],target)<.002 for k,target in enumerate((a,b)))
        # Native plate middles must coincide with the documented lead contacts.
        plates=cap.findall('./{http://www.w3.org/2000/svg}path')
        assert len(plates)==2,(variant,key,len(plates))
        for plate,contact in zip(plates,(left,right)):
            coords=[tuple(float(v) for v in pair.split(','))
                    for pair in plate.get('d').replace('M ','').split(' L ')]
            center=((coords[0][0]+coords[-1][0])/2,
                    (coords[0][1]+coords[-1][1])/2)
            assert math.dist(center,contact)<.002,(variant,key,center,contact)
        assert math.dist(left,right)>5,(variant,key)
    meta=json.loads(manifest.read_text(encoding='utf-8'))
    assert meta['topology']==('CCC' if variant.startswith('ccc') else 'LCC')
    assert meta['series_capacitors']==(3 if variant.startswith('ccc') else 0)
    assert meta['shunt_capacitors']==(3 if variant.endswith('_shunt') else 0)
    assert meta['dc_positive_y']<meta['dc_negative_y']
print('PASS: 4 native Schemdraw variants, all electrical components and connections.')
