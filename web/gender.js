// Noun genders for a list of words: 'm', 'f', 'n', 'c' (common: Dutch de, Swedish en) or null per word.
// German, below, has its own rules; tag() covers the other languages.
// Line-for-line port of gender.py (read its docstring for the why); tests/test_web_parity.py runs both
// over a whole book and fails on any difference, so change them together.
// Works as a page script (window.Gender), a browser-extension content script, or a Node module.
(function(root){
  const DET={der:'mfL',die:'fL',das:'n',den:'mL',dem:'mn',des:'mn',
    im:'mn',am:'mn',vom:'mn',zum:'mn',beim:'mn',zur:'f',ins:'n',ans:'n',aufs:'n',durchs:'n',fürs:'n',ums:'n'};
  const EIN={'':'mn',e:'fL',en:'mL',em:'mn',er:'fL',es:'mn'};
  const DER={er:'mfL',e:'fL',es:'mn',en:'mL',em:'mn'};
  for(const stem of['ein','kein','mein','dein','sein','ihr','unser','euer','eur'])
    for(const[end,r]of Object.entries(EIN))if(!(stem+end in DET))DET[stem+end]=r;
  DET.eine='f';DET.einer='f';
  for(const stem of['dies','jen','jed','welch','manch','solch'])
    for(const[end,r]of Object.entries(DER))DET[stem+end]=r;
  const END=/[.!?…:]["'”’“‘)»«]*$/, OPEN=/^[»«„“"‚‘'(\[—–-]/, WORD=/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu;
  const PRONOUN=new Set(['Er','Sie','Es','Ihr','Ihre','Ihnen','Ihm','Ihn','Ich','Du','Dich','Dir','Wir','Man']);
  const ADJ=/(e|en|er|es|em)$/;
  const bare=w=>w.replace(WORD,'');
  const isUpper=c=>c!==c.toLowerCase()&&c===c.toUpperCase();
  const isLower=c=>c!==c.toUpperCase()&&c===c.toLowerCase();
  const allUpper=w=>w!==w.toLowerCase()&&w===w.toUpperCase();

  // gzipped JSON from a URL; a server that already unpacked it (Content-Encoding) is fine too, and so is
  // the plain file: Android's packager unpacks 'x.json.gz' assets into 'x.json' inside the APK
  async function load(url){
    let res=await fetch(url);
    if(!res.ok&&url.endsWith('.gz'))res=await fetch(url.slice(0,-3));
    if(!res.ok)throw new Error(url+' '+res.status);
    const buf=new Uint8Array(await res.arrayBuffer());
    const text=buf[0]===0x1f&&buf[1]===0x8b
      ?await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text()
      :new TextDecoder().decode(buf);
    return JSON.parse(text);
  }
  function readings(data,w){           // -> [readings, maybeNotANoun]
    if(Object.hasOwn(data,w)){const r=data[w];return[r.replace(/\*$/,''),r.endsWith('*')]}
    for(let k=3;k<w.length-2;k++){     // longest head first; a 3-letter head needs a 4+ letter prefix
      const head=w[k].toUpperCase()+w.slice(k+1);
      if(Object.hasOwn(data,head)&&(head.length>=4||k>=4))return[data[head].replace(/\*$/,''),true];
    }
    return['',false];
  }
  function pick(r,allowed){
    const ok=allowed?[...r].filter(x=>allowed.includes(x)||'MFNP'.includes(x)&&allowed.includes('L')):[];
    const x=(ok.length?ok:r.length?[...r]:[' '])[0];
    return x===' '||x==='P'?null:x.toLowerCase();
  }
  function determiner(words,i){
    for(let j=i-1;j>Math.max(-1,i-5);j--){
      const w=words[j];
      if(END.test(w)||w.endsWith(',')||w.endsWith(';'))return null;
      const t=bare(w).toLowerCase();
      if(Object.hasOwn(DET,t))return DET[t];
      if(!(isLower(t.slice(0,1))||/^\d+$/.test(t)))return null;
    }
    return null;
  }
  function genders(words,data,paraStart=[]){
    const starts=new Set(paraStart),out=[];
    for(let i=0;i<words.length;i++){
      const raw=words[i];let w=bare(raw);
      if(w.includes('-'))w=w.slice(w.lastIndexOf('-')+1);
      if(w.length<2||!isUpper(w[0])||allUpper(w)){out.push(null);continue}
      const[r,maybe]=readings(data,w);
      const first=i===0||starts.has(i)||END.test(words[i-1])||OPEN.test(raw);
      const nxt=i+1<words.length&&!END.test(raw)?bare(words[i+1]):'';
      if(!r||PRONOUN.has(w)||maybe&&(first||ADJ.test(w)&&isUpper(nxt.slice(0,1))&&readings(data,nxt)[0])){out.push(null);continue}
      out.push(pick(r,determiner(words,i)));
    }
    return out;
  }

  // Other languages (genders-<lang>.json.gz from tools/build_genders_more.py): nouns are lowercase, so a word
  // is a noun when the data says so; one marked * is also a common other word and is only colored after an
  // article. The article also picks between two genders ('el/la parte'). Allowed readings per article:
  // m f n c singular, M F N C plural; '' = an article that says nothing about gender (l', les).
  const ROM={   // [masc sing, fem sing, masc pl, fem pl] word lists
    es:[['el','un','del','al','este','ese','aquel','otro','mucho','nuestro','vuestro','todo','ningún','algún','cierto'],['la','una','esta','esa','aquella','otra','mucha','nuestra','vuestra','toda','ninguna','alguna','cierta'],
        ['los','unos','estos','esos','aquellos','otros','muchos','nuestros','vuestros','todos','algunos'],['las','unas','estas','esas','aquellas','otras','muchas','nuestras','vuestras','todas','algunas']],
    fr:[['le','un','du','au','ce','cet','mon','ton','son','quel','aucun','nul'],['la','une','cette','ma','ta','sa','quelle','aucune','nulle'],[],[]],
    it:[['il','lo','un','uno','del','dello','al','allo','nel','nello','sul','sullo','dal','dallo','questo','quel','quello','mio','tuo','suo','nostro','vostro'],['la','una','della','alla','nella','sulla','dalla','questa','quella','mia','tua','sua','nostra','vostra'],
        ['i','gli','dei','degli','ai','agli','nei','negli','sui','sugli','dai','dagli','questi','quei','quegli','miei','tuoi','suoi','nostri','vostri'],['le','delle','alle','nelle','sulle','dalle','queste','quelle','mie','tue','sue','nostre','vostre']],
    pt:[['o','um','do','no','ao','pelo','dum','num','este','esse','aquele','deste','desse','neste','nesse','meu','teu','seu','nosso','vosso'],['a','uma','da','na','à','pela','duma','numa','esta','essa','aquela','desta','dessa','nesta','nessa','minha','tua','sua','nossa','vossa'],
        ['os','uns','dos','nos','aos','pelos','estes','esses','aqueles','meus','teus','seus','nossos'],['as','umas','das','nas','às','pelas','estas','essas','aquelas','minhas','tuas','suas','nossas']]};
  const ART={};
  for(const[lang,[m,f,M,F]]of Object.entries(ROM)){const a=ART[lang]={};
    m.forEach(w=>a[w]='m');f.forEach(w=>a[w]='f');M.forEach(w=>a[w]='M');F.forEach(w=>a[w]='F')}
  for(const w of['les','des','aux','ces','mes','tes','ses','nos','vos','leurs'])ART.fr[w]='MF';
  for(const w of["l'","l’"])ART.fr[w]=ART.it[w]='';
  for(const[w,r]of[["un'",'f'],["dell'",''],["all'",''],["nell'",''],["sull'",''],["dall'",''],["quell'",'']]){ART.it[w]=r;ART.it[w.replace("'",'’')]=r}
  ART.nl={de:'cC',het:'n',een:'cn',deze:'cC',dit:'n',die:'cC',dat:'n',elk:'n',elke:'c',geen:'',mijn:'',zijn:'',haar:'',ons:'n',onze:'cC'};
  ART.sv={en:'c',ett:'n',den:'c',det:'n',min:'c',mitt:'n',din:'c',ditt:'n',sin:'c',sitt:'n',vår:'c',vårt:'n',någon:'c',något:'n',ingen:'c',inget:'n',denna:'c',detta:'n',de:'CN',dessa:'CN'};
  ART.ru=ART.pl={};   // no articles: only words that are always nouns get a color
  const ELIDE=/^(.*?['’])(\p{L}.*)$/u;
  function article(words,i,lang,data){   // the article in front, over up to two words that are not nouns ('la vieja casa')
    for(let j=i-1;j>=Math.max(0,i-3);j--){
      const w=words[j];if(END.test(w)||/[,;]$/.test(w))return null;
      const t=bare(w).toLowerCase();
      if(Object.hasOwn(ART[lang],t))return ART[lang][t];
      const r=Object.hasOwn(data,t)?data[t]:'';if(r&&!r.endsWith('*'))return null;
    }
    return null;
  }
  function tag(words,data,lang,paraStart=[]){
    if(lang==='de')return genders(words,data,paraStart);
    const starts=new Set(paraStart),out=[];
    for(let i=0;i<words.length;i++){
      let w=bare(words[i]),art=null;
      const el=ELIDE.exec(w);if(el&&Object.hasOwn(ART[lang],el[1].toLowerCase())){art=ART[lang][el[1].toLowerCase()];w=el[2]}   // l'eau, dell'anno
      if(w.length<2||allUpper(w)){out.push(null);continue}
      const first=i===0||starts.has(i)||END.test(words[i-1])||OPEN.test(words[i]);
      if(isUpper(w[0])&&!first){out.push(null);continue}   // a name, mid-sentence
      const lw=w.toLowerCase(),r=Object.hasOwn(data,lw)?data[lw]:'';
      if(art===null)art=article(words,i,lang,data);
      if(!r||r.endsWith('*')&&art===null){out.push(null);continue}
      const rs=r.replace(/\*$/,''),ok=art?[...rs].filter(x=>art.includes(x)):[];
      const x=(ok.length?ok:[...rs])[0];   // an article that fits no reading ('el agua') leaves the dictionary's
      out.push(x==='P'?null:x.toLowerCase());
    }
    return out;
  }
  // Shown in Settings: what each color means in that language.
  const KEY={de:{m:'der',f:'die',n:'das'},es:{m:'el',f:'la'},fr:{m:'le',f:'la'},it:{m:'il',f:'la'},pt:{m:'o',f:'a'},
    ru:{m:'он',f:'она',n:'оно'},pl:{m:'ten',f:'ta',n:'to'},nl:{c:'de',n:'het'},sv:{c:'en',n:'ett'}};
  const Gender={LANG:'de',LANGS:Object.keys(KEY),KEY,load,genders,readings,tag};
  if(typeof module!=='undefined'&&module.exports)module.exports=Gender;else root.Gender=Gender;
})(typeof self!=='undefined'?self:this);
