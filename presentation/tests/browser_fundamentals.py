"""Interactive browser regression for Chapter 00 and legacy slider behavior."""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'dist/lcc_hvdc_interactive.html'

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium') or None,
                              args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1600,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('!!window.LCCPresentationTest',timeout=45000)
    assert page.evaluate('window.LCCPresentationTest.deck.length')==82
    for index in range(3,11):
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',index)
        assert page.locator('#fund-circuit-host svg').count()==(2 if index==9 else 1)
        assert page.locator('#fund-waveforms').evaluate('(node)=>node.width>100')
    page.evaluate('window.LCCPresentationTest.setSlide(7)')
    initial=page.locator('#fund-beta').inner_text()
    page.locator('#hL-fund').fill('130')
    updated=page.locator('#fund-beta').inner_text()
    assert initial!=updated, (initial,updated)
    # The full angular sweep must work with the same input node and pointer capture.
    page.evaluate('window.__sameSlider = document.getElementById("fund-angle")')
    slider=page.locator('#fund-angle')
    slider.scroll_into_view_if_needed()
    box=slider.bounding_box()
    assert box is not None
    x0,travel=box['x']+10,box['width']-20
    y=box['y']+box['height']/2
    old=float(slider.input_value())
    page.mouse.move(x0+travel*old/360,y)
    page.mouse.down()
    for target in (125,185,245,300):
        page.mouse.move(x0+travel*target/360,y,steps=8)
        page.wait_for_timeout(100)
        assert page.evaluate('window.__sameSlider === document.getElementById("fund-angle")')
        actual=float(slider.input_value())
        assert abs(actual-target)<5,(target,actual)
    page.mouse.up()
    # Retained three-phase chapters keep their own continuous range control.
    for side in ('rectifier','inverter','hvdc'):
        idx=page.evaluate('side => window.LCCPresentationTest.deck.findIndex(s => s.side===side && s.type==="state")',side)
        assert idx>10
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',idx)
        assert page.locator('#angle-range').count()==1
        assert page.locator('#plot-canvas').evaluate('(c)=>c.width>100')
    assert not errors,errors
    browser.close()
print('PASS: Chapter 00, 82 slides, dynamic extinction beta, full mouse drag, retained three-phase chapters.')
