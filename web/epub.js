/* EPUB reading uses XML namespaces and bounded ZIP inflation; no network resources are loaded. */
(function(root){
  const named=(doc,name)=>[...doc.getElementsByTagNameNS('*',name)];
  function xml(text){
    if(!text)throw new Error('Missing EPUB metadata');
    const doc=new DOMParser().parseFromString(text,'application/xml');
    if(doc.querySelector('parsererror'))throw new Error('Invalid EPUB metadata');
    return doc;
  }
  async function open(file){
    if(file.size>150*1024*1024)throw new Error('EPUB exceeds 150 MB');
    const bytes=new Uint8Array(await file.arrayBuffer()),dv=new DataView(bytes.buffer),files=new Map();
    const valid=(at,n)=>Number.isSafeInteger(at)&&at>=0&&at+n<=bytes.length;
    let end=bytes.length-22;
    const floor=Math.max(0,end-65535);
    while(end>=floor&&(!valid(end,22)||dv.getUint32(end,true)!==0x06054b50||end+22+dv.getUint16(end+20,true)!==bytes.length))end--;
    if(end<floor||dv.getUint16(end+4,true)||dv.getUint16(end+6,true))throw new Error('Invalid EPUB archive');
    const count=dv.getUint16(end+10,true);let off=dv.getUint32(end+16,true),inflated=0;
    if(count===65535||!valid(off,dv.getUint32(end+12,true)))throw new Error('Unsupported EPUB archive');
    for(let k=0;k<count;k++){
      if(!valid(off,46)||dv.getUint32(off,true)!==0x02014b50)throw new Error('Invalid EPUB directory');
      const flags=dv.getUint16(off+8,true),method=dv.getUint16(off+10,true),size=dv.getUint32(off+20,true),uncompressed=dv.getUint32(off+24,true),local=dv.getUint32(off+42,true);
      const nl=dv.getUint16(off+28,true),extra=dv.getUint16(off+30,true),comment=dv.getUint16(off+32,true);
      if(!valid(off+46,nl+extra+comment)||!valid(local,30))throw new Error('Invalid EPUB entry');
      const name=new TextDecoder().decode(bytes.subarray(off+46,off+46+nl));
      files.set(name,{flags,method,size,uncompressed,local});off+=46+nl+extra+comment;
    }
    async function read(name){
      const f=files.get(name);if(!f)return null;
      if(f.flags&1||![0,8].includes(f.method))throw new Error('Encrypted or unsupported EPUB entry');
      if(f.uncompressed>40*1024*1024)throw new Error('EPUB chapter exceeds 40 MB');
      if(dv.getUint32(f.local,true)!==0x04034b50)throw new Error('Invalid EPUB entry');
      const start=f.local+30+dv.getUint16(f.local+26,true)+dv.getUint16(f.local+28,true);
      if(!valid(start,f.size))throw new Error('Truncated EPUB');
      const raw=bytes.subarray(start,start+f.size),chunks=[];let size=0;
      const stream=f.method===0?new Blob([raw]).stream():new Blob([raw]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
      const reader=stream.getReader();
      try{
        for(;;){const {done,value}=await reader.read();if(done)break;
          size+=value.length;inflated+=value.length;
          if(size>40*1024*1024||inflated>120*1024*1024)throw new Error('EPUB text is too large');
          chunks.push(value);
        }
      }catch(e){await reader.cancel().catch(()=>{});throw e}
      if(size!==f.uncompressed)throw new Error('Truncated EPUB entry');
      return new TextDecoder().decode(await new Blob(chunks).arrayBuffer());
    }
    return {read};
  }
  async function toBook(file,{Reading,TextClean}){
    const {read}=await open(file),container=xml(await read('META-INF/container.xml'));
    const opfPath=named(container,'rootfile')[0]?.getAttribute('full-path');
    if(!opfPath)throw new Error('Missing EPUB package');
    const opf=xml(await read(opfPath)),items=new Map(named(opf,'item').map(i=>[i.getAttribute('id'),i]));
    const tagged=Reading.langCode(named(opf,'language')[0]?.textContent||'');
    const path=(base,href)=>{
      const u=new URL(href,'https://epub.invalid/'+base);
      if(u.origin!=='https://epub.invalid')throw new Error('External EPUB chapter');
      return [decodeURIComponent(u.pathname.slice(1)),decodeURIComponent(u.hash.slice(1))];
    };
    const toc=[],nav=[...items.values()].find(i=>(i.getAttribute('properties')||'').split(/\s+/).includes('nav'));
    const tocItem=nav||items.get(named(opf,'spine')[0]?.getAttribute('toc'));
    if(tocItem){
      const tp=path(opfPath,tocItem.getAttribute('href'))[0],src=await read(tp);
      if(src){
        const doc=nav?new DOMParser().parseFromString(src,'text/html'):xml(src);
        if(nav){
          const navs=[...doc.querySelectorAll('nav')],tocNav=navs.find(n=>(n.getAttribute('epub:type')||'').split(/\s+/).includes('toc'))||navs[0];
          tocNav?.querySelectorAll('a[href]').forEach(a=>toc.push([a.textContent.trim().replace(/\s+/g,' '),...path(tp,a.getAttribute('href'))]));
        }else named(doc,'navPoint').forEach(n=>{
          const content=named(n,'content')[0];if(content)toc.push([(named(n,'text')[0]?.textContent||'').trim().replace(/\s+/g,' '),...path(tp,content.getAttribute('src'))]);
        });
      }
    }
    const words=[],para=[],chapters=[];
    const blocks=new Set(['p','div','li','h1','h2','h3','h4','h5','h6','blockquote','section','article','pre','td','figcaption']);
    for(const ref of named(opf,'itemref')){
      const item=items.get(ref.getAttribute('idref'));if(!item)continue;
      const name=path(opfPath,item.getAttribute('href'))[0],html=await read(name);if(!html)continue;
      const doc=new DOMParser().parseFromString(html,'text/html');
      doc.querySelectorAll('style,script,head').forEach(e=>e.remove());
      doc.querySelectorAll('sup').forEach(e=>{if(/^\s*[\[(]?[\d*†‡]{1,3}[\])]?\s*$/.test(e.textContent))e.remove()});
      const base=words.length,pending=toc.filter(([,f])=>f===name).map(([title,,id])=>({title,id,at:id?null:base}));
      if(!toc.length){const h=doc.querySelector('h1,h2');if(h)pending.push({title:h.textContent.trim().replace(/\s+/g,' ').slice(0,60),at:base})}
      let text='';
      const flush=()=>{const ws=Reading.tokenize(text,tagged);if(ws.length){para.push(words.length);for(const w of ws)words.push(w)}text=''};
      function visit(node){
        if(node.nodeType===3){text+=node.textContent;return}
        if(node.nodeType!==1)return;
        const tag=node.localName.split(':').pop(),block=blocks.has(tag);
        if(['script','style','head'].includes(tag))return;
        if(block||tag==='br')flush();
        for(const p of pending)if(p.id&&p.at===null&&node.id===p.id)p.at=words.length+Reading.tokenize(text,tagged).length;
        for(const child of node.childNodes)visit(child);
        if(block)flush();
      }
      visit(doc.body);flush();chapters.push(...pending.map(p=>[p.title,p.at]));
    }
    const title=named(opf,'title')[0]?.textContent.trim()||file.name.replace(/\.epub$/i,''),authors=named(opf,'creator').map(n=>n.textContent).join(' ');
    const c=TextClean.clean(words,para,chapters,title+' '+authors);
    if(!c.words.length)throw new Error('This EPUB has no readable text');
    c.chapters=TextClean.resolveMissing(c.words,c.para,c.chapters).filter(([t,i])=>t&&i!==null&&i<c.words.length);
    const lang=tagged&&!['und','mul','zxx'].includes(tagged)?tagged:TextClean.detectLang(c.words)||'';
    return {id:'f:'+file.name+':'+file.size,title,lang,...c};
  }
  const Epub={open,toBook};if(typeof module!=='undefined'&&module.exports)module.exports=Epub;else root.Epub=Epub;
})(typeof self!=='undefined'?self:this);
