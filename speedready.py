#!/usr/bin/env python3
"""Speedready: pacer + RSVP reader for epub/txt, built for language learners. GTK4 / libadwaita.

space play/pause · ←/→ ±10 words · PageUp/PageDown ±page · ↑/↓ speed (shift: coarse) · [ ] chunk size · M mode · R replay sentence
click a word = continue from there · double-click = dictionary popup (flow resumes when you close it) · right-click = mark unknown
D define current word · P speak from here to the end of the sentence (again = stop) · A read-along (speech drives the pace) · C chapters · F11 fullscreen · S settings · O open
Lookups are appended to ~/.config/speedready/vocab.tsv, importable into Anki as-is. Unknown words live in unknown.txt (one lemma per line).
"""
import bisect,html,json,os,re,shutil,subprocess,sys,threading,time,urllib.error,urllib.parse,urllib.request,wave,zipfile,posixpath
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET
import gi;gi.require_version('Gtk','4.0');gi.require_version('Adw','1');gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Adw,Gdk,GLib,Pango,PangoCairo
try:import simplemma
except ImportError:simplemma=None

APP_ID='io.github.cyoren.speedready'
DIR=Path.home()/'.config/speedready';DIR.mkdir(parents=True,exist_ok=True)
CFG_FILE,POS_FILE,VOCAB,CACHE,UNKNOWN=DIR/'config.json',DIR/'positions.json',DIR/'vocab.tsv',DIR/'dict-cache.json',DIR/'unknown.txt'
VOICES=Path.home()/'.cache/speedready/voices'
DEFAULTS={  # change in-app (S) or edit ~/.config/speedready/config.json
 'mode':'pacer',                    # pacer = highlight sweeps through the text · rsvp = one flash at a time
 'wpm':300,'chunk':1,               # words per step
 'font_text':'Inter','text_size':19,'font_word':'JetBrainsMono Nerd Font','word_size':64,
 'bg':'#101012','fg':'#e8e6e3','dim':'#5c5c60','pivot':'#ff5252','highlight':'#2f5d45','panel':'#18181b','accent':'#ff5252','unknown':'#e0a030',
 'sentence_pause':2.5,'comma_pause':1.5,'paragraph_pause':3.0,'long_word_len':10,'long_word_pause':1.3,'unknown_pause':1.8,
 'follow_margin':0.3,'dim_read':True,'hide_bars_when_playing':True,'pivot_guides':True,'page_words':300,'context_words':40,
 'dict_langs':'en,duden',           # sources in order: a wiktionary language code or 'duden' (German only). Wikimedia rate-limits bursts, so keep it short
 'web_dicts':'de=https://www.duden.de/rechtschreibung/{word}, *=https://{lang}.wiktionary.org/wiki/{word}',  # lang=url, * = fallback
 'tts_voices':'de=de_DE-thorsten-medium, en=en_US-lessac-medium, fr=fr_FR-siwis-medium, es=es_ES-davefx-medium, it=it_IT-riccardo-x_low, pt=pt_PT-tugão-medium',  # piper voices, downloaded on first use
 'tts_speed':1.0,'txt_lang':'de','save_vocab':True,
}
RANGES={'wpm':(50,1500,5),'chunk':(1,8,1),'text_size':(8,60,1),'word_size':(16,160,2),'long_word_len':(4,30,1),'page_words':(50,2000,50),'context_words':(10,200,10),'follow_margin':(0.0,0.49,0.05),'tts_speed':(0.5,2.0,0.05)}
SECTION={'de':'German','en':'English','fr':'French','es':'Spanish','it':'Italian','pt':'Portuguese','nl':'Dutch','ru':'Russian','sv':'Swedish','pl':'Polish'}
POS='Noun|Proper noun|Verb|Adjective|Adverb|Pronoun|Preposition|Conjunction|Interjection|Numeral|Article|Particle|Determiner|Contraction|Phrase'
BLOCK={'p','div','br','h1','h2','h3','h4','h5','h6','li','blockquote','tr','section','article','dd','dt','pre','hr'}
END_RE=re.compile(r'[.!?…]["\'”’)»]*$');COMMA_RE=re.compile(r'[,;:]["\'”’)»]*$');UA={'User-Agent':'Speedready/1.0 (https://github.com/cYoren/speedready) python-urllib'}
strip=lambda w:re.sub(r'^\W+|\W+$','',w)
def lemma_of(w,lang):
    w=strip(w)
    if not w:return ''
    try:return simplemma.lemmatize(w,lang=lang).lower() if simplemma else w.lower()
    except Exception:return w.lower()
def table(spec):return dict(x.strip().split('=',1) for x in spec.split(',') if '=' in x)

# ---------------------------------------------------------------- book
class Html(HTMLParser):
    """Body text with newlines at block boundaries; records the word count at wanted anchors (for the chapter list)."""
    def __init__(s,anchors=()):super().__init__();s.out=[];s.skip=0;s.want=set(anchors);s.found={}
    def handle_starttag(s,t,a):
        s.skip+=t in('style','script');t in BLOCK and s.out.append('\n')
        i=dict(a).get('id')
        if i in s.want:s.found[i]=len(''.join(s.out).split())
    def handle_endtag(s,t):s.skip-=t in('style','script');t in BLOCK and s.out.append('\n')
    def handle_data(s,d):s.skip or s.out.append(d)

class NavHtml(HTMLParser):
    """Links of the first <nav> in an EPUB3 nav document -> [(title, href)]."""
    def __init__(s):super().__init__();s.links=[];s.nav=0;s.href=None;s.text=[]
    def handle_starttag(s,t,a):
        a=dict(a)
        if t=='nav' and not s.links:s.nav+=1
        if t=='a' and s.nav and a.get('href'):s.href=a['href'];s.text=[]
    def handle_endtag(s,t):
        if t=='a' and s.href:s.links.append((' '.join(''.join(s.text).split()),s.href));s.href=None
        if t=='nav':s.nav=max(0,s.nav-1);s.nav or setattr(s,'done',True)
    def handle_data(s,d):s.href and s.text.append(d)

