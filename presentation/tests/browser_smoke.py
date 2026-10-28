"""Offline Chromium smoke checks for the HTML-only advanced LCC lecture."""
from __future__ import annotations

from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
HTML=ROOT/'dist/lcc_hvdc_interactive.html'
assert HTML.exists(), 'Build the HTML before checking the browser'

with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1500,'height':900})
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.goto(HTML.resolve().as_uri(),wait_until='domcontentloaded')
    page.wait_for_function('Boolean(window.LCCPresentationTest)')
    assert page.evaluate('window.LCCPresentationTest.deck.length')==64
    page.evaluate('window.LCCPresentationTest.setSlide(11)')
    assert page.locator('#load-choice option').count()==4
    page.locator('#load-choice').select_option('RLE')
    page.locator('#load-chart-mode').select_option('vak')
    page.locator('#scr-filter').select_option('T3')
    assert page.locator('#circuit-host svg').count()==1
    assert page.locator('#load-plots').evaluate('(canvas)=>canvas.width>100')
    page.evaluate('window.LCCPresentationTest.setSlide(16)')
    page.locator('#chart-mode').select_option('vak')
    page.locator('#scr-filter').select_option('T3')
    assert page.locator('#plot-canvas').evaluate('(canvas)=>canvas.width>100')
    for ix in (28,44):
        page.evaluate('(ix)=>window.LCCPresentationTest.setSlide(ix)',ix)
        page.locator('#chart-mode').select_option('valvePair')
        assert page.locator('#plot-canvas').evaluate('(canvas)=>canvas.width>100')
    assert not errors, '\n'.join(errors)
    browser.close()
print('PASS: 64 slides, four load models, SCR vAK, selected valves, offline charts.')
