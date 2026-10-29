"""Validate fixed chart domains under parameter changes in the offline HTML."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'dist'/'lcc_hvdc_interactive.html'

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'],
        executable_path=str(Path(pw.chromium.executable_path)) if Path(pw.chromium.executable_path).exists() else '/usr/bin/chromium')
    page=browser.new_page(viewport={'width':1600,'height':900})
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    errors=[]
    page.on('pageerror',lambda exc:errors.append(str(exc)))
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('!!window.LCCPresentationTest')
    deck=page.evaluate('window.LCCPresentationTest.deck')
    assert len(deck)==86
    assert page.evaluate('window.LCCPresentationTest.axisPreset()')=='focus'

    def snapshot():
        return page.evaluate("""() => Array.from(document.querySelectorAll('#slide canvas')).map(c => ({
            mode:c.dataset.axisMode, limits:JSON.parse(c.dataset.axisLimits||'[]'),
            valid:c.dataset.valid
        }))""")

    for i,s in enumerate(deck):
        if s['type'] not in ('fundamentals','load','state','current_source'):
            continue
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',i)
        plotted=snapshot()
        assert plotted,(i,s)
        for chart in plotted:
            assert chart['mode']=='fixed' and chart['limits'],(i,s,chart)
            for ax in chart['limits']:
                assert ax['min']<ax['max'] and ax['x'] in ([0,360],[0,.35]),(i,s,ax)
    print('Fixed metadata present across all interactive slides.',flush=True)

    lesson_index=lambda typ,name:next(i for i,s in enumerate(deck) if s['type']==typ and s.get('lesson')==name)
    stage_index=lambda side:next(i for i,s in enumerate(deck) if s['type']=='state' and s['side']==side)
    cases=[
        (lesson_index('fundamentals','rl_circuit'),{'hV':260,'hR':2,'hL':140}),
        (lesson_index('load','rle_intro'),{'vPeak':2,'loadR':.2,'loadL':.1,'loadE':1.8}),
        (lesson_index('load','le_intro'),{'vPeak':2,'loadL':.1,'loadI0':2,'loadE':0}),
        (lesson_index('load','advanced_compare'),{'vPeak':2,'loadR':.2,'loadL':.1,'loadI0':2}),
        (stage_index('rectifier'),{'vPeak':2,'idc':2,'muR':40}),
        (stage_index('inverter'),{'vPeak':2,'idc':2,'alphaI':130,'muI':25}),
        (stage_index('hvdc'),{'vPeak':2,'idc':2,'muR':40,'muI':25}),
        (lesson_index('current_source','controller'),{'idc':2,'loadR':.2,'loadL':.1,'loadE':1.8}),
    ]
    defaults={'idc':1,'vPeak':1,'loadR':1,'loadL':8,'loadE':.2,'loadI0':.5,
              'hV':120,'hR':12,'hL':70,'muR':12,'muI':15,'alphaI':145}
    for i,changes in cases:
        page.evaluate('''([i,defaults])=>{
            Object.assign(window.LCCPresentationTest.params,defaults);
            window.LCCPresentationTest.setSlide(i);
        }''',[i,defaults])
        before=snapshot()
        page.evaluate('''([i,changes])=>{
            Object.assign(window.LCCPresentationTest.params,changes);
            window.LCCPresentationTest.setSlide(i);
        }''',[i,changes])
        after=snapshot()
        assert [x['limits'] for x in before]==[x['limits'] for x in after],(i,before,after)
        assert all(x['mode']=='fixed' for x in after),(i,after)

    i=lesson_index('load','advanced_compare')
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',i)
    bounds=snapshot()[0]['limits']
    assert len(bounds)==4,bounds
    assert bounds[0]['right']==bounds[1]['right']==bounds[3]['right'],bounds
    # Focus keeps the current scale comparable across all four load models.
    assert bounds[2]['right']==bounds[3]['right'],bounds
    page.evaluate("window.LCCPresentationTest.setAxisPreset('full')")
    full_bounds=snapshot()[0]['limits']
    # Full spans LE's physically large one-cycle envelope independently.
    assert full_bounds[2]['right'][1]>full_bounds[3]['right'][1],full_bounds
    page.evaluate("window.LCCPresentationTest.setAxisPreset('focus')")
    # The screenshot regression: RLE versus ideal DC current must use a readable 0–3 p.u.
    defaults={'idc':1,'vPeak':1,'loadR':1,'loadL':8,'loadE':.2,'loadI0':.5,
              'hV':120,'hR':12,'hL':70,'muR':12,'muI':15,'alphaI':145}
    page.evaluate('''([i,defaults])=>{
       Object.assign(window.LCCPresentationTest.params,defaults);
       window.LCCPresentationTest.setSlide(i);
    }''',[lesson_index('current_source','intro'),defaults])
    focus_chart=page.locator('#cs-left')
    focus_limits=page.evaluate('JSON.parse(document.getElementById("cs-left").dataset.axisLimits)')
    assert focus_limits[0]['kind']=='loadCurrent' and focus_limits[0]['max']==3,focus_limits
    assert focus_chart.get_attribute('data-axis-clipped')=='false'
    page.locator('#axis-scale-btn').click()
    full_limits=page.evaluate('JSON.parse(document.getElementById("cs-left").dataset.axisLimits)')
    assert full_limits[0]['max']>=20,full_limits
    page.locator('#cs-loadR').evaluate('''el=>{
      el.value="0.2";el.dispatchEvent(new Event("input",{bubbles:true}));
    }''')
    page.wait_for_timeout(150)
    assert page.locator('#cs-left').get_attribute('data-axis-clipped')=='false'
    assert page.evaluate('JSON.parse(document.getElementById("cs-left").dataset.axisLimits)')==full_limits
    page.locator('#axis-scale-btn').click()
    page.wait_for_timeout(150)
    assert page.evaluate('JSON.parse(document.getElementById("cs-left").dataset.axisLimits)')==focus_limits
    assert page.locator('#cs-left').get_attribute('data-axis-clipped')=='true'
    # The settings control uses the same preset and has no slider-dependent rescaling.
    page.locator('#settings-open').click()
    page.locator('#axis-scale-settings').click()
    page.locator('#settings-close').click()
    assert page.locator('#cs-left').get_attribute('data-axis-clipped')=='false'
    assert page.evaluate('window.LCCPresentationTest.axisPreset()')=='full'
    assert not errors,errors
    print('86-slide fixed-axis audit, readable RLE focus and full-envelope switching verified.',flush=True)
    browser.close()
