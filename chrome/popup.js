// The reader keeps its habit numbers in its own localStorage ('sr:days', 'sr:goal'); this popup shares
// the extension's origin, so it reads them directly. Same streak rule as the reader's streak().
const $ = s => document.querySelector(s);
const t = key => chrome.i18n.getMessage(key) || key;
for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);

const get = (k, d) => { try { const v = localStorage.getItem('sr:' + k); return v === null ? d : JSON.parse(v); } catch { return d; } };
const dayKey = (d = new Date()) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
const days = get('days', {}), goal = get('goal', 1000), today = days[dayKey()] || 0;
const day = new Date(); let streak = 0;
if (today < goal) day.setDate(day.getDate() - 1);
while ((days[dayKey(day)] || 0) >= goal) { streak++; day.setDate(day.getDate() - 1); }
const fmt = n => n.toLocaleString(chrome.i18n.getUILanguage());
$('#today').textContent = `${fmt(today)} / ${fmt(goal)}`;
$('#fill').style.width = Math.min(100, 100 * today / goal) + '%';
$('#streak').textContent = fmt(streak);

const [command] = await chrome.commands.getAll();
$('#shortcut').textContent = command?.shortcut ? t('shortcutHint').replace('{key}', command.shortcut) + ' · ' : '';
$('#read').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  await chrome.runtime.sendMessage({type: 'read', tab}); close();
});
$('#library').addEventListener('click', () => { chrome.tabs.create({url: chrome.runtime.getURL('app/index.html')}); close(); });
