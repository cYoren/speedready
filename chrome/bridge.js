// Extension glue, loaded after the reader's own script (so S, addBooks and toast are in scope).
// #embed=token: text handed over by background.js, shown over the page with a close button.
// #text=token: the same in a tab of its own. #pdf=url: a PDF the browser was showing.
(() => {
  const hash = new URLSearchParams(location.hash.slice(1)), embedded = hash.has('embed');
  const close = () => parent.postMessage({type: 'speedready-close'}, '*');
  if (embedded) {
    const b = Object.assign(document.createElement('button'), {id: 'sr-close', className: 'btn icon', textContent: '✕'});
    b.setAttribute('aria-label', chrome.i18n.getMessage('close'));
    b.onclick = close;
    document.querySelector('header').append(b);
    // Escape closes an open sheet first (the reader's own handler); with none open it closes the reader.
    addEventListener('keydown', e => { if (e.key === 'Escape' && !document.querySelector('.sheet.on')) close(); }, true);
  }
  const ready = () => new Promise(ok => { const t = setInterval(() => {
    if (S.book && document.getElementById('splash').classList.contains('hidden')) { clearInterval(t); ok(); } }, 100); });
  const fileName = title => (title || 'Page').replace(/[\\/:*?"<>|]+/g, ' ').trim().slice(0, 120);

  (async () => {
    const token = hash.get('embed') || hash.get('text'), pdf = hash.get('pdf');
    history.replaceState(null, '', location.pathname);   // a reload must not add the same text twice
    let file = null;
    if (token) {
      const key = 'sr:' + token, {[key]: page} = await chrome.storage.session.get(key);
      await chrome.storage.session.remove(key);
      if (page?.text) file = new File([page.text], fileName(page.title) + '.txt', {type: 'text/plain'});
    } else if (pdf) {
      const name = decodeURIComponent(new URL(pdf).pathname.split('/').pop() || 'document.pdf');
      const blob = await fetch(pdf).then(r => r.ok ? r.blob() : null).catch(() => null);
      await ready();
      if (blob) file = new File([blob], /\.pdf$/i.test(name) ? name : name + '.pdf', {type: 'application/pdf'});
      else toast(chrome.i18n.getMessage('pdfBlocked'));
    }
    if (!file) return;
    await ready();
    await addBooks([file]);
  })();
})();
