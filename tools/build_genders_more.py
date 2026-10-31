#!/usr/bin/env python3
"""Build web/genders-<lang>.json.gz (German: build_genders.py): every noun form -> the genders it can have, from the Wiktionary
extracts (kaikki.org) that Speedready's pack builder already downloads to ~/.cache/speedready/build.

    python3 tools/build_genders_more.py [lang ...]      # default: all of LANGS

Value per form, like genders-de.json.gz: readings in the order to prefer them when the text
gives no clue. m f n c = singular of a masculine / feminine / neuter / common-gender noun, M F N C = a
plural of one, P = plural-only (no gender), trailing * = the same spelling is also a common word of
another kind ('est' the noun 'east' and 'est' of être), so it is only colored right after an article.
Only common other words count: 'casa' is also a form of casar, but that verb is rare, so 'casa' stays a
noun. Dutch and Swedish only need two classes (de/het, en/ett), so their m and f become c.
"""
import gzip, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path.home() / '.cache/speedready/build'
LANGS = {'es': 'Spanish', 'fr': 'French', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian',
         'pl': 'Polish', 'nl': 'Dutch', 'sv': 'Swedish'}
SKIP = {'table-tags', 'inflection-template', 'class', 'romanization', 'diminutive', 'augmentative', 'masculine',
        'feminine', 'neuter', 'alternative', 'obsolete', 'archaic', 'misspelling', 'dialectal', 'canonical'}
COMMON = 1500   # a non-noun lemma this high in the frequency list makes its forms ambiguous

def unstress(w):   # Russian: 'цари́ца' -> 'царица'; dictionaries mark stress, running text does not ('ё' stays)
    return unicodedata.normalize('NFC', unicodedata.normalize('NFD', w).replace('́', '').replace('̀', ''))

def genders(e, common):
    for h in e.get('head_templates', []):
        head = re.sub(r'^\S+\s*(•\s*\([^)]*\))?', '', h.get('expansion', '')).split(' (')[0].split()   # 'дом • (dom) m inan (genitive …)' -> m inan
        g = ''.join(dict.fromkeys(('c' if common and x in 'mf' else x) for x in head if x in ('m', 'f', 'n', 'c')))
        if g: return g
        if 'pl' in head: return 'P'
    return ''

def build(lang):
    plain = unstress if lang == 'ru' else (lambda w: w)
    common = lang in ('nl', 'sv')
    rank = {l.split()[0]: i for i, l in enumerate(open(CACHE / f'freq-{lang}.txt', encoding='utf-8')) if l.strip()}
    frequent = lambda w: rank.get(w, COMMON) < COMMON
    head, infl, other = {}, {}, set()
    def add(d, form, r):
        if r not in d.get(form, ''): d[form] = d.get(form, '') + r
    with gzip.open(CACHE / f'en-{LANGS[lang]}.jsonl.gz', 'rt', encoding='utf-8') as f:
        for line in f:
            e = json.loads(line); w = plain(e.get('word', ''))
            if not w[:1].islower() or ' ' in w: continue   # names and phrases
            senses = e.get('senses', [])
            form_of = [plain(t.get('word', '')) for s in senses for t in s.get('form_of', [])]
            if e.get('pos') != 'noun':
                if form_of and any(map(frequent, form_of)) or not form_of and (frequent(w) or e.get('pos') in ('prep', 'conj', 'det', 'pron', 'article', 'adv')):
                    other.add(w)
                    if frequent(w): other.update(plain(x.get('form', '')) for x in e.get('forms', []) if 'romanization' not in x.get('tags', []))
                continue
            g = genders(e, common)
            if not g or senses and all(s.get('form_of') or 'form-of' in s.get('tags', []) for s in senses): continue   # 'casas: plural of casa': the lemma's forms cover it
            for x in g: add(head, w, x)
            for x in e.get('forms', []):
                fm = plain(x.get('form', '')); tags = set(x.get('tags', []))
                if not fm or ' ' in fm or tags & SKIP or not fm[:1].islower(): continue
                for r in g: add(infl, fm, 'P' if r == 'P' else r.upper() if 'plural' in tags and 'singular' not in tags else r)
    data = {}
    for form in head.keys() | infl.keys():
        r = head.get(form, '')
        for x in infl.get(form, ''):
            if x.lower() not in r.lower(): r += x
        data[form] = r + ('*' if form in other else '')
    out = ROOT / 'web' / f'genders-{lang}.json.gz'
    with gzip.open(out, 'wt', encoding='utf-8', compresslevel=9) as f: json.dump(data, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    print(f'{lang}: {len(data):,} forms, {sum(v.endswith("*") for v in data.values()):,} need an article -> {out.name} ({out.stat().st_size / 1e6:.1f} MB)', flush=True)

if __name__ == '__main__':
    for lang in sys.argv[1:] or LANGS: build(lang)
