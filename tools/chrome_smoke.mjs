// Loads dist/chrome (python3 tools/build_chrome.py first) in a temporary headless Chromium and checks:
// reading a page over itself, closing it, words counted for the habit, the popup, a PDF, a selection.
// The test copy gets host access to every site because headless Chromium has no toolbar to click
// (the shipped extension relies on activeTab).  SHOTS=dir saves screenshots.
//   CHROMIUM=/path/to/chrome node tools/chrome_smoke.mjs
import {cp, mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import {tmpdir} from 'node:os';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

const dist = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'dist', 'chrome');
const work = await mkdtemp(resolve(tmpdir(), 'speedready-chrome-')), ext = resolve(work, 'ext');
await cp(dist, ext, {recursive: true});
const manifest = JSON.parse(await readFile(resolve(ext, 'manifest.json'), 'utf8'));
await writeFile(resolve(ext, 'manifest.json'), JSON.stringify({...manifest, host_permissions: ['<all_urls>']}));
const id = [...createHash('sha256').update(ext).digest('hex').slice(0, 32)].map(c => String.fromCharCode(97 + parseInt(c, 16))).join('');

const para = n => `Paragraph ${n} of the Speedready test article explains why steady pacing helps readers keep their place. ` +
  'A reader who follows a moving highlight spends less time going back over lines, and finishes the page with better recall. '.repeat(3);
