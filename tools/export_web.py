#!/usr/bin/env python3
"""Export a gloss pack for the web reader: gloss-<src>-<tgt>.sqlite -> web/dict-<src>-<tgt>.json

Also rewrites web/bundle.json, which is the only place the shipped language pair is named. The
reader and the service worker both read it, so changing which pair the web app and the Android
APK carry is this command plus a starter book, with no edit to index.html or sw.js.

The desktop pack is ~33 MB of SQLite indexes and English fallbacks the app never shows.
What the web needs is four maps, which gzip to under 2 MB:
    {"g": {lemma: "gloss"}, "f": {form: lemma}, "o": {word: ["gloss", "lemma"]}, "s": {form: "gloss"}}
"g" is chosen with the desktop reader's own scorer (speedready.pick_gloss), so both readers weigh
exact case, part of speech and frequency the same way instead of the web taking the highest priority
row. "o" is the curated override table, applied before everything else, same as the desktop app. "s"
carries only the surface forms whose scored answer differs from their lemma's, because the desktop
scores a word and its lemma separately ('Forscher' is the noun "explorer", not a form of 'forschen');
'' means the desktop shows no gloss for that word either.

    export_web.py de pt                  # write web/dict-de-pt.json from the installed pack
    export_web.py --patch web/dict-*.json   # rewrite only the curated overrides
    export_web.py --check                # the shipped dictionary vs the desktop reader, over its starter book
"""
import argparse,gzip,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from speedready import GLOSS_OVERRIDES,Gloss,pick_gloss,strip
from coreglosses import core

ROOT=Path(__file__).resolve().parent.parent
PACKS=Path.home()/'.cache/speedready/packs'

def overrides(src,tgt,forms,glosses):
    """word -> [gloss, lemma]: the core vocabulary (every pair), then the hand-curated pair on top. '' = no gloss."""
    lemma=lambda w:next((x for x in (w,w.capitalize()) if x in glosses),None) or forms.get(w) or forms.get(w.capitalize()) or w   # 'mann' is Mann, not a form of 'Männin'
    return {**{w:[g,lemma(w)] for w,g in core(src,tgt).items()},**{w:list(v) for w,v in GLOSS_OVERRIDES.get((src,tgt),{}).items()}}

def selected(db,src,tgt):
    """(g, f, s): the gloss the desktop reader would show, as maps the web reader can look up."""
    rows={}   # prio 1-2: Wiktionary translations; 9: English definitions, the gloss itself when tgt is en. 3 was MUSE (CC BY-NC) and is never exported
    for w,pos,t,prio in db.execute(f"SELECT word,pos,tgt,prio FROM gloss WHERE prio IN (1,2{',9' if tgt=='en' else ''}) ORDER BY rowid"):
        rows.setdefault(w,[]).append((w,pos,t,prio))
    freq={w:r for w,r in db.execute('SELECT word,rank FROM freq WHERE rank<=250')}
    def candidates(*keys):
        """The rows Gloss.raw offers the scorer: the lemma and the surface word, lowercased ('Haus' vs 'haus')."""
        return [r for k in dict.fromkeys(keys) for r in rows.get(k,())]
    g={}
    for w in rows:
        r=pick_gloss(candidates(w,w.lower()),w,freq.get(w.lower()))   # a lemma scores as its own surface, exactly as Gloss.raw does
        if r:g[w]=Gloss.short(r[2])
    forms={f:l for f,l in db.execute('SELECT form,lemma FROM forms') if l in g}
    # Gloss.lemma: the forms table first, then any word the pack glosses (prio 9 counts, or 'Rauschen' would stop
    # falling back to 'rauschen'). The export's own form map is narrower, so ask the pack.
    all_forms=dict(db.execute('SELECT form,lemma FROM forms'));all_words={w for (w,) in db.execute('SELECT word FROM gloss')}
    def lemma_of(w):
        for c in dict.fromkeys((w,w.lower(),w.capitalize())):
            if c in all_forms:return all_forms[c]
            if c in all_words:return c
        return w
    over=overrides(src,tgt,forms,g)
    def reader_gloss(w):
        """What web/index.html would show without 's': the curated overrides, then the lemma's or the word's gloss."""
        if (o:=over.get(w.lower())) is not None:return o[0] or None
        lemma=forms.get(w) or (w if w in g else None) or forms.get(w.lower()) or forms.get(w[:1].upper()+w[1:]) or (w.lower() if w.lower() in g else w)
        return g.get(lemma) or g.get(w) or g.get(w.lower())
    s={}
    for form in dict.fromkeys((*all_forms,*g)):
        # sentence-initial German capitalises the word the reader looks up: score 'Dicht' as well as 'dicht'
        for surface in dict.fromkeys((form,form[:1].upper()+form[1:])):
            r=pick_gloss(candidates(lemma_of(surface),surface,surface.lower()),surface,freq.get(surface.lower()))
            shown=Gloss.short(r[2]) if r else None
            if (shown or '')!=(reader_gloss(surface) or ''):s[surface]=shown or ''
    return g,forms,s

