"""The web reader's gender.js / textclean.js must give exactly what gender.py / Book.clean give,
and its shipped dictionary lookup exactly what the exported gloss map answers."""
import json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path

import gender
import speedready as app

ROOT=Path(__file__).resolve().parent.parent
NODE=shutil.which('node')
sys.path.insert(0,str(ROOT/'tools'))
from export_web import web_lookup
RUN="""
const G=require(process.argv[2]+'/web/gender.js'),C=require(process.argv[2]+'/web/textclean.js'),zlib=require('zlib'),fs=require('fs');
const data=JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[2]+'/web/genders-de.json.gz')));
const input=JSON.parse(fs.readFileSync(process.argv[3]));
const out=input.map(b=>{const c=C.clean(b.words,b.para,b.chapters,b.names);
  c.chapters=C.resolveMissing(c.words,c.para,c.chapters).filter(([t,i])=>t&&i<c.words.length);
  return {genders:G.genders(b.words,data,b.para),clean:c,start:C.start(c.chapters,c.words.length)}});
fs.writeFileSync(process.argv[3],JSON.stringify(out));
"""

LOOKUP="""
const fs=require('fs');
const html=fs.readFileSync(process.argv[2]+'/web/index.html','utf8');
const NL=String.fromCharCode(10);
const at=html.indexOf('const strip=');
const strip=html.slice(at,html.indexOf(NL,at));
const a=html.indexOf('function glossOf(word){'),b=html.indexOf(NL+'}',a);
const fn=html.slice(a,b+2);
const dict=JSON.parse(fs.readFileSync(process.argv[2]+'/web/dict-de-pt.json','utf8'));
const words=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const S={dict,book:null,native:'pt'};
const lookup=eval(strip+NL+fn+NL+';glossOf');
fs.writeFileSync(process.argv[3],JSON.stringify(words.map(w=>{const [g,l]=lookup(w);return [g,l]})));
"""

def js_lookup(words):
    with tempfile.TemporaryDirectory() as d:
        f=Path(d)/'words.json';f.write_text(json.dumps(words));script=Path(d)/'lookup.js';script.write_text(LOOKUP)
        subprocess.run([NODE,str(script),str(ROOT),str(f)],check=True);return json.loads(f.read_text())

def js(books):
    with tempfile.TemporaryDirectory() as d:
        f=Path(d)/'io.json';f.write_text(json.dumps(books));script=Path(d)/'run.js';script.write_text(RUN)
        subprocess.run([NODE,str(script),str(ROOT),str(f)],check=True);return json.loads(f.read_text())

def py(b):
    book=object.__new__(app.Book);book.words=list(b['words']);book.para_start=list(b['para']);book.chapters=[tuple(c) for c in b['chapters']]
    book.title='';book.old2new=[];book.clean(b['names']);book.resolve_missing();book.n=len(book.words);book.chapters=[[t,i] for t,i in book.chapters if t and i<book.n]
    return {'genders':gender.genders(b['words'],app.gender_data(),b['para']),'words':book.words,'para':book.para_start,'old2new':book.old2new,'chapters':book.chapters,'start':book.start()}

def synthetic():
    page='Er sah den Meister, der ihn lange und sehr genau und still an-\n– 7 –\nOtfried Preußler - Krabat\nschaute. Die stille See lag im Haus\x00fn1 der Mühlen.\n42\nNeu.\n'
    words=[];para=[]
    for line in(('Inhalt\n'+page*6)).split('\n'):
        ws=line.split()
        if ws:para.append(len(words));words+=ws
    return {'words':words,'para':para,'chapters':[['Inhalt',0],['Neu.',None],['Nirgends',None]],'names':'Krabat Otfried Preußler'}   # None: a broken anchor

def compare(t,books):
    for b,j in zip(books,js(books)):
        p=py(b)
        t.assertEqual(p['genders'],j['genders'])
        t.assertEqual((p['words'],p['para'],p['old2new'],p['chapters'],p['start']),(j['clean']['words'],j['clean']['para'],j['clean']['old2new'],j['clean']['chapters'],j['start']))

@unittest.skipUnless(NODE,'node not installed')
class WebParity(unittest.TestCase):
    def test_shipped_dictionary_lookup_matches_the_exported_map(self):
        dictionary=json.loads((ROOT/'web/dict-de-pt.json').read_text())
        words=list(dict.fromkeys(json.loads((ROOT/'web/starter-de.json').read_text())['words']))[:3000]
        self.assertEqual([list(web_lookup(dictionary,w)) for w in words],js_lookup(words))
    def test_same_output_on_the_starter_book_and_page_junk(self):
        s=json.loads((ROOT/'web/starter-de.json').read_text())
        wrapped='Der Müller stand in der Tür der alten Mühle und sah hinaus auf den Weg, der zum Dorf führte. Es war kalt'.split()
        words=['The','End','of','the','Road'];para=[0]   # a punctuation-free heading, then a book broken into one line per paragraph
        for k in range(0,len(wrapped)*4,8):para.append(len(words));words+=(wrapped*4)[k:k+8]
        prose=['Er','sah','ihn','an','und','ging'];ppara=[0]   # short, but not a heading: gets reflowed
        for k in range(0,len(wrapped)*4,8):ppara.append(len(prose));prose+=(wrapped*4)[k:k+8]
        compare(self,[synthetic(),{'words':words,'para':para,'chapters':[],'names':''},{'words':prose,'para':ppara,'chapters':[],'names':''},{'words':s['words'],'para':s['para'],'chapters':s['chapters'],'names':s['title']}])

if __name__=='__main__':   # python tests/test_web_parity.py book.epub … : the same check over real books
    import sys
    if len(sys.argv)<2:unittest.main()
    books=[]
    for p in sys.argv[1:]:
        parts,lang,authors=app.read_epub(p);words=[];para=[];chapters=[]
        b=object.__new__(app.Book);b.words=[];b.para_start=[]
        for text,toc in parts:
            base=len(b.words);b.add(text);chapters+=[[t,base+o if o is not None else None] for t,o in toc]
        books.append({'words':b.words,'para':b.para_start,'chapters':chapters,'names':app.book_title(p)+' '+authors})
    t=unittest.TestCase();t.maxDiff=2000;compare(t,books);print(f'identical on {len(books)} books, {sum(len(b["words"]) for b in books):,} words')
