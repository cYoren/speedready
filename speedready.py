#!/usr/bin/env python3
"""Speedready: pacer + RSVP reader for epub/txt, built for language learners. GTK4 / libadwaita.

space play/pause · ←/→ ±10 words · PageUp/PageDown ±page · ↑/↓ speed · [ ] chunk size · M mode · R replay sentence
click a word = go there + dictionary popup (flow resumes when you close it) · ctrl+click = just go there
D define current word · F11 fullscreen · S settings · O open
Lookups are appended to ~/.config/speedready/vocab.tsv, importable into Anki as-is.
"""
import bisect,html,json,os,re,sys,threading,urllib.error,urllib.parse,urllib.request,zipfile,posixpath
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET
import gi;gi.require_version('Gtk','4.0');gi.require_version('Adw','1');gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Adw,Gdk,GLib,Pango,PangoCairo
try:import simplemma
except ImportError:simplemma=None

APP_ID='io.github.cyoren.speedready'
DIR=Path.home()/'.config/speedready';DIR.mkdir(parents=True,exist_ok=True)
CFG_FILE,POS_FILE,VOCAB,CACHE=DIR/'config.json',DIR/'positions.json',DIR/'vocab.tsv',DIR/'dict-cache.json'
DEFAULTS={  # change in-app (S) or edit ~/.config/speedready/config.json
 'mode':'pacer',                    # pacer = highlight sweeps through the text · rsvp = one flash at a time
 'wpm':300,'chunk':1,               # words per step
 'font_text':'Inter','text_size':19,'font_word':'JetBrainsMono Nerd Font','word_size':64,
 'bg':'#101012','fg':'#e8e6e3','dim':'#5c5c60','pivot':'#ff5252','highlight':'#2f5d45','panel':'#18181b','accent':'#ff5252',
 'sentence_pause':2.5,'comma_pause':1.5,'paragraph_pause':3.0,'long_word_len':10,'long_word_pause':1.3,
 'dim_read':True,'hide_bars_when_playing':True,'pivot_guides':True,'page_words':300,'context_words':40,
 'dict_langs':'en,de',              # wiktionaries to ask, in order. en uses the definition API and shows only the book-language section
 'web_dicts':'de=https://www.duden.de/rechtschreibung/{word}, *=https://{lang}.wiktionary.org/wiki/{word}',  # lang=url, * = fallback
 'txt_lang':'de','save_vocab':True,
}
RANGES={'wpm':(100,1000,10),'chunk':(1,8,1),'text_size':(8,60,1),'word_size':(16,160,2),'long_word_len':(4,30,1),'page_words':(50,2000,50),'context_words':(10,200,10)}
SECTION={'de':'German','en':'English','fr':'French','es':'Spanish','it':'Italian','pt':'Portuguese','nl':'Dutch','ru':'Russian','sv':'Swedish','pl':'Polish'}
POS='Noun|Proper noun|Verb|Adjective|Adverb|Pronoun|Preposition|Conjunction|Interjection|Numeral|Article|Particle|Determiner|Contraction|Phrase'
BLOCK={'p','div','br','h1','h2','h3','h4','h5','h6','li','blockquote','tr','section','article','dd','dt','pre','hr'}
END_RE=re.compile(r'[.!?…]["\'”’)»]*$');COMMA_RE=re.compile(r'[,;:]["\'”’)»]*$');UA={'User-Agent':'speedready/1 (personal desktop reader)'}

# ---------------------------------------------------------------- book
class Html(HTMLParser):
    def __init__(s):super().__init__();s.out=[];s.skip=0
    def handle_starttag(s,t,a):s.skip+=t in('style','script');t in BLOCK and s.out.append('\n')
    def handle_endtag(s,t):s.skip-=t in('style','script');t in BLOCK and s.out.append('\n')
    def handle_data(s,d):s.skip or s.out.append(d)

def read_epub(path):
    z=zipfile.ZipFile(path);names=set(z.namelist())
    opf_path=ET.fromstring(z.read('META-INF/container.xml')).find('.//{*}rootfile').get('full-path')
    opf=ET.fromstring(z.read(opf_path));d=posixpath.dirname(opf_path);d=d+'/' if d else ''
    lang=(opf.findtext('.//{*}language') or 'en')[:2].lower();out=[]
    for r in opf.iterfind('.//{*}itemref'):  # spine order
        item=opf.find(f'.//{{*}}item[@id="{r.get("idref")}"]')
        if item is None:continue
        name=posixpath.normpath(d+urllib.parse.unquote(item.get('href')))
        if name in names:p=Html();p.feed(z.read(name).decode('utf-8','replace'));out.append(''.join(p.out))
    return '\n'.join(out),lang  # ponytail: no chapter list; add a TOC from the nav doc if you want chapter jumps

