"""Offline Chromium smoke test for the extended presentation."""
from __future__ import annotations
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[2]
html = root / 'dist/lcc_hvdc_interactive.html'
if not html.exists():
    raise SystemExit('Build the HTML before running the browser test.')

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1600, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(html.resolve().as_uri(), wait_until='load')
    page.wait_for_function('Boolean(window.LCCPresentationTest)')
    page.evaluate('window.LCCPresentationTest.setSlide(11)')
    assert page.locator('#load-choice').count() == 1
    assert page.locator('#load-choice option').count() == 4
    page.locator('#load-choice').select_option('RLE')
    page.locator('#load-chart-mode').select_option('scrv')
    page.locator('#load-scr-focus').select_option('T3')
    assert page.locator('#load-plots').evaluate('(el) => el.width > 100')
    assert page.locator('#load-scr-focus-wrap').is_visible()
    assert page.locator('#circuit-host svg').count() > 0
    page.evaluate('window.LCCPresentationTest.setSlide(12)')
    page.locator('#chart-mode').select_option('scrv')
    assert page.locator('#plot-canvas').evaluate('(el) => el.width > 100')
    assert page.locator('#scr-voltage-note').is_visible()
    for index in (25,38):
        page.evaluate('(index) => window.LCCPresentationTest.setSlide(index)', index)
        page.locator('#chart-mode').select_option('scrv')
        assert page.locator('#plot-canvas').evaluate('(el) => el.width > 100')
    if errors:
        raise AssertionError('Browser JS errors: ' + '; '.join(errors))
    browser.close()
print('PASS: 4 DC loads, SCR A-K plots, rectifier, inverter, and HVDC, offline.')
