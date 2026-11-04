// Public ebook downloads only. Never forward cookies, credentials, or arbitrary hosts.
const HOSTS=new Set(['www.gutenberg.org','gutenberg.org','standardebooks.org','www.openbookpublishers.com','openbookpublishers.com','books.openbookpublishers.com','cdn.openbookpublishers.com']);
const LIMIT=30*1024*1024;
function allowed(value){
  const u=new URL(value);
  if(u.protocol!=='https:'||u.port||u.username||u.password||!HOSTS.has(u.hostname))throw new Error('Unsupported book source');
  return u;
}
async function download(value){
  let u=allowed(value);
  for(let n=0;n<4;n++){
    const r=await fetch(u,{redirect:'manual',signal:AbortSignal.timeout(45000)});
    if([301,302,303,307,308].includes(r.status)){
      await r.body?.cancel();u=allowed(new URL(r.headers.get('location'),u).href);continue;
    }
    if(!r.ok)throw new Error('The source could not provide this book');
    if(Number(r.headers.get('content-length'))>LIMIT){await r.body?.cancel();throw new Error('Book exceeds 30 MB')}
    const chunks=[];let size=0;
    for await(const chunk of r.body){size+=chunk.length;if(size>LIMIT){throw new Error('Book exceeds 30 MB')}chunks.push(chunk)}
    const data=Buffer.concat(chunks);
    // An HTML error/login page must never enter the library as a book.
    let type;
    if(data.subarray(0,2).toString()==='PK')type='application/epub+zip';
    else if(data.subarray(0,5).toString()==='%PDF-')type='application/pdf';
    else if((r.headers.get('content-type')||'').startsWith('text/plain'))type='text/plain; charset=utf-8';
    else throw new Error('Use a direct EPUB, PDF or text download link');
    return {data,type};
  }
  throw new Error('Too many redirects');
}
async function handler(req,res){
  res.setHeader('Access-Control-Allow-Origin','*');
  if(req.method!=='GET'){res.statusCode=405;return res.end('GET required')}
  try{
    const q=new URL(req.url,'https://speedready.invalid').searchParams,id=q.get('id');
    if(id&&!/^[1-9]\d{0,6}$/.test(id))throw new Error('Invalid Gutenberg book number');
    const url=id?`https://www.gutenberg.org/ebooks/${id}.epub.noimages`:q.get('url');
    const {data,type}=await download(url);
    res.setHeader('Content-Type',type);res.setHeader('Cache-Control','public, s-maxage=86400');
    res.setHeader('Content-Disposition','attachment; filename="book.'+(type.includes('epub')?'epub':type.includes('pdf')?'pdf':'txt')+'"');
    res.end(data);
  }catch(e){res.statusCode=400;res.setHeader('Content-Type','text/plain; charset=utf-8');res.end(e.message)}
}
module.exports=handler;
module.exports.allowed=allowed;
module.exports.download=download;