class Book:
    def __init__(s,path,txt_lang):
        text,s.lang=read_epub(path) if path.lower().endswith('.epub') else (Path(path).read_text(errors='replace'),txt_lang)
        s.path=path;s.name=Path(path).name;s.words=[];s.para_start=[]
        for para in text.split('\n'):
            ws=para.split()
            if ws:s.para_start.append(len(s.words));s.words.extend(ws)
        s.n=len(s.words)
    def is_para_start(s,i):k=bisect.bisect_left(s.para_start,i);return k<len(s.para_start) and s.para_start[k]==i
    def sent_start(s,i):
        while i>0 and not s.is_para_start(i) and not END_RE.search(s.words[i-1]):i-=1
        return i
    def sent_end(s,i):
        while i<s.n-1 and not END_RE.search(s.words[i]) and not s.is_para_start(i+1):i+=1
        return i+1
    def sentence(s,i):return ' '.join(s.words[s.sent_start(i):s.sent_end(i)])

# ---------------------------------------------------------------- dictionary
class Dict:
    """Wiktionary lookups, at most 3 requests per word, cached on disk."""
    def __init__(s):s.cache=json.loads(CACHE.read_text()) if CACHE.exists() else {}
    def get(s,url):
        if url not in s.cache:
            try:s.cache[url]=json.load(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=8))
            except urllib.error.HTTPError as e:
                if e.code==404:s.cache[url]=None
                elif e.code==429:raise RuntimeError('Wiktionary rate limit hit, wait a few seconds')
                else:raise
            CACHE.write_text(json.dumps(s.cache))
        return s.cache[url]
    def en(s,word,lang):  # en.wiktionary definition API: only the book-language section
        d=s.get(f'https://en.wiktionary.org/api/rest_v1/page/definition/{urllib.parse.quote(word)}')
        out=[]
        for e in (d or {}).get(lang,[]):
            defs=[html.unescape(re.sub(r'<[^>]+>','',x['definition'])).strip() for x in e['definitions']]
            defs=[x for x in defs if x][:6]
            defs and out.append(e['partOfSpeech']+'\n'+'\n'.join(f'  {k}. {x}' for k,x in enumerate(defs,1)))
        return '\n'.join(out)
    def extract(s,wl,word,lang):  # any other wiktionary: plain-text page extract
        q=urllib.parse.urlencode({'action':'query','prop':'extracts','explaintext':1,'redirects':1,'format':'json','titles':word})
        d=s.get(f'https://{wl}.wiktionary.org/w/api.php?{q}');t=next(iter(d['query']['pages'].values())).get('extract','') if d else ''
        if t and wl!=lang and lang in SECTION:m=re.search(rf'^== {SECTION[lang]} ==\n(.*?)(?=^== |\Z)',t,re.S|re.M);t=m.group(1) if m else ''
        return re.sub(r'\n{3,}','\n\n',t.strip())[:2500]
    def lookup(s,word,lemma,lang,langs):
        """-> [(source, text)], gloss for Anki. en gets the form and the lemma, other wiktionaries just the lemma: max 3 requests."""
        out=[];glosses={}
        for wl in langs:
            for cand in dict.fromkeys([word,lemma] if wl=='en' else [lemma]):
                t=s.en(cand,lang) if wl=='en' else s.extract(wl,cand,lang)
                if not t and cand!=cand.lower():t=s.en(cand.lower(),lang) if wl=='en' else s.extract(wl,cand.lower(),lang)
                if t:out.append((f'{cand}  ·  {wl}.wiktionary',t));glosses.setdefault(cand==lemma,re.sub(r'\s+',' ',t)[:300] if wl=='en' else s.gloss(t,cand))
        return out,glosses.get(True) or glosses.get(False,'')
    @staticmethod
    def gloss(t,cand):
        m=re.search(rf'^===+ (?:{POS}) ===+\n(.*?)(?=^==|\Z)',t,re.S|re.M)
        return ' / '.join(l for l in (m.group(1) if m else t).splitlines() if l.strip() and not l.startswith(('=',cand)))[:300]

