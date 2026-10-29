"""Browser regression for capacitor-voltage-led commutation teaching laboratory."""
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=Path(__file__).resolve().parents[2]/'dist'/'lcc_hvdc_interactive.html'
with sync_playwright() as pw:
    executable=Path(pw.chromium.executable_path)
    browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'],
        executable_path=str(executable) if executable.exists() else '/usr/bin/chromium')
    page=browser.new_page(viewport={'width':1600,'height':900})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('!!window.LCCPresentationTest')
    index=page.evaluate('''() => window.LCCPresentationTest.deck.findIndex(
      s=>s.type==='reactive'&&s.lesson==='series')''')
    assert index>=0
    page.evaluate('(index)=>window.LCCPresentationTest.setSlide(index)',index)
    assert page.locator('#ch4-cap-chart').count()==1
    assert page.locator('#ch4-chart-a').count()==1
    assert page.locator('#ch4-chart-b').count()==1
    assert page.locator('#ch4-series-reference').input_value()=='100'
    assert page.locator('#ch4-series-reference-info').is_visible()
    assert page.locator('#ch4-CmF').get_attribute('min')=='8'
    assert page.locator('#ch4-circuit svg [data-role="series-capacitor"]').count()==3
    assert page.locator('#ch4-circuit svg [data-role="dc-smoothing"]').count()==0

    def trace_names(name):
        return page.locator('#'+name).evaluate(
            'c=>JSON.parse(c.dataset.traceNames||"[]")')
    assert trace_names('ch4-cap-chart')==['v C,a','v C,b','v C,c']
    assert trace_names('ch4-chart-a')==['AC drive','Cap assist','Net drive','Net C ref']
    assert trace_names('ch4-chart-b')==['Incoming T6','Outgoing T4','I dc','Incoming ref']

    def snapshot():
        return page.evaluate('''() => {
           const stats=CCCChapter.getResults(),a=stats.main,r=stats.seriesReference;
           return {c:a.params.CmF,mu:a.avgMu,q:a.powers.Q,ref:r.avgMu,
             vC:CCCSeriesSensitivity.fromSolved(a).voltagePeak,
             capNow:CCCSeriesSensitivity.sample(a,8).capacitor,
             driveNow:CCCSeriesSensitivity.sample(a,8).net,
             limits:['ch4-cap-chart','ch4-chart-a','ch4-chart-b'].map(
               id=>JSON.parse(document.getElementById(id).dataset.plotLimits)),
             names:['ch4-cap-chart','ch4-chart-a','ch4-chart-b'].map(
               id=>JSON.parse(document.getElementById(id).dataset.traceNames))
           };
        }''')

    initial=snapshot()
    assert initial['limits'][0]['x']==[0,360]
    assert initial['limits'][0]['y']==[-.3,.3]
    assert initial['limits'][1]['x']==[0,30]
    assert initial['limits'][2]['x']==[0,30]
    assert page.locator('#ch4-cursor').get_attribute('max')=='30'

    def capacitance(value):
        page.locator('#ch4-CmF').evaluate('''(el,value)=>{
           el.value=String(value);el.dispatchEvent(new Event('input',{bubbles:true}));
        }''',value)
        return snapshot()

    small=capacitance(12)
    big=capacitance(100)
    assert small['c']==12 and big['c']==100
    assert small['mu']+3<big['mu'],(small,big)
    assert small['vC']>big['vC']*5,(small,big)
    assert abs(small['capNow']-big['capNow'])>.1
    assert abs(small['q']-big['q'])>.01
    assert small['limits']==initial['limits']==big['limits']
    assert abs(big['mu']-big['ref'])<1e-5

    capacitance(26)
    before=snapshot()
    page.locator('#ch4-series-reference').select_option('50')
    after=snapshot()
    assert page.evaluate('CCCChapter.getSeriesReferenceC()')==50
    assert abs(after['ref']-before['ref'])>.5
    assert after['limits']==before['limits']
    assert '50 mF' in page.locator('#ch4-series-reference-info').inner_text()
    page.locator('#ch4-series-reference').select_option('100')

    svgBefore=page.locator('#ch4-circuit svg #live-capacitor-a').text_content()
    page.locator('#ch4-cursor').evaluate('''el=>{
      el.value="17";el.dispatchEvent(new Event('input',{bubbles:true}));
    }''')
    svgAfter=page.locator('#ch4-circuit svg #live-capacitor-a').text_content()
    assert svgAfter!=svgBefore
    assert '@θ' in page.locator('#ch4-metrics').inner_text()

    page.locator('#ch4-sensitivity summary').click()
    page.wait_for_function('''()=>
      document.querySelectorAll('#ch4-sensitivity-table tbody tr').length===6''')
    assert page.locator('#ch4-sensitivity-table thead th').count()==8

    page.locator('#axis-scale-btn').click()
    full=snapshot()
    assert [lim['x'] for lim in full['limits']]==[[0,360],[0,60],[0,60]],full
    assert full['limits'][0]['y']==[-1.3,1.3]
    assert page.locator('#ch4-cursor').get_attribute('max')=='60'
    assert full['limits']!=initial['limits']
    page.locator('#ch4-CmF').evaluate('''el=>{
       el.value="8";el.dispatchEvent(new Event('input',{bubbles:true}));
    }''')
    assert snapshot()['limits']==full['limits']
    page.locator('#axis-scale-btn').click()
    focus=snapshot()
    assert focus['limits']==initial['limits']
    assert page.locator('#ch4-cursor').get_attribute('max')=='30'

    page.set_viewport_size({'width':390,'height':844})
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',index)
    for selector in ('#ch4-cap-chart','#ch4-chart-a','#ch4-chart-b','#ch4-circuit'):
        assert page.locator(selector).is_visible(),selector
    boxes=[page.locator(sel).bounding_box() for sel in
           ('#ch4-cap-chart','#ch4-chart-a')]
    assert all(b and b['height']>=100 for b in boxes),boxes
    assert boxes[0]['y']+boxes[0]['height']<=boxes[1]['y']+3,boxes
    assert not errors,errors
    browser.close()
print('PASS: series-C interactive capacitor phase voltages, commutating drive, current transfer, reference and FOCUS/FULL in desktop/mobile.')
