"""Continuous pointer-capture and electrical coherence of the current-source slides."""
from __future__ import annotations

from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0,str(ROOT))
HTML=ROOT/'dist/lcc_hvdc_interactive.html'
if not HTML.exists():
    raise SystemExit(f'Build the HTML before testing: {HTML}')

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',
                              args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    page=browser.new_page(viewport={'width':1700,'height':950})
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('Boolean(window.LCCPresentationTest)',timeout=55000)
    assert page.evaluate('window.LCCPresentationTest.deck.length')==82
    indices=page.evaluate('window.LCCPresentationTest.deck.map((s,i)=>s.type==="current_source"?i:null).filter(i=>i!==null)')
    assert len(indices)==9,indices
    # Validate source-current equations against the independently coded Python model.
    from current_source_model import CurrentSourceSettings, sample as python_sample, overlap_degrees
    for mode in ('manual', 'calculated'):
        for angle in (0, 1, 10, 30, 60, 62, 68, 72, 95, 120, 185, 359):
            config=CurrentSourceSettings(overlap_mode=mode,mu_deg=12)
            expected=python_sample(angle,config)
            actual=page.evaluate("([a,m]) => CurrentSourceModel.sample(a, {alphaR:15,muR:12,idc:1,vPeak:1,csLc:.2,csOverlapMode:m})",[angle,mode])
            assert abs(actual['mu']-expected['mu'])<1e-9
            for name in expected['scr']:
                assert abs(actual['scr'][name]-expected['scr'][name])<1e-9,(angle,name,mode)
            assert abs(actual['dc']-expected['dc'])<1e-9,(angle,mode,'Vdc')
    signs=page.evaluate('CurrentSourceModel.inverterPower(window.LCCPresentationTest.params)')
    assert signs['rectifier']>0 and signs['inverter']<0,signs
    for idx in indices:
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',idx)
        assert page.locator('#cs-circuit svg').count()==1,(idx,'circuit')
        assert page.locator('#cs-left').evaluate('(e)=>e.width>100')
        assert page.locator('#cs-right').evaluate('(e)=>e.width>100')
        assert page.locator('#cs-angle').count()==1
        assert page.locator('#cs-status').inner_text()
        assert page.locator('#cs-left').get_attribute('data-valid')=='true'
    comm=indices[3]
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',comm)
    page.evaluate('window.LCCPresentationTest.setTheta(62)')
    assert page.locator('#cs-left').get_attribute('data-incoming')=='T3'
    assert page.locator('#cs-left').get_attribute('data-outgoing')=='T1'
    slider=page.locator('#cs-angle');slider.scroll_into_view_if_needed()
    page.evaluate('window.__sourceRange=document.getElementById("cs-angle")')
    bb=slider.bounding_box();assert bb is not None
    x0=bb['x']+8;travel=bb['width']-16;y=bb['y']+bb['height']/2
    start=float(slider.input_value())
    page.mouse.move(x0+travel*start/360,y);page.mouse.down()
    for dest in (75,135,250,320):
        page.mouse.move(x0+travel*dest/360,y,steps=5)
        page.wait_for_timeout(60)
        assert page.evaluate('window.__sourceRange===document.getElementById("cs-angle")')
        assert abs(float(slider.input_value())-dest)<5,(dest,slider.input_value())
    page.mouse.up()
    # Computed overlap must depend on imposed DC current and AC inductance.
    page.locator('#cs-overlap-mode').select_option('calculated')
    before=float(page.locator('#cs-left').get_attribute('data-mu'))
    page.locator('#cs-csLc').evaluate('(e)=>{e.value="0.30";e.dispatchEvent(new Event("input",{bubbles:true}));}')
    page.wait_for_timeout(100)
    after=float(page.locator('#cs-left').get_attribute('data-mu'))
    assert after>before,(before,after)
    # Source model has no DC smoothing reactor, while RLE does.
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',indices[0])
    assert page.locator('#cs-loadL').is_disabled()
    assert page.locator('#cs-loadR').is_disabled()
    assert page.locator('#cs-loadE').is_disabled()
    page.locator('#cs-topology').select_option('RLE')
    assert page.locator('#cs-loadL').is_enabled()
    # In both models, the RLE diagram and comparison use the displayed firing angle.
    assert page.locator('#cs-circuit svg').count()==1
    page.locator('#cs-alphaR').evaluate('(e)=>{e.value="30";e.dispatchEvent(new Event("input",{bubbles:true}));}')
    page.wait_for_timeout(100)
    assert abs(page.evaluate('window.LCCPresentationTest.params.alphaR')-30)<1e-12
    actual = page.evaluate('LoadCharts.model("RLE", {...window.LCCPresentationTest.params, alphaLoad: 30}).config.alpha')
    assert abs(actual-30)<1e-12
    # Existing chapters are still navigable.
    for side in ('fundamentals','rectifier','inverter','hvdc'):
        idx=page.evaluate('side=>window.LCCPresentationTest.deck.findIndex(s=>s.side===side&&s.type==="chapter")',side)
        assert idx>=0
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',idx)
        assert page.locator('article#slide').count()==1
    assert not errors,errors
    browser.close()
print('PASS: 9 current-source slides, continuous drag, overlap physics and old chapters.')