def read_epub(path):
    """-> [(text, [(title, word_offset_in_text)])] per spine file, lang"""
    z=zipfile.ZipFile(path);names=set(z.namelist())
    opf_path=ET.fromstring(z.read('META-INF/container.xml')).find('.//{*}rootfile').get('full-path')
    opf=ET.fromstring(z.read(opf_path));d=posixpath.dirname(opf_path);d=d+'/' if d else ''
    lang=(opf.findtext('.//{*}language') or 'en')[:2].lower();items={i.get('id'):i for i in opf.iterfind('.//{*}item')}
    def resolve(base,href):
        f,_,anchor=urllib.parse.unquote(href).partition('#');return posixpath.normpath(posixpath.join(posixpath.dirname(base),f)) if f else base,anchor
    toc=[]  # (title, file, anchor)
    nav=next((i for i in items.values() if 'nav' in (i.get('properties') or '').split()),None)
    if nav is not None:
        np=posixpath.normpath(d+urllib.parse.unquote(nav.get('href')));p=NavHtml();p.feed(z.read(np).decode('utf-8','replace'))
        toc=[(t,*resolve(np,h)) for t,h in p.links]
    elif (ncx:=items.get(opf.find('.//{*}spine').get('toc') or '')) is not None:
        np=posixpath.normpath(d+urllib.parse.unquote(ncx.get('href')));x=ET.fromstring(z.read(np))
        toc=[(' '.join((n.findtext('.//{*}text') or '').split()),*resolve(np,n.find('.//{*}content').get('src'))) for n in x.iterfind('.//{*}navPoint')]
    out=[]
    for r in opf.iterfind('.//{*}itemref'):  # spine order
        item=items.get(r.get('idref'))
        if item is None:continue
        name=posixpath.normpath(d+urllib.parse.unquote(item.get('href')))
        if name not in names:continue
        mine=[(t,a) for t,f,a in toc if f==name];p=Html(a for t,a in mine if a);p.feed(z.read(name).decode('utf-8','replace'))
        out.append((''.join(p.out),[(t,p.found.get(a) if a else 0) for t,a in mine]))  # None = anchor missing (broken epub), Book searches the title text
    return out,lang

class Book:
    def __init__(s,path,txt_lang):
        s.path=path;s.name=Path(path).name;s.words=[];s.para_start=[];s.chapters=[]
        if path.lower().endswith('.epub'):
            parts,s.lang=read_epub(path)
            for text,toc in parts:
                base=len(s.words);s.add(text);s.chapters+=[(t,base+off if off is not None else None) for t,off in toc]
            s.resolve_missing()
        else:s.lang=txt_lang;s.add(Path(path).read_text(errors='replace'))
        s.n=len(s.words);s.chapters=[(t,i) for t,i in s.chapters if t and i<s.n];s.chapter_idx=[i for t,i in s.chapters]
        s.lemmas=[lemma_of(w,s.lang) for w in s.words]
    def resolve_missing(s):
        """Broken epubs point at anchors that don't exist: find each title as a short heading paragraph instead, skipping the book's own table of contents."""
        if all(i is not None for t,i in s.chapters):return
        norm=lambda ws:' '.join(strip(x).lower() for x in ws)
        heads={}
        for k,p in enumerate(s.para_start):
            q=s.para_start[k+1] if k+1<len(s.para_start) else len(s.words)
            if q-p<=12:heads.setdefault(norm(s.words[p:q]),[]).append((p,q))
        titles=[norm(t.split()) for t,_ in s.chapters];res=[]
        for k,(t,i) in enumerate(s.chapters):
            if i is None:
                nxt=titles[k+1] if k+1<len(titles) else None
                i=next((p for p,q in heads.get(titles[k],[]) if not(nxt and nxt in norm(s.words[q:q+len(nxt.split())+12]))),None)  # a heading with the next title right behind it is the TOC page
            res.append((t,i))
        res=[(t,i) for t,i in res if i is not None];out=[]
        for k,(t,i) in enumerate(res):  # keep the in-order ones, drop outliers (e.g. a title only found in a back-of-book index)
            if (not out or i>out[-1][1]) and (k+1==len(res) or i<res[k+1][1]):out.append((t,i))
        s.chapters=out
    def add(s,text):
        for para in text.split('\n'):
            ws=para.split()
            if ws:s.para_start.append(len(s.words));s.words.extend(ws)
    def is_para_start(s,i):k=bisect.bisect_left(s.para_start,i);return k<len(s.para_start) and s.para_start[k]==i
    def sent_start(s,i):
        while i>0 and not s.is_para_start(i) and not END_RE.search(s.words[i-1]):i-=1
        return i
    def sent_end(s,i):
        while i<s.n-1 and not END_RE.search(s.words[i]) and not s.is_para_start(i+1):i+=1
        return i+1
    def sentence(s,i):return ' '.join(s.words[s.sent_start(i):s.sent_end(i)])
    def chapter(s,i):k=bisect.bisect_right(s.chapter_idx,i)-1;return s.chapters[k][0] if k>=0 else ''

