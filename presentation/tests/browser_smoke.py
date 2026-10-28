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
    # Regression: a dragged range control must remain mounted across state changes.
    for side in ('rectifier', 'inverter', 'hvdc'):
        index = page.evaluate(
            "side => window.LCCPresentationTest.deck.findIndex("
            "s => s.side === side && s.type === 'state' && s.id === 1)", side)
        assert index >= 0
        page.evaluate('(i) => window.LCCPresentationTest.setSlide(i)', index)
        slider = page.locator('#angle-range')
        slider.scroll_into_view_if_needed()
        page.evaluate('window.__sliderNode = document.getElementById("angle-range")')
        initial = float(slider.input_value())
        box = slider.bounding_box()
        assert box is not None
        left, travel = box['x'] + 8, box['width'] - 16
        y = box['y'] + box['height'] / 2
        page.mouse.move(left + travel * initial / 359.75, y)
        page.mouse.down()
        seen = set()
        for angle in (90, 165, 250, 315):
            page.mouse.move(left + travel * angle / 359.75, y, steps=5)
            page.wait_for_timeout(80)
            assert page.evaluate(
                'window.__sliderNode === document.getElementById("angle-range")'), side
            actual = float(slider.input_value())
            assert abs(actual - angle) < 6, (side, angle, actual)
            seen.add(page.evaluate('window.LCCPresentationTest.getIndex()'))
        page.mouse.up()
        assert len(seen) > 1, side
    assert not errors, '\n'.join(errors)
    browser.close()
print('PASS: 64 slides, four load models, SCR vAK, selected valves, offline charts.')