const article = `<!doctype html><meta charset="utf-8"><title>Speedready test article</title>
<nav><a href="/">Home</a> <a href="/about">About</a></nav>
<article><h1>Reading at a steady pace</h1>${[1, 2, 3, 4, 5, 6].map(n => `<p id="p${n}">${para(n)}</p>`).join('')}</article>
<footer>Copyright footer text that should not be read</footer>`;
// A one-page PDF written by hand (Helvetica, one text line per row), wrapped like a printed page.
const lines = ['Reading at a steady pace', ...[1, 2, 3, 4, 5, 6].flatMap(n => para(n).match(/.{1,88}(\s|$)/g).map(l => l.trim()))];
const pdf = (() => {
  const esc = t => t.replace(/[\\()]/g, m => '\\' + m);
  const content = 'BT /F1 9 Tf 11 TL 40 770 Td ' + lines.map(l => `(${esc(l)}) Tj T*`).join(' ') + ' ET';
  const objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    '<< /Title (Speedready test PDF) >>'];
  let out = '%PDF-1.4\n'; const at = [];
  objs.forEach((o, i) => { at.push(out.length); out += `${i + 1} 0 obj\n${o}\nendobj\n`; });
  const xref = out.length;
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n` + at.map(o => String(o).padStart(10, '0') + ' 00000 n \n').join('');
  return Buffer.from(out + `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n${xref}\n%%EOF\n`, 'latin1');
})();
const server = createServer((req, res) => {
  if (req.url === '/doc.pdf') { res.setHeader('Content-Type', 'application/pdf'); return res.end(pdf); }
  res.setHeader('Content-Type', 'text/html'); res.end(article);
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = spawn(process.env.CHROMIUM || 'chromium', ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--remote-debugging-port=0',
  '--user-data-dir=' + resolve(work, 'profile'), '--disable-extensions-except=' + ext, '--load-extension=' + ext, 'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
let ws;
try {
  const endpoint = await new Promise((ok, no) => { let log = ''; const t = setTimeout(() => no(Error('Chromium startup timed out')), 15000);
    browser.stderr.on('data', b => { log += b; const m = log.match(/DevTools listening on (ws:\/\/\S+)/); if (m) { clearTimeout(t); ok(m[1]); } }); browser.on('error', no); });
  ws = new WebSocket(endpoint);
  await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = no; });
  let seq = 0; const pending = new Map(), errors = [];
  ws.onmessage = e => { const m = JSON.parse(e.data);
    if (m.id) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(Error(m.error.message)) : p.resolve(m.result); }
    else if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text); };
  const call = (method, params = {}, sessionId) => new Promise((resolve, reject) => { const i = ++seq; pending.set(i, {resolve, reject}); ws.send(JSON.stringify({id: i, method, params, sessionId})); });
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const evaluate = async (session, expression) => { const r = await call('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true}, session);
    if (r.exceptionDetails) throw Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
  const until = async (what, fn) => { for (let i = 0; i < 200; i++) { const v = await fn().catch(() => null); if (v) return v; await sleep(100); } throw Error('Timed out: ' + what + ' ' + errors.join('\n')); };
  const attach = async targetId => { const {sessionId} = await call('Target.attachToTarget', {targetId, flatten: true}); await call('Runtime.enable', {}, sessionId); return sessionId; };
  const target = (type, prefix) => until(`${type} ${prefix}`, async () => (await call('Target.getTargets')).targetInfos.find(t => t.type === type && t.url.startsWith(prefix) && !t.attached));
  const open = async url => attach((await call('Target.createTarget', {url})).targetId);
  const shot = async (session, name) => process.env.SHOTS && writeFile(`${process.env.SHOTS}/${name}.png`, Buffer.from((await call('Page.captureScreenshot', {}, session)).data, 'base64'));
  const reader = s => until('reader ready', () => evaluate(s, "S.book && document.getElementById('splash').classList.contains('hidden') && S.book.id !== 'starter' && ({title: S.book.title, words: S.book.words.length, text: S.book.words.join(' ')})"));

  const page = await open(base + '/article.html');
  await until('article', () => evaluate(page, "document.readyState === 'complete'"));
  const worker = await attach((await target('service_worker', `chrome-extension://${id}/`)).targetId);
  const readTab = extra => evaluate(worker, `(async () => { const tab = (await chrome.tabs.query({})).find(t => t.url?.endsWith('/article.html')); await read({...tab, ...${JSON.stringify(extra || {})}}); return true; })()`);

  // 1. The page, read over itself: article text only, no nav or footer.
  await call('Emulation.setDeviceMetricsOverride', {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false}, page);
  await readTab();
  const frame = await attach((await target('iframe', `chrome-extension://${id}/app/index.html`)).targetId);
  const book = await reader(frame);
  if (book.title !== 'Speedready test article' || book.words < 300 || /Copyright|About/.test(book.text)) throw Error('Page text: ' + JSON.stringify({...book, text: book.text.slice(0, 200)}));

  // 2. Reading counts toward today's words; the popup (same extension origin) shows them.
  const counted = await evaluate(frame, "(async () => { setWpm(1500); play(); await new Promise(r => setTimeout(r, 2500)); pause(); return (JSON.parse(localStorage.getItem('sr:days')) || {}); })()");
  const today = Object.values(counted)[0] || 0;
  if (today < 20) throw Error('Words counted: ' + JSON.stringify(counted));
  await shot(page, 'overlay-1440');
  await evaluate(frame, "document.getElementById('sr-close').click()");
  await until('overlay closed', () => evaluate(page, "!document.getElementById('speedready-frame') && document.documentElement.style.overflow !== 'hidden'"));
  const popup = await open(`chrome-extension://${id}/popup.html`);
  await call('Emulation.setDeviceMetricsOverride', {width: 320, height: 420, deviceScaleFactor: 2, mobile: false}, popup);
  const shown = await until('popup', () => evaluate(popup, "document.getElementById('today').textContent"));
  if (!shown.startsWith(today.toLocaleString('en'))) throw Error('Popup shows ' + shown + ', reader counted ' + today);
  await shot(popup, 'popup');

  // 3. A PDF opens in a reader tab of its own.
  await evaluate(worker, `read({url: '${base}/doc.pdf', index: 0}).then(() => true)`);
  const pdfTab = await attach((await target('page', `chrome-extension://${id}/app/index.html`)).targetId);
  const pdfBook = await until('pdf book', () => evaluate(pdfTab, "S.book?.id.startsWith('f:doc.pdf:') && ({title: S.book.title, words: S.book.words.length, text: S.book.words.join(' ')})"));
  if (pdfBook.title !== 'Speedready test PDF' || pdfBook.words < 300 || !pdfBook.text.includes('steady pacing helps readers keep their place')) throw Error('PDF: ' + JSON.stringify({...pdfBook, text: pdfBook.text.slice(0, 300)}));
  for (const [w, h] of [[390, 844], [820, 1180]]) {
    await call('Emulation.setDeviceMetricsOverride', {width: w, height: h, deviceScaleFactor: 1, mobile: false}, pdfTab);
    await sleep(400); await shot(pdfTab, `pdf-${w}`);
  }

  // 4. A selection: only that paragraph.
  await evaluate(page, "(() => { const r = document.createRange(); r.selectNodeContents(document.getElementById('p3')); getSelection().removeAllRanges(); getSelection().addRange(r); return true; })()");
  await readTab();
  const selFrame = await attach((await target('iframe', `chrome-extension://${id}/app/index.html`)).targetId);
  const sel = await reader(selFrame);
  if (!sel.text.startsWith('Paragraph 3') || sel.words > 80) throw Error('Selection: ' + JSON.stringify({...sel, text: sel.text.slice(0, 120)}));

  if (errors.length) throw Error('Page errors: ' + errors.join('\n'));
  console.log('speedready chrome ok:', JSON.stringify({page: book.words, today, pdf: pdfBook.words, pdfTitle: pdfBook.title, selection: sel.words}));
} finally {
  ws?.close(); browser.kill(); server.close(); await sleep(300); await rm(work, {recursive: true, force: true});
}
async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
