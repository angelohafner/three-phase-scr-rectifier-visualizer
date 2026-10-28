"""Capture lecture slides and hyperlink geometry from the self-contained HTML.

Captures preserve the live HTML visual styling and default electrical parameters.
"""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[2] / 'dist' / 'lcc_hvdc_interactive.html'
OUT = Path(__file__).resolve().parent
PICS = OUT / 'screenshots'
PICS.mkdir(parents=True, exist_ok=True)

META = []
ERRORS = []

with sync_playwright() as p:
    import shutil
    chrome = shutil.which('chromium') or shutil.which('chromium-browser')
    browser = p.chromium.launch(executable_path=chrome,headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    page = browser.new_page(viewport={'width':1600,'height':900},device_scale_factor=1.25)
    page.on('pageerror',lambda e: ERRORS.append(str(e)))
    page.route('http://**/*',lambda r:r.abort('blocked'))
    page.route('https://**/*',lambda r:r.abort('blocked'))
    page.set_content(HTML.read_text(encoding='utf-8'),wait_until='load',timeout=120000)
    page.wait_for_timeout(300)
    assert page.evaluate('window.LCCPresentationTest.deck.length') == 61
    for i in range(61):
        page.evaluate('(i) => window.LCCPresentationTest.setSlide(i)',i)
        page.wait_for_timeout(95)
        meta=page.evaluate('''() => {
           const api=window.LCCPresentationTest;
           const el=(id)=>{const node=document.getElementById(id);if(!node)return null;const b=node.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height}};
           const stage=api.getSlide();
           const st=(id)=>document.getElementById(id)?.textContent?.trim()||null;
           return {
              index:api.getIndex(),side:stage.side,type:stage.type,state:stage.id,lesson:stage.lesson||null,alpha:stage.alpha??null,
              title:document.querySelector('.tech-title h1')?.textContent || document.querySelector('.hero-title')?.innerText || '',
              subtitle:document.querySelector('.tech-title p')?.textContent || document.querySelector('.hero-sub')?.textContent || '',
              explanation:document.querySelector('.insight')?.textContent?.trim() || document.querySelector('.explain')?.textContent?.trim() || '',
              status:st('angle-status'),
              currentChapter:st('current-chapter'),
              controls:Object.fromEntries(['nav-rect','nav-inv','nav-hvdc','overview-open','settings-open','help-open','fullscreen-btn','footer-prev','footer-next','angle-range','state-prev','state-next','play-btn','zoom-btn','ref-btn','chart-mode','load-settings','load-choice','load-chart-mode'].map(id=>[id,el(id)])),
              schedule:stage.side==='hvdc'&&stage.type==='state'?api.schedule():null,
           }
        }''')
        # Convert the HTML-only animation control to a visible static-mode hint.
        if meta['type']=='state':
            page.evaluate('''() => {
              const play=document.getElementById('play-btn');if(play){play.textContent='PPTX MODE';play.setAttribute('aria-label','Use the HTML file for animation');}
              const source=document.getElementById('ref-btn');if(source){source.textContent='SOURCE SVG';}
            }''')
        filename=PICS/f'slide_{i+1:03d}.png'
        page.screenshot(path=str(filename),full_page=False,animations='disabled')
        meta['image']=str(filename)
        META.append(meta)
        if i in (0,2,3,4,6,7,8,9,10,22,23,35,36,45,60):
            print(f"slide {i+1:02d}/61: {meta['side']}/{meta['type']} {meta['title'][:75]}",flush=True)
    print('errors',ERRORS[:8],flush=True)
    browser.close()

(OUT/'slide_metadata.json').write_text(json.dumps(META,ensure_ascii=False,indent=2),encoding='utf-8')
assert not ERRORS,ERRORS
assert len(list(PICS.glob('slide_*.png')))==61
print('Captured 61 slides; metadata written',flush=True)
