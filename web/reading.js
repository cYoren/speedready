/* Reading language is independent of interface and dictionary coverage. */
(function(root){
  const ISO3={ger:'de',deu:'de',eng:'en',spa:'es',fre:'fr',fra:'fr',ita:'it',dut:'nl',nld:'nl',pol:'pl',por:'pt',rus:'ru',swe:'sv',ara:'ar',heb:'he',chi:'zh',zho:'zh',jpn:'ja',kor:'ko',hin:'hi',tha:'th',vie:'vi',tur:'tr',gre:'el',ell:'el',per:'fa',fas:'fa',urd:'ur',ind:'id',ukr:'uk'};
  let aliases=ISO3;
  const langCode=tag=>{const t=String(tag||'').trim().toLowerCase().replace(/_/g,'-').split('-')[0];return /^(?:[a-z]{2,3})$/.test(t)?aliases[t]||t:''};
  const rtl=lang=>/^(ar|he|fa|ur|ps|sd|ug|yi|dv|syr|arc|ckb)$/.test(langCode(lang));
  const segments=new Map();
  function tokenize(text,lang){
    // The EPUB reader marks non-text (page titles, footnote markers) with a leading \u0000. Segmentation must keep
    // the mark on every piece of a marked span, the way spaced scripts keep it on every word.
    if(text.includes('\u0000'))return text.split('\u0000').flatMap((piece,k)=>{const ws=segment(piece,lang);return k?ws.map(w=>'\u0000'+w):ws});
    return segment(text,lang);
  }
  function segment(text,lang){
    // Keep the established indices for spaced scripts. Segment only scripts which need it.
    if(!/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Thai}\p{Script=Lao}\p{Script=Khmer}\p{Script=Myanmar}]/u.test(text))return text.trim().split(/\s+/u).filter(Boolean);
    let s;
    if(typeof Intl.Segmenter==='function'){
      const code=langCode(lang)||'und';
      if(!segments.has(code))segments.set(code,new Intl.Segmenter(code,{granularity:'word'}));
      s=[...segments.get(code).segment(text)].map(x=>x.segment);
    }else s=text.match(/\p{L}\p{M}*|\p{N}+|[^\s]/gu)||[];
    const words=[];
    for(const part of s){
      if(!part.trim())continue;
      if(/^[\p{P}\p{S}]+$/u.test(part)&&words.length)words[words.length-1]+=part;
      else words.push(part);
    }
    return words;
  }
  function languageName(code,ui='en'){
    try{return new Intl.DisplayNames([ui],{type:'language'}).of(code)||code}catch{return code}
  }
  function decodeText(bytes,contentType=''){
    let encoding=(contentType.match(/charset\s*=\s*["']?([^;\s"']+)/i)||[])[1]||'utf-8';
    if(bytes[0]===0xff&&bytes[1]===0xfe)encoding='utf-16le';
    else if(bytes[0]===0xfe&&bytes[1]===0xff)encoding='utf-16be';
    return new TextDecoder(encoding).decode(bytes);
  }
  const Reading={langCode,rtl,tokenize,languageName,decodeText,setAliases:value=>{aliases={...ISO3,...value}}};
  if(typeof module!=='undefined'&&module.exports)module.exports=Reading;else root.Reading=Reading;
})(typeof self!=='undefined'?self:this);
