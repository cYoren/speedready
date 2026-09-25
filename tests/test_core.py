import sqlite3
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path

import speedready as app


class CoreTests(unittest.TestCase):
    def test_legacy_position_is_migrated(self):
        self.assertEqual(app.normalize_book_state(123), {'position': 123})
        state={'position':42,'wpm':275,'mode':'rsvp'}
        self.assertEqual(app.normalize_book_state(state),state)

    def test_atomic_text_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.json';app.atomic_text(path,'old');app.atomic_text(path,'new')
            self.assertEqual(path.read_text(),'new')
            self.assertFalse(path.with_suffix('.json.tmp').exists())

    def test_translation_urls_include_languages_and_phrase(self):
        phrase='Wie weit ist es?'
        deep=app.make_translation_url('deepl',phrase,'de','pt')
        google=urllib.parse.urlparse(app.make_translation_url('google',phrase,'de','pt'))
        self.assertIn('#de/pt/Wie%20weit%20ist%20es%3F',deep)
        query=urllib.parse.parse_qs(google.query)
        self.assertEqual(query['sl'],['de']);self.assertEqual(query['tl'],['pt']);self.assertEqual(query['text'],[phrase])

    def test_beginner_mode_never_claims_glosses_it_is_not_showing(self):
        def fake(db=None,error=None,src='de',tgt='pt'):
            g=object.__new__(app.Gloss);g.src,g.tgt,g.db,g.error,g.progress=src,tgt,db,error,'';return g
        state=lambda *a:app.gloss_state(*a)[0]
        self.assertEqual(state(False,'de','pt',None),'gloss_off')
        self.assertEqual(state(True,None,'pt',None),'gloss_no_book')
        self.assertEqual(state(True,'pt','pt',None),'gloss_same_lang')
        self.assertEqual(state(True,'de','pt',None),'gloss_loading')
        self.assertEqual(state(True,'de','pt',fake(db=sqlite3.connect(':memory:'))),app.GLOSS_OK)
        # the bug this guards: a 404 pack left the toggle on and the page blank, saying nothing
        self.assertEqual(state(True,'de','pt',fake(error='pack_none_published')),'gloss_unavailable')
        self.assertEqual(state(True,'de','en',fake(src='de',tgt='pt')),'gloss_loading')  # stale pack for another pair
        self.assertNotIn('gloss_off',app.BANNER_STATES);self.assertNotIn(app.GLOSS_OK,app.BANNER_STATES)

    def test_every_gloss_state_has_text_in_both_locales(self):
        for beginner,lang,gloss in ((False,'de',None),(True,None,None),(True,'pt',None),(True,'de',None)):
            key,values=app.gloss_state(beginner,lang,'pt',gloss)
            for loc in app.TEXT:self.assertTrue(app.tr(loc,key,**values))
        g=object.__new__(app.Gloss);g.src,g.tgt,g.db,g.error,g.progress='de','pt',None,'pack_none_published',''
        key,values=app.gloss_state(True,'de','pt',g)
        for loc in app.TEXT:self.assertIn(app.tr(loc,'pack_none_published'),app.tr(loc,key,**dict(values,error=app.tr(loc,values['error']))))

    def test_pack_error_explains_a_missing_release(self):
        e=urllib.error.HTTPError('u',404,'Not Found',{},None);self.addCleanup(e.close)
        self.assertEqual(app.pack_error(e),'pack_none_published')
        self.assertIn('pack_none_published',app.TEXT['en'])
        self.assertIn('network error',app.pack_error(urllib.error.URLError('down')))

    def test_library_lists_real_books_newest_first(self):
        pos={'_last':'/books/b.epub',                       # a pointer, not a book
             'Die_Welle.epub':698,                          # legacy key from before paths were used
             '/books/a.epub':{'position':10,'n':100,'read_at':50},
             '/books/b.epub':{'position':5,'n':200,'read_at':99},
             '/books/c.epub':{'position':0}}                # added, never opened: no read_at
        got=app.library_entries(pos)
        self.assertEqual([p for p,_ in got],['/books/b.epub','/books/a.epub','/books/c.epub'])
        self.assertEqual(got[0][1]['position'],5)
        self.assertEqual(app.library_entries({'_last':'/x'}),[])

    def test_book_title_prefers_epub_metadata_and_always_returns_something(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            good=Path(d)/'hash_1a2b3c_Annas.epub'
            with zipfile.ZipFile(good,'w') as z:
                z.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="c.opf"/></rootfiles></container>')
                z.writestr('c.opf','<package xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Krabat</dc:title></metadata></package>')
            self.assertEqual(app.book_title(str(good)),'Krabat')
            broken=Path(d)/'not_really_an_epub.epub';broken.write_bytes(b'nope')
            self.assertEqual(app.book_title(str(broken)),'not really an epub')   # never raises, never empty
            self.assertEqual(app.book_title(str(Path(d)/'a_plain_book.txt')),'a plain book')

    def test_web_reader_names_its_language_pair_only_in_bundle_json(self):
        """The web app is also the Android app. It used to hardcode de->pt in three files, so the
        phone app could only ever read German. bundle.json is now the single place that says which
        pair ships; nothing else may name a dictionary or starter file."""
        import json
        web=Path(__file__).resolve().parent.parent/'web'
        bundle=json.loads((web/'bundle.json').read_text())
        for key in ('dict','starter'):
            self.assertTrue((web/bundle[key]).exists(),f'bundle.json {key}={bundle[key]!r} is missing from web/')
        d=json.loads((web/bundle['dict']).read_text())
        self.assertEqual(bundle['dict'],f"dict-{d['src']}-{d['tgt']}.json")   # the dict agrees with its own name
        for name in ('index.html','sw.js'):
            text=(web/name).read_text()
            for bad in ('dict-de-pt','starter-de',"'de'",'"de"','de-DE'):
                self.assertNotIn(bad,text,f'{name} hardcodes {bad!r}; it must come from bundle.json or the dictionary')

    def test_web_lookup_prefers_an_exact_case_hit_over_a_lowercased_form(self):
        """German capitalisation separates the noun from the verb. When the lowercase form lookup
        ran first, the web reader resolved 'Buch' through 'buchen' and glossed a book as "to record"
        (agreement with the desktop reader over the starter book: 89.4% -> 93.3% once reordered)."""
        js=(Path(__file__).resolve().parent.parent/'web'/'index.html').read_text()
        exact=js.index('(S.dict.g[w]?w:null)')
        lowered=js.index('S.dict.f[w.toLowerCase()]')
        self.assertLess(exact,lowered,'the exact-case gloss must be tried before any lowercased form lemma')

    def test_old_config_still_gets_languages_added_later(self):
        # a saved config wins wholesale over DEFAULTS, so a user who once edited one voice
        # would otherwise be pinned to the languages that existed that day
        cfg={'tts_voices':'de=my_custom_voice','web_dicts':'de=https://example.invalid/{word}'}
        v=app.merged(cfg,'tts_voices')
        self.assertEqual(v['de'],'my_custom_voice')                 # their edit survives
        for lang,_ in app.LANGUAGES:self.assertIn(lang,v)           # every offered language has a voice
        self.assertIn('*',app.merged(cfg,'web_dicts'))              # and the wiktionary fallback survives

    def test_german_portuguese_grammar_overrides(self):
        g=object.__new__(app.Gloss);g.src='de';g.tgt='pt';g.cache={};g.learned=set();g.db=sqlite3.connect(':memory:')
        g.db.executescript('CREATE TABLE forms(form TEXT,lemma TEXT);CREATE TABLE gloss(word TEXT,pos TEXT,tgt TEXT,prio INT);CREATE TABLE freq(word TEXT,rank INT);')
        self.assertEqual(g.raw('dem'),('ao; no','der'))
        self.assertEqual(g.raw('im'),('no; na','in'))

    def test_common_exact_word_beats_wrong_lemma_sense(self):
        g=object.__new__(app.Gloss);g.src='de';g.tgt='pt';g.cache={};g.learned=set();g.db=sqlite3.connect(':memory:')
        g.db.executescript("""
            CREATE TABLE forms(form TEXT,lemma TEXT);CREATE TABLE gloss(word TEXT,pos TEXT,tgt TEXT,prio INT);CREATE TABLE freq(word TEXT,rank INT);
            INSERT INTO forms VALUES('nun','noun');INSERT INTO freq VALUES('nun',20);
            INSERT INTO gloss VALUES('noun','pron','alguém',1);INSERT INTO gloss VALUES('nun','adv','agora',1);
        """)
        self.assertEqual(g.raw('Nun')[0],'agora')

    def test_non_target_fallback_is_hidden(self):
        g=object.__new__(app.Gloss);g.src='de';g.tgt='pt';g.cache={};g.learned=set();g.db=sqlite3.connect(':memory:')
        g.db.executescript("""
            CREATE TABLE forms(form TEXT,lemma TEXT);CREATE TABLE gloss(word TEXT,pos TEXT,tgt TEXT,prio INT);CREATE TABLE freq(word TEXT,rank INT);
            INSERT INTO gloss VALUES('Holztreppe','noun','wooden staircase',9);
        """)
        self.assertEqual(g.raw('Holztreppe')[0],None)


if __name__=='__main__':unittest.main()
