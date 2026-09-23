#!/usr/bin/env python3
"""Build every gloss pack Speedready can offer, keep the ones worth shipping, and upload them.

    fetch_sources.py                    # first: ~2 GB of Wiktionary extracts
    release_packs.py --jobs 6           # build + measure, writes to --out
    release_packs.py --upload           # then: gh release upload, needs a repo you can write to

A pack that exists but glosses nothing is worse than no pack: the app would report the dictionary
ready and then show a page of blank glosses. So every build is measured against the words a reader
actually meets (the top of the frequency list) and anything under --min-coverage is left unpublished,
which makes the app say "none published for this pair yet" - true, and actionable.
"""
import argparse,concurrent.futures,sqlite3,subprocess,sys,time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from build_pack import LANGNAME

TOOLS=Path(__file__).parent

def coverage(pack,top=2000):
    """Share of the commonest words that get a gloss a reader would actually see.
    Mirrors Gloss.raw() in speedready.py: same lemma fallback, and prio 9 is English-only filler
    that raw() discards for every target except English."""
    db=sqlite3.connect(pack)
    tgt=dict(db.execute('SELECT key,value FROM meta')).get('tgt')
    usable='' if tgt=='en' else ' AND prio<9'
    words=[w for (w,) in db.execute('SELECT word FROM freq ORDER BY rank LIMIT ?',(top,))]
    if not words:return 0.0,0
    hit=0
    for w in words:
        cands=list(dict.fromkeys((w,w.lower(),w.capitalize())))
        lemma=next((r[0] for c in cands for r in [db.execute('SELECT lemma FROM forms WHERE form=?',(c,)).fetchone()] if r),None)
        keys=cands+([lemma] if lemma else [])
        q=f'SELECT 1 FROM gloss WHERE word IN ({",".join("?"*len(keys))}){usable} LIMIT 1'
        hit+=bool(db.execute(q,keys).fetchone())
    total=db.execute(f'SELECT count(DISTINCT word) FROM gloss WHERE 1{usable}').fetchone()[0]
    db.close()
    return hit/len(words),total

def finished(pack):
    """build_pack writes meta last, then VACUUMs, so a readable 'built' row means the file is complete
    and a pack killed mid-write is rebuilt rather than silently shipped half-empty."""
    try:
        db=sqlite3.connect(f'file:{pack}?mode=ro',uri=True)
        try:return bool(db.execute("SELECT 1 FROM meta WHERE key='built'").fetchone())
        finally:db.close()
    except sqlite3.Error:return False

def build(src,tgt,d,out):
    pack=out/f'gloss-{src}-{tgt}.sqlite';t0=time.time()
    if finished(pack):
        cov,total=coverage(pack)
        return src,tgt,pack,cov,total,'cached'
    r=subprocess.run([sys.executable,str(TOOLS/'build_pack.py'),src,tgt,'--dir',str(d),'--out',str(pack)],
                     capture_output=True,text=True)
    if r.returncode:return src,tgt,None,0.0,0,r.stderr.strip().splitlines()[-1] if r.stderr else 'build failed'
    cov,total=coverage(pack)
    return src,tgt,pack,cov,total,f'{time.time()-t0:.0f}s'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dir',default=str(Path.home()/'.cache/speedready/build'))
    ap.add_argument('--out',default=str(Path.home()/'.cache/speedready/packs-release'))
    ap.add_argument('--jobs',type=int,default=6)
    ap.add_argument('--min-coverage',type=float,default=0.50,help='share of the top 2000 words that must get a gloss')
    ap.add_argument('--langs',nargs='*',default=sorted(LANGNAME))
    ap.add_argument('--upload',metavar='REPO',nargs='?',const='cYoren/speedready',help='gh release upload the kept packs')
    a=ap.parse_args()
    d=Path(a.dir).expanduser();out=Path(a.out).expanduser();out.mkdir(parents=True,exist_ok=True)
    pairs=[(s,t) for s in a.langs for t in a.langs if s!=t]

    if not a.upload:
        print(f'building {len(pairs)} packs with {a.jobs} jobs',file=sys.stderr)
        keep,drop=[],[]
        with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
            for src,tgt,pack,cov,total,note in ex.map(lambda p:build(*p,d,out),pairs):
                if pack is None:print(f'{src}->{tgt}  FAILED  {note}',file=sys.stderr);drop.append((src,tgt));continue
                ok=cov>=a.min_coverage
                print(f'{src}->{tgt}  top2000 {cov:5.1%}  {total:>6,} words  {pack.stat().st_size/1e6:5.1f} MB  {note}  {"keep" if ok else "DROP"}',
                      file=sys.stderr,flush=True)
                (keep if ok else drop).append((src,tgt))
                if not ok:pack.unlink()
        print(f'\nkeeping {len(keep)}, dropped {len(drop)}: {" ".join(f"{s}-{t}" for s,t in drop) or "none"}',file=sys.stderr)
        print('review, then rerun with --upload',file=sys.stderr)
        return 0

    packs=sorted(out.glob('gloss-*.sqlite'))
    if not packs:sys.exit(f'no packs in {out}; build them first')
    print(f'uploading {len(packs)} packs ({sum(p.stat().st_size for p in packs)/1e9:.1f} GB) to {a.upload} release "packs"',file=sys.stderr)
    subprocess.run(['gh','release','create','packs','--repo',a.upload,'--title','Offline gloss packs',
                    '--notes','Offline dictionaries for beginner mode, one per language pair. Built by tools/release_packs.py from '
                              'English Wiktionary and each language\'s own Wiktionary edition (kaikki.org), MUSE, and hermitdave/FrequencyWords. '
                              'Downloaded by the app on first use.'],capture_output=True)  # already exists -> fine
    r=subprocess.run(['gh','release','upload','packs','--repo',a.upload,'--clobber',*map(str,packs)])
    return r.returncode

if __name__=='__main__':sys.exit(main())
