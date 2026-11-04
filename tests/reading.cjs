const assert=require('node:assert/strict'),R=require('../web/reading.js'),api=require('../api/book.js');
assert.equal(R.langCode('fil'),'fil');assert.equal(R.langCode('jpn'),'ja');assert.equal(R.langCode('pt_BR'),'pt');
assert.equal(R.rtl('ar'),true);assert.equal(R.rtl('en'),false);
for(const [lang,text] of [['zh','我喜欢读书。你呢？'],['ja','私は本を読みます。'],['th','ฉันชอบอ่านหนังสือ']]){
  const words=R.tokenize(text,lang);assert(words.length>1);assert.equal(words.join(''),text);
}
assert.deepEqual(R.tokenize('مَرْحَبًا بالعالم','ar'),['مَرْحَبًا','بالعالم']);
for(const u of ['http://www.gutenberg.org/a','https://localhost/a','https://www.gutenberg.org.evil.test/a','https://user@www.gutenberg.org/a','https://www.gutenberg.org:444/a'])assert.throws(()=>api.allowed(u));
(async()=>{
  const original=global.fetch;
  try{
    global.fetch=async()=>new Response('<html>error</html>',{headers:{'content-type':'text/html'}});
    await assert.rejects(api.download('https://www.gutenberg.org/ebooks/11'),/direct EPUB/);
    global.fetch=async()=>new Response(null,{status:302,headers:{location:'https://localhost/private'}});
    await assert.rejects(api.download('https://www.gutenberg.org/ebooks/11'),/Unsupported/);
    global.fetch=async()=>new Response('PKbook',{headers:{'content-type':'application/epub+zip'}});
    assert.equal((await api.download('https://www.gutenberg.org/ebooks/11')).data.toString(),'PKbook');
    global.fetch=async()=>new Response('x',{headers:{'content-length':String(31*1024*1024)}});
    await assert.rejects(api.download('https://www.gutenberg.org/ebooks/11'),/30 MB/);
    console.log('Reading and download endpoint checks passed');
  }finally{global.fetch=original}
})().catch(e=>{console.error(e);process.exitCode=1});
