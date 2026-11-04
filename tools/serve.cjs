#!/usr/bin/env node
// Local preview, including the same ebook download endpoint used in production.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const book=require('../api/book.js'),root=path.resolve(__dirname,'../web');
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json','.gz':'application/gzip','.svg':'image/svg+xml','.png':'image/png','.mjs':'text/javascript','.webmanifest':'application/manifest+json'};
http.createServer(async(req,res)=>{
  const u=new URL(req.url,'http://localhost');
  if(u.pathname==='/api/book')return book(req,res);
  const file=path.resolve(root,'.'+decodeURIComponent(u.pathname==='/'?'/index.html':u.pathname));
  if(!file.startsWith(root+path.sep)){res.statusCode=403;return res.end()}
  try{const data=await fs.promises.readFile(file);res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');res.end(data)}
  catch{res.statusCode=404;res.end('Not found')}
}).listen(8765,'127.0.0.1',()=>console.log('Speedready: http://127.0.0.1:8765'));