# ---------------------------------------------------------------- dictionary + speech
class Dict:
    """Wiktionary lookups, one request per wiktionary, cached on disk."""
    def __init__(s):s.cache=json.loads(CACHE.read_text()) if CACHE.exists() else {};s.last=0
    def get(s,url,retry=True,raw=False):
        if url in s.cache:return s.cache[url]
        time.sleep(max(0,s.last+0.6-time.time()));s.last=time.time()  # ponytail: crude throttle, Wikimedia 429s on bursts
        try:r=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=8);s.cache[url]=r.read().decode('utf-8','replace') if raw else json.load(r)
        except urllib.error.HTTPError as e:
            if e.code==404:s.cache[url]=None
            elif e.code==429 and retry:time.sleep(float(e.headers.get('Retry-After') or 5));return s.get(url,retry=False)
            elif e.code==429:raise RuntimeError('Wiktionary rate limit hit, wait a minute')
            else:raise
        CACHE.write_text(json.dumps(s.cache));return s.cache[url]
    def en(s,word,lang):  # en.wiktionary definition API: only the book-language section
        d=s.get(f'https://en.wiktionary.org/api/rest_v1/page/definition/{urllib.parse.quote(word)}');out=[]
        for e in (d or {}).get(lang,[]):
            defs=[x for x in (html.unescape(re.sub(r'<[^>]+>','',x['definition'])).strip() for x in e['definitions']) if x][:6]
            defs and out.append(e['partOfSpeech']+'\n'+'\n'.join(f'  {k}. {x}' for k,x in enumerate(defs,1)))
        return '\n'.join(out)
    def extract(s,wl,word,lang):  # any other wiktionary: plain-text page extract
        q=urllib.parse.urlencode({'action':'query','prop':'extracts','explaintext':1,'redirects':1,'format':'json','titles':word})
        d=s.get(f'https://{wl}.wiktionary.org/w/api.php?{q}');t=next(iter(d['query']['pages'].values())).get('extract','') if d else ''
        if t and wl!=lang and lang in SECTION:m=re.search(rf'^== {SECTION[lang]} ==\n(.*?)(?=^== |\Z)',t,re.S|re.M);t=m.group(1) if m else ''
        return re.sub(r'\n{3,}','\n\n',t.strip())[:2500]
    def duden(s,word):
        w=word.translate(str.maketrans({'ä':'ae','ö':'oe','ü':'ue','Ä':'Ae','Ö':'Oe','Ü':'Ue','ß':'sz'}))
        h=s.get(f'https://www.duden.de/rechtschreibung/{urllib.parse.quote(w)}',raw=True) or ''
        txt=lambda x:html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',x))).strip()
        kind=re.search(r'Wortart:.*?<dd[^>]*>(.*?)</dd>',h,re.S);means=[txt(m) for m in re.findall(r'<div class="enumeration__text">(.*?)</div>',h,re.S)]
        if not means:m=re.search(r'<div[^>]*id="bedeutung".*?<p>(.*?)</p>',h,re.S);means=[txt(m.group(1))] if m else []
        return (txt(kind.group(1))+'\n' if kind else '')+'\n'.join(f'  {k}. {x}' for k,x in enumerate(means[:8],1)) if means else ''
    def lookup(s,word,lemma,lang,langs):
        """-> [(source, text)], gloss for Anki. Lemma first, the inflected form only if the lemma has no entry."""
        out=[];gloss=''
        for wl in langs:
            if wl=='duden' and lang!='de':continue
            for cand in dict.fromkeys([lemma,word]):
                t=s.duden(cand) if wl=='duden' else s.en(cand,lang) if wl=='en' else s.extract(wl,cand,lang)
                if t:out.append((f'{cand}  ·  {"Duden" if wl=="duden" else wl+".wiktionary"}',t));gloss=gloss or (s.gloss(t,cand) if wl not in('en','duden') else re.sub(r'\s+',' ',t)[:300]);break
        return out,gloss
    @staticmethod
    def gloss(t,cand):
        m=re.search(rf'^===+ (?:{POS}) ===+\n(.*?)(?=^==|\Z)',t,re.S|re.M)
        return ' / '.join(l for l in (m.group(1) if m else t).splitlines() if l.strip() and not l.startswith(('=',cand)))[:300]

class TTS:
    """Piper text to speech; voices are fetched from HuggingFace on first use."""
    def __init__(s):
        s.voices={};s.rate={};s.proc=None;s.lock=threading.Lock();VOICES.mkdir(parents=True,exist_ok=True)
        for f in VOICES.glob('ra-*.wav'):f.unlink()
        s.player=next((p for p in(['pw-play'],['paplay'],['aplay','-q'],['ffplay','-nodisp','-autoexit','-loglevel','quiet']) if shutil.which(p[0])),None)
    def voice(s,name,status):
        if name in s.voices:return s.voices[name]
        from piper import PiperVoice
        loc,who,q=name.split('-',2);sub=f'{loc.split("_")[0]}/{loc}/{who}/{q}'
        for ext in('.onnx','.onnx.json'):
            f=VOICES/(name+ext)
            if not f.exists():status(f'downloading voice {name}…');urllib.request.urlretrieve(f'https://huggingface.co/rhasspy/piper-voices/resolve/main/{sub}/{name}{ext}',f)
        s.voices[name]=PiperVoice.load(str(VOICES/(name+'.onnx')));return s.voices[name]
    def synth(s,text,name,status,scale=1.0):
        """-> (wav path, seconds). Cached per text+speed."""
        from piper import SynthesisConfig
        with s.lock:
            v=s.voice(name,status);wav=VOICES/f'ra-{abs(hash((text,name,round(scale,2)))):x}.wav'
            if not wav.exists():
                with wave.open(str(wav),'wb') as f:v.synthesize_wav(text,f,SynthesisConfig(length_scale=scale))
        with wave.open(str(wav)) as f:return wav,f.getnframes()/f.getframerate()
    def natural_rate(s,name,status):  # words per second of this voice at speed 1
        if name not in s.rate:
            txt='Die Mühle im Koselbruch mahlte Tag für Tag, werktags und sonntags, vom frühen Morgen an bis zum Einbruch der Dunkelheit.' if name.startswith('de') else 'The quick brown fox jumps over the lazy dog while the sun sets slowly behind the distant hills.'
            s.rate[name]=len(txt.split())/s.synth(txt,name,status)[1]
        return s.rate[name]
    def play(s,wav):
        s.stop_audio()
        if not s.player:raise RuntimeError('no audio player found (pw-play/paplay/aplay/ffplay)')
        s.proc=subprocess.Popen(s.player+[str(wav)])
    def stop_audio(s):s.proc and s.proc.poll() is None and s.proc.kill()
    def say(s,text,name,status):
        def go():
            try:wav,_=s.synth(text,name,status);s.play(wav);status('')
            except Exception as e:status(f'speech failed: {e}')
        threading.Thread(target=go,daemon=True).start()

