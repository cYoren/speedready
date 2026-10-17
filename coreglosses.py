"""Hand-checked glosses for each language's ~300 most frequent words, the ones a context-free
dictionary most often gets wrong ('für' -> "before", 'katt' -> "damn", 'come' -> "sperm").

core/<src>.tsv   word<TAB>English gloss, for every source language but English
core/en.psv      word|de|es|fr|...  English words straight into each target language

Any other pair goes through English: a word's English gloss is looked up in en.psv's column for
the target. A gloss that does not pivot cleanly is left out, so the language pack answers instead.
"""
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent / 'core'
LANGS = ('de', 'en', 'es', 'fr', 'it', 'nl', 'pl', 'pt', 'ru', 'sv')

def _gloss(g):
    return '' if g.startswith('(') else g   # '(article)': the language has none, show nothing rather than a guess

@lru_cache(None)
def _english():
    """{word: {tgt: gloss}} from en.psv"""
    rows = [l.rstrip('\n').split('|') for l in (DIR / 'en.psv').read_text(encoding='utf-8').splitlines() if l.strip()]
    head = rows[0]
    return {r[0]: {t: _gloss(g) for t, g in zip(head[1:], r[1:])} for r in rows[1:]}

@lru_cache(None)
def _to_english(src):
    f = DIR / f'{src}.tsv'
    if not f.exists():
        return {}
    return dict(l.split('\t', 1) for l in f.read_text(encoding='utf-8').splitlines() if '\t' in l)

def _pivot(english, tgt):
    en, out = _english(), []
    for part in english.split(';'):
        p = part.strip().lower()
        p = p[3:] if p.startswith('to ') and p[3:] in en else p
        hit = en.get(p, {}).get(tgt)
        if hit is None:
            return None          # one sense we cannot carry over: better the pack than half a gloss
        if hit and hit.split(';')[0].strip() not in out:
            out.append(hit.split(';')[0].strip())
    return '; '.join(out[:2])

@lru_cache(None)
def core(src, tgt):
    """{word (lowercase): gloss} for the pair; '' means show no gloss"""
    if src == tgt:
        return {}
    if src == 'en':
        return {w: g[tgt] for w, g in _english().items() if tgt in g}
    words = _to_english(src)
    if tgt == 'en':
        return dict(words)
    return {w: p for w, e in words.items() if (p := _pivot(e, tgt)) is not None}

if __name__ == '__main__':
    assert core('sv', 'en')['katt'] == 'cat'
    assert core('en', 'de')['come'] == 'kommen'
    assert core('en', 'pl')['the'] == ''
    assert core('sv', 'pt')['och'] == 'e'          # och -> and -> e
    assert core('de', 'es')['für'] == 'para'
    assert 'jag' in core('sv', 'de') and core('sv', 'de')['jag'] == 'ich'
    n = sum(len(core(s, t)) for s in LANGS for t in LANGS)
    print('ok', n, 'glosses over', len(LANGS) * (len(LANGS) - 1), 'pairs')
