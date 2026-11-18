// Injected on demand. Returns {title, text, lang, headings, isPdf}: the selection when requested or
// present, else the page's main text with paragraphs separated by blank lines and section headings.
(() => {
  const mode = window.__srMode || 'auto';
  delete window.__srMode;
  const lang = (document.documentElement.lang || '').trim();
  const title = document.title || location.hostname;
  if (document.contentType === 'application/pdf') return {title, text: '', lang, headings: [], isPdf: true};

  const selected = getSelection()?.toString().trim();
  if (mode === 'selection' && selected) return {title, text: selected, lang, headings: []};
  if (mode === 'auto' && selected && selected.split(/\s+/).length >= 3) {
    return {title, text: selected, lang, headings: []};
  }

  const blocks = 'h1,h2,h3,h4,p,li,blockquote,pre,figcaption';
  const skip = 'nav,header,footer,aside,form,[role=navigation],[aria-hidden=true],.mw-editsection,.reflist,.navbox,sup.reference';
  const collect = root => {
    const paras = [], headings = [];
    for (const el of root.querySelectorAll(blocks)) {
      if (el.checkVisibility?.() === false || el.closest(skip) || el.parentElement?.closest(blocks)) continue;
      const t = el.innerText.replace(/\s+/g, ' ').trim();
      if (t.length <= 1) continue;
      if (/^H[1-3]$/.test(el.tagName) && t.length <= 100) headings.push([t, paras.length]);
      paras.push(t);
    }
    return {paras, headings};
  };

  const candidates = [...document.querySelectorAll('article,main,[role=main],#content,.content,.post,.entry-content')];
  let best = candidates.map(collect).sort((a, b) => b.paras.join(' ').length - a.paras.join(' ').length)[0];
  if (!best || best.paras.join(' ').length < 400) best = collect(document.body);
  if (!best.paras.length) best = {paras: [document.body.innerText], headings: []};
  return {title, text: best.paras.join('\n\n'), lang, headings: best.headings};
})();
