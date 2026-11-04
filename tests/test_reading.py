import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import reading,bookcatalog,speedready as app

class ReadingTests(unittest.TestCase):
    def test_language_codes_do_not_truncate_unrelated_languages(self):
        for tag,want in [('de-DE','de'),('ger','de'),('zho-Hant','zh'),('jpn','ja'),('ara','ar'),('fil','fil'),('haw','haw'),('und','und'),('pt_BR','pt')]:
            self.assertEqual(reading.lang_code(tag),want)
        self.assertEqual(reading.lang_code('not a language'),'')
    def test_spaced_text_indices_stay_unchanged(self):
        self.assertEqual(reading.tokenize('Olá, mundo!\nComo vai?','pt'),['Olá,','mundo!','Como','vai?'])
    def test_unspaced_scripts_segment_without_losing_text(self):
        for lang,text in [('zh','我喜欢读书。你呢？'),('ja','私は本を読みます。'),('th','ฉันชอบอ่านหนังสือ')]:
            words=reading.tokenize(text,lang)
            self.assertGreater(len(words),1);self.assertEqual(''.join(words),text)
    def test_rtl_and_combining_marks(self):
        self.assertTrue(reading.rtl('ara'));self.assertTrue(reading.rtl('he'));self.assertFalse(reading.rtl('ja'))
        self.assertEqual(reading.tokenize('مَرْحَبًا بالعالم','ar'),['مَرْحَبًا','بالعالم'])
    def test_book_uses_language_independent_segmentation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'book.txt';p.write_text('我喜欢读书。你呢？')
            b=app.Book(str(p),'zh');self.assertGreater(b.n,1)
            self.assertEqual(''.join(b.words),'我喜欢读书。你呢？')
    def test_catalog_search_includes_languages_without_dictionaries(self):
        self.assertGreater(len(bookcatalog.books()),70000)
        self.assertTrue(bookcatalog.search(language='zh'));self.assertTrue(bookcatalog.search(language='ja'))
        self.assertTrue(any(b[0]==11 for b in bookcatalog.search('alice carroll','en')))
    def test_download_reuses_existing_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'gutenberg-11.epub';p.write_bytes(b'existing')
            with patch('urllib.request.build_opener',side_effect=AssertionError('Must reuse cached file')):
                self.assertEqual(bookcatalog.download(11,directory=d),p)
    def test_download_rejects_unsafe_sources(self):
        for u in ['http://www.gutenberg.org/a','https://localhost/a','https://www.gutenberg.org.evil.test/a','https://user@www.gutenberg.org/a','https://www.gutenberg.org:444/a']:
            with self.assertRaises(ValueError):bookcatalog.validate(u)
