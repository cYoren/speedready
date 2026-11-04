"""Tiny, synthetic books exercising valid EPUBs missed by regex-based parsers."""
import zipfile
from pathlib import Path

def make_epub(path,lang='fil'):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','application/epub+zip')
        z.writestr('META-INF/container.xml',"""<?xml version='1.0'?><container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'><rootfiles><rootfile full-path='OPS/book.opf' media-type='application/oebps-package+xml'/></rootfiles></container>""")
        z.writestr('OPS/book.opf',f"""<?xml version='1.0'?><o:package xmlns:o='http://www.idpf.org/2007/opf' xmlns:d='http://purl.org/dc/elements/1.1/' version='3.0'><o:metadata><d:title>A &amp; B</d:title><d:language>{lang}</d:language><d:creator>Writer</d:creator></o:metadata><o:manifest><o:item id='text' href='text.xhtml' media-type='application/xhtml+xml'/><o:item id='nav' href='nav.xhtml' properties='nav' media-type='application/xhtml+xml'/></o:manifest><o:spine><o:itemref idref='text'/></o:spine></o:package>""")
        z.writestr('OPS/nav.xhtml',"""<html xmlns='http://www.w3.org/1999/xhtml' xmlns:epub='http://www.idpf.org/2007/ops'><body><nav epub:type='landmarks'><a href='text.xhtml'>Front</a></nav><nav epub:type='toc'><a href='text.xhtml#chapter'>Our chapter</a></nav></body></html>""")
        z.writestr('OPS/text.xhtml',"""<html xmlns='http://www.w3.org/1999/xhtml'><head><title>Do not read</title></head><body><h1 id='chapter'>Our chapter</h1><div>Before <p>Nested <b>prose</b> stays.</p> After</div><section>Direct section text.</section><p>Footnote<sup>1</sup> gone.</p><script>Never execute</script></body></html>""")
if __name__=='__main__':
    root=Path(__file__).resolve().parent.parent/'dist/audit-fixtures';root.mkdir(parents=True,exist_ok=True);make_epub(root/'namespaced.epub');print('Created synthetic EPUB fixture')
