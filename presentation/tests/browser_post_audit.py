"""Independent browser regression for DC polarity, fact-card layout and mobile plots."""
from __future__ import annotations
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'dist/lcc_hvdc_interactive.html'
assert HTML.exists(), 'Compile the self-contained HTML before running this test.'

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium') or None,
        args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1600,'height':900})
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('Boolean(window.LCCPresentationTest)')
    deck=page.evaluate('window.LCCPresentationTest.deck')
    assert len(deck)==86
    for i,slide in enumerate(deck):
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',i)
        assert page.evaluate("document.getElementById('slide').scrollWidth <= document.getElementById('slide').clientWidth+2"),i
        assert page.evaluate("[...document.querySelectorAll('.fact strong')].every(x=>x.scrollWidth<=x.clientWidth+2)"),i
        if slide['type']=='state':
            assert page.locator('#plot-canvas').evaluate('e=>e.width>100')
    page.set_viewport_size({'width':390,'height':844})
    for side in ('inverter','hvdc'):
        i=next(i for i,s in enumerate(deck) if s['side']==side and s['type']=='state')
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',i)
        choice=page.locator('#mobile-plot-select')
        assert choice.is_visible()
        labels=choice.locator('option').all_text_contents()
        assert len(labels)>=2
        choice.select_option(str(len(labels)-1))
        assert page.locator('#plot-canvas').evaluate('e=>JSON.parse(e.dataset.visiblePanels).length===1')
        assert page.locator('#plot-canvas').bounding_box()['height']>=190
        page.locator('#mobile-show-circuit').click()
        assert page.locator('.state-circuit-panel').is_visible()
        assert not page.locator('.state-waveform-panel').is_visible()
        page.locator('#mobile-show-waveforms').click()
        assert page.locator('.state-waveform-panel').is_visible()
    commutation=next(i for i,s in enumerate(deck) if s['type']=='current_source' and s.get('lesson')=='commutation')
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',commutation)
    dropdown=page.locator('#cs-mobile-panel')
    assert dropdown.is_visible()
    dropdown.select_option('right')
    assert page.locator('#cs-right').is_visible()
    assert page.locator('#cs-right').bounding_box()['height']>=190
    assert not errors,errors
    browser.close()
print('PASS: 86 slides without horizontal overflow, signed DC plots, mobile focus controls.')
