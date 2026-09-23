// Cache everything on first visit so the app works with no connection afterwards.
const CACHE='speedready-v1';
const ASSETS=['./','index.html','bundle.json','manifest.webmanifest','icon.svg','icon-180.png','icon-512.png'];
// The dictionary and starter book are named in bundle.json, so this build caches whichever
// language pair it ships without the filenames being written here twice.
async function precache(){
  const c=await caches.open(CACHE);
  await c.addAll(ASSETS);
  try{
    const b=await fetch('bundle.json').then(r=>r.json());
    await c.addAll([b.dict,b.starter].filter(Boolean));
  }catch(e){/* offline on first load: the fetch handler caches them on first use instead */}
}
self.addEventListener('install',e=>{
  e.waitUntil(precache().then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(caches.match(e.request,{ignoreSearch:true}).then(hit=>hit||fetch(e.request).then(res=>{
    if(res.ok&&new URL(e.request.url).origin===location.origin){const copy=res.clone();caches.open(CACHE).then(c=>c.put(e.request,copy))}
    return res;
  }).catch(()=>caches.match('index.html'))));
});
