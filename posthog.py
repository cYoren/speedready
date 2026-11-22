#!/usr/bin/env python3
"""Speedready usage analytics, sent to PostHog (PostHog, Inc., USA) as plain HTTP batches.

What leaves the device: event names plus small numbers and enums (reading speed, session length in
minutes, interface language, app version). It never carries a book title, a file name, read text, a
looked-up word, a URL or anything typed: `track` drops any property whose name looks free-form.

Three off switches:
  1. reset the project API key in PostHog: every installed build is rejected, no release needed;
  2. set KEY to '' below and ship;
  3. delete this file and its call sites.
The Settings switch ("Share anonymous usage data") stops the calls themselves: every event asks the
configured is_enabled callback, and nothing is sent while it is off. The web reader, Android and iOS
share web/posthog.js instead; this file is the desktop reader's sender.
"""
import datetime,json,re,threading,urllib.request,uuid

KEY='phc_xiF5C5q2NPD6oMh5A2VdUWT7UULDUW8SCGTKZVM7i7mm'
HOST='https://us.i.posthog.com/batch/'
UA={'Content-Type':'application/json','User-Agent':'Speedready/1.0 (https://github.com/cYoren/speedready)'}
BLOCKED=re.compile(r'(email|name|token|password|secret|message|text|query|prompt|content|transcript|note|title|file|path|url|book|sentence)',re.I)

class Analytics:
    """Anonymous events only. A call returns at once: the POST happens on a daemon thread and a
    failure is dropped, because losing an event must never interrupt reading."""
    def __init__(s,state_path,version,platform='linux',locale='en',is_enabled=None,key=None,host=None,send=None,timeout=5):
        s.path,s.version,s.platform,s.locale,s.timeout=state_path,version,platform,locale,timeout
        s.key=KEY if key is None else key   # a test passes '' to prove the off switch
        s.host=host or HOST
        s.enabled=is_enabled or (lambda:True)
        s.send=send or s._post
        s.state={'distinct_id':str(uuid.uuid4()),'first_value':False}
        try:s.state.update(json.loads(s.path.read_text()))
        except Exception:pass                  # no state yet, or unreadable: start a fresh anonymous id
        s.lock=threading.Lock()
        s.save()   # the anonymous id must survive the first launch, long before any reading milestone
    @property
    def on(s):return bool(s.key) and bool(s.enabled())
    def save(s):
        try:s.path.parent.mkdir(parents=True,exist_ok=True);s.path.write_text(json.dumps(s.state))
        except Exception:pass
    def event(s,name,props=None):
        now=datetime.datetime.now(datetime.timezone.utc).isoformat()
        clean={k:v for k,v in (props or {}).items()
               if not BLOCKED.search(k) and isinstance(v,(str,int,float,bool))}
        locale=s.locale() if callable(s.locale) else s.locale   # the interface language can change while it runs
        clean.update(app='speedready',platform=s.platform,app_version=s.version,locale=locale,
                     **{'$process_person_profile':False})
        return {'event':name,'distinct_id':s.state['distinct_id'],'timestamp':now,'uuid':str(uuid.uuid4()),'properties':clean}
    def track(s,name,**props):
        if not s.on:return
        batch=[s.event(name,props)]
        threading.Thread(target=s._flush,args=(batch,),daemon=True).start()
    def opt_out(s):
        """Sent once, before the switch goes off: the last event we hear from this device."""
        if not s.key:return
        s.state['opted_out']=True;s.save()
        threading.Thread(target=s._flush,args=([s.event('settings_analytics_opt_out')],),daemon=True).start()
    def first_value(s,**props):
        """Once per device, the first time the reader finishes a real reading session."""
        if s.state.get('first_value'):return
        s.state['first_value']=True;s.save()
        s.track('first_value',**props)
    def _flush(s,batch):
        try:s.send({'api_key':s.key,'batch':batch})
        except Exception:pass
    def _post(s,body):
        req=urllib.request.Request(s.host,data=json.dumps(body).encode(),headers=UA)
        with urllib.request.urlopen(req,timeout=s.timeout) as r:r.read(200)

_instance=None
def configure(*args,**kwargs):
    global _instance
    _instance=Analytics(*args,**kwargs);return _instance
def track(name,**props):
    if _instance:_instance.track(name,**props)
def opt_out():
    if _instance:_instance.opt_out()
def first_value(**props):
    if _instance:_instance.first_value(**props)
