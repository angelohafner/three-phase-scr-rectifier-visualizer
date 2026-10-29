"""Offline regression: reactive-power chapter, CCC switching physics and controls."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'dist/lcc_hvdc_interactive.html'
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'],
        executable_path=str(Path(pw.chromium.executable_path)) if Path(pw.chromium.executable_path).exists() else '/usr/bin/chromium')
    page=browser.new_page(viewport={'width':1600,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('https://**/*',lambda route:route.abort())
    page.route('http://**/*',lambda route:route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('!!window.LCCPresentationTest')
    deck=page.evaluate('window.LCCPresentationTest.deck')
    assert len(deck)==97,len(deck)
    ch=[i for i,s in enumerate(deck) if s['type']=='reactive']
    assert len(ch)==15
    for idx in ch:
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',idx)
        assert 'INVALID' not in page.locator('#ch4-status').inner_text()
        assert page.locator('#ch4-circuit svg').count()==1
        svg=page.locator('#ch4-circuit svg')
        assert svg.get_attribute('data-native-symbols')=='true'
        assert svg.locator('[data-role="scr"][data-symbol-source="native-instance"]').count()==6
        assert svg.locator('[data-symbol="schemdraw.elements.Transformer"]').count()==3
        assert svg.locator('[data-symbol="schemdraw.elements.SourceI"]').count()==1
        assert svg.get_attribute('data-dynamic-state')=='synchronized'
        assert page.locator('#ch4-chart-a').evaluate('c=>c.width>150')
        assert page.locator('#ch4-chart-b').evaluate('c=>c.dataset.axisMode==="fixed"')
    main=ch[9]
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',main)
    assert 'How Series Capacitors Assist Thyristor Commutation' in page.locator('h1').inner_text()
    before=page.locator('#ch4-status').inner_text()
    assert page.locator('#ch4-circuit svg [data-valve]').count()==6
    old=page.locator('#ch4-chart-b').get_attribute('data-plot-limits')
    page.locator('#ch4-CmF').evaluate('e=>{e.value="12";e.dispatchEvent(new Event("input",{bubbles:true}))}')
    after=page.locator('#ch4-status').inner_text()
    assert page.locator('#ch4-circuit svg [data-role="series-capacitor"]').count()==3
    assert before!=after,(before,after)
    assert old==page.locator('#ch4-chart-b').get_attribute('data-plot-limits')
    page.locator('#ch4-mode').select_option('LCC')
    assert page.locator('#ch4-CmF').is_disabled()
    assert page.locator('#ch4-circuit svg [data-role="series-capacitor"]').count()==0
    assert 'LCC · ' in page.locator('#ch4-status').inner_text()
    page.locator('#ch4-mode').select_option('CCC')
    assert page.locator('#ch4-CmF').is_enabled()
    page.locator('#axis-scale-btn').click()
    assert old!=page.locator('#ch4-chart-b').get_attribute('data-plot-limits')
    page.set_viewport_size({'width':390,'height':844})
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',main)
    assert page.locator('#ch4-circuit').is_visible()
    assert page.locator('#ch4-chart-a').is_visible()
    assert page.locator('#ch4-chart-b').is_visible()
    assert not errors,errors
    browser.close()
print('PASS: 97 slides, 15 new CCC lessons, stable axes and dynamic parameter controls.')