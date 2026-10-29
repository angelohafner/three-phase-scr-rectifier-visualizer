"""Verify four simplified reactive-power/CCC laboratories in the offline HTML."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'dist/lcc_hvdc_interactive.html'
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'],
        executable_path=str(Path(pw.chromium.executable_path)) if Path(pw.chromium.executable_path).exists() else '/usr/bin/chromium')
    page=browser.new_page(viewport={'width':1600,'height':900})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('!!window.LCCPresentationTest')
    deck=page.evaluate('window.LCCPresentationTest.deck')
    assert len(deck)==86,len(deck)
    labs={s['lesson']:i for i,s in enumerate(deck) if s['type']=='reactive'}
    assert list(labs)==['lcc','shunt','series','compare'],labs

    def visit(name):
        page.evaluate('(index)=>window.LCCPresentationTest.setSlide(index)',labs[name])
        assert page.locator('#ch4-chart-a').get_attribute('data-axis-mode')=='fixed'
        assert page.locator('#ch4-chart-b').get_attribute('data-axis-mode')=='fixed'
        assert 'OUTSIDE VALID' not in page.locator('#ch4-status').inner_text()

    def axis_limits():
        return [page.locator('#'+name).get_attribute('data-plot-limits')
                for name in ['ch4-chart-a','ch4-chart-b']]

    visit('lcc')
    assert page.locator('#ch4-circuit svg').count()==1
    assert page.locator('#ch4-circuit svg [data-valve]').count()==6
    assert page.locator('#ch4-circuit svg [data-role="series-capacitor"]').count()==0
    assert page.locator('#ch4-circuit svg [data-symbol="schemdraw.elements.SourceI"]').count()==0
    assert page.locator('#ch4-circuit svg [id="dc-current-label"]').count()==1
    assert page.locator('#ch4-circuit svg [id="smoothing-inductor"]').count()==0
    assert page.locator('#ch4-CmF').is_hidden()
    assert page.locator('#ch4-qShunt').is_hidden()
    before=page.evaluate('CCCChapter.getResults().main.powers.Q')
    scale=axis_limits()
    page.locator('#ch4-alpha').evaluate('el=>{el.value="30";el.dispatchEvent(new Event("input",{bubbles:true}))}')
    after=page.evaluate('CCCChapter.getResults().main.powers.Q')
    assert abs(after-before)>.01,(before,after)
    assert axis_limits()==scale,'Firing-angle change altered chart limits'
    page.locator('#ch4-enlarge').click()
    assert page.locator('#zoom-content svg').count()==1
    page.locator('#zoom-close').click()

    visit('shunt')
    assert page.locator('#ch4-qShunt').is_visible()
    assert page.locator('#ch4-CmF').is_hidden()
    assert page.locator('#ch4-circuit svg [data-role="shunt-capacitor"]').count()==3
    base=page.evaluate('CCCChapter.getResults().main.powers')
    scale=axis_limits()
    page.locator('#ch4-qShunt').evaluate('el=>{el.value="0.9";el.dispatchEvent(new Event("input",{bubbles:true}))}')
    changed=page.evaluate('CCCChapter.getResults().main.powers')
    assert abs(base['Q']-changed['Q'])<1e-8,'Shunt incorrectly changed intrinsic converter Q'
    assert changed['Qgrid']<base['Qgrid'],'Shunt should reduce reactive demand from the grid'
    assert axis_limits()==scale

    visit('series')
    assert page.locator('#ch4-CmF').is_visible()
    assert page.locator('#ch4-qShunt').is_hidden()
    assert page.locator('#ch4-circuit svg [data-role="series-capacitor"]').count()==3
    old_mu=page.evaluate('CCCChapter.getResults().main.avgMu')
    scale=axis_limits()
    page.locator('#ch4-CmF').evaluate('el=>{el.value="70";el.dispatchEvent(new Event("input",{bubbles:true}))}')
    new_mu=page.evaluate('CCCChapter.getResults().main.avgMu')
    assert abs(new_mu-old_mu)>.15,'Series C did not change calculated overlap'
    assert axis_limits()==scale

    page.evaluate('''() => {
      Object.assign(CCCChapter.settings,{alpha:15,idc:.8,vPeak:1,LmH:.24,CmF:26,qShunt:.4});
    }''')
    visit('compare')
    assert page.locator('#ch4-circuit svg').count()==2
    assert page.locator('#ch4-circuit svg[data-topology="LCC"]').count()==1
    assert page.locator('#ch4-circuit svg[data-topology="CCC"]').count()==1
    # Both immutable native SVGs are focused on the commutation area.
    assert all(svg.get_attribute('viewBox')=='315 58 640 456'
               for svg in page.locator('#ch4-circuit svg').all())
    assert page.evaluate('''() => JSON.parse(
       document.getElementById('ch4-chart-b').dataset.plotLimits).y''')==[0,.85]
    assert page.locator('#ch4-compare-basis').input_value()=='equal-power'
    assert page.evaluate('CCCChapter.getComparisonBasis()')=='equal-power'
    metrics=page.locator('#ch4-metrics').inner_text()
    for name in ('P₁ LCC','P₁ CCC','ΔP₁','Q₁ LCC','Q₁ CCC','ΔQ₁',
                 'Q/P LCC','Q/P CCC','PF₁ LCC','PF₁ CCC',
                 'α LCC','α CCC','μ LCC','μ CCC'):
        assert name in metrics,(name,metrics)
    equal=page.evaluate('''() => {
      const {main,lcc,matched}=CCCChapter.getResults();
      return {P_LCC:lcc.powers.P,P_CCC:main.powers.P,
        Q_LCC:lcc.powers.Q,Q_CCC:main.powers.Q,
        alpha_LCC:lcc.params.alpha,alpha_CCC:main.params.alpha,
        idc_LCC:lcc.params.idc,idc_CCC:main.params.idc,
        residual:matched.errorP,ratio:main.powers.Q/main.powers.P};
    }''')
    assert abs(equal['P_CCC']-equal['P_LCC'])<5e-7,equal
    assert equal['idc_LCC']==equal['idc_CCC'],equal
    assert equal['alpha_CCC']>equal['alpha_LCC'],equal
    # Same-active-power comparison can reverse the nominal CCC Q advantage.
    assert equal['Q_CCC']>equal['Q_LCC'],equal
    domain=axis_limits()
    page.locator('#ch4-compare-basis').select_option('same-settings')
    same=page.evaluate('''() => {
      const {main,lcc}=CCCChapter.getResults();
      return {P_LCC:lcc.powers.P,P_CCC:main.powers.P,
        Q_LCC:lcc.powers.Q,Q_CCC:main.powers.Q,
        alpha_LCC:lcc.params.alpha,alpha_CCC:main.params.alpha};
    }''')
    assert same['alpha_CCC']==same['alpha_LCC'],same
    assert abs(same['P_CCC']-same['P_LCC'])>.004,same
    assert same['Q_CCC']<same['Q_LCC'],same
    assert axis_limits()==domain,'Changing comparison basis rescaled chart'
    page.locator('#ch4-compare-basis').select_option('equal-power')
    assert page.evaluate('CCCChapter.getComparisonBasis()')=='equal-power'
    assert axis_limits()==domain
    beforeQ=page.evaluate('CCCChapter.getResults().main.powers.Q')
    page.locator('#ch4-CmF').evaluate('''el=>{
      el.value="73";el.dispatchEvent(new Event("input",{bubbles:true}))
    }''')
    afterChange=page.evaluate('''() => {
      const {main,lcc}=CCCChapter.getResults();
      return {pErr:main.powers.P-lcc.powers.P,q:main.powers.Q};
    }''')
    assert abs(afterChange['pErr'])<5e-7,afterChange
    assert abs(afterChange['q']-beforeQ)>.001,afterChange
    assert axis_limits()==domain
    assert page.locator('#ch4-qShunt').is_hidden()
    page.locator('#ch4-CmF').is_visible()
    page.locator('#ch4-enlarge').click()
    assert page.locator('#zoom-content svg').count()==2
    assert all(svg.get_attribute('viewBox')=='0 0 1080 564'
               for svg in page.locator('#zoom-content svg').all())
    page.locator('#zoom-close').click()

    for width,height in ((1100,760),(390,844)):
        page.set_viewport_size({'width':width,'height':height})
        for name in labs:
            visit(name)
            assert page.locator('#ch4-circuit').is_visible()
            assert page.locator('#ch4-chart-a').is_visible()
            assert page.locator('#ch4-chart-b').is_visible()
            assert page.locator('#ch4-circuit svg').count()==(2 if name=='compare' else 1)
    assert not errors,errors
    browser.close()
print('PASS: 86-slide offline presentation, four focused parameter-driven labs, DC boundary and LCC/CCC comparison.')