# ---------------------------------------------------------------- widgets
class WordView(Gtk.TextView):
    """Read-only text showing words[a:b] with paragraph breaks; maps clicks back to word indices."""
    def __init__(s,win,**kw):
        super().__init__(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,**kw)
        s.win=win;s.a=s.b=0;s.offs=[];s.buf=s.get_buffer()
        s.cur=s.buf.create_tag('cur');s.read=s.buf.create_tag('read');s.unk=s.buf.create_tag('unk',underline=Pango.Underline.SINGLE)
        g=Gtk.GestureClick();g.connect('pressed',s.click);s.add_controller(g)
        g=Gtk.GestureClick(button=3);g.connect('pressed',lambda g,n,x,y:s.win.toggle_unknown(s.word_at(x,y)));s.add_controller(g)
    def render(s,a,b):
        bk=s.win.book;s.a,s.b=a,b;s.offs=[];parts=[];pos=0
        for i in range(a,b):
            if i>a and bk.is_para_start(i):parts.append('\n\n');pos+=2
            s.offs.append(pos);w=bk.words[i]+' ';parts.append(w);pos+=len(w)
        s.buf.set_text(''.join(parts));s.mark_unknown()
    def span(s,i):
        b=s.buf;st=b.get_iter_at_offset(s.offs[i-s.a]);return st,b.get_iter_at_offset(s.offs[i-s.a]+len(s.win.book.words[i]))
    def mark_unknown(s,only=None):
        bk,unk=s.win.book,s.win.unknown
        for i in range(s.a,s.b):
            l=bk.lemmas[i]
            if only is not None and l!=only:continue
            if l:(s.buf.apply_tag if l in unk else s.buf.remove_tag)(s.unk,*s.span(i))
    def word_at(s,x,y):
        if not s.offs:return None
        bx,by=s.window_to_buffer_coords(Gtk.TextWindowType.WIDGET,int(x),int(y));ok,it=s.get_iter_at_location(bx,by)
        return s.a+max(0,bisect.bisect_right(s.offs,it.get_offset())-1)
    def click(s,g,n,x,y):
        i=s.word_at(x,y)
        if i is None:return
        if n==2:s.win.lookup(i)
        else:s.win.goto(i,keep_playing=True)
    def highlight(s,i,n,dim):
        b=s.buf;b.remove_tag(s.cur,b.get_start_iter(),b.get_end_iter());b.remove_tag(s.read,b.get_start_iter(),b.get_end_iter())
        if not(s.a<=i<s.b):return
        e=min(i+n-1,s.b-1);st=s.span(i)[0];en=s.span(e)[1]
        b.apply_tag(s.cur,st,en);dim and b.apply_tag(s.read,b.get_start_iter(),st)
        s.scroll_to_mark(b.create_mark(None,en,False),s.win.cfg['follow_margin'],False,0,0)  # scrolls only when the word leaves the middle band

