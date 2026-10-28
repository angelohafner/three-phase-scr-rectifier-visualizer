"""Browser regression: pure-R circuits cannot display inductor-only quantities."""
from __future__ import annotations

from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / 'dist/lcc_hvdc_interactive.html'
assert HTML.exists(), 'Build the offline HTML first.'

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True, executable_path=shutil.which('chromium') or None,
        args=['--no-sandbox', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width': 1600, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('http://**/*', lambda route: route.abort())
    page.route('https://**/*', lambda route: route.abort())
    page.set_content(HTML.read_text(encoding='utf-8'),
                     wait_until='domcontentloaded', timeout=120000)
    page.wait_for_function('Boolean(window.LCCPresentationTest)', timeout=45000)

    for index in (3, 4, 5):
        page.evaluate('(i) => window.LCCPresentationTest.setSlide(i)', index)
        assert page.locator('#fund-mode option[value="energy"]').is_disabled()
        assert '180' in page.locator('#fund-angle-status').inner_text()
        for chart in ('overview', 'voltages', 'vak'):
            page.locator('#fund-mode').select_option(chart)
            metadata = page.locator('#fund-waveforms').evaluate("""node => ({
                load: node.dataset.activeLoad,
                signals: JSON.parse(node.dataset.signals),
                titles: JSON.parse(node.dataset.panelTitles)
            })""")
            assert metadata['load'] == 'R'
            assert 'vl' not in metadata['signals']
            assert 'w' not in metadata['signals']
            assert not any('INDUCTOR' in title for title in metadata['titles'])
        page.evaluate("""() => {
            const menu = document.getElementById('fund-mode');
            menu.value = 'energy';
            menu.dispatchEvent(new Event('change'));
        }""")
        assert page.locator('#fund-mode').input_value() == 'overview'

    for index in (6, 7, 8, 10):
        page.evaluate('(i) => window.LCCPresentationTest.setSlide(i)', index)
        assert page.locator('#fund-mode option[value="energy"]').is_enabled()
        page.locator('#fund-mode').select_option('overview')
        signals = page.locator('#fund-waveforms').evaluate(
            'node => JSON.parse(node.dataset.signals)')
        assert 'vl' in signals
        page.locator('#fund-mode').select_option('energy')
        signals = page.locator('#fund-waveforms').evaluate(
            'node => JSON.parse(node.dataset.signals)')
        assert 'w' in signals

    assert not errors, errors
    browser.close()
print('PASS: no inductor voltage or energy on R-load slides.')
