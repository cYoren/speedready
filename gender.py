"""German noun genders for a list of words: 'm', 'f', 'n' or None per word.

Pure Python, no GTK, one data file (genders-de.json.gz, built by tools/build_genders.py), so a browser
extension can port it line for line. What makes it hard, and what each part below answers:
web/gender.js is the same logic for the web reader (and a future browser extension); change both together.
  * which words are nouns      -> German capitalizes nouns; the dictionary says which capitalized words are
                                  nouns. At a sentence start everything is capitalized, so a word that is also
                                  a lowercase word ('Essen', 'Gestern', 'Aus') is left alone there.
  * one spelling, two genders  -> der See / die See, der / das Teil: the article or determiner in front decides
                                  (skipping adjectives: 'die stille See'). No article: the dictionary's first.
  * plurals                    -> 'die Mühlen' is colored as its singular, die Mühle (f); plural-only nouns
                                  ('Eltern', 'Leute') have no gender and stay uncolored.
  * compounds not in the data  -> the gender is the last part's: 'Hahnenfeder' -> 'Feder' (f).
"""
import gzip,json,re

# which readings each determiner allows: m f n singular, L = any plural. Case is ignored; it only narrows.
DET={'der':'mfL','die':'fL','das':'n','den':'mL','dem':'mn','des':'mn',
     'im':'mn','am':'mn','vom':'mn','zum':'mn','beim':'mn','zur':'f','ins':'n','ans':'n','aufs':'n','durchs':'n','fürs':'n','ums':'n'}
EIN={'':'mn','e':'fL','en':'mL','em':'mn','er':'fL','es':'mn'}     # ein, kein, mein … (ein itself has no plural: fixed below)
DER={'er':'mfL','e':'fL','es':'mn','en':'mL','em':'mn'}              # dieser, jener, jeder …
for stem in('ein','kein','mein','dein','sein','ihr','unser','euer','eur'):
    for end,r in EIN.items():DET.setdefault(stem+end,r)
for end,r in(('e','f'),('er','f')):DET['ein'+end]=r               # 'eine', 'einer': singular only
for stem in('dies','jen','jed','welch','manch','solch'):
    for end,r in DER.items():DET[stem+end]=r
END=re.compile(r'[.!?…:]["\'”’“‘)»«]*$')
OPEN=re.compile(r'^[»«„“"‚‘\'(\[—–-]')
WORD=re.compile(r'^[\W_]+|[\W_]+$')   # '_Werk_' (Gutenberg italics) is 'Werk'
PRONOUN={'Er','Sie','Es','Ihr','Ihre','Ihnen','Ihm','Ihn','Ich','Du','Dich','Dir','Wir','Man'}   # also nouns in Wiktionary ('das Ich'), almost never in a book
ADJ=re.compile(r'(e|en|er|es|em)$')

def load(path):
    with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)

def readings(data,w):
    """-> (readings, maybe_not_a_noun) for a capitalized word, trying the compound's last part if needed."""
    if w in data:r=data[w];return r.rstrip('*'),r.endswith('*')
    for k in range(3,len(w)-2):   # longest head first; a 3-letter head ('Tür', 'Tag') needs a 4+ letter prefix
        head=w[k].upper()+w[k+1:]
        if head in data and (len(head)>=4 or k>=4):return data[head].rstrip('*'),True
    return '',False

def pick(r,allowed):
    """First reading the determiner allows, else the dictionary's first. -> 'm'/'f'/'n'/None."""
    ok=[x for x in r if x in allowed or x in 'MFNP' and 'L' in allowed] if allowed else []
    x=(ok or r or ' ')[0]
    return None if x in ' P' else x.lower()

def determiner(words,i):
    """What the article in front of words[i] allows, skipping up to three adjectives/numbers. None if there is none."""
    for j in range(i-1,max(-1,i-5),-1):
        w=words[j]
        if END.search(w) or w.endswith((',',';')):return None
        t=WORD.sub('',w).lower()
        if t in DET:return DET[t]
        if not(t[:1].islower() or t.isdigit()):return None   # another noun or a name: not our phrase
    return None

def genders(words,data,para_start=()):
    starts=set(para_start);out=[]
    for i,raw in enumerate(words):
        w=WORD.sub('',raw)
        if '-' in w:w=w.rsplit('-',1)[1]   # 'S-Bahn', 'Hagecius-Gymnasium': the last part decides
        if len(w)<2 or not w[0].isupper() or w.isupper():out.append(None);continue
        r,maybe=readings(data,w)
        first=i==0 or i in starts or END.search(words[i-1]) or OPEN.match(raw)
        nxt=WORD.sub('',words[i+1]) if i+1<len(words) and not END.search(raw) else ''
        if not r or w in PRONOUN or maybe and (first or ADJ.search(w) and nxt[:1].isupper() and readings(data,nxt)[0]):out.append(None);continue   # 'am Schwarzen Wasser': an adjective
        out.append(pick(r,determiner(words,i)))
    return out

if __name__=='__main__':   # self-check: python gender.py
    from pathlib import Path
    d=load(Path(__file__).parent/'web'/'genders-de.json.gz')
    t='Er ging an die stille See . Der See war kalt . Das Teil lag im Haus , die Mühlen standen still . Essen gab es nicht . Die Hahnenfeder und die Eltern .'.split()
    got={w:g for w,g in zip(t,genders(t,d)) if g}
    assert got=={'See':'m','Teil':'n','Haus':'n','Mühlen':'f','Hahnenfeder':'f'} or print(got),got
    g=genders(t,d);assert g[5]=='f' and g[8]=='m',g   # die stille See = sea (f); Der See = lake (m)
    assert g[t.index('Eltern')] is None and g[t.index('Essen')] is None
    print('ok')