class Win(Adw.ApplicationWindow):
    def __init__(s,app,path):
        super().__init__(application=app,title='Speedready',default_width=1100,default_height=760,icon_name=APP_ID)
        s.cfg={**DEFAULTS,**(json.loads(CFG_FILE.read_text()) if CFG_FILE.exists() else {})}
        s.pos=json.loads(POS_FILE.read_text()) if POS_FILE.exists() else {}
        s.seen={l.split('\t')[1].lower() for l in VOCAB.read_text().splitlines() if '\t' in l and not l.startswith('#')} if VOCAB.exists() else set()
        s.unknown=set(UNKNOWN.read_text().split()) if UNKNOWN.exists() else set()
        s.book=None;s.i=0;s.timer=None;s.playing=False;s.ra=False;s.token=0;s.dict=Dict();s.tts=TTS();s.req=0;s.resume=False;s.css=Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),s.css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        # header
        hb=Adw.HeaderBar();s.prog=Adw.WindowTitle();hb.set_title_widget(s.prog)
        B=lambda icon,tip,cb:(lambda b:(b.connect('clicked',lambda *_:cb()),b.set_focus_on_click(False),b)[-1])(Gtk.Button(icon_name=icon,tooltip_text=tip))
        hb.pack_start(B('document-open-symbolic','Open (O)',s.open));s.playbtn=B('media-playback-start-symbolic','Play (space)',s.toggle);hb.pack_start(s.playbtn)
        s.modebtn=Gtk.Button(tooltip_text='Mode (M)');s.modebtn.set_focus_on_click(False);s.modebtn.connect('clicked',lambda *_:s.toggle_mode());hb.pack_start(s.modebtn)
        s.chunk=Gtk.SpinButton.new_with_range(1,8,1);s.chunk.set_tooltip_text('words per step ( [ ] )');s.chunk.connect('value-changed',lambda w:s.cfg.__setitem__('chunk',int(w.get_value())));hb.pack_start(s.chunk)
        s.wpm=Gtk.SpinButton.new_with_range(50,1500,5);s.wpm.set_increments(5,25);s.wpm.set_tooltip_text('words per minute (↑ ↓ = 5, shift = 25)');s.wpm.set_width_chars(5)
        s.wpm.connect('value-changed',lambda w:s.cfg.__setitem__('wpm',int(w.get_value())));hb.pack_start(s.wpm);hb.pack_start(Gtk.Label(label='wpm',css_classes=['dim-label']))
        s.chapters=Gtk.ListBox(css_classes=['navigation-sidebar','chapters'],selection_mode=Gtk.SelectionMode.SINGLE);s.chapters.connect('row-activated',lambda lb,row:(s.split.set_show_sidebar(False),s.goto(row.idx,keep_playing=True)))
        s.chapbtn=B('view-list-symbolic','Chapters (C)',lambda:s.split.set_show_sidebar(not s.split.get_show_sidebar()))
        hb.pack_end(B('emblem-system-symbolic','Settings (S)',s.settings));hb.pack_end(B('view-fullscreen-symbolic','Fullscreen (F11)',s.toggle_full));hb.pack_end(s.chapbtn)
        s.rabtn=Gtk.ToggleButton(icon_name='audio-speakers-symbolic',tooltip_text='Read along: speech sets the pace (A)');s.rabtn.set_focus_on_click(False);s.rabtn.connect('toggled',lambda b:s.set_ra(b.get_active()));hb.pack_end(s.rabtn)
        hb.pack_end(B('audio-volume-high-symbolic','Speak sentence (P)',s.speak))
        # body
        s.pacer=WordView(s,left_margin=48,right_margin=48,top_margin=32,bottom_margin=32,pixels_below_lines=6,css_classes=['pacer'])
        sw=Adw.Clamp(child=Gtk.ScrolledWindow(child=s.pacer,hscrollbar_policy=Gtk.PolicyType.NEVER),maximum_size=900,tightening_threshold=700,vexpand=True)
        s.cv=Gtk.DrawingArea(vexpand=True);s.cv.set_draw_func(s.draw_word)
        g=Gtk.GestureClick();g.connect('pressed',lambda *_:s.lookup(s.i));s.cv.add_controller(g)
        s.ctx=WordView(s,left_margin=24,right_margin=24,top_margin=12,bottom_margin=12,css_classes=['ctx']);s.ctx.set_size_request(-1,130)
        rsvp=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);rsvp.append(s.cv);rsvp.append(s.ctx)
        s.stack=Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE);s.stack.add_named(sw,'pacer');s.stack.add_named(rsvp,'rsvp')
        s.pbar=Gtk.ProgressBar(css_classes=['osd'])
        side=Gtk.ScrolledWindow(child=s.chapters,hscrollbar_policy=Gtk.PolicyType.NEVER);side.set_size_request(320,-1)
        s.split=Adw.OverlaySplitView(content=s.stack,sidebar=side,collapsed=True,show_sidebar=False,max_sidebar_width=460,sidebar_width_fraction=0.35)
        s.tv=Adw.ToolbarView(content=s.split,top_bar_style=Adw.ToolbarStyle.FLAT);s.tv.add_top_bar(hb);s.tv.add_bottom_bar(s.pbar);s.set_content(s.tv)
        # dictionary popup
        s.pop=Adw.Dialog(content_width=560,content_height=440,follows_content_size=False);s.pop.connect('closed',lambda *_:s.resume and s.play())
        s.pop_title=Adw.WindowTitle();hb2=Adw.HeaderBar(title_widget=s.pop_title)
        for icon,tip,cb in(('web-browser-symbolic','open in web dictionary',s.webdict),('audio-volume-high-symbolic','pronounce',lambda:s.say(s.word))):
            b=Gtk.Button(icon_name=icon,tooltip_text=tip);b.connect('clicked',lambda *_,cb=cb:cb());hb2.pack_end(b)
        s.unkbtn=Gtk.ToggleButton(label='unknown');s.unkbtn.connect('toggled',lambda b:s.set_unknown(s.lemma,b.get_active()));hb2.pack_start(s.unkbtn)
        s.defn=Gtk.TextView(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,left_margin=20,right_margin=20,top_margin=12,bottom_margin=12,css_classes=['defn'])
        db=s.defn.get_buffer();s.tag_src=db.create_tag('src')
        pv=Adw.ToolbarView(content=Gtk.ScrolledWindow(child=s.defn,hscrollbar_policy=Gtk.PolicyType.NEVER));pv.add_top_bar(hb2);s.pop.set_child(pv)
        k=Gtk.EventControllerKey();k.connect('key-pressed',s.key);s.add_controller(k)
        s.connect('close-request',lambda *_:s.save())
        s.apply()
        path=path or s.pos.get('_last');path and Path(path).exists() and s.load(path)
        if os.environ.get('SPEEDREADY_SHOT'):GLib.timeout_add(1500,s.shot)  # dev: render the window to a png
    def shot(s):
        sn=Gtk.Snapshot();Gtk.WidgetPaintable.new(s).snapshot(sn,s.get_width(),s.get_height());node=sn.to_node()
        node and s.get_native().get_renderer().render_texture(node,None).save_to_png(os.environ['SPEEDREADY_SHOT']);return node is None

    # ---- theme / layout
    def apply(s):
        c=s.cfg
        s.css.load_from_string(f'''
        window.background{{background-color:{c['bg']};color:{c['fg']};}}
        textview,textview text{{background-color:transparent;color:{c['fg']};}}
        .pacer{{font-family:"{c['font_text']}";font-size:{c['text_size']}px;}}
        .ctx,.defn{{font-family:"{c['font_text']}";font-size:{c['text_size']-3}px;}}
        .ctx text{{background-color:{c['panel']};}}
        progressbar trough{{min-height:3px;background-color:{c['panel']};}}progressbar progress{{min-height:3px;background-color:{c['accent']};}}
        .chapters label{{font-family:"{c['font_text']}";font-size:{c['text_size']-2}px;}}
        headerbar{{background-color:transparent;}}''')
        for t in(s.pacer,s.ctx):t.cur.set_property('background',c['highlight']);t.read.set_property('foreground',c['dim']);t.unk.set_property('underline-rgba',Gdk.RGBA(*[int(c['unknown'][i:i+2],16)/255 for i in(1,3,5)],1))
        s.tag_src.set_property('foreground',c['dim'])
        s.wpm.set_value(c['wpm']);s.chunk.set_value(c['chunk']);s.set_mode(c['mode'])
    def set_mode(s,m):
        s.cfg['mode']=m;s.modebtn.set_label('Pacer' if m=='pacer' else 'RSVP');s.stack.set_visible_child_name(m);s.pacer.a=s.pacer.b=0;s.show()
    def toggle_mode(s):s.set_mode('rsvp' if s.cfg['mode']=='pacer' else 'pacer')
    def toggle_full(s):s.unfullscreen() if s.is_fullscreen() else s.fullscreen()
    def key(s,ctl,kv,code,state):
        if isinstance(s.get_focus(),Gtk.Text):return False
        K=Gdk;big=25 if state&Gdk.ModifierType.SHIFT_MASK else 5
        acts={K.KEY_space:s.toggle,K.KEY_Left:lambda:s.jump(-10),K.KEY_Right:lambda:s.jump(10),K.KEY_Up:lambda:s.wpm.set_value(s.cfg['wpm']+big),K.KEY_Down:lambda:s.wpm.set_value(s.cfg['wpm']-big),
              K.KEY_Page_Down:lambda:s.jump(s.cfg['page_words']),K.KEY_Page_Up:lambda:s.jump(-s.cfg['page_words']),
              K.KEY_bracketleft:lambda:s.chunk.set_value(s.cfg['chunk']-1),K.KEY_bracketright:lambda:s.chunk.set_value(s.cfg['chunk']+1),K.KEY_m:s.toggle_mode,K.KEY_r:s.replay,
              K.KEY_d:lambda:s.lookup(s.i),K.KEY_p:s.speak,K.KEY_a:lambda:s.rabtn.set_active(not s.ra),K.KEY_c:lambda:s.split.set_show_sidebar(not s.split.get_show_sidebar()),K.KEY_o:s.open,K.KEY_s:s.settings,K.KEY_F11:s.toggle_full,K.KEY_Escape:lambda:(s.tts.stop_audio(),s.unfullscreen())}
        if kv in acts:acts[kv]();return True
        return False

    # ---- book
    def open(s):
        f=Gtk.FileFilter();f.set_name('Books');f.add_pattern('*.epub');f.add_pattern('*.txt')
        d=Gtk.FileDialog(default_filter=f);d.open(s,None,lambda d,r:s.load(d.open_finish(r).get_path()))
    def load(s,p):
        s.stop()
        try:s.book=Book(p,s.cfg['txt_lang'])
        except Exception as e:s.book=None;return s.status(f'Could not open: {e}')
        if not s.book.n:s.book=None;return s.status('No text found in that file')
        s.i=min(s.pos.get(s.book.name,0),s.book.n-1);s.pos['_last']=p;s.set_title(f'Speedready · {s.book.name}');s.pacer.a=s.pacer.b=0
        s.chapters.remove_all()
        for t,i in s.book.chapters:row=Gtk.ListBoxRow(child=Gtk.Label(label=t,xalign=0,wrap=True,margin_start=10,margin_end=10,margin_top=6,margin_bottom=6));row.idx=i;s.chapters.append(row)
        s.chapbtn.set_sensitive(bool(s.book.chapters));s.show();s.save()
    def status(s,msg):GLib.idle_add(s.prog.set_subtitle,msg)
    def save(s):
        if s.book:s.pos[s.book.name]=s.i
        POS_FILE.write_text(json.dumps(s.pos));return False
    def chunk_len(s,i):  # never merge across a sentence end or paragraph break
        b=s.book
        for k in range(i,min(i+s.cfg['chunk'],b.n)):
            if k>i and b.is_para_start(k):return k-i
            if END_RE.search(b.words[k]):return k-i+1
        return min(s.cfg['chunk'],b.n-i)

    # ---- display
    def show(s):
        if not s.book:return
        b,c,i=s.book,s.cfg,s.i;n=s.chunk_len(i);cw=c['context_words']
        if c['mode']=='rsvp':s.cv.queue_draw();s.ctx.render(max(0,i-cw),min(b.n,i+cw));s.ctx.highlight(i,n,c['dim_read'])
        else:s.pacer.b or s.pacer.render(0,b.n);s.pacer.highlight(i,n,c['dim_read'])
        s.prog.set_title(b.chapter(i) or b.name);k=bisect.bisect_right(b.chapter_idx,i)-1;k>=0 and s.chapters.select_row(s.chapters.get_row_at_index(k));s.prog.set_subtitle(f'{i+1:,} / {b.n:,}   ·   {(b.n-i)//c["wpm"]} min left');s.pbar.set_fraction(i/b.n)
    def draw_word(s,area,cr,W,H):
        if not s.book:return
        c=s.cfg;chunk=s.book.words[s.i:s.i+s.chunk_len(s.i)];w=' '.join(chunk);mid=len(chunk)//2
        p=sum(len(x)+1 for x in chunk[:mid])+min((len(chunk[mid])-1)//3,4)
        fd=Pango.FontDescription(f'{c["font_word"]} {c["word_size"]}px');lay=lambda t:(l:=area.create_pango_layout(t),l.set_font_description(fd),l)[-1]
        L,P,R=lay(w[:p]),lay(w[p]),lay(w[p+1:]);pw,ph=P.get_pixel_size();cx,cy=W/2,H/2
        rgb=lambda h:cr.set_source_rgb(*[int(h[i:i+2],16)/255 for i in(1,3,5)])
        if c['pivot_guides']:
            rgb(c['dim']);cr.set_line_width(2)
            for y in(cy-ph*.75,cy+ph*.75):cr.move_to(cx,y-ph*.12);cr.line_to(cx,y+ph*.12)
            cr.stroke()
        for lay_,x,col in((L,cx-pw/2-L.get_pixel_size()[0],c['fg']),(P,cx-pw/2,c['pivot']),(R,cx+pw/2,c['fg'])):
            rgb(col);cr.move_to(x,cy-ph/2);PangoCairo.show_layout(cr,lay_)

    # ---- playback
    def tick(s):
        s.show();b,c=s.book,s.cfg;n=s.chunk_len(s.i);last=b.words[s.i+n-1];d=60000/c['wpm']*n
        if END_RE.search(last):d*=c['sentence_pause']
        elif COMMA_RE.search(last):d*=c['comma_pause']
        if any(len(w)>=c['long_word_len'] for w in b.words[s.i:s.i+n]):d*=c['long_word_pause']
        if any(l in s.unknown for l in b.lemmas[s.i:s.i+n]):d*=c['unknown_pause']
        if s.i+n<b.n and b.is_para_start(s.i+n):d=max(d,60000/c['wpm']*c['paragraph_pause'])
        s.timer=GLib.timeout_add(int(d),s.step)
    def step(s):
        s.timer=None;s.i+=s.chunk_len(s.i)
        if s.i<s.book.n:s.tick()
        else:s.i=s.book.n-1;s.stop()
        return False
    def play(s):
        s.resume=False
        if not s.book or s.playing:return
        s.playing=True;s.token+=1;s.playbtn.set_icon_name('media-playback-pause-symbolic')
        if s.cfg['hide_bars_when_playing']:s.tv.set_reveal_top_bars(False)
        s.ra_sentence() if s.ra else s.tick()
    def stop(s):
        if s.timer:GLib.source_remove(s.timer);s.timer=None
        s.playing=False;s.token+=1;s.tts.stop_audio();s.playbtn.set_icon_name('media-playback-start-symbolic');s.tv.set_reveal_top_bars(True);s.save()
    # read-along: piper reads each sentence, the highlight follows the audio, WPM sets the speech speed
    def set_ra(s,on):
        s.ra=on
        if s.playing:s.stop();s.play()
    def ra_scale(s,name):return max(0.5,min(2.0,s.tts.natural_rate(name,s.status)*60/s.cfg['wpm']))*s.cfg['tts_speed']
    def ra_sentence(s):
        b=s.book;a=s.i;e=b.sent_end(a);name=table(s.cfg['tts_voices']).get(b.lang)  # starts exactly where you are, to the end of the sentence
        if not name:s.status(f'no voice for "{b.lang}", falling back to the pacer');s.rabtn.set_active(False);return
        tok=s.token;text=' '.join(b.words[a:e])
        def go():
            try:wav,secs=s.tts.synth(text,name,s.status,s.ra_scale(name))
            except Exception as ex:return s.status(f'speech failed: {ex}')
            GLib.idle_add(s.ra_play,tok,a,e,wav,secs)
            if e<b.n:  # prefetch the next sentence while this one plays
                try:s.tts.synth(' '.join(b.words[e:b.sent_end(e)]),name,s.status,s.ra_scale(name))
                except Exception:pass
        threading.Thread(target=go,daemon=True).start()
    def ra_play(s,tok,a,e,wav,secs):
        if tok!=s.token or not s.playing:return False
        try:s.tts.play(wav)
        except Exception as ex:s.status(str(ex));s.stop();return False
        ws=s.book.words[a:e];tot=sum(len(w)+1 for w in ws);s.ra_d=[secs*1000*(len(w)+1)/tot for w in ws];s.ra_a,s.ra_e=a,e;s.i=a;s.ra_tick();return False
    def ra_tick(s):
        s.show();s.timer=GLib.timeout_add(int(s.ra_d[s.i-s.ra_a]),s.ra_step)
    def ra_step(s):
        s.timer=None;s.i+=1
        if s.i<s.ra_e:s.ra_tick()
        elif s.i<s.book.n:s.ra_sentence()
        else:s.i=s.book.n-1;s.stop()
        return False
    def toggle(s):s.stop() if s.playing else s.play()
    def goto(s,i,keep_playing=False):
        if not s.book or i is None:return
        was=s.playing;s.stop();s.i=max(0,min(s.book.n-1,i));s.show();keep_playing and was and s.play()
    def jump(s,d):s.book and s.goto(s.i+d,keep_playing=True)
    def replay(s):s.book and s.goto(s.book.sent_start(s.i),keep_playing=True)

    # ---- unknown words
    def toggle_unknown(s,i):
        if s.book and i is not None and s.book.lemmas[i]:s.set_unknown(s.book.lemmas[i],s.book.lemmas[i] not in s.unknown)
    def set_unknown(s,lemma,flag):
        if not lemma or (lemma in s.unknown)==flag:return
        (s.unknown.add if flag else s.unknown.discard)(lemma);UNKNOWN.write_text('\n'.join(sorted(s.unknown))+'\n')
        for t in(s.pacer,s.ctx):t.b and t.mark_unknown(only=lemma)
        s.status(f'{len(s.unknown)} unknown words')

    # ---- dictionary / speech
    def lookup(s,i):
        if not s.book or i is None:return
        was=s.playing;s.goto(i);s.resume=was  # flow resumes from here when the popup closes
        b=s.book;w=strip(b.words[i]);lemma=lemma_of(w,b.lang)
        if not w:return
        s.word,s.lemma=w,lemma;s.req+=1;s.show_def(w,lemma,[('','…')]);s.unkbtn.set_active(lemma in s.unknown);s.pop.present(s)
        threading.Thread(target=s.fetch,args=(s.req,w,lemma,b.lang,b.sentence(i),b.name),daemon=True).start()
    def fetch(s,req,w,lemma,lang,sent,bookname):
        try:out,gloss=s.dict.lookup(w,lemma,lang,[x.strip() for x in s.cfg['dict_langs'].split(',') if x.strip()])
        except Exception as e:out,gloss=[('lookup failed',str(e))],''
        if req!=s.req:return
        GLib.idle_add(s.show_def,w,lemma,out or [('not found','No entry. Try the web dictionary button.')])
        out and gloss and s.add_vocab(w,lemma,gloss,sent,bookname)
    def show_def(s,w,lemma,entries):
        s.pop_title.set_title(w);s.pop_title.set_subtitle(f'→ {lemma}' if lemma!=w.lower() else '');b=s.defn.get_buffer();b.set_text('')
        for src,t in entries:src and b.insert_with_tags(b.get_end_iter(),src+'\n',s.tag_src);b.insert(b.get_end_iter(),t+'\n\n')
        return False
    def web_url(s):
        t=table(s.cfg['web_dicts']);lang=s.book.lang;url=t.get(lang) or t.get('*') or 'https://{lang}.wiktionary.org/wiki/{word}';w=s.lemma or s.word
        if 'duden' in url:w=w.translate(str.maketrans({'ä':'ae','ö':'oe','ü':'ue','Ä':'Ae','Ö':'Oe','Ü':'Ue','ß':'sz'}))
        return url.format(word=urllib.parse.quote(w),lang=lang)
    def webdict(s):Gtk.UriLauncher(uri=s.web_url()).launch(s,None,None)
    def say(s,text):
        if not s.book or not text:return
        name=table(s.cfg['tts_voices']).get(s.book.lang)
        if not name:return s.status(f'no voice configured for "{s.book.lang}" (settings → tts voices)')
        s.tts.say(text,name,s.status)
    def speaking(s):p=s.tts.proc;return bool(p) and p.poll() is None
    def speak(s):  # P: read from the current word to the end of the sentence; press again to stop
        if s.speaking():return s.tts.stop_audio()
        s.book and s.say(' '.join(s.book.words[s.i:s.book.sent_end(s.i)]))
    def add_vocab(s,w,lemma,gloss,sent,bookname):
        if not s.cfg['save_vocab'] or lemma in s.seen:return
        if not VOCAB.exists():VOCAB.write_text('#separator:tab\n#html:false\n#tags:speedready\n#columns:Word\tLemma\tMeaning\tSentence\tBook\n')
        s.seen.add(lemma)
        with VOCAB.open('a') as f:f.write('\t'.join(x.replace('\t',' ').replace('\n',' ') for x in(w,lemma,gloss,sent,bookname))+'\n')

    # ---- settings
    def settings(s):
        d=Adw.PreferencesDialog(title='Settings');page=Adw.PreferencesPage();d.add(page)
        groups={'Reading':('mode','wpm','chunk','follow_margin','dim_read','hide_bars_when_playing','pivot_guides','page_words','context_words'),
                'Pauses':('sentence_pause','comma_pause','paragraph_pause','long_word_len','long_word_pause','unknown_pause'),
                'Look':('font_text','text_size','font_word','word_size','bg','fg','dim','pivot','highlight','panel','accent','unknown'),
                'Dictionary & speech':('dict_langs','web_dicts','tts_voices','txt_lang','save_vocab')}
        def upd(k,v):s.cfg[k]=v;CFG_FILE.write_text(json.dumps(s.cfg,indent=1));s.apply()
        for gname,keys in groups.items():
            g=Adw.PreferencesGroup(title=gname);page.add(g)
            for k in keys:
                v=s.cfg[k];title=k.replace('_',' ')
                if k=='mode':
                    r=Adw.ComboRow(title=title,model=Gtk.StringList.new(['pacer','rsvp']));r.set_selected(0 if v=='pacer' else 1)
                    r.connect('notify::selected',lambda r,_:upd('mode',['pacer','rsvp'][r.get_selected()]))
                elif isinstance(v,bool):
                    r=Adw.SwitchRow(title=title,active=v);r.connect('notify::active',lambda r,_,k=k:upd(k,r.get_active()))
                elif isinstance(v,(int,float)):
                    lo,hi,st=RANGES.get(k,(0.5,10,0.1));r=Adw.SpinRow.new_with_range(lo,hi,st);r.set_title(title);r.set_digits(0 if isinstance(v,int) else 2 if st<0.1 else 1);r.set_value(v)
                    r.connect('notify::value',lambda r,_,k=k,t=type(v):upd(k,t(r.get_value())))
                elif v.startswith('#'):
                    r=Adw.ActionRow(title=title);cb=Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False),valign=Gtk.Align.CENTER);rgba=Gdk.RGBA();rgba.parse(v);cb.set_rgba(rgba)
                    cb.connect('notify::rgba',lambda cb,_,k=k:upd(k,'#%02x%02x%02x'%tuple(int(x*255) for x in(cb.get_rgba().red,cb.get_rgba().green,cb.get_rgba().blue))));r.add_suffix(cb)
                else:
                    r=Adw.EntryRow(title=title,text=v);r.connect('apply',lambda r,k=k:upd(k,r.get_text()));r.set_show_apply_button(True)
                g.add(r)
        g=Adw.PreferencesGroup(description=f'vocab: {VOCAB}\nunknown words: {UNKNOWN} ({len(s.unknown)})\nlemmatizer: {"on" if simplemma else "off (pip install simplemma)"}');page.add(g)
        d.present(s)

class App(Adw.Application):
    def __init__(s):super().__init__(application_id=APP_ID);s.connect('activate',lambda app:Win(app,sys.argv[1] if len(sys.argv)>1 else None).present())

if __name__=='__main__':App().run(None)
