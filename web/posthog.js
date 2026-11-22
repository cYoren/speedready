// Speedready usage analytics, sent to PostHog (PostHog, Inc., USA) as plain HTTP batches.
//
// What leaves the device: event names plus small numbers and enums (reading speed bucket, minutes
// bucket, book format, dictionary pair, interface language, app version). It never carries a book
// title, a file name, read text, a looked-up word, a URL, or anything typed.
//
// Three off switches:
//   1. reset the project API key in PostHog: every installed build is rejected, no release needed;
//   2. set KEY to '' below and ship;
//   3. delete this file and its call sites.
// The Settings switch ("Share anonymous usage data") stops the calls themselves: every event checks
// it and sends nothing while it is off. The desktop reader (speedready.py) has its own sender in
// posthog.py; this file covers the website, Android and iOS, which all run this page.
const PostHog=(function(){
  const KEY='phc_xiF5C5q2NPD6oMh5A2VdUWT7UULDUW8SCGTKZVM7i7mm';
  const HOST='https://us.i.posthog.com/batch/';
  const VERSION='1.0.10';                    // the reader build: Android's versionName, the iOS bundle version
  const OPT_KEY='sr:analytics', ID_KEY='sr:anon';
  const BLOCKED=/(email|name|token|password|secret|message|text|query|prompt|content|transcript|note|title|file|path|url|book|sentence)/i;
  const mem={};

  const read=k=>{try{const v=localStorage.getItem(k);return v===null?null:v}catch(e){return k in mem?mem[k]:null}};
  const write=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){mem[k]=v}};   // private mode still works, it just forgets

  function uuid(){
    try{if(crypto&&crypto.randomUUID)return crypto.randomUUID()}catch(e){}
    return 'anon-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,10);
  }
  function platform(){
    if(typeof window==='undefined')return 'web';
    if(window.AndroidShell)return 'android';
    if(window.webkit&&window.webkit.messageHandlers&&window.webkit.messageHandlers.scanFolder)return 'ios';
    return 'web';
  }
  function locale(){
    try{return document.documentElement.lang||'en'}catch(e){return 'en'}
  }
  // The Chrome, Firefox and Safari extensions ship a copy of this page; they stay out of analytics.
  function inExtension(){
    try{return /-extension:$/.test(location.protocol)}catch(e){return false}
  }
  function clean(props){
    const out={};
    for(const k of Object.keys(props||{})){
      if(BLOCKED.test(k))continue;                          // belt and braces: nothing free-form is ever sent
      const v=props[k];
      if(v===null||v===undefined||typeof v==='object')continue;
      out[k]=v;
    }
    return out;
  }

  // opts: {key, store:{read,write}, send(batch)} - the defaults are the browser ones; the test builds its own.
  function create(opts){
    opts=opts||{};
    const key=opts.key===undefined?KEY:opts.key;
    const rd=opts.store?opts.store.read:read, wr=opts.store?opts.store.write:write;
    const post=opts.send||function(batch){
      try{
        fetch(HOST,{method:'POST',headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({api_key:key,batch}),keepalive:true}).catch(()=>{});
      }catch(e){/* never let analytics break reading */}
    };
    const id=()=>{let v=rd(ID_KEY);if(!v){v=uuid();wr(ID_KEY,v)}return v};
    const event=(name)=>{
      const props={app:'speedready',platform:platform(),app_version:VERSION,locale:locale(),$process_person_profile:false};
      return {event:name,distinct_id:id(),timestamp:new Date().toISOString(),uuid:uuid(),properties:props};
    };
    const on=()=>!!key&&!inExtension()&&rd(OPT_KEY)!=='false';
    const optedOut=()=>rd(OPT_KEY)==='false';
    return {
      on,optedOut,
      track(name,props){
        if(!on())return;
        const e=event(name);Object.assign(e.properties,clean(props));
        post([e]);
      },
      // Sent once, before the switch goes off: the last event we hear from this device.
      optOut(){
        if(!key||inExtension())return;
        post([event('settings_analytics_opt_out')]);
      },
      setOptOut(off){wr(OPT_KEY,off?'false':'true')}
    };
  }
  const api=create();api.create=create;   // the test builds its own copies; the page uses this one
  return api;
})();
if(typeof module!=='undefined'&&module.exports)module.exports=PostHog;
