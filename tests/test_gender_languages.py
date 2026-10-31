"""gender.js tag() for the languages besides German: one sentence each, with the traps the rules are for
(an article picking between two genders, el agua, l'eau, a word that is also a verb, names mid-sentence).
Runs under node; skipped when node is not installed."""
import json,shutil,subprocess,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
NODE=shutil.which('node')
RUN="""
const G=require(process.argv[1]+'/web/gender.js'),zlib=require('zlib'),fs=require('fs'),out={};
for(const[lang,text]of Object.entries(JSON.parse(process.argv[2]))){
  const d=JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[1]+'/web/genders-'+lang+'.json.gz')));
  const words=text.split(' ');out[lang]=Object.fromEntries(G.tag(words,d,lang).map((g,i)=>[words[i],g]));
}
console.log(JSON.stringify(out));
"""
CASES={
  'es':('La casa de María tiene el agua fría y la parte vieja . Parte mañana .',{'casa':'f','María':None,'agua':'f','parte':'f','Parte':None,'mañana':None}),
  'fr':("Il est dans la maison avec l'eau et le livre .",{'est':None,'maison':'f',"l'eau":'f','livre':'m'}),
  'it':("La città e il problema dell'anno .",{'città':'f','problema':'m',"dell'anno":'m'}),
  'pt':('O coração da avó está na casa .',{'coração':'m','avó':'f','casa':'f'}),
  'ru':('Книга лежит в доме у окна .',{'Книга':'f','доме':'m','окна':'n'}),
  'pl':('Kobieta i dziecko są w domu .',{'Kobieta':'f','dziecko':'n','domu':'m'}),
  'nl':('Het meisje zit aan de tafel in het huis .',{'meisje':'n','tafel':'c','huis':'n'}),
  'sv':('Bilen står vid huset och en bil .',{'Bilen':'c','huset':'n','bil':'c'}),
}

@unittest.skipUnless(NODE,'node not installed')
class GenderLanguages(unittest.TestCase):
    def test_each_language(self):
        got=json.loads(subprocess.run([NODE,'-e',RUN,str(ROOT),json.dumps({l:t for l,(t,_) in CASES.items()})],check=True,capture_output=True,text=True).stdout)
        for lang,(_,want) in CASES.items():
            with self.subTest(lang=lang):self.assertEqual({w:got[lang][w] for w in want},want)

if __name__=='__main__':unittest.main()
