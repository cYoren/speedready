// Opens the reader over the page (selection, else the article), or in its own tab where pages can't be
// scripted (PDF viewer, chrome:// pages). The text travels through storage.session under a one-time
// token, so a web page can never push text into the reader.
const app = path => chrome.runtime.getURL('app/index.html' + path);

chrome.runtime.onInstalled.addListener(() => {
  if (!chrome.contextMenus) return;
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({id: 'selection', title: chrome.i18n.getMessage('readSelection'), contexts: ['selection']});
    chrome.contextMenus.create({id: 'page', title: chrome.i18n.getMessage('readPage'), contexts: ['page']});
  });
});

chrome.contextMenus?.onClicked?.addListener((info, tab) => {
  read(tab, info.menuItemId === 'selection' ? 'selection' : 'page', info.selectionText, info.frameId);
});

chrome.commands?.onCommand?.addListener((command, tab) => {
  if (command === 'read-page') read(tab, 'auto');
});

chrome.runtime.onMessage.addListener((m, sender, reply) => {
  if (m.type === 'read') read(m.tab, 'auto').finally(() => reply());
  return true;
});

async function hand(payload) {
  const token = crypto.randomUUID();
  await chrome.storage.session.set({['sr:' + token]: payload});
  return token;
}

async function fetchPdfInTab(tabId) {
  try {
    const [{result}] = await chrome.scripting.executeScript({
      target: {tabId},
      func: async () => {
        const res = await fetch(location.href, {credentials: 'include'});
        if (!res.ok) return null;
        const buf = await res.arrayBuffer();
        if (buf.byteLength > 4 * 1024 * 1024) return null;
        const bytes = new Uint8Array(buf);
        let bin = '';
        for (let i = 0; i < bytes.length; i += 0x8000) {
          bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
        }
        return btoa(bin);
      },
    });
    return result || null;
  } catch {
    return null;
  }
}

async function read(tab, mode = 'auto', selection = '', frameId) {
  const url = tab?.url || '';
  if (/\.pdf($|[?#])/i.test(url)) {
    const b64 = tab?.id ? await fetchPdfInTab(tab.id) : null;
    if (b64) {
      const token = await hand({pdfBase64: b64, title: tab.title || 'document.pdf', url});
      return chrome.tabs.create({url: app('#text=' + token), index: (tab?.index ?? 0) + 1});
    }
    return chrome.tabs.create({url: app('#pdf=' + encodeURIComponent(url)), index: (tab?.index ?? 0) + 1});
  }

  // If the overlay is already open and user re-triggers the shortcut without a new selection, toggle it closed.
  if (mode === 'auto' && tab?.id) {
    try {
      const [{result: closed}] = await chrome.scripting.executeScript({
        target: {tabId: tab.id},
        func: () => {
          const f = document.getElementById('speedready-frame');
          if (!f) return false;
          f.remove();
          document.documentElement.style.overflow = document.documentElement.dataset.srOverflow ?? '';
          delete document.documentElement.dataset.srOverflow;
          return true;
        },
      });
      if (closed) return;
    } catch (_) {}
  }

  let page = null;
  if (tab?.id) {
    try {
      await chrome.scripting.executeScript({
        target: {tabId: tab.id, ...(frameId != null ? {frameIds: [frameId]} : {})},
        func: (m) => { window.__srMode = m; },
        args: [mode],
      });
      [{result: page}] = await chrome.scripting.executeScript({
        target: {tabId: tab.id, ...(frameId != null ? {frameIds: [frameId]} : {})},
        files: ['content.js'],
      });
    } catch (_) {}
  }
  if (page?.isPdf) {
    const b64 = await fetchPdfInTab(tab.id);
    if (b64) {
      const token = await hand({pdfBase64: b64, title: page.title || 'document.pdf', url});
      return chrome.tabs.create({url: app('#text=' + token), index: (tab?.index ?? 0) + 1});
    }
    return chrome.tabs.create({url: app('#pdf=' + encodeURIComponent(url)), index: (tab?.index ?? 0) + 1});
  }
  if (mode === 'selection' && selection && (!page?.text || page.text.length < selection.trim().length)) {
    page = {title: tab?.title || 'Selection', text: selection.trim(), lang: page?.lang || '', headings: []};
  } else if (!page?.text && selection) {
    page = {title: tab?.title || 'Selection', text: selection.trim(), lang: page?.lang || '', headings: []};
  }
  if (!page?.text) return chrome.tabs.create({url: app(''), index: (tab?.index ?? 0) + 1});
  const token = await hand(page);
  try {
    await chrome.scripting.executeScript({target: {tabId: tab.id}, func: overlay, args: [app('#embed=' + token)]});
    // If the page's CSP frame-src blocks chrome-extension:// iframes, bridge.js never boots; fall back to a new tab.
    setTimeout(async () => {
      const bootKey = 'sr:boot:' + token;
      const got = await chrome.storage.session.get(bootKey).catch(() => ({}));
      if (got[bootKey]) {
        await chrome.storage.session.remove(bootKey).catch(() => {});
        return;
      }
      await chrome.scripting.executeScript({
        target: {tabId: tab.id},
        func: () => {
          document.getElementById('speedready-frame')?.remove();
          document.documentElement.style.overflow = document.documentElement.dataset.srOverflow ?? '';
          delete document.documentElement.dataset.srOverflow;
        },
      }).catch(() => {});
      chrome.tabs.create({url: app('#text=' + token), index: tab.index + 1});
    }, 1200);
  } catch (_) {
    chrome.tabs.create({url: app('#text=' + token), index: tab.index + 1});
  }
}

// Runs in the page: the reader in a full-window frame; it asks to close with a message.
function overlay(src) {
  document.getElementById('speedready-frame')?.remove();
  const frame = Object.assign(document.createElement('iframe'), {id: 'speedready-frame', src, allow: 'clipboard-write'});
  frame.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;border:0;margin:0;z-index:2147483647;background:#101012;color-scheme:normal';
  if (!('srOverflow' in document.documentElement.dataset)) {
    document.documentElement.dataset.srOverflow = document.documentElement.style.overflow;
  }
  document.documentElement.style.overflow = 'hidden';
  const close = e => {
    if (e.source !== frame.contentWindow || e.data?.type !== 'speedready-close') return;
    frame.remove();
    document.documentElement.style.overflow = document.documentElement.dataset.srOverflow ?? '';
    delete document.documentElement.dataset.srOverflow;
    removeEventListener('message', close);
  };
  addEventListener('message', close);
  document.documentElement.append(frame);
  frame.focus();
}