# ---------------------------------------------------------------- widgets
class WordView(Gtk.TextView):
    """Read-only text showing words[a:b] with paragraph breaks; maps clicks back to word indices."""
    def __init__(s,win,**kw):
        super().__init__(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,**kw)
        s.win=win;s.a=s.b=0;s.offs=[];s.buf=s.get_buffer();s.cur=s.buf.create_tag('cur');s.read=s.buf.create_tag('read')
        g=Gtk.GestureClick();g.connect('pressed',s.click);s.add_controller(g)
    def render(s,a,b):
        bk=s.win.book;s.a,s.b=a,b;s.offs=[];parts=[];pos=0
        for i in range(a,b):
            if i>a and bk.is_para_start(i):parts.append('\n\n');pos+=2
            s.offs.append(pos);w=bk.words[i]+' ';parts.append(w);pos+=len(w)
        s.buf.set_text(''.join(parts))
    def click(s,g,n,x,y):
        if not s.offs:return
        bx,by=s.window_to_buffer_coords(Gtk.TextWindowType.WIDGET,int(x),int(y));ok,it=s.get_iter_at_location(bx,by)
        i=s.a+max(0,bisect.bisect_right(s.offs,it.get_offset())-1)
        if g.get_current_event_state()&Gdk.ModifierType.CONTROL_MASK:s.win.goto(i,keep_playing=True)
        else:s.win.lookup(i,anchor=(s,s.word_rect(i)))
    def word_rect(s,i):
        b=s.buf;st=b.get_iter_at_offset(s.offs[i-s.a]);en=b.get_iter_at_offset(s.offs[i-s.a]+len(s.win.book.words[i]))
        l1,l2=s.get_iter_location(st),s.get_iter_location(en);x,y=s.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,l1.x,l1.y)
        r=Gdk.Rectangle();r.x,r.y,r.width,r.height=x,y,max(l2.x-l1.x,l1.width),l1.height;return r
    def highlight(s,i,n,dim):
        b=s.buf;b.remove_tag(s.cur,b.get_start_iter(),b.get_end_iter());b.remove_tag(s.read,b.get_start_iter(),b.get_end_iter())
        if not(s.a<=i<s.b):return
        e=min(i+n-1,s.b-1);st=b.get_iter_at_offset(s.offs[i-s.a]);en=b.get_iter_at_offset(s.offs[e-s.a]+len(s.win.book.words[e]))
        b.apply_tag(s.cur,st,en);dim and b.apply_tag(s.read,b.get_start_iter(),st)
        s.scroll_mark_onscreen(b.create_mark(None,en,False))

