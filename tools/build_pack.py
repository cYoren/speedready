#!/usr/bin/env python3
"""Build an offline gloss pack: gloss-<src>-<tgt>.sqlite, used by Speedready's beginner mode.

    build_pack.py de pt --dir ~/.cache/speedready/build

Sources (all public, downloaded once into --dir):
  en-<Src>.jsonl     kaikki.org extract of English Wiktionary entries for the source language
                     -> inflected forms -> lemma, English glosses (pivot, or the target itself when tgt == en)
  de-<Src>.jsonl     kaikki.org extract of the source language's own Wiktionary edition (translation tables -> tgt), optional
  en-<Tgt>.jsonl     kaikki extract for the target language, inverted into an English -> target map for the pivot, optional
  muse-<src>-<tgt>.txt   Meta MUSE bilingual word list, optional fallback
  freq-<src>.txt     hermitdave/FrequencyWords "<word> <count>" list

Pack schema: forms(form, lemma) · gloss(word, pos, tgt, prio) · freq(word, rank) · meta(key, value)
prio: 1 own-edition translation · 2 pivot through English Wiktionary · 3 MUSE · 9 English gloss only
"""
import argparse,collections,gzip,json,re,sqlite3,sys,time
from pathlib import Path

LANGNAME={'de':'German','pt':'Portuguese','en':'English','es':'Spanish','fr':'French','it':'Italian','nl':'Dutch','ru':'Russian','sv':'Swedish','pl':'Polish'}
OWN_EDITION_NAME={'de':'Deutsch','fr':'Français','es':'Español','it':'Italiano','pt':'Português','nl':'Nederlands','ru':'Русский','pl':'Polski','sv':'Svenska'}
PAREN=re.compile(r'\([^)]*\)|\[[^\]]*\]');SKIP_GLOSS=re.compile(r'^(?:\w+[ -])*(?:of|form of|inflection of|spelling of|abbreviation of|initialism of|misspelling of)\b',re.I)

def jsonl(path):
    path=path if path.exists() else path.with_suffix(path.suffix+'.gz')
    with (gzip.open if path.suffix=='.gz' else open)(path,'rt',encoding='utf-8') as f:
        for n,line in enumerate(f):
            if n and n%200000==0:print(f'  {path.name}: {n:,} lines',file=sys.stderr,flush=True)
            try:yield json.loads(line)
            except json.JSONDecodeError:break  # partial download

def candidates(gloss):
    """'to go, to walk (on foot)' -> ['go','walk']: short pieces of an English gloss usable as dictionary keys."""
    g=PAREN.sub('',gloss);out=[]
    for part in re.split(r'[,;]',g):
        part=part.strip().strip('.').lower();part=re.sub(r'^(to|a|an|the) ','',part)
        if part and len(part.split())<=2 and re.fullmatch(r"[a-z' -]+",part):out.append(part)
    return out

