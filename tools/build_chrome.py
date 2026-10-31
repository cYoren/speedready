#!/usr/bin/env python3
"""Build the Chrome extension from this repository:
    python3 tools/build_chrome.py
Writes dist/chrome/ (load unpacked in chrome://extensions) and dist/speedready-chrome-<version>.zip
(the Chrome Web Store upload). The reader is web/ itself, copied to app/, so every change to the web
reader ships in the extension on the next build. Extension pages allow no inline script, so the
reader's inline <script> becomes app/app.js, followed by bridge.js (the extension glue). Version =
the reader's version (index.html #v-num) + commit count, so every newer commit is a valid store update.
Needs rsvg-convert for the icons.
"""
import json, re, shutil, subprocess, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB, OUT = ROOT / 'web', ROOT / 'dist' / 'chrome'

html = (WEB / 'index.html').read_text()
app = re.search(r'<b id="v-num">([\d.]+)</b>', html).group(1)
commits = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD'], cwd=ROOT, text=True).strip()
version = f'{app}.{commits}'

shutil.rmtree(OUT, ignore_errors=True)
shutil.copytree(ROOT / 'chrome', OUT)
shutil.copytree(WEB, OUT / 'app', ignore=shutil.ignore_patterns('sw.js', 'manifest.webmanifest'))
shutil.move(OUT / 'bridge.js', OUT / 'app' / 'bridge.js')

inline = re.findall(r'<script>(.*?)</script>', html, re.S)
assert len(inline) == 1, 'expected exactly one inline <script> in web/index.html'
script = inline[0]
register = "if('serviceWorker'in navigator)addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));\n"
assert register in script, 'service worker registration moved; update build_chrome.py'
(OUT / 'app' / 'app.js').write_text(script.replace(register, ''))   # the extension ships its files: no offline cache
html = html.replace(f'<script>{script}</script>', '<script src="app.js"></script>\n<script src="bridge.js"></script>')
html = html.replace('<link rel="manifest" href="manifest.webmanifest">\n', '')
(OUT / 'app' / 'index.html').write_text(html)

(OUT / 'icons').mkdir()
for size in (16, 32, 48, 128):
    subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size), '-o', OUT / 'icons' / f'{size}.png', WEB / 'icon.svg'], check=True)
manifest = json.loads((OUT / 'manifest.json').read_text())
manifest['version'] = version
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
for messages in (OUT / '_locales').glob('*/messages.json'):   # store limits: name 75, description 132
    m = json.loads(messages.read_text())
    assert len(m['extName']['message']) <= 75 and len(m['extDescription']['message']) <= 132, messages

archive = ROOT / 'dist' / f'speedready-chrome-{version}.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(OUT.rglob('*')):
        if f.is_file(): z.write(f, f.relative_to(OUT))
print(f'{OUT}\n{archive} ({archive.stat().st_size // 1024} KB)')
