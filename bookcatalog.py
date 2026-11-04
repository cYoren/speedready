"""Local search of Gutenberg's official catalog and bounded, user-selected downloads."""
import gzip,json,urllib.parse,urllib.request,unicodedata
from pathlib import Path
from reading import asset,lang_code,LANGUAGES
LANGUAGE_NAMES=LANGUAGES['names']
_books=None
def books():
    global _books
    if _books is None:_books=json.loads(gzip.decompress(asset('catalog.json.gz').read_bytes()))['books']
    return _books
def normalize(text):return ''.join(c for c in unicodedata.normalize('NFKD',text).casefold() if not unicodedata.combining(c))
def search(query='',language=''):
    terms=normalize(query).split()
    return [b for b in books() if (not language or language in b[3]) and all(t in normalize(b[1]+' '+b[2]) for t in terms)]
LIMIT=30*1024*1024
HOSTS={'www.gutenberg.org','gutenberg.org','standardebooks.org','www.openbookpublishers.com','openbookpublishers.com','books.openbookpublishers.com','cdn.openbookpublishers.com'}
def validate(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname not in HOSTS or u.port or u.username or u.password:raise ValueError('Use a direct link from Gutenberg, Standard Ebooks or Open Book Publishers')
    return url
class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return super().redirect_request(req,fp,code,msg,headers,validate(newurl))
def download(book_id=None,url=None,directory=None):
    import hashlib
    directory=Path(directory or Path.home()/'.local/share/speedready/books');directory.mkdir(parents=True,exist_ok=True)
    if book_id is not None:
        if not str(book_id).isdigit() or not 0<int(book_id)<10000000:raise ValueError('Invalid Gutenberg book number')
        url=f'https://www.gutenberg.org/ebooks/{int(book_id)}.epub.noimages';name='gutenberg-'+str(int(book_id))
    else:name='book-'+hashlib.sha256(validate(url).encode()).hexdigest()[:20]
    for ext in ('epub','txt'):
        path=directory/(name+'.'+ext)
        if path.exists():return path
    with urllib.request.build_opener(Redirects).open(validate(url),timeout=45) as r:
        if int(r.headers.get('content-length') or 0)>LIMIT:raise ValueError('Book exceeds 30 MB')
        data=r.read(LIMIT+1)
        if len(data)>LIMIT:raise ValueError('Book exceeds 30 MB')
        ext='epub' if data.startswith(b'PK') else 'txt' if (r.headers.get('content-type') or '').startswith('text/plain') else None
        if not ext:raise ValueError('Use a direct EPUB or text download link')
    path=directory/(name+'.'+ext);tmp=path.with_suffix('.part');tmp.write_bytes(data);tmp.replace(path)
    return path
