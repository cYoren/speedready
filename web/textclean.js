// What the printed page left in an ebook: page numbers, running headers, sentences cut by a page break,
// PDF-style one-line paragraphs. Line-for-line port of Book.clean / Book.start in speedready.py;
// tests/test_web_parity.py checks both give the same words, paragraphs and position map.
(function(root){
  const DROP='\u0000';   // the parser's mark on words that are not text; dropped here, raw word counts stay put
  const END=/[.!?…]["'”’“‘)»«]*$/;
  const PAGE_NUM=/^(?:[-–—|\[(]\s*)?(?:(?:seite|page|s\.|p\.)\s*)?\d{1,4}(?:\s*[-–—|\])])?$/i;   // '– 7 –', '[7]', 'Seite 7', '7'
  const FRONT=/^(cover|titel(seite)?|title( page)?|inhalt(sverzeichnis)?|(table of )?contents|impressum|copyright|widmung|dedication|(das |zum )?buch|(der |über den )?autor(in)?|about the author|introduction|how to read.*)$/i;
  const LOWER=/^(?:(?![A-ZÄÖÜ])\p{L})+[,.;:!?]?$/u, HYPHEN=/\p{L}-$/u, ALPHA=/\p{L}/u;
  const CONJ=new Set(['und','oder','bis','sowie','als','and','or']);
  const isUpper=c=>c!==c.toLowerCase()&&c===c.toUpperCase();
  const strip=w=>w.replace(/^[^\p{L}\p{N}_]+|[^\p{L}\p{N}_]+$/gu,'');

  // words/para as parsed, chapters [[title, wordIndex|null]], names = title + authors
  // -> {words, para, chapters, old2new}: old2new[i] is where raw word i ended up
  function clean(raw,rawPara,chapters,names){
    const P=[...rawPara,raw.length],pre=[],paras=[];
    for(let k=0;k<rawPara.length;k++){
      const p=[];
      for(const w0 of raw.slice(P[k],P[k+1])){pre.push([paras.length,p.length]);const w=w0.split(DROP)[0];if(w)p.push(w)}
      paras.push(p);
    }
    const texts=paras.map(p=>p.join(' '));
    const meta=new Set(names.split(/\s+/).map(w=>strip(w).toLowerCase()).filter(Boolean)),count=new Map();
    paras.forEach((p,k)=>{if(p.length<=8)count.set(texts[k],(count.get(texts[k])||0)+1)});
    const header=(t,p)=>{
      const ws=new Set(p.map(w=>strip(w).toLowerCase()).filter(Boolean));
      return p.length<=8&&count.get(t)>=5&&ws.size>0&&[...ws].every(x=>meta.has(x));
    };
    const big=paras.filter(p=>p.length>=4);
    const lines=big.length>0&&big.filter(p=>!END.test(p[p.length-1])).length>big.length/2;
    const words=[],starts=[],first=[];let cut=false;
    for(let k=0;k<paras.length;k++){
      let p=paras[k];const t=texts[k];
      first.push(words.length);
      if(!p.length)continue;
      const last=words[words.length-1];
      const open=words.length>0&&!END.test(last)&&ALPHA.test(last);
      if(header(t,p)||PAGE_NUM.test(t)&&(!/^\d+$/.test(t)||open)){first[k]=null;cut=true;continue}
      const lower=LOWER.test(p[0]),run=starts.length?words.length-starts[starts.length-1]:0;
      const head=starts.length>0&&run<=8&&words.slice(starts[starts.length-1]).filter(w=>/[\p{L}\p{N}]/u.test(w)).every(w=>isUpper(w[0])||/\d/.test(w[0]));   // 'Chapter One The Arrival'
      if(open&&(lines&&run>=4&&!head||lower&&(cut||run>=12))){
        if(lower&&(cut||lines)&&HYPHEN.test(last)&&!CONJ.has(p[0])){
          words[words.length-1]=last.slice(0,-1)+p[0];p=p.slice(1);first[k]-=1;   // 'Mühlen-' | page break | 'knappe'
        }
      }else starts.push(words.length);
      words.push(...p);cut=false;
    }
    const start=new Array(first.length);let nxt=words.length;
    for(let k=first.length-1;k>=0;k--){if(first[k]!==null)nxt=first[k];start[k]=nxt}   // a dropped paragraph maps to the next kept word
    const at=(k,j)=>Math.min(first[k]!==null?start[k]+j:start[k],words.length);
    const old2new=[...pre.map(([k,j])=>at(k,j)),words.length];
    return {words,para:starts,old2new:old2new.slice(0,-1),
            chapters:chapters.map(([t,i])=>[t,i===null?null:old2new[Math.min(i,pre.length)]])};
  }
  // Broken epubs point at anchors that don't exist (null): find each title as a short heading paragraph instead,
  // skipping the book's own table of contents. Port of Book.resolve_missing; runs after clean().
  function resolveMissing(words,para,chapters){
    if(chapters.every(([,i])=>i!==null))return chapters;
    const norm=ws=>ws.map(x=>strip(x).toLowerCase()).join(' '),heads=new Map();
    para.forEach((p,k)=>{
      const q=k+1<para.length?para[k+1]:words.length;
      if(q-p<=12){const key=norm(words.slice(p,q));if(!heads.has(key))heads.set(key,[]);heads.get(key).push([p,q])}
    });
    const titles=chapters.map(([t])=>norm(t.split(/\s+/).filter(Boolean))),res=[];
    chapters.forEach(([t,i],k)=>{
      if(i===null){
        const nxt=k+1<titles.length?titles[k+1]:null,len=nxt?nxt.split(/\s+/).filter(Boolean).length:0;
        const hit=(heads.get(titles[k])||[]).find(([,q])=>!(nxt&&norm(words.slice(q,q+len+12)).includes(nxt)));   // a heading with the next title right behind it is the TOC page
        i=hit?hit[0]:null;
      }
      res.push([t,i]);
    });
    const kept=res.filter(([,i])=>i!==null),out=[];
    kept.forEach(([t,i],k)=>{   // keep the in-order ones, drop outliers (a title only found in a back-of-book index)
      if((!out.length||i>out[out.length-1][1])&&(k+1===kept.length||i<kept[k+1][1]))out.push([t,i]);
    });
    return out;
  }
  const remap=(old2new,n,i)=>old2new.length?Math.min(i>=0&&i<old2new.length?old2new[i]:i,Math.max(0,n-1)):i;
  // where a new book should open: the first chapter that is not cover, title page, contents or imprint
  function start(chapters,n){
    for(const[t,i]of chapters)if(!FRONT.test(t.replace(/^[ .:]+|[ .:]+$/g,''))&&i<n*0.2)return i;
    return 0;
  }
  // The language of a book with no (or a wrong) <dc:language>: whichever language's commonest little words
  // turn up most. A thousand words is plenty; ponytail: stopword vote, an n-gram model if languages ever blur.
  const STOP={de:'der die und das ist nicht ich sie es zu den mit sich ein auch auf dem nach',en:'the and of to is that it was he you with for his as not had her',
    fr:'le la les et des est un une que il pas qui dans pour sur au elle',es:'el la los las que y en un una es por con para no se lo del',
    it:'il di che e un una per non sono del della con mi si ma gli',pt:'o os as que e do da em um uma não para com se no na',
    nl:'het een en van is dat niet ik je op te zijn met er maar',pl:'i w nie na się z do to że jest jak co ale jego',
    ru:'и в не на я что он с как то это по она его',sv:'och att det som är på jag inte med för har av till men'};
  const SETS=Object.fromEntries(Object.entries(STOP).map(([l,s])=>[l,new Set(s.split(' '))]));
  function detectLang(words){
    const score={};for(const l in SETS)score[l]=0;
    for(const w of words.slice(0,1000)){const t=strip(w).toLowerCase();for(const l in SETS)if(SETS[l].has(t))score[l]++}
    const best=Object.entries(score).sort((a,b)=>b[1]-a[1])[0];
    return best&&best[1]>=5?best[0]:null;
  }
  // an epub's <dc:language> as a two-letter code: 'DE', 'de-DE', 'ger' and 'deu' are all 'de' (same as lang_code in speedready.py)
  const ISO3={ger:'de',deu:'de',eng:'en',spa:'es',fre:'fr',fra:'fr',ita:'it',dut:'nl',nld:'nl',pol:'pl',por:'pt',rus:'ru',swe:'sv'};
  const langCode=tag=>{const t=tag.trim().toLowerCase();return ISO3[t.slice(0,3)]||t.slice(0,2)};
  const TextClean={clean,resolveMissing,remap,start,detectLang,langCode,DROP};
  if(typeof module!=='undefined'&&module.exports)module.exports=TextClean;else root.TextClean=TextClean;
})(typeof self!=='undefined'?self:this);
