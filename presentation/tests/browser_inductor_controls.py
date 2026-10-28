"""Browser check that inductance sliders follow the selected load topology."""
from __future__ import annotations

from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'dist/lcc_hvdc_interactive.html'

with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True,
        executable_path=shutil.which('chromium') or None,
        args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1600,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('!!window.LCCPresentationTest',timeout=45000)

    # Chapter 00: R has no inductor; RL and the R/RL comparison contain one.
    for index,enabled in ((3,False),(4,False),(5,False),(6,True),
                          (7,True),(8,True),(9,True),(10,True)):
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',index)
        actual=page.locator('#hL-fund').is_enabled()
        assert actual==enabled,(index,enabled,actual)
        assert page.locator('#hL-range').is_enabled()==enabled
        assert page.locator('#hL-fund').get_attribute('aria-disabled')==str(not enabled).lower()
    page.evaluate('window.LCCPresentationTest.setSlide(6)')
    slider=page.locator('#hL-fund')
    slider.fill('105')
    assert abs(float(slider.input_value())-105)<1
    assert page.locator('#fund-beta').inner_text()
    page.evaluate('window.LCCPresentationTest.setSlide(4)')
    assert not page.locator('#hL-fund').is_enabled()
    assert float(page.locator('#hL-fund').input_value())==105
    page.evaluate('window.LCCPresentationTest.setSlide(6)')
    assert page.locator('#hL-fund').is_enabled()
    assert float(page.locator('#hL-fund').input_value())==105

    # Chapter 01: the global smoothing-reactor control follows the selected load.
    index=page.evaluate('window.LCCPresentationTest.deck.findIndex(s=>s.type==="load" && s.lesson==="rl_intro")')
    assert index>=0
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',index)
    page.locator('#load-choice').select_option('R')
    assert not page.locator('#loadL-range').is_enabled()
    page.locator('#load-choice').select_option('RL')
    assert page.locator('#loadL-range').is_enabled()
    page.locator('#load-choice').select_option('LE')
    assert page.locator('#loadL-range').is_enabled()
    page.locator('#load-choice').select_option('RLE')
    assert page.locator('#loadL-range').is_enabled()
    page.locator('#load-choice').select_option('R')
    assert not page.locator('#loadL-range').is_enabled()
    compare=page.evaluate('window.LCCPresentationTest.deck.findIndex(s=>s.type==="load" && s.lesson==="advanced_compare")')
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',compare)
    assert page.locator('#loadL-range').is_enabled()
    assert not errors, errors
    browser.close()
print('PASS: 8 half-wave states, four 3-phase load types and comparison slider availability.')
