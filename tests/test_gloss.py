"""The shipped web dictionary must carry the desktop reader's answers, surface forms included (TODO 7)."""
import json,sys,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from export_web import web_lookup

D=json.loads((ROOT/'web/dict-de-pt.json').read_text())

class WebDictionaryTests(unittest.TestCase):
    def test_surface_forms_carry_their_own_scored_answer(self):
        self.assertIn('s',D)
        self.assertEqual(web_lookup(D,'Forscher')[0],'explorador')   # the noun, not a form of 'forschen'
        self.assertEqual(web_lookup(D,'Daten')[0],'dados')           # Datum, not the verb 'daten'
        self.assertEqual(web_lookup(D,'Dicht')[0],'grosso, crasso')  # the adjective the desktop picks
    def test_curated_glosses_still_win(self):
        self.assertEqual(web_lookup(D,'Buch'),('livro','Buch'))
        self.assertEqual(web_lookup(D,'ist'),('é; está','sein'))
        self.assertEqual(web_lookup(D,'wollen'),('querer','wollen'))
    def test_punctuation_is_stripped_the_way_the_reader_does(self):
        self.assertEqual(web_lookup(D,'»Haus«')[0],'casa')
        self.assertIsNone(web_lookup(D,'')[0])

if __name__=='__main__':unittest.main()
