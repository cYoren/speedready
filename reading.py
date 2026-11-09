"""Unicode reading helpers; existing spaced-script word indices stay stable."""
import ctypes,ctypes.util,json,re,unicodedata
from pathlib import Path

def asset(name):
    here=Path(__file__).resolve().parent
    return next((p for p in (here/'web'/name,here/name) if p.is_file()),here/'web'/name)
LANGUAGES=json.loads(asset('languages.json').read_text())
def lang_code(tag):
    t=(tag or '').strip().lower().replace('_','-').split('-')[0]
    return LANGUAGES['aliases'].get(t,t) if re.fullmatch('[a-z]{2,3}',t) else ''
def rtl(lang):return lang_code(lang) in {'ar','he','fa','ur','ps','sd','ug','yi','dv','syr','arc','ckb'}
_NEEDS_BREAK=re.compile('[\u0e00-\u0fff\u1000-\u109f\u1780-\u17ff\u3040-\u30ff\u3400-\u9fff\U00020000-\U000323af]')
DROP='\x00'   # parser marker for text that must not be read (same value as speedready.DROP)
_icu=None

def _breaker():
    global _icu
    if _icu is None:
        try:
            path=ctypes.util.find_library('icuuc');lib=ctypes.CDLL(path);suffix=re.search(r'\.so\.(\d+)',path)
            def fn(name):return getattr(lib,name+'_'+suffix[1] if suffix else name)
            op,first,nxt,close=[fn('ubrk_'+name) for name in ('open','first','next','close')]
            op.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_void_p,ctypes.c_int32,ctypes.POINTER(ctypes.c_int32)];op.restype=ctypes.c_void_p
            for f in (first,nxt):f.argtypes=[ctypes.c_void_p];f.restype=ctypes.c_int32
            close.argtypes=[ctypes.c_void_p];_icu=(lib,op,first,nxt,close)
        except (OSError,AttributeError,TypeError):_icu=False
    return _icu

def tokenize(text,lang=''):
    # speedready.py prefixes parser-known non-text (page titles, footnote markers) with DROP. A marked span
    # that has to be segmented must not lose its mark on the second word: '\x00日本語の本' is not text either.
    if DROP in text:
        words=[]
        for k,piece in enumerate(text.split(DROP)):
            part=_segment(piece,lang)
            words+=part if k==0 else [DROP+w for w in part]
        return words
    return _segment(text,lang)

def _segment(text,lang=''):
    if not _NEEDS_BREAK.search(text):return text.split()
    parts=[];icu=_breaker()
    if icu:
        _,op,first,nxt,close=icu;raw=text.encode('utf-16-le');buf=ctypes.create_string_buffer(raw);err=ctypes.c_int32(0)
        iterator=op(1,(lang_code(lang) or 'und').encode(),buf,len(raw)//2,ctypes.byref(err))
        if iterator and err.value<=0:
            try:
                a=first(iterator)
                while (b:=nxt(iterator))!=-1:parts.append(raw[a*2:b*2].decode('utf-16-le'));a=b
            finally:close(iterator)
        elif iterator:close(iterator)
    if not parts:
        # Keep every codepoint when ICU is absent, with combining marks attached.
        for c in text:
            if unicodedata.combining(c) and parts:parts[-1]+=c
            else:parts.append(c)
    words=[]
    for part in parts:
        if not part.strip():continue
        if words and all(unicodedata.category(c)[0] in 'PS' for c in part):words[-1]+=part
        else:words.append(part)
    return words


def decode_text(data):
    if data.startswith((b'\xff\xfe',b'\xfe\xff')):return data.decode('utf-16',errors='replace')
    return data.decode('utf-8-sig',errors='replace')
