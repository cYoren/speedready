// Injected on demand. Returns {title, text}: the selection if there is one, else the page's main text,
// paragraphs separated by blank lines (the reader's paragraph mark).
(() => {
  const selected = getSelection()?.toString().trim();
  if (selected && selected.split(/\s+/).length >= 3) return {title: document.title, text: selected};
  const blocks = 'h1,h2,h3,h4,p,li,blockquote,pre,figcaption,td';
  const textOf = root => [...root.querySelectorAll(blocks)]
    .filter(el => el.checkVisibility?.() !== false && !el.closest('nav,header,footer,aside,form,[role=navigation],[aria-hidden=true]')
                  && !el.parentElement.closest(blocks))   // a <p> inside an <li> counts once
    .map(el => el.innerText.replace(/\s+/g, ' ').trim()).filter(t => t.length > 1);
  const candidates = [...document.querySelectorAll('article,main,[role=main],#content,.content,.post,.entry-content')];
  let best = candidates.map(textOf).sort((a, b) => b.join(' ').length - a.join(' ').length)[0];
  if (!best || best.join(' ').length < 400) best = textOf(document.body);
  if (!best.length) best = [document.body.innerText];
  return {title: document.title || location.hostname, text: best.join('\n\n')};
})();
