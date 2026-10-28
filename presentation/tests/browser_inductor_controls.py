"""Browser regression for topology-aware inductance sliders."""
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
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.route('http://**/*',lambda route:route.abort())
    page.route('https://**/*',lambda route:route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),
        wait_until='domcontentloaded',timeout=120000)
    page.wait_for_function('!!window.LCCPresentationTest',timeout=45000)

    # Chapter 00: R circuits have no L; RL and R/RL comparison include L.
    for index,enabled in ((3,False),(4,False),(5,False),(6,True),
                          (7,True),(8,True),(9,True),(10,True)):
        page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',index)
        assert page.locator('#hL-fund').is_enabled()==enabled,(index,enabled)
        assert page.locator('#hL-range').is_enabled()==enabled
        assert page.locator('#hL-fund').get_attribute('aria-disabled')==str(not enabled).lower()
    page.evaluate('window.LCCPresentationTest.setSlide(6)')
    page.locator('#hL-fund').fill('105')
    assert page.locator('#fund-beta').inner_text()
    page.evaluate('window.LCCPresentationTest.setSlide(4)')
    assert not page.locator('#hL-fund').is_enabled()
    assert float(page.locator('#hL-fund').input_value())==105
    page.evaluate('window.LCCPresentationTest.setSlide(6)')
    assert page.locator('#hL-fund').is_enabled()
    assert float(page.locator('#hL-fund').input_value())==105

    # Chapter 01: a smoothing-reactor control depends on the load topology.
    index=page.evaluate(
        'window.LCCPresentationTest.deck.findIndex(s=>s.type==="load" && s.lesson==="r_intro")')
    assert index>=0
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',index)
    assert not page.locator('#loadL-range').is_enabled()
    for mode in ('RL','LE','RLE'):
        page.locator('#load-choice').select_option(mode)
        assert page.locator('#loadL-range').is_enabled(),mode
    page.locator('#load-choice').select_option('R')
    assert not page.locator('#loadL-range').is_enabled()
    compare=page.evaluate(
        'window.LCCPresentationTest.deck.findIndex(s=>s.type==="load" && s.lesson==="advanced_compare")')
    page.evaluate('(i)=>window.LCCPresentationTest.setSlide(i)',compare)
    assert page.locator('#loadL-range').is_enabled()
    assert not errors,errors
    browser.close()
print('PASS: half-wave, R/RL/LE/RLE and comparison slider availability.')