def build(src,tgt,d,out):
    t0=time.time();forms={};gloss=collections.defaultdict(dict);en_gloss={}  # (word,pos)->[english candidates]
    # ---- 1. English Wiktionary, source language: forms and English glosses
    f=d/f'en-{LANGNAME[src]}.jsonl'
    if not f.exists() and not f.with_suffix('.jsonl.gz').exists():sys.exit(f'missing {f}')
    n=0
    for e in jsonl(f):
        w,pos=e.get('word',''),e.get('pos','');n+=1
        for x in e.get('forms',[]):
            fm=x.get('form','');tags=set(x.get('tags',[]))
            if fm and fm!=w and ' ' not in fm and not tags&{'table-tags','inflection-template','class','romanization','alternative','obsolete','archaic','misspelling'}:forms.setdefault(fm,w)
        glosses=[]
        for s in e.get('senses',[]):
            fo=s.get('form_of') or s.get('alt_of')
            if fo:forms.setdefault(w,fo[0].get('word',w));continue
            if 'form-of' in s.get('tags',[]) or 'alt-of' in s.get('tags',[]):continue
            for g in s.get('glosses',[])[:1]:
                if not SKIP_GLOSS.match(g):glosses.append(g)
        if glosses:en_gloss[(w,pos)]=glosses
    print(f'en-{src}: {n:,} entries, {len(forms):,} forms, {len(en_gloss):,} glossed lemmas',file=sys.stderr)
    if tgt=='en':
        for (w,pos),gs in en_gloss.items():gloss[(w,pos)].setdefault(9,PAREN.sub('',gs[0]).strip()[:80])
    else:
        for (w,pos),gs in en_gloss.items():gloss[(w,pos)].setdefault(9,PAREN.sub('',gs[0]).strip()[:80])  # English fallback, shown only when nothing else exists
    # ---- 2. own-edition translation tables
    f=d/f'de-{OWN_EDITION_NAME.get(src,"")}.jsonl'
    if tgt!='en' and (f.exists() or f.with_suffix('.jsonl.gz').exists()):
        n=k=0
        for e in jsonl(f):
            n+=1;w,pos=e.get('word',''),e.get('pos','');tr=[t.get('word') for t in e.get('translations',[]) if t.get('lang_code')==tgt and t.get('word')]
            if tr:
                tr=[t for t in dict.fromkeys(tr) if len(t.split())<=3][:3]
                if tr:gloss[(w,pos)].setdefault(1,', '.join(tr));k+=1
        print(f'own edition: {n:,} entries, {k:,} with {tgt} translations',file=sys.stderr)
    # ---- 3. pivot through English: target-language extract inverted
    f=d/f'en-{LANGNAME.get(tgt,"")}.jsonl'
    if tgt!='en' and (f.exists() or f.with_suffix('.jsonl.gz').exists()):
        en2t=collections.defaultdict(collections.Counter);n=0
        for e in jsonl(f):
            n+=1;w,pos=e.get('word',''),e.get('pos','')
            if ' ' in w:continue
            for s in e.get('senses',[]):
                if s.get('form_of') or s.get('alt_of') or 'form-of' in s.get('tags',[]):continue
                for g in s.get('glosses',[])[:1]:
                    for c in candidates(g):en2t[(c,pos)][w]+=1;en2t[(c,None)][w]+=1
        k=0
        for (w,pos),gs in en_gloss.items():
            for g in gs[:2]:
                hit=next((en2t[(c,pos)] or en2t[(c,None)] for c in candidates(g) if en2t.get((c,pos)) or en2t.get((c,None))),None)
                if hit:gloss[(w,pos)].setdefault(2,', '.join(x for x,_ in hit.most_common(2)));k+=1;break
        print(f'pivot: {n:,} {tgt} entries, {k:,} {src} lemmas glossed via English',file=sys.stderr)
    # ---- 4. MUSE
    f=d/f'muse-{src}-{tgt}.txt'
    if f.exists():
        m=collections.defaultdict(list)
        for line in f.read_text(encoding='utf-8').splitlines():
            p=line.split()
            if len(p)==2 and p[1] not in m[p[0]]:m[p[0]].append(p[1])
        for w,ts in m.items():gloss[(w,'')].setdefault(3,', '.join(ts[:3]))
        print(f'muse: {len(m):,} forms',file=sys.stderr)
    # ---- 5. frequency
    freq={};f=d/f'freq-{src}.txt'
    if f.exists():
        for r,line in enumerate(f.read_text(encoding='utf-8').splitlines(),1):
            w=line.split()[0]
            if w not in freq:freq[w]=r
    # ---- write
    out.unlink(missing_ok=True);db=sqlite3.connect(out)
    db.executescript('''CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE forms(form TEXT PRIMARY KEY,lemma TEXT);
        CREATE TABLE gloss(word TEXT,pos TEXT,tgt TEXT,prio INT);CREATE INDEX gw ON gloss(word);CREATE TABLE freq(word TEXT PRIMARY KEY,rank INT);''')
    db.executemany('INSERT INTO forms VALUES(?,?)',forms.items())
    db.executemany('INSERT INTO gloss VALUES(?,?,?,?)',((w,pos,t,p) for (w,pos),d_ in gloss.items() for p,t in d_.items()))
    db.executemany('INSERT INTO freq VALUES(?,?)',freq.items())
    db.executemany('INSERT INTO meta VALUES(?,?)',[('src',src),('tgt',tgt),('built',time.strftime('%Y-%m-%d')),('sources','en.wiktionary (kaikki.org), own-edition wiktionary, MUSE (CC BY-NC 4.0), hermitdave/FrequencyWords')])
    db.commit();db.execute('VACUUM');db.close()
    print(f'wrote {out} ({out.stat().st_size/1e6:.1f} MB) in {time.time()-t0:.0f}s',file=sys.stderr)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('src');ap.add_argument('tgt');ap.add_argument('--dir',default=str(Path.home()/'.cache/speedready/build'));ap.add_argument('--out')
    a=ap.parse_args();build(a.src,a.tgt,Path(a.dir).expanduser(),Path(a.out or f'gloss-{a.src}-{a.tgt}.sqlite'))
