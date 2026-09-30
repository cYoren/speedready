// German noun genders for a list of words: 'm', 'f', 'n' or null per word.
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

  // gzipped JSON from a URL; a server that already unpacked it (Content-Encoding) is fine too
  async function load(url){
    const buf=new Uint8Array(await (await fetch(url)).arrayBuffer());
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
  const Gender={LANG:'de',load,genders,readings};   // German only: the one language whose nouns carry a gender this data knows
  if(typeof module!=='undefined'&&module.exports)module.exports=Gender;else root.Gender=Gender;
})(typeof self!=='undefined'?self:this);
