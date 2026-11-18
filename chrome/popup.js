// The reader keeps its habit numbers in its own localStorage ('sr:days', 'sr:goal'); this popup shares
// the extension's origin, so it reads them directly. Same streak rule as the reader's streak().
const $ = s => document.querySelector(s);
const t = key => chrome.i18n.getMessage(key) || key;
for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);

const get = (k, d) => { try { const v = localStorage.getItem('sr:' + k); return v === null ? d : JSON.parse(v); } catch { return d; } };
const set = (k, v) => { try { localStorage.setItem('sr:' + k, JSON.stringify(v)); } catch {} };
const dayKey = (d = new Date()) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
const days = get('days', {}), goal = get('goal', 1000), today = days[dayKey()] || 0;
const day = new Date(); let streak = 0;
if (today < goal) day.setDate(day.getDate() - 1);
while ((days[dayKey(day)] || 0) >= goal) { streak++; day.setDate(day.getDate() - 1); }
const fmt = n => n.toLocaleString(chrome.i18n.getUILanguage());
$('#today').textContent = `${fmt(today)} / ${fmt(goal)}`;
$('#fill').style.width = Math.min(100, 100 * today / goal) + '%';
$('#streak').textContent = fmt(streak);

let wpm = Math.max(100, Math.min(1500, Number(get('extWpm', get('wpm', 280))) || 280));
let mode = get('extMode', 'pacer') === 'rsvp' ? 'rsvp' : 'pacer';
let pageWords = 0;

function renderPrefs() {
  $('#mode-pacer').classList.toggle('active', mode === 'pacer');
  $('#mode-rsvp').classList.toggle('active', mode === 'rsvp');
  $('#wpm-val').textContent = `${wpm} WPM`;
  if (pageWords >= 30) {
    const mins = Math.max(1, Math.round(pageWords / wpm));
    $('#read-meta').textContent = `${fmt(pageWords)} words · ~${mins} min`;
  }
  set('extMode', mode);
  set('extWpm', wpm);
  chrome.storage?.local?.set?.({extMode: mode, extWpm: wpm}).catch?.(() => {});
}
renderPrefs();

$('#mode-pacer').addEventListener('click', () => { mode = 'pacer'; renderPrefs(); });
$('#mode-rsvp').addEventListener('click', () => { mode = 'rsvp'; renderPrefs(); });
$('#wpm-down').addEventListener('click', () => { wpm = Math.max(100, wpm - (wpm > 300 ? 50 : 20)); renderPrefs(); });
$('#wpm-up').addEventListener('click', () => { wpm = Math.min(1500, wpm + (wpm >= 300 ? 50 : 20)); renderPrefs(); });

const command = (await chrome.commands?.getAll?.().catch(() => []) ?? []).find(c => c.name === 'read-page');
$('#shortcut').textContent = command?.shortcut ? t('shortcutHint').replace('{key}', command.shortcut) + ' · ' : '';

// Preview word count & reading time on the active tab when scriptable.
chrome.tabs.query({active: true, currentWindow: true}).then(async ([tab]) => {
  const url = tab?.url || '';
  if (!tab?.id || !/^https?:/i.test(url)) return;
  if (/\.pdf($|[?#])/i.test(url)) {
    $('#read-meta').textContent = 'PDF document';
    return;
  }
  try {
    const [{result}] = await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['content.js']});
    pageWords = result?.text ? result.text.trim().split(/\s+/).filter(Boolean).length : 0;
    renderPrefs();
  } catch {}
});

$('#read').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  await chrome.runtime.sendMessage({type: 'read', tab}); close();
});
$('#library').addEventListener('click', () => { chrome.tabs.create({url: chrome.runtime.getURL('app/index.html')}); close(); });