def export(src,tgt,pack,out,starter=None):
    db=sqlite3.connect(pack)
    g,forms,s=selected(db,src,tgt)
    over=overrides(src,tgt,forms,g)
    freq={w:r for w,r in db.execute('SELECT word,rank FROM freq WHERE rank<=2000')}
    data={'src':src,'tgt':tgt,'g':g,'f':forms,'o':over,'s':s,'r':freq}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'{out} {out.stat().st_size/1e6:.1f} MB  ({len(g):,} glosses, {len(forms):,} forms, {len(over):,} overrides, {len(s):,} surface forms)')
    bundle=out.parent/'bundle.json'
    if starter is None:          # keep whatever starter book is already bundled
        starter=json.loads(bundle.read_text())['starter'] if bundle.exists() else f'starter-{src}.json'
    keep=json.loads(bundle.read_text()) if bundle.exists() else {}   # 'packs' and 'languages' too: the reader needs them
    bundle.write_text(json.dumps({**keep,'dict':out.name,'starter':starter},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"{bundle} -> dict {out.name}, starter {starter}")
    if not (out.parent/starter).exists():
        print(f'  WARNING: {starter} is not in {out.parent}; the reader will fail to open its starter book',file=sys.stderr)

def patch(path):
    """Rewrite only the overrides of an exported dictionary (.json or .json.gz), keeping its glosses as they are."""
    path=Path(path);gz=path.suffix=='.gz'
    d=json.loads((gzip.decompress(path.read_bytes()) if gz else path.read_bytes()).decode('utf-8'))
    d['o']=overrides(d['src'],d['tgt'],d['f'],d['g'])
    raw=json.dumps(d,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    path.write_bytes(gzip.compress(raw,9,mtime=0) if gz else raw)
    return len(d['o'])

def web_strip(w):
    """index.html's strip(): leading and trailing characters that are not letters or digits."""
    a,b=0,len(w)
    while a<b and not w[a].isalnum():a+=1
    while b>a and not w[b-1].isalnum():b-=1
    return w[a:b]

def web_lookup(d,word):
    """web/index.html's glossOf, in Python, so --check measures the reader as it ships: 'o', then 's', then 'g'."""
    w=web_strip(word)
    if not w:return None,w
    if (o:=d['o'].get(w.lower())):return o[0] or None,o[1]
    g,f=d['g'],d['f']
    lemma=f.get(w) or (w if w in g else None) or f.get(w.lower()) or f.get(w[0].upper()+w[1:]) or (w.lower() if w.lower() in g else w)
    if w in d.get('s',{}):return d['s'][w] or None,lemma
    return g.get(lemma) or g.get(w) or g.get(w.lower()),lemma

def check(dict_path=None,pack=None,starter=None,minimum=99.0):
    """Compare the shipped dictionary with the desktop reader over its starter book. Exit 2 when it cannot run."""
    bundle=json.loads((ROOT/'web'/'bundle.json').read_text())
    dict_path=Path(dict_path or ROOT/'web'/bundle['dict'])
    d=json.loads(dict_path.read_text(encoding='utf-8'));src,tgt=d['src'],d['tgt']
    pack=Path(pack or PACKS/f'gloss-{src}-{tgt}.sqlite');starter=Path(starter or ROOT/'web'/bundle['starter'])
    if not pack.exists():print(f'{pack} is not installed: build it with tools/build_pack.py {src} {tgt} or pass --pack',file=sys.stderr);return 2
    if sqlite3.connect(pack).execute('SELECT count(*) FROM gloss WHERE prio=3').fetchone()[0]:
        print(f'note: {pack.name} still carries prio-3 MUSE rows, which the export never includes; agreement against it is lower',file=sys.stderr)
    desk=Gloss(src,tgt,lambda *_:None,lambda *_:None,path=pack)
    words=json.loads(starter.read_text(encoding='utf-8'))['words']
    bad=[(w,web_lookup(d,w)[0],desk.raw(w)[0]) for w in words if (web_lookup(d,w)[0] or '')!=(desk.raw(w)[0] or '')]
    unique=list(dict.fromkeys(words));badu=[w for w in unique if (web_lookup(d,w)[0] or '')!=(desk.raw(w)[0] or '')]
    pct=(len(words)-len(bad))*100/len(words);pctu=(len(unique)-len(badu))*100/len(unique)
    print(f'{dict_path.name}: web and desktop agree on {len(words)-len(bad):,}/{len(words):,} words ({pct:.2f}%)')
    print(f'  distinct words: {len(unique)-len(badu):,}/{len(unique):,} ({pctu:.2f}%)   disagreements: {len(bad)}')
    for w,we,dg in bad[:10]:print(f'  {w!r}: web {we!r}, desktop {dg!r}')
    if pct<minimum:print(f'below --min {minimum}%',file=sys.stderr);return 1
    return 0

if __name__=='__main__' and sys.argv[1:2]==['--patch']:
    for f in sys.argv[2:]:print(f,patch(f))
    sys.exit()
if __name__=='__main__' and sys.argv[1:2]==['--check']:
    a=argparse.ArgumentParser();a.add_argument('--dict',default=None);a.add_argument('--pack',default=None);a.add_argument('--starter',default=None)
    a.add_argument('--min',type=float,default=99.0,help='minimum agreement, in percent');a=a.parse_args(sys.argv[2:])
    sys.exit(check(a.dict,a.pack,a.starter,a.min))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('src');a.add_argument('tgt')
    a.add_argument('--pack',default=None);a.add_argument('--out',default=None)
    a.add_argument('--starter',default=None,help='starter book json to bundle (default: keep the current one)');a=a.parse_args()
    export(a.src,a.tgt,a.pack or PACKS/f'gloss-{a.src}-{a.tgt}.sqlite',
           Path(a.out or ROOT/'web'/f'dict-{a.src}-{a.tgt}.json'),a.starter)
