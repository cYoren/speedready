#!/usr/bin/env python3
"""Quality gate for gloss packs: does each pair translate a dozen basic words correctly?

    score_packs.py ~/.cache/speedready/packs-release            # every pack in a directory
    score_packs.py gloss-en-pt.sqlite gloss-sv-en.sqlite         # or some

Reads the same rows tools/export_web.py ships (Wiktionary prio 1-2; prio 9 when the target is English), so
a score here is what a reader sees. A pair below 10/12 is not fit to advertise; the failures it prints say why
(wrong sense of a homograph, a definition instead of a translation, nothing at all).
"""
import os,re,sqlite3,sys
from pathlib import Path

CONCEPTS={   # one basic word per language; '|' separates accepted answers
 'house':dict(de='Haus',en='house',es='casa',fr='maison',it='casa',nl='huis',pl='dom',pt='casa',ru='дом',sv='hus'),
 'water':dict(de='Wasser',en='water',es='agua',fr='eau',it='acqua',nl='water',pl='woda',pt='água',ru='вода',sv='vatten'),
 'dog':dict(de='Hund',en='dog',es='perro',fr='chien',it='cane',nl='hond',pl='pies',pt='cão|cachorro',ru='собака',sv='hund'),
 'book':dict(de='Buch',en='book',es='libro',fr='livre',it='libro',nl='boek',pl='książka',pt='livro',ru='книга',sv='bok'),
 'day':dict(de='Tag',en='day',es='día',fr='jour',it='giorno',nl='dag',pl='dzień',pt='dia',ru='день',sv='dag'),
 'mother':dict(de='Mutter',en='mother',es='madre',fr='mère',it='madre',nl='moeder',pl='matka',pt='mãe',ru='мать',sv='mor|mamma'),
 'big':dict(de='groß',en='big|large',es='grande',fr='grand',it='grande',nl='groot',pl='duży',pt='grande',ru='большой',sv='stor'),
 'red':dict(de='rot',en='red',es='rojo',fr='rouge',it='rosso',nl='rood',pl='czerwony',pt='vermelho',ru='красный',sv='röd'),
 'eat':dict(de='essen',en='eat',es='comer',fr='manger',it='mangiare',nl='eten',pl='jeść',pt='comer',ru='есть|кушать',sv='äta'),
 'go':dict(de='gehen',en='go|walk',es='ir',fr='aller',it='andare',nl='gaan',pl='iść',pt='ir',ru='идти',sv='gå'),
 'and':dict(de='und',en='and',es='y',fr='et',it='e',nl='en',pl='i',pt='e',ru='и',sv='och'),
 'with':dict(de='mit',en='with',es='con',fr='avec',it='con',nl='met',pl='z',pt='com',ru='с',sv='med'),
}

def score(path):
    src,tgt=Path(path).stem.split('-')[1:3];db=sqlite3.connect(path);ok=0;bad=[]
    for c,w in CONCEPTS.items():
        word=w[src].split('|')[0]
        row=db.execute("SELECT tgt FROM gloss WHERE word=? AND (prio IN (1,2) OR (prio=9 AND ?='en')) ORDER BY prio,rowid LIMIT 1",(word,tgt)).fetchone()
        g=(row or [''])[0];parts=[re.sub(r'^(a|an|the|to) |[.:;!?]+$','',p.strip().lower()) for p in g.replace(';',',').split(',')]   # 'a dog', 'book:'
        hit=any(a.lower() in parts or a.lower() in g.lower().split() for a in w[tgt].split('|'))
        ok+=hit;hit or bad.append(f'{word}={g[:20] or "-"}')
    return src,tgt,ok,bad

if __name__=='__main__':
    paths=[p for a in sys.argv[1:] for p in(sorted(Path(a).glob('gloss-*.sqlite')) if os.path.isdir(a) else [Path(a)])]
    res=sorted(score(p) for p in paths)
    for s,t,ok,bad in sorted(res,key=lambda r:r[2]):print(f'{s}->{t} {ok:2}/{len(CONCEPTS)}  {" ".join(bad[:4])}')
    low=[f'{s}-{t}' for s,t,ok,_ in res if ok<10]
    print(f'\n{len(res)} pairs, {len(low)} below 10/{len(CONCEPTS)}: {" ".join(low)}' if low else f'\n{len(res)} pairs, all at least 10/{len(CONCEPTS)}')
    sys.exit(1 if low else 0)
