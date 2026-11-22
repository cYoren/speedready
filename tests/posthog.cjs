#!/usr/bin/env node
// The web sender (web/posthog.js) that the site, Android and iOS run: nothing goes out when the key is
// empty or the switch is off, and what does go out carries the app name and no free-form property.
// Run: node tests/posthog.cjs
const assert=require('assert'),path=require('path'),os=require('os'),fs=require('fs');
const PostHog=require(path.join(__dirname,'..','web','posthog.js'));

const store=()=>{const m={};return{read:k=>k in m?m[k]:null,write:(k,v)=>{m[k]=v}}};
const make=(opts={})=>{const sent=[];const ph=PostHog.create(Object.assign({store:store(),send:b=>sent.push(...b)},opts));return{ph,sent}};

// the key is empty: the whole module is dead
let {ph,sent}=make({key:''});
ph.track('app_opened');ph.optOut();
assert.deepStrictEqual(sent,[]);

// the reader switched it off
({ph,sent}=make());
ph.setOptOut(true);
ph.track('app_opened');
assert.deepStrictEqual(sent,[]);
assert.strictEqual(ph.on(),false);

// what does go out
({ph,sent}=make());
ph.track('reading_session_completed',{wpm_bucket:'250_399',minutes_bucket:'5_14',title:'Der Prozess',text:'hello',note:'x'});
assert.strictEqual(sent.length,1);
const e=sent[0];
assert.strictEqual(e.event,'reading_session_completed');
assert.strictEqual(e.properties.app,'speedready');
assert.strictEqual(e.properties.wpm_bucket,'250_399');
for(const k of ['title','text','note'])assert.ok(!(k in e.properties),k+' must never be sent');
for(const k of ['app','platform','app_version','locale','$process_person_profile'])assert.ok(k in e.properties,k);
assert.strictEqual(e.properties.$process_person_profile,false);
assert.ok(e.distinct_id&&e.timestamp&&e.uuid);

// the opt-out event still leaves, once, before the switch closes
({ph,sent}=make());
ph.optOut();
assert.deepStrictEqual(sent.map(x=>x.event),['settings_analytics_opt_out']);

// the switch comes back on
({ph,sent}=make());
ph.setOptOut(true);ph.setOptOut(false);ph.track('app_opened');
assert.deepStrictEqual(sent.map(x=>x.event),['app_opened']);

// storage that reads empty and refuses every write: the switch still has to take effect now
{
  const sent=[];
  const ph=PostHog.create({key:'phc_test',
    store:{read:()=>null,write:()=>{throw new Error('quota')}},   // what a full/private localStorage looks like
    send:b=>sent.push(...b)});
  ph.setOptOut(true);ph.track('app_opened');
  assert.deepStrictEqual(sent,[],'an opt-out that could not be saved must still stop the events');
  assert.strictEqual(ph.on(),false);
}

// one anonymous id per device, kept
const st=store();
const a=PostHog.create({store:st,send:()=>{}}),b=PostHog.create({store:st,send:()=>{}});
const sent2=[];const c=PostHog.create({store:st,send:x=>sent2.push(...x)});
c.track('app_opened');PostHog.create({store:st,send:()=>{}}).track('app_opened');
assert.strictEqual(sent2[0].distinct_id,st.read('sr:anon'));

console.log('posthog web module: ok');
