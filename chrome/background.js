// Opens the reader over the page (selection, else the article), or in its own tab where pages can't be
// scripted (PDF viewer, chrome:// pages). The text travels through storage.session under a one-time
// token, so a web page can never push text into the reader.
const app = path => chrome.runtime.getURL('app/index.html' + path);

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({id: 'selection', title: chrome.i18n.getMessage('readSelection'), contexts: ['selection']});
  chrome.contextMenus.create({id: 'page', title: chrome.i18n.getMessage('readPage'), contexts: ['page']});
});
chrome.contextMenus.onClicked.addListener((info, tab) => read(tab, info.selectionText));
chrome.commands.onCommand.addListener((command, tab) => command === 'read-page' && read(tab));
chrome.runtime.onMessage.addListener((m, sender, reply) => {
  if (m.type === 'read') read(m.tab).then(() => reply());
  return true;
});

async function hand(payload) {
  const token = crypto.randomUUID();
  await chrome.storage.session.set({['sr:' + token]: payload});
  return token;
}

async function read(tab, selection) {
  const url = tab?.url || '';
  if (/\.pdf($|[?#])/i.test(url)) return chrome.tabs.create({url: app('#pdf=' + encodeURIComponent(url)), index: tab.index + 1});
  let page = null;
  try { [{result: page}] = await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['content.js']}); } catch (_) {}
  if (!page?.text && selection) page = {title: tab.title || 'Selection', text: selection};
  if (!page?.text) return chrome.tabs.create({url: app(''), index: tab.index + 1});   // nothing readable here: the library
  const token = await hand(page);
  try {
    await chrome.scripting.executeScript({target: {tabId: tab.id}, func: overlay, args: [app('#embed=' + token)]});
  } catch (_) {
    chrome.tabs.create({url: app('#text=' + token), index: tab.index + 1});
  }
}

// Runs in the page: the reader in a full-window frame; it asks to close with a message.
function overlay(src) {
  document.getElementById('speedready-frame')?.remove();
  const frame = Object.assign(document.createElement('iframe'), {id: 'speedready-frame', src, allow: 'clipboard-write'});
  frame.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;border:0;margin:0;z-index:2147483647;background:#101012;color-scheme:normal';
  const overflow = document.documentElement.style.overflow;
  document.documentElement.style.overflow = 'hidden';
  const close = e => {
    if (e.source !== frame.contentWindow || e.data?.type !== 'speedready-close') return;
    frame.remove(); document.documentElement.style.overflow = overflow; removeEventListener('message', close);
  };
  addEventListener('message', close);
  document.documentElement.append(frame);
  frame.focus();
}
