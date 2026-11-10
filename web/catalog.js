/* Build once, search many times. Titles and authors never need re-normalizing per query. */
(function(root){
  const normalize=text=>text.normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase();
  async function createIndex(books,yieldTask=()=>Promise.resolve()){
    const all=[],languages=new Map();
    for(let i=0;i<books.length;i++){
      const b=books[i],entry={book:b,text:normalize(b[1]+' '+b[2])};all.push(entry);
      for(const language of b[3]){
        if(!languages.has(language))languages.set(language,[]);
        languages.get(language).push(entry);
      }
      if(i&&i%2048===0)await yieldTask();
    }
    return {search(query,language=''){
      const terms=normalize(query.trim()).split(/\s+/).filter(Boolean),entries=language?(languages.get(language)||[]):all;
      return entries.filter(e=>terms.every(t=>e.text.includes(t))).map(e=>e.book);
    }};
  }
  const Catalog={normalize,createIndex};if(typeof module!=='undefined'&&module.exports)module.exports=Catalog;else root.Catalog=Catalog;
})(typeof self!=='undefined'?self:this);
