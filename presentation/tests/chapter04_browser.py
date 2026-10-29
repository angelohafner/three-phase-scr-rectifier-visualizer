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
    comparison=ch[12]
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',comparison)
    assert page.locator('#ch4-mode').is_disabled()
    comparison_metrics=page.locator('#ch4-metrics').inner_text()
    for name in ['LCC μ','CCC μ','Δμ','LCC Q₁','CCC Q₁','ΔQ₁','LCC Ucomm','CCC Ucomm']:
        assert name in comparison_metrics,(name,comparison_metrics)
    assert page.locator('#ch4-qShunt').is_disabled()
    # Shunt reactive injection must exist only where the capacitor bank is connected.
    for k in [0,9,14]:
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',ch[k])
        assert page.locator('#ch4-qShunt').is_disabled()
        assert '0.000 p.u.' in page.locator('#ch4-metrics').inner_text()
    for k in [5,6]:
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',ch[k])
        assert page.locator('#ch4-qShunt').is_enabled()
        assert page.locator('#ch4-circuit svg [data-role="shunt-capacitor"]').count()==3
    main=ch[9]
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',main)
    assert 'How Series Capacitors Assist Thyristor Commutation' in page.locator('h1').inner_text()
    before=page.locator('#ch4-status').inner_text()
    assert page.locator('#ch4-circuit svg [data-valve]').count()==6
    # Current annotations must end before the nearest active valve column.
    clearances=page.evaluate('''() => {
      const svg=document.querySelector('#ch4-circuit svg');
      return ['a','b','c'].map((ph,i)=>{
        const box=svg.querySelector('#live-current-'+ph).getBBox();
        return box.x+box.width < [590,715,840][i]-9;
      });
    }''')
    assert all(clearances),clearances
    page.locator('#ch4-enlarge').click()
    assert page.locator('#zoom-overlay').get_attribute('aria-hidden')=='false'
    assert page.locator('#zoom-content svg [data-valve]').count()==6
    page.locator('#zoom-close').click()
    assert page.locator('#zoom-overlay').get_attribute('aria-hidden')=='true'
    old=page.locator('#ch4-chart-b').get_attribute('data-plot-limits')
    page.locator('#ch4-CmF').evaluate('e=>{e.value="12";e.dispatchEvent(new Event("input",{bubbles:true}))}')
    after=page.locator('#ch4-status').inner_text()
    assert page.locator('#ch4-circuit svg [data-role="series-capacitor"]').count()==3
    assert page.locator('#ch4-qShunt').is_disabled()
    # Firing and capacitance changes must preserve fixed graph domains.
    assert page.locator('#ch4-chart-a').get_attribute('data-axis-mode')=='fixed'
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
    page.locator('#ch4-enlarge').click()
    assert page.locator('#zoom-content svg[data-native-symbols="true"]').count()==1
    page.locator('#zoom-close').click()
    # Audit the entire new chapter at a typical notebook width as well.
    page.set_viewport_size({'width':1100,'height':760})
    for i in ch:
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',i)
        assert page.locator('#ch4-circuit svg').count()==1
        assert page.locator('#ch4-chart-a').get_attribute('data-axis-mode')=='fixed'
        assert page.locator('#ch4-chart-b').get_attribute('data-axis-mode')=='fixed'
        assert page.evaluate("document.querySelector('#slide').scrollWidth-document.querySelector('#slide').clientWidth")<=2
    assert not errors,errors
    browser.close()
print('PASS: 97 slides, 15 new CCC lessons, stable axes and dynamic parameter controls.')