class Win(Adw.ApplicationWindow):
    def __init__(s,app,path):
        super().__init__(application=app,title='Speedready',default_width=1100,default_height=760,icon_name=APP_ID)
        s.cfg={**DEFAULTS,**(json.loads(CFG_FILE.read_text()) if CFG_FILE.exists() else {})}
        s.pos=json.loads(POS_FILE.read_text()) if POS_FILE.exists() else {}
        s.seen={l.split('\t')[1].lower() for l in VOCAB.read_text().splitlines() if '\t' in l and not l.startswith('#')} if VOCAB.exists() else set()
        s.book=None;s.i=0;s.timer=None;s.dict=Dict();s.req=0;s.resume=False;s.css=Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),s.css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        # header
        hb=Adw.HeaderBar();s.prog=Gtk.Label(css_classes=['dim-label']);hb.set_title_widget(s.prog)
        B=lambda icon,tip,cb:(lambda b:(b.connect('clicked',lambda *_:cb()),b.set_focus_on_click(False),b)[-1])(Gtk.Button(icon_name=icon,tooltip_text=tip))
        hb.pack_start(B('document-open-symbolic','Open (O)',s.open));s.playbtn=B('media-playback-start-symbolic','Play (space)',s.toggle);hb.pack_start(s.playbtn)
        s.modebtn=Gtk.Button(tooltip_text='Mode (M)');s.modebtn.set_focus_on_click(False);s.modebtn.connect('clicked',lambda *_:s.toggle_mode());hb.pack_start(s.modebtn)
        s.chunk=Gtk.SpinButton.new_with_range(1,8,1);s.chunk.set_tooltip_text('words per step ( [ ] )');s.chunk.connect('value-changed',lambda w:s.cfg.__setitem__('chunk',int(w.get_value())));hb.pack_start(s.chunk)
        s.wpm=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,100,1000,10);s.wpm.set_size_request(220,-1);s.wpm.set_draw_value(True);s.wpm.set_value_pos(Gtk.PositionType.RIGHT)
        s.wpm.set_tooltip_text('words per minute (↑ ↓)');s.wpm.set_can_focus(False);s.wpm.connect('value-changed',lambda w:s.cfg.__setitem__('wpm',int(w.get_value())));hb.pack_start(s.wpm)
        hb.pack_end(B('emblem-system-symbolic','Settings (S)',s.settings));hb.pack_end(B('view-fullscreen-symbolic','Fullscreen (F11)',s.toggle_full))
        # body
        s.pacer=WordView(s,left_margin=48,right_margin=48,top_margin=32,bottom_margin=32,pixels_below_lines=6,css_classes=['pacer'])
        sw=Gtk.ScrolledWindow(child=Adw.Clamp(child=s.pacer,maximum_size=900,tightening_threshold=700),vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        s.cv=Gtk.DrawingArea(vexpand=True);s.cv.set_draw_func(s.draw_word)
        g=Gtk.GestureClick();g.connect('pressed',lambda *_:s.lookup(s.i));s.cv.add_controller(g)
        s.ctx=WordView(s,left_margin=24,right_margin=24,top_margin=12,bottom_margin=12,css_classes=['ctx']);s.ctx.set_size_request(-1,130)
        rsvp=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);rsvp.append(s.cv);rsvp.append(s.ctx)
        s.stack=Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE);s.stack.add_named(sw,'pacer');s.stack.add_named(rsvp,'rsvp')
        s.pbar=Gtk.ProgressBar(css_classes=['osd'])
        s.tv=Adw.ToolbarView(content=s.stack,top_bar_style=Adw.ToolbarStyle.FLAT);s.tv.add_top_bar(hb);s.tv.add_bottom_bar(s.pbar);s.set_content(s.tv)
        # dictionary popup
        s.pop=Gtk.Popover(autohide=True);s.pop.set_size_request(460,-1);s.pop.set_parent(s.cv);s.pop.connect('closed',lambda *_:s.resume and s.play())
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,margin_top=6,margin_bottom=6,margin_start=6,margin_end=6);s.pop.set_child(box)
        row=Gtk.Box(spacing=8);s.pop_title=Gtk.Label(xalign=0,hexpand=True,css_classes=['title-3'],ellipsize=Pango.EllipsizeMode.END);row.append(s.pop_title)
        s.webbtn=Gtk.Button(label='↗');s.webbtn.connect('clicked',lambda *_:s.webdict());row.append(s.webbtn);box.append(row)
        s.defn=Gtk.TextView(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,left_margin=8,right_margin=8,top_margin=6,bottom_margin=6,css_classes=['defn'])
        db=s.defn.get_buffer();s.tag_src=db.create_tag('src');s.tag_b=db.create_tag('b',weight=Pango.Weight.BOLD)
        box.append(Gtk.ScrolledWindow(child=s.defn,min_content_height=200,max_content_height=440,propagate_natural_height=True,hscrollbar_policy=Gtk.PolicyType.NEVER))
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
        popover>contents{{background-color:{c['panel']};color:{c['fg']};}}
        progressbar trough{{min-height:3px;background-color:{c['panel']};}}progressbar progress{{min-height:3px;background-color:{c['accent']};}}
        headerbar{{background-color:transparent;}}''')
        for t in(s.pacer,s.ctx):t.cur.set_property('background',c['highlight']);t.read.set_property('foreground',c['dim'])
        s.tag_src.set_property('foreground',c['dim']);s.tag_b.set_property('foreground',c['accent'])
        s.wpm.set_value(c['wpm']);s.chunk.set_value(c['chunk']);s.set_mode(c['mode'])
    def set_mode(s,m):
        s.cfg['mode']=m;s.modebtn.set_label('Pacer' if m=='pacer' else 'RSVP');s.stack.set_visible_child_name(m);s.pacer.a=s.pacer.b=0;s.show()
    def toggle_mode(s):s.set_mode('rsvp' if s.cfg['mode']=='pacer' else 'pacer')
    def toggle_full(s):s.unfullscreen() if s.is_fullscreen() else s.fullscreen()
    def key(s,ctl,kv,code,state):
        if isinstance(s.get_focus(),Gtk.Text):return False
        K=Gdk;acts={K.KEY_space:s.toggle,K.KEY_Left:lambda:s.jump(-10),K.KEY_Right:lambda:s.jump(10),K.KEY_Up:lambda:s.wpm.set_value(s.cfg['wpm']+20),K.KEY_Down:lambda:s.wpm.set_value(s.cfg['wpm']-20),
              K.KEY_Page_Down:lambda:s.jump(s.cfg['page_words']),K.KEY_Page_Up:lambda:s.jump(-s.cfg['page_words']),
              K.KEY_bracketleft:lambda:s.chunk.set_value(s.cfg['chunk']-1),K.KEY_bracketright:lambda:s.chunk.set_value(s.cfg['chunk']+1),K.KEY_m:s.toggle_mode,K.KEY_r:s.replay,
              K.KEY_d:lambda:s.lookup(s.i),K.KEY_o:s.open,K.KEY_s:s.settings,K.KEY_F11:s.toggle_full,K.KEY_Escape:s.unfullscreen}
        if kv in acts:acts[kv]();return True
        return False

    # ---- book
    def open(s):
        f=Gtk.FileFilter();f.set_name('Books');f.add_pattern('*.epub');f.add_pattern('*.txt')
        d=Gtk.FileDialog(default_filter=f);d.open(s,None,lambda d,r:s.load(d.open_finish(r).get_path()))
    def load(s,p):
        s.stop()
        try:s.book=Book(p,s.cfg['txt_lang'])
        except Exception as e:s.book=None;return s.toast(f'Could not open: {e}')
        if not s.book.n:s.book=None;return s.toast('No text found in that file')
        s.i=min(s.pos.get(s.book.name,0),s.book.n-1);s.pos['_last']=p;s.set_title(f'Speedready · {s.book.name}');s.pacer.a=s.pacer.b=0;s.show();s.save()
    def toast(s,msg):s.prog.set_text(msg)
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
        s.prog.set_text(f'{i+1:,} / {b.n:,}   ·   {(b.n-i)//c["wpm"]} min left');s.pbar.set_fraction(i/b.n)
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
        if s.i+n<b.n and b.is_para_start(s.i+n):d=max(d,60000/c['wpm']*c['paragraph_pause'])
        s.timer=GLib.timeout_add(int(d),s.step)
    def step(s):
        s.i+=s.chunk_len(s.i)
        if s.i<s.book.n:s.tick()
        else:s.i=s.book.n-1;s.stop()
        return False
    def play(s):
        s.resume=False
        if not s.book or s.timer:return
        s.playbtn.set_icon_name('media-playback-pause-symbolic')
        if s.cfg['hide_bars_when_playing']:s.tv.set_reveal_top_bars(False)
        s.tick()
    def stop(s):
        if s.timer:GLib.source_remove(s.timer);s.timer=None
        s.playbtn.set_icon_name('media-playback-start-symbolic');s.tv.set_reveal_top_bars(True);s.save()
    def toggle(s):s.stop() if s.timer else s.play()
    def goto(s,i,keep_playing=False):
        if not s.book or i is None:return
        was=bool(s.timer);s.stop();s.i=max(0,min(s.book.n-1,i));s.show();keep_playing and was and s.play()
    def jump(s,d):s.book and s.goto(s.i+d,keep_playing=True)
    def replay(s):s.book and s.goto(s.book.sent_start(s.i),keep_playing=True)

    # ---- dictionary
    def lookup(s,i,anchor=None):
        if not s.book or i is None:return
        was=bool(s.timer);s.goto(i);s.resume=was  # flow resumes from here when the popup closes
        b=s.book;w=re.sub(r'^\W+|\W+$','',b.words[i])
        if not w:return
        try:lemma=simplemma.lemmatize(w,lang=b.lang) if simplemma else w
        except Exception:lemma=w
        s.word,s.lemma=w,lemma;s.req+=1;s.show_def(w,lemma,[('','…')])
        parent,rect=anchor or (s.cv,None)
        if s.pop.get_parent() is not parent:s.pop.unparent();s.pop.set_parent(parent)
        if rect is None:rect=Gdk.Rectangle();rect.x,rect.y,rect.width,rect.height=parent.get_width()//2,parent.get_height()//2,1,1
        s.pop.set_pointing_to(rect);s.pop.popup()
        threading.Thread(target=s.fetch,args=(s.req,w,lemma,b.lang,b.sentence(i),b.name),daemon=True).start()
    def fetch(s,req,w,lemma,lang,sent,bookname):
        try:out,gloss=s.dict.lookup(w,lemma,lang,[x.strip() for x in s.cfg['dict_langs'].split(',') if x.strip()])
        except Exception as e:out,gloss=[('lookup failed',str(e))],''
        if req!=s.req:return
        GLib.idle_add(s.show_def,w,lemma,out or [('not found','No entry. Try the ↗ button.')])
        out and gloss and s.add_vocab(w,lemma,gloss,sent,bookname)
    def show_def(s,w,lemma,entries):
        s.pop_title.set_text(w+(f'  →  {lemma}' if lemma!=w else ''));b=s.defn.get_buffer();b.set_text('')
        for src,t in entries:src and b.insert_with_tags(b.get_end_iter(),src+'\n',s.tag_src);b.insert(b.get_end_iter(),t+'\n\n')
        return False
    def web_url(s):
        table=dict(x.strip().split('=',1) for x in s.cfg['web_dicts'].split(',') if '=' in x);lang=s.book.lang
        url=table.get(lang) or table.get('*') or 'https://{lang}.wiktionary.org/wiki/{word}';w=s.lemma or s.word
        if 'duden' in url:w=w.translate(str.maketrans({'ä':'ae','ö':'oe','ü':'ue','Ä':'Ae','Ö':'Oe','Ü':'Ue','ß':'sz'}))
        return url.format(word=urllib.parse.quote(w),lang=lang)
    def webdict(s):
        url=s.web_url();s.pop.popdown()
        try:
            gi.require_version('WebKit','6.0');from gi.repository import WebKit
        except (ValueError,ImportError):return Gtk.UriLauncher(uri=url).launch(s,None,None)
        wv=WebKit.WebView();wv.load_uri(url);d=Adw.Dialog(title=s.word,content_width=980,content_height=760)
        t=Adw.ToolbarView(content=wv);t.add_top_bar(Adw.HeaderBar());d.set_child(t);d.connect('closed',lambda *_:s.resume and s.play());d.present(s)
    def add_vocab(s,w,lemma,gloss,sent,bookname):
        if not s.cfg['save_vocab'] or lemma.lower() in s.seen:return
        if not VOCAB.exists():VOCAB.write_text('#separator:tab\n#html:false\n#tags:speedready\n#columns:Word\tLemma\tMeaning\tSentence\tBook\n')
        s.seen.add(lemma.lower())
        with VOCAB.open('a') as f:f.write('\t'.join(x.replace('\t',' ').replace('\n',' ') for x in(w,lemma,gloss,sent,bookname))+'\n')

    # ---- settings
    def settings(s):
        d=Adw.PreferencesDialog(title='Settings');page=Adw.PreferencesPage();d.add(page)
        groups={'Reading':('mode','wpm','chunk','dim_read','hide_bars_when_playing','pivot_guides','page_words','context_words'),
                'Pauses':('sentence_pause','comma_pause','paragraph_pause','long_word_len','long_word_pause'),
                'Look':('font_text','text_size','font_word','word_size','bg','fg','dim','pivot','highlight','panel','accent'),
                'Dictionary':('dict_langs','web_dicts','txt_lang','save_vocab')}
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
                    lo,hi,st=RANGES.get(k,(0.5,10,0.1));r=Adw.SpinRow.new_with_range(lo,hi,st);r.set_title(title);r.set_digits(0 if isinstance(v,int) else 1);r.set_value(v)
                    r.connect('notify::value',lambda r,_,k=k,t=type(v):upd(k,t(r.get_value())))
                elif v.startswith('#'):
                    r=Adw.ActionRow(title=title);cb=Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False),valign=Gtk.Align.CENTER);rgba=Gdk.RGBA();rgba.parse(v);cb.set_rgba(rgba)
                    cb.connect('notify::rgba',lambda cb,_,k=k:upd(k,'#%02x%02x%02x'%tuple(int(x*255) for x in(cb.get_rgba().red,cb.get_rgba().green,cb.get_rgba().blue))));r.add_suffix(cb)
                else:
                    r=Adw.EntryRow(title=title,text=v);r.connect('apply',lambda r,k=k:upd(k,r.get_text()));r.set_show_apply_button(True)
                g.add(r)
        g=Adw.PreferencesGroup(description=f'vocab file: {VOCAB}\nlemmatizer: {"on" if simplemma else "off (pip install simplemma)"}');page.add(g)
        d.present(s)

class App(Adw.Application):
    def __init__(s):super().__init__(application_id=APP_ID);s.connect('activate',lambda app:Win(app,sys.argv[1] if len(sys.argv)>1 else None).present())

if __name__=='__main__':App().run(None)
