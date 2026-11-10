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
    def test_parser_exclusions_survive_segmentation(self):
        # A page title or a footnote marker in Chinese or Japanese: every piece of the marked span has to stay
        # marked, or Book.clean() keeps the title as reading text (Codex review, PR #13).
        marked=app.DROP+'日本語の本'
        self.assertEqual(reading.tokenize(marked,'ja'),[app.DROP+'日本語',app.DROP+'の',app.DROP+'本'])
        Html=app.Html('',lang='ja');Html.feed('<head><title>日本語の本</title></head><body><p>本文です。</p></body>')
        clean=object.__new__(app.Book);clean.words=reading.tokenize(''.join(Html.out),'ja');clean.para_start=[0];clean.old2new=[];clean.chapters=[]
        clean.clean('')
        self.assertNotIn('日本語の本',''.join(clean.words))
    def test_footnote_marker_does_not_swallow_the_rest_of_the_paragraph(self):
        # Codex review, PR #14: the mark covers the footnote token only, not the prose after it.
        words=reading.tokenize('First word'+app.DROP+'1 then the rest of this sentence.')
        self.assertEqual([w for w in words if not w.startswith(app.DROP)],['First','word','then','the','rest','of','this','sentence.'])
        self.assertEqual([w for w in words if w.startswith(app.DROP)],[app.DROP+'1'])
        ja=reading.tokenize('本'+app.DROP+'日本語 そして本文です。','ja')
        marked=[w for w in ja if w.startswith(app.DROP)]
        self.assertEqual(''.join(marked),app.DROP*len(marked)+'日本語');self.assertEqual(''.join(w for w in ja if not w.startswith(app.DROP)),'本そして本文です。')
        h=app.Html();h.feed('<p>First word<sup>1</sup> then the rest of this sentence.</p>')
        b=object.__new__(app.Book);b.words=reading.tokenize(''.join(h.out)) ;b.para_start=[0];b.old2new=[];b.chapters=[]
        b.clean('')
        self.assertEqual(' '.join(b.words),'First word then the rest of this sentence.')
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
    def test_desktop_unknown_words_are_scoped_to_language(self):
        from types import SimpleNamespace
        win=SimpleNamespace(book=SimpleNamespace(lang='de'),unknown={'de:gift'})
        self.assertTrue(app.Win.is_unknown(win,'gift'))
        win.book.lang='en';self.assertFalse(app.Win.is_unknown(win,'gift'))
    def test_failed_desktop_import_keeps_the_current_book(self):
        from types import SimpleNamespace
        book=object();messages=[]
        win=SimpleNamespace(book=book,cfg={'txt_lang':'en'},stop=lambda:None,status=messages.append,t=lambda key,**values:key)
        with patch.object(app,'Book',side_effect=ValueError('bad archive')):app.Win.load(win,'bad.epub')
        self.assertIs(win.book,book);self.assertEqual(messages,['could_not_open'])
    def test_native_epub_prefers_toc_and_preserves_nested_prose(self):
        from epub_fixtures import make_epub
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'book.epub';make_epub(path)
            b=app.Book(str(path),'')
            self.assertEqual(b.lang,'fil');self.assertEqual(b.title,'A & B')
            self.assertEqual(b.chapters[0][0],'Our chapter')
            for word in ('Before','Nested','After','Direct','Footnote'):
                self.assertIn(word,' '.join(b.words))

    def test_unicode_text_files_keep_their_encoding(self):
        for encoding in ('utf-8-sig','utf-16'):
            with self.subTest(encoding=encoding):self.assertEqual(reading.decode_text('日本語'.encode(encoding)),'日本語')
    def test_native_text_download_obeys_source_charset(self):
        from email.message import Message
        from unittest.mock import MagicMock
        headers=Message();headers['Content-Type']='text/plain; charset=iso-8859-1';headers['Content-Length']='4'
        response=MagicMock();response.headers=headers;response.read.return_value=b'caf\xe9'
        opener=MagicMock();opener.open.return_value.__enter__.return_value=response
        with tempfile.TemporaryDirectory() as d,patch('urllib.request.build_opener',return_value=opener):
            path=bookcatalog.download(url='https://www.gutenberg.org/example.txt',directory=d)
            self.assertEqual(path.read_text(encoding='utf-8'),'café')
