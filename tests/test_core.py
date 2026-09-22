import sqlite3
import tempfile
import unittest
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
