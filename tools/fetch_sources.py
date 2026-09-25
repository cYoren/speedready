#!/usr/bin/env python3
"""Download everything build_pack.py needs, for every language pair Speedready offers.

    fetch_sources.py                 # all languages in LANGUAGES
    fetch_sources.py de pt es        # just these

Files land in --dir under the names build_pack.py expects. Already-downloaded files are skipped,
so a failed run is resumed by running it again.

kaikki.org serves these .jsonl extracts with Content-Encoding: gzip, which is a valid .gz stream,
so we save the bytes straight to <name>.jsonl.gz: ~10x less transfer and no recompression.
~2 GB over the wire for all ten languages, ~21 GB of JSON once decompressed on the fly by the build.
"""
import argparse,concurrent.futures,sys,urllib.error,urllib.parse,urllib.request
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from build_pack import LANGNAME,OWN_EDITION_NAME

KAIKKI='https://kaikki.org/{edition}/{dir}/kaikki.org-dictionary-{file}.jsonl'
FREQ='https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/{c}/{c}_50k.txt'
MUSE='https://dl.fbaipublicfiles.com/arrival/dictionaries/{src}-{tgt}.txt'
UA={'User-Agent':'Speedready pack builder (https://github.com/cYoren/speedready)'}
GZIP_MAGIC=b'\x1f\x8b'

def kaikki_url(edition,name):
    """The directory keeps the language name's spaces ('jezyk polski'); the filename strips them."""
    q=lambda s:urllib.parse.quote(s)
    return KAIKKI.format(edition=edition,dir=q(name),file=q(name.replace(' ','')))

def targets(langs):
    """-> [(destination filename, url, required)] for every source file the builds need."""
    out=[]
    for c in langs:
        out.append((f'en-{LANGNAME[c]}.jsonl.gz',kaikki_url('dictionary',LANGNAME[c]),True))
        if c in OWN_EDITION_NAME:out.append((f'{c}-{OWN_EDITION_NAME[c]}.jsonl.gz',kaikki_url(f'{c}wiktionary',OWN_EDITION_NAME[c]),False))
        out.append((f'freq-{c}.txt',FREQ.format(c=c),False))
    for src in langs:
        for tgt in langs:
            if src!=tgt:out.append((f'muse-{src}-{tgt}.txt',MUSE.format(src=src,tgt=tgt),False))
    return out

def get(d,name,url,required):
    """Ask for gzip only where we mean to keep the compressed bytes. Asking for it on a plain .txt
    and saving the body verbatim writes a gzip stream under a text name, which the build then reads
    as UTF-8 and dies on - so the magic bytes are checked both ways before anything is kept."""
    dest=d/name;want_gz=name.endswith('.gz')
    if dest.exists() and dest.stat().st_size>1000:return f'have  {name}'
    part=dest.with_suffix(dest.suffix+'.part')
    try:
        headers=dict(UA,**({'Accept-Encoding':'gzip'} if want_gz else {'Accept-Encoding':'identity'}))
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as r:
            if want_gz and r.headers.get('Content-Encoding')!='gzip':
                return f'FAIL  {name}: server sent it uncompressed, refusing to store {int(r.headers.get("Content-Length",0))/1e9:.1f} GB raw'
            with part.open('wb') as f:
                while chunk:=r.read(1<<20):f.write(chunk)
        head=part.open('rb').read(2)
        if (head==GZIP_MAGIC)!=want_gz:
            part.unlink(missing_ok=True)
            return f'FAIL  {name}: got {"gzip" if head==GZIP_MAGIC else "plain"} bytes, expected {"gzip" if want_gz else "plain"}'
        part.rename(dest)
        return f'got   {name} ({dest.stat().st_size/1e6:.0f} MB)'
    except urllib.error.HTTPError as e:
        part.unlink(missing_ok=True)
        # MUSE covers only some pairs and its bucket answers 403, not 404, for the rest
        if not required and e.code in(403,404):return f'none  {name} (optional, not published)'
        return f'FAIL  {name}: HTTP {e.code}'
    except Exception as e:
        part.unlink(missing_ok=True)
        return f'FAIL  {name}: {e}'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('langs',nargs='*',default=None,help=f'language codes (default: all of {" ".join(sorted(LANGNAME))})')
    ap.add_argument('--dir',default=str(Path.home()/'.cache/speedready/build'))
    ap.add_argument('--jobs',type=int,default=4,help='parallel downloads; kaikki.org is one small server, be kind')
    a=ap.parse_args()
    langs=a.langs or sorted(LANGNAME)
    bad=[c for c in langs if c not in LANGNAME]
    if bad:sys.exit(f'unknown language code(s): {" ".join(bad)}')
    d=Path(a.dir).expanduser();d.mkdir(parents=True,exist_ok=True)
    jobs=targets(langs)
    print(f'{len(jobs)} files -> {d}',file=sys.stderr)
    fails=0
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
        for line in ex.map(lambda j:get(d,*j),jobs):
            print(line,file=sys.stderr,flush=True);fails+=line.startswith('FAIL')
    print(f'\n{"done" if not fails else f"{fails} failed, rerun to resume"}',file=sys.stderr)
    return 1 if fails else 0

if __name__=='__main__':sys.exit(main())
