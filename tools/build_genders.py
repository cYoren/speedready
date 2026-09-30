#!/usr/bin/env python3
"""Build genders-de.json.gz: every German noun form -> the genders it can have, for gender.py.

    build_genders.py ~/.cache/speedready/build/en-German.jsonl.gz

Value per form: reading letters in the order to prefer them when the text gives no clue.
  m f n  singular of a masculine / feminine / neuter noun   ('See' -> 'mf': lake first, sea second)
  M F N  plural of one                                       ('Seen' -> 'MF')
  P      plural-only noun, no gender                         ('Eltern' -> 'P')
  *      suffix: the lowercase word is also a non-noun ('Essen'/'essen', 'Morgen'/'morgen'), so at the
         start of a sentence, where everything is capitalized, it may not be this noun at all.
A form's own headword readings come before readings it gets as someone else's inflection, so 'Essen' is
'nF' (das Essen before the plural of die Esse). Plain JSON + gzip: Python and a browser extension
(DecompressionStream) both read it without a library.
"""
import gzip,json,re,sys
from pathlib import Path

SKIP={'table-tags','inflection-template','class','romanization','diminutive','masculine','feminine','neuter','alternative','obsolete','archaic','misspelling','dialectal'}

def genders(e):
    """'See m (mixed, …)' -> 'm'; 'Teil m or n' -> 'mn'; 'Eltern pl (plural only)' -> 'P'."""
    for h in e.get('head_templates',[]):
        head=h.get('expansion','').split(' (')[0].split()[1:]
        if 'pl' in head and not any(g in head for g in 'mfn'):return 'P'
        g=''.join(x for x in head if x in('m','f','n'))
        if g:return g
    return ''

def main(src,out):
    head,infl,other={},{},set()
    add=lambda d,form,r:d.setdefault(form,'') if r in d.get(form,'') else d.__setitem__(form,d.get(form,'')+r)
    with gzip.open(src,'rt',encoding='utf-8') as f:
        for line in f:
            e=json.loads(line);w=e.get('word','')
            if e.get('pos')!='noun':
                other.update(x for x in [w]+[x.get('form','') for x in e.get('forms',[])] if x[:1].islower());continue   # not names: 'Mühle' the surname
            g=genders(e);senses=e.get('senses',[])
            if g=='P' and senses and all(s.get('form_of') or 'form-of' in s.get('tags',[]) for s in senses):continue   # 'Ohren: plural of Ohr' is not a plural-only noun (but 'Lehrer: agent of lehren' is a noun)
            if not g or ' ' in w:continue   # form-of entries have no gender of their own; the lemma's form list covers them
            for x in g:add(head,w,x)
            for x in e.get('forms',[]):
                fm=x.get('form','');tags=set(x.get('tags',[]))
                if not fm or ' ' in fm or tags&SKIP or not fm[:1].isupper():continue
                for r in g:add(infl,fm,'P' if r=='P' else r.upper() if 'plural' in tags and 'singular' not in tags else r)
    data={}
    for form in head.keys()|infl.keys():
        r=head.get(form,'')
        for x in infl.get(form,''):
            if x not in r:r+=x
        data[form]=r+('*' if form.lower() in other else '')
    with gzip.open(out,'wt',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,separators=(',',':'),sort_keys=True)
    print(f'{len(data):,} forms -> {out} ({Path(out).stat().st_size/1e6:.1f} MB)')

if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else Path.home()/'.cache/speedready/build/en-German.jsonl.gz',Path(__file__).parent.parent/'genders-de.json.gz')
