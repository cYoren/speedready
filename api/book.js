// Public ebook downloads only. Never forward cookies, credentials, or arbitrary hosts.
const HOSTS=new Set(['www.gutenberg.org','gutenberg.org','standardebooks.org','www.openbookpublishers.com','openbookpublishers.com','books.openbookpublishers.com','cdn.openbookpublishers.com']);
const LIMIT=30*1024*1024;
function allowed(value){
  const u=new URL(value);
  if(u.protocol!=='https:'||u.port||u.username||u.password||!HOSTS.has(u.hostname))throw new Error('Unsupported book source');
  return u;
}
function bookType(data,contentType){
  if(data.subarray(0,2).toString()==='PK')return 'application/epub+zip';
  if(data.subarray(0,5).toString()==='%PDF-')return 'application/pdf';
  if(contentType.startsWith('text/plain')&&!/^\s*<(?:!doctype|html)/i.test(data.toString()))return contentType;
  throw new Error('Use a direct EPUB, PDF or text download link');
}
async function download(value,onChunk,signal=AbortSignal.timeout(45000)){
  let u=allowed(value);
  for(let n=0;n<4;n++){
    const r=await fetch(u,{redirect:'manual',signal});
    if([301,302,303,307,308].includes(r.status)){
      await r.body?.cancel();const location=r.headers.get('location');
      if(!location)throw new Error('Invalid source redirect');
      u=allowed(new URL(location,u).href);continue;
    }
    if(!r.ok){await r.body?.cancel();throw new Error('The source could not provide this book')}
    if(Number(r.headers.get('content-length'))>LIMIT){await r.body?.cancel();throw new Error('Book exceeds 30 MB')}
    const chunks=[];let size=0,head=Buffer.alloc(0),type;
    // Peek at enough bytes to identify the format, even if the source splits its header.
    for await(const chunk of r.body){
      size+=chunk.length;if(size>LIMIT)throw new Error('Book exceeds 30 MB');
      if(!type){
        head=Buffer.concat([head,chunk]);if(head.length<5)continue;
        type=bookType(head,r.headers.get('content-type')||'');
        if(onChunk)await onChunk(head,type);else chunks.push(head);head=Buffer.alloc(0);
      }else if(onChunk)await onChunk(chunk,type);else chunks.push(chunk);
    }
    if(!type){
      if(!head.length)throw new Error('The source returned an empty book');
      type=bookType(head,r.headers.get('content-type')||'');
      if(onChunk)await onChunk(head,type);else chunks.push(head);
    }
    return {data:onChunk?null:Buffer.concat(chunks),type};
  }
  throw new Error('Too many redirects');
}
async function handler(req,res){
  res.setHeader('Access-Control-Allow-Origin','*');
  res.setHeader('Cache-Control','no-store');
  res.setHeader('X-Content-Type-Options','nosniff');
  if(req.method!=='GET'){res.setHeader('Allow','GET');res.statusCode=405;return res.end('GET required')}
  const controller=new AbortController(),abort=()=>{if(!res.writableFinished)controller.abort()};
  res.on('close',abort);
  try{
    const q=new URL(req.url,'https://speedready.invalid').searchParams,id=q.get('id');
    if(id!==null&&!/^[1-9]\d{0,6}$/.test(id))throw new Error('Invalid Gutenberg book number');
    const url=id?`https://www.gutenberg.org/ebooks/${id}.epub.noimages`:q.get('url');
    await download(url,async(chunk,type)=>{
      if(!res.headersSent){
        res.setHeader('Content-Type',type);
        res.setHeader('Content-Disposition','attachment; filename="book.'+(type.includes('epub')?'epub':type.includes('pdf')?'pdf':'txt')+'"');
        res.flushHeaders(); // Stream: buffered Vercel function responses are limited to 4.5 MB.
      }
      if(!res.write(chunk))await new Promise((resolve,reject)=>{
        const clean=()=>{res.off('drain',drain);res.off('close',close)};
        const drain=()=>{clean();resolve()},close=()=>{clean();reject(new Error('Download interrupted'))};
        res.once('drain',drain);res.once('close',close);
      });
    },AbortSignal.any([controller.signal,AbortSignal.timeout(45000)]));
    res.end();
  }catch(e){
    if(res.headersSent)res.destroy(e);
    else{res.statusCode=400;res.setHeader('Content-Type','text/plain; charset=utf-8');res.end(e.message)}
  }finally{res.off('close',abort)}
}
module.exports=handler;
module.exports.allowed=allowed;
module.exports.download=download;
