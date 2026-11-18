// Extension glue, loaded after the reader's own script (so S, LS, textToBook, loadBook, saveBook,
// setMode, setWpm, addBooks, pause, save, and toast are in scope).
// #embed=token: text handed over by background.js, shown over the page with Save + Close buttons.
// #text=token: the same (or fetched PDF bytes) in a tab of its own. #pdf=url: fallback PDF fetch.
(() => {
  const hash = new URLSearchParams(location.hash.slice(1)), embedded = hash.has('embed');
  const close = () => {
    try { if (typeof pause === 'function') pause(); if (typeof save === 'function') save(); } catch {}
    parent.postMessage({type: 'speedready-close'}, '*');
  };
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

  function attachHeadings(book, headings) {
    if (!Array.isArray(headings) || !headings.length || !book.paras?.length) return;
    book.chapters = headings
      .map(([name, pIdx]) => [name, book.paras[pIdx] ?? 0])
      .filter(([, wi]) => wi >= 0 && wi < book.words.length);
  }

  function addSaveButton(book) {
    const header = document.querySelector('header');
    if (!header || document.getElementById('sr-save')) return;
    const btn = Object.assign(document.createElement('button'), {id: 'sr-save', className: 'btn icon', textContent: '☆', title: 'Save to library'});
    btn.setAttribute('aria-label', 'Save to library');
    btn.onclick = async () => {
      const savedBook = {...book, id: 'ext:' + Date.now() + ':' + book.words.length};
      await saveBook(savedBook).catch(() => {});
      btn.textContent = '★';
      btn.disabled = true;
      toast('Saved to library');
    };
    const closeBtn = document.getElementById('sr-close');
    if (closeBtn) header.insertBefore(btn, closeBtn);
    else header.append(btn);
  }

  (async () => {
    const token = hash.get('embed') || hash.get('text'), pdf = hash.get('pdf');
    history.replaceState(null, '', location.pathname);   // a reload must not add the same text twice
    let payload = null, pdfFile = null;
    if (token) {
      if (embedded) await chrome.storage.session.set({['sr:boot:' + token]: 1}).catch(() => {});
      const key = 'sr:' + token, {[key]: data} = await chrome.storage.session.get(key);
      await chrome.storage.session.remove(key);
      if (data?.pdfBase64) {
        const bin = atob(data.pdfBase64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        const name = fileName(data.title || 'document') + '.pdf';
        pdfFile = new File([bytes], name, {type: 'application/pdf'});
      } else if (data?.text) {
        payload = data;
      }
    } else if (pdf) {
      const name = decodeURIComponent(new URL(pdf).pathname.split('/').pop() || 'document.pdf');
      const blob = await fetch(pdf).then(r => r.ok ? r.blob() : null).catch(() => null);
      await ready();
      if (blob) pdfFile = new File([blob], /\.pdf$/i.test(name) ? name : name + '.pdf', {type: 'application/pdf'});
      else toast(chrome.i18n.getMessage('pdfBlocked'));
    }

    if (pdfFile) {
      await ready();
      await addBooks([pdfFile]);
      return;
    }
    if (!payload) return;

    await ready();
    const prevLast = LS.get('lastBook', 'starter');
    const book = textToBook(payload.text, fileName(payload.title), 'ext:ephemeral', payload.lang || '');
    if (!book.words.length) return;
    attachHeadings(book, payload.headings);
    await loadBook(book, 0);
    if (prevLast) LS.set('lastBook', prevLast); // keep ephemeral web reads from overwriting real book bookmarks

    const prefs = await chrome.storage?.local?.get?.(['extMode', 'extWpm']).catch(() => ({})) ?? {};
    const desiredMode = prefs.extMode || LS.get('extMode', 'pacer');
    const desiredWpm = Number(prefs.extWpm || LS.get('extWpm', LS.get('wpm', 280))) || 280;
    if (typeof setMode === 'function') setMode(desiredMode === 'rsvp' ? 'rsvp' : 'pacer');
    if (typeof setWpm === 'function') setWpm(desiredWpm);
    addSaveButton(book);
  })();
})();
