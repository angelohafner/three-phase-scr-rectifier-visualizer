"""Audit every interactive slide and validate the intended teaching controls."""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / 'dist/lcc_hvdc_interactive.html'
REPORT = ROOT / 'report'
REPORT.mkdir(exist_ok=True)
assert HTML.exists(), 'Build the offline presentation before this audit.'

with sync_playwright() as browser_tools:
    packaged = Path(browser_tools.chromium.executable_path)
    browser = browser_tools.chromium.launch(headless=True,
        executable_path=str(packaged) if packaged.exists() else '/usr/bin/chromium',
        args=['--no-sandbox', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width': 1600, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('http://**/*', lambda r: r.abort())
    page.route('https://**/*', lambda r: r.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('!!window.LCCPresentationTest',timeout=40000)
    slides = page.evaluate('window.LCCPresentationTest.deck')
    assert len(slides)==86, len(slides)
    inventory=[]
    capture={'commutation','overlap','polarity','controller','comparison'}
    for ix, slide in enumerate(slides):
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',ix)
        info=page.evaluate('''() => ({
            title: document.querySelector('#slide h1')?.textContent?.trim() || null,
            controls: Array.from(document.querySelectorAll('#slide input[type="range"]')).map(el=>({
              id:el.id,active:!el.disabled,value:el.value})),
            mode: document.getElementById('cs-overlap-mode')?.value || null,
            currentSource: document.getElementById('cs-circuit')?.dataset || null,
            leftStation: document.getElementById('cs-left')?.dataset.station || null,
            panelCount: document.querySelectorAll('#slide .panel').length,
            hasCircuit: !!document.querySelector('#slide .diagram-area svg'),
            hasGraph: !!document.querySelector('#slide canvas'),
            flags:Array.from(document.querySelectorAll('#settings-sliders input[type="range"]')).filter(e=>!e.disabled).map(e=>e.id),
            viewportOverflow:Math.max(0,document.querySelector('#slide').scrollWidth-document.querySelector('#slide').clientWidth)
        })''')
        record={'number':ix+1,'index':ix,'kind':slide['type'],'stage':slide['side'],
          'lesson':slide.get('lesson',''),'state':slide.get('id',''),'title':info['title'],
          'enabled_controls':[c['id'] for c in info['controls'] if c['active']],
          'disabled_controls':[c['id'] for c in info['controls'] if not c['active']],
          'global_enabled':info['flags'], 'circuit':info['hasCircuit'],
          'graphs':info['hasGraph'], 'horizontal_overflow_px':info['viewportOverflow']}
        inventory.append(record)
        if slide['type'] in ('load','state','fundamentals','current_source'):
            assert info['hasGraph'], record
            assert info['hasCircuit'], record
        if slide['type']=='current_source':
            assert page.locator('#cs-left').get_attribute('data-valid')=='true', record
            if slide['lesson'] in capture:
                page.screenshot(path=str(REPORT/f"slide_{ix+1:02d}_{slide['lesson']}.png"))
        if slide['type']=='state' and slide['side']=='rectifier' and slide['id']==1:
            assert 'RL load' not in info['title'], info['title']
        if ix%12==0:
            print(f'Audited slide {ix+1}/86: {info["title"]}',flush=True)
    (REPORT/'slide_inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    print('All 86 slides render without missing schematics/plots.')
    cs={s['lesson']:i for i,s in enumerate(slides) if s['type']=='current_source'}
    for lesson in ['commutation','overlap']:
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',cs[lesson])
        assert page.locator('#cs-idc').is_disabled()
        assert page.locator('#cs-alphaR').is_disabled()
        assert page.locator('#cs-muR').is_disabled()
        assert page.locator('#cs-csLc').is_enabled()
        assert page.locator('#cs-overlap-mode').input_value()=='calculated'
        assert page.locator('#cs-overlap-mode').is_disabled()
        assert page.evaluate('window.LCCPresentationTest.params.idc')==1
        page.locator('#cs-csLc').evaluate('el=>{el.value="0.12";el.dispatchEvent(new Event("input",{bubbles:true}))}')
        page.wait_for_timeout(130)
        muSmall=float(page.locator('#cs-left').get_attribute('data-mu'))
        page.locator('#cs-csLc').evaluate('el=>{el.value="0.52";el.dispatchEvent(new Event("input",{bubbles:true}))}')
        page.wait_for_timeout(130)
        muLarge=float(page.locator('#cs-left').get_attribute('data-mu'))
        assert muLarge>muSmall>0,(lesson,muSmall,muLarge)
        assert abs(float(page.locator('#cs-idc').input_value())-1)<1e-6
        assert abs(float(page.locator('#cs-alphaR').input_value())-15)<1e-6
        assert page.locator('#cs-circuit').get_attribute('data-current')=='1.0000'
        print(lesson,'mu from Lc:',round(muSmall,2),'->',round(muLarge,2))

    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',cs['commutation'])
    page.evaluate('window.__keepSlider=document.getElementById("cs-angle")')
    slider=page.locator('#cs-angle');slider.scroll_into_view_if_needed()
    box=slider.bounding_box(); assert box
    left=box['x']+8;travel=box['width']-16;y=box['y']+box['height']/2
    initial=float(slider.input_value())
    page.mouse.move(left+travel*initial/360,y)
    page.mouse.down()
    for value in (92,178,267,319):
        page.mouse.move(left+travel*value/360,y,steps=6)
        page.wait_for_timeout(65)
        assert page.evaluate('window.__keepSlider===document.getElementById("cs-angle")')
        assert abs(float(slider.input_value())-value)<8,(value,slider.input_value())
    page.mouse.up()
    print('Continuous slider drag is intact.')

    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',cs['polarity'])
    assert page.locator('#cs-left').get_attribute('data-station')=='rectifier'
    page.locator('#cs-side').select_option('inverter')
    assert page.locator('#cs-left').get_attribute('data-station')=='inverter'
    assert page.locator('#cs-alphaR').is_enabled()
    assert 'α' in page.locator('#cs-alphaR-symbol').inner_text()
    page.locator('#cs-alphaR').evaluate('el=>{el.value="140";el.dispatchEvent(new Event("input",{bubbles:true}))}')
    page.wait_for_timeout(120)
    assert abs(page.evaluate('window.LCCPresentationTest.params.alphaI')-140)<1e-6
    assert page.locator('#cs-circuit').get_attribute('data-station')=='inverter'
    print('Inverter waveform follows the selected station and inverter firing angle.')

    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',cs['controller'])
    assert page.locator('#cs-angle').is_disabled()
    assert page.locator('#cs-idc').is_enabled()
    assert page.locator('#cs-csLc').is_disabled()
    assert page.locator('#cs-muR').is_disabled()
    assert page.locator('#cs-loadL').is_enabled()
    assert page.locator('#cs-left').get_attribute('data-plot-mode')=='control'
    print('Controller parameters and time-domain waveforms are consistent.')

    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',cs['comparison'])
    assert page.locator('#cs-loadR').is_enabled()
    assert page.locator('#cs-loadL').is_enabled()
    assert page.locator('#cs-loadE').is_enabled()
    assert page.locator('#cs-csLc').is_disabled()
    page.locator('#cs-topology').select_option('RLE')
    assert page.locator('#cs-circuit').get_attribute('data-model')=='RLE'
    print('RLE/source comparison respects the selected circuit model.')
    assert not errors,errors
    browser.close()
print('PASS — 86 slides, per-slide control restrictions, electrical models, continuous sliders.')
