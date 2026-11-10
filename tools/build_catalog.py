#!/usr/bin/env python3
"""Build a searchable snapshot from Gutenberg's official public-domain metadata.
The source is cached; pass --refresh only when deliberately updating the snapshot.
"""
import argparse,csv,gzip,io,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SOURCE='https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv'
def main():
    p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');a=p.parse_args()
    cache=Path.home()/'.cache/speedready/pg_catalog.csv';cache.parent.mkdir(parents=True,exist_ok=True)
    if a.refresh or not cache.exists():
        with urllib.request.urlopen(SOURCE,timeout=60) as r:data=r.read()
        cache.write_bytes(data)
    rows=csv.DictReader(io.StringIO(cache.read_text(encoding='utf-8-sig')))
    books=[[int(r['Text#']),r['Title'],r['Authors'],r['Language'].replace(' ','').split(';')] for r in rows if r['Type']=='Text']
    target=ROOT/'web/catalog.json.gz'
    target.write_bytes(gzip.compress(json.dumps({'source':SOURCE,'books':books},ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    print(f'{len(books)} books, {len(set(l for b in books for l in b[3]))} languages, {target.stat().st_size:,} bytes')
if __name__=='__main__':main()
