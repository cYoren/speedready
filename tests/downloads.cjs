// No live downloads: exercise production streaming with controlled upstream responses.
const assert=require('node:assert/strict'),http=require('node:http'),handler=require('../api/book.js');
(async()=>{
 const original=global.fetch;let upstreamFinished=false,mode='large';
 const server=http.createServer(handler);await new Promise(ok=>server.listen(0,'127.0.0.1',ok));
 const base=`http://127.0.0.1:${server.address().port}`;
 global.fetch=async()=>{
  if(mode==='redirect')return new Response(null,{status:302,headers:{location:'https://localhost/private'}});
  if(mode==='latin')return new Response(Buffer.from([0x63,0x61,0x66,0xe9]),{headers:{'content-type':'text/plain; charset=iso-8859-1'}});
  if(mode==='empty')return new Response(null,{headers:{'content-type':'text/plain'}});
  if(mode==='pdf')return new Response(new ReadableStream({start(c){c.enqueue(Buffer.from('%P'));c.enqueue(Buffer.from('DF-1.4'));c.close()}}));
  let i=0;return new Response(new ReadableStream({async pull(c){
   await new Promise(ok=>setTimeout(ok,5));
   if(i===6){upstreamFinished=true;c.close();return}
   const bytes=Buffer.alloc(1024*1024);if(i===0)bytes.write('PK');i++;c.enqueue(bytes);
  }}),{headers:{'content-type':'application/epub+zip'}});
 };
 try{
  const r=await original(base+'/api/book?id=11');assert.equal(r.status,200);
  const reader=r.body.getReader(),first=await reader.read();assert(first.value.length);assert.equal(upstreamFinished,false,'Response must stream before upstream finishes');
  let size=first.value.length;for(;;){const chunk=await reader.read();if(chunk.done)break;size+=chunk.value.length}
  assert.equal(size,6*1024*1024);console.log('6 MB download streamed before upstream completion');
  mode='latin';const latin=await original(base+'/api/book?id=11');assert.equal(latin.headers.get('content-type'),'text/plain; charset=iso-8859-1');
  assert.equal(require('../web/reading.js').decodeText(new Uint8Array(await latin.arrayBuffer()),latin.headers.get('content-type')),'café');
  mode='redirect';assert.equal((await original(base+'/api/book?id=11')).status,400);
  mode='empty';assert.equal((await original(base+'/api/book?id=11')).status,400);
  mode='pdf';const pdf=await original(base+'/api/book?id=11');assert.equal(pdf.headers.get('content-type'),'application/pdf');assert.equal(await pdf.text(),'%PDF-1.4');
  assert.equal((await original(base+'/api/book?id=')).status,400);
  assert.equal((await original(base+'/api/book?id=11',{method:'POST'})).status,405);
  console.log('Unsafe redirects, empty books, split format headers and invalid requests checked');
 }finally{global.fetch=original;await new Promise(ok=>server.close(ok))}
})().catch(e=>{console.error(e);process.exitCode=1});
