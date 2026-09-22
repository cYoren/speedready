#!/usr/bin/env python3
"""Export a gloss pack for the web reader: gloss-<src>-<tgt>.sqlite -> web/dict-<src>-<tgt>.json

The desktop pack is ~33 MB of SQLite indexes and English fallbacks the app never shows.
What the web needs is two maps, which gzip to under 2 MB:
    {"g": {lemma: "gloss"}, "f": {form: lemma}, "o": {word: ["gloss","lemma"]}}
"o" is the curated override table, applied before everything else, same as the desktop app.
"""
import argparse,json,re,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from speedready import GLOSS_OVERRIDES,Gloss

def export(src,tgt,pack,out):
    db=sqlite3.connect(pack);best={}
    for w,t in db.execute('SELECT word,tgt FROM gloss WHERE prio<9 ORDER BY prio DESC'):best[w]=Gloss.short(t)
    forms={f:l for f,l in db.execute('SELECT form,lemma FROM forms') if l in best}
    over={w:list(v) for w,v in GLOSS_OVERRIDES.get((src,tgt),{}).items()}
    freq={w:r for w,r in db.execute('SELECT word,rank FROM freq WHERE rank<=2000')}
    data={'src':src,'tgt':tgt,'g':best,'f':forms,'o':over,'r':freq}
    out.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'{out} {out.stat().st_size/1e6:.1f} MB  ({len(best):,} glosses, {len(forms):,} forms, {len(over):,} overrides)')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('src');a.add_argument('tgt')
    a.add_argument('--pack',default=None);a.add_argument('--out',default=None);a=a.parse_args()
    export(a.src,a.tgt,a.pack or Path.home()/f'.cache/speedready/packs/gloss-{a.src}-{a.tgt}.sqlite',
           Path(a.out or Path(__file__).resolve().parent.parent/'web'/f'dict-{a.src}-{a.tgt}.json'))
