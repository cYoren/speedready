// Start tools/serve.cjs, then run with PLAYWRIGHT_MODULE/CHROMIUM if needed.
// Generates only synthetic fixtures; no books are fetched from public sources.
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path'),{execFileSync}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'dist/audit'),base=process.env.AUDIT_URL||'http://127.0.0.1:8765';
(async()=>{
 execFileSync('python',[path.join(__dirname,'epub_fixtures.py')]);await fs.mkdir(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  await context.addInitScript(()=>{localStorage.setItem('sr:native','"pt"');localStorage.setItem('sr:ui','"en"');localStorage.setItem('sr:gloss','false');localStorage.setItem('sr:gender','false')});
  const p=await context.newPage(),errors=[],checks=[];p.on('pageerror',e=>errors.push(e.message));
  await p.goto(base);await p.locator('#splash').waitFor({state:'hidden'});
  const fixture=(await fs.readFile(path.join(root,'dist/audit-fixtures/namespaced.epub'))).toString('base64');
  const imported=await p.evaluate(async data=>{
   const file=new File([Uint8Array.from(atob(data),c=>c.charCodeAt(0))],'test.epub');const book=await epubToBook(file);await saveBook(book);await loadBook(book);
   return {title:book.title,lang:book.lang,text:book.words.join(' '),chapters:book.chapters};
  },fixture);
  assert.equal(imported.title,'A & B');assert.equal(imported.lang,'fil');
  for(const word of ['Before','Nested','prose','After','Direct','section','Footnote'])assert(imported.text.includes(word),word+' missing');
  assert(!imported.text.includes('Never execute'));assert.equal(imported.chapters[0][0],'Our chapter');checks.push('Valid namespaced/single-quoted EPUB preserves title, text and TOC');
  await p.evaluate(async()=>{const b=textToBook(Array.from({length:16000},(_,i)=>'word'+i).join(' '),'Long book','audit:long');await loadBook(b);S.cells[0].focus();S.i=2700;show(false)});
  assert.equal(await p.locator('#page .cur').innerText(),'word2700');assert.equal(await p.evaluate(()=>document.activeElement.textContent),'word2700');checks.push('Pacer continues beyond the first 2,040 words, including one long paragraph');
  await p.evaluate(()=>{S.i=15999;show(false)});assert.equal(await p.locator('#page .cur').innerText(),'word15999');
  await p.evaluate(async()=>{await loadBook(textToBook('Keep this book open.','Keep','audit:keep'))});
  await p.locator('#page .cur').focus();await p.keyboard.press('Enter');await p.locator('#s-word').waitFor({state:'visible'});await p.keyboard.press('Escape');
  await p.evaluate(async()=>addBooks([new File(['   \n\n'],'empty.txt')]));assert.equal(await p.evaluate(()=>S.book.id),'audit:keep');checks.push('Empty import leaves the current book intact; words open with keyboard');
  await p.evaluate(async()=>{
   const real=idb;idb=(mode,fn)=>mode==='readwrite'?Promise.reject(new Error('QuotaExceededError')):real(mode,fn);
   try{await addBooks([new File(['A readable temporary book.'],'temporary.txt')])}finally{idb=real}
  });assert((await p.locator('#toast').innerText()).includes('could not save'));checks.push('Storage failure is visible while the book remains readable');
  await p.evaluate(async()=>{await loadBook(textToBook('Der M\u00fcller stand in der T\u00fcr der alten M\u00fchle.','Gloss','audit:gloss','de'))});
  await p.evaluate(()=>{S.gloss=true;document.body.classList.remove('plain');refreshGlosses();show(false)});
  const glossShown=await p.evaluate(()=>[...document.querySelectorAll('#page .c .g')].some(g=>g.textContent.trim()&&getComputedStyle(g).display!=='none'));
  await p.evaluate(()=>{S.gloss=false;document.body.classList.add('plain');refreshGlosses()});
  const glossHidden=await p.evaluate(()=>[...document.querySelectorAll('#page .c .g')].every(g=>getComputedStyle(g).display==='none'));
  assert(glossShown&&glossHidden,'translations must show with the toggle on, and hide only when it is off');
  checks.push('Translation above the words shows while enabled and hides when disabled');
  await p.locator('#b-settings').tap();
  assert.equal(await p.locator('#s-settings').getAttribute('role'),'dialog');assert(await p.locator('main').evaluate(e=>e.inert));
  await p.locator('#t-dark').focus();const before=await p.locator('#t-dark').getAttribute('aria-checked');await p.keyboard.press('Space');
  assert.notEqual(await p.locator('#t-dark').getAttribute('aria-checked'),before);
  const close=p.locator('#s-settings .sheet-close');await close.focus();await p.keyboard.press('Shift+Tab');assert(await p.evaluate(()=>document.querySelector('#s-settings').contains(document.activeElement)));checks.push('Switch keyboard/state, modal focus containment, and focus restoration');
  await p.keyboard.press('Escape');assert(!await p.locator('main').evaluate(e=>e.inert));assert.equal(await p.evaluate(()=>document.activeElement.id),'b-settings');
  await p.emulateMedia({reducedMotion:'reduce'});await p.locator('#b-library').tap();assert.equal(await p.locator('#s-library>div').evaluate(e=>getComputedStyle(e).animationName),'none');
  await p.locator('#discover summary').first().tap();await p.waitForFunction(()=>catalogIndex!==null);await p.locator('#catalog-language').selectOption('zh');
  assert((await p.locator('#catalog-status').innerText()).includes('443'));checks.push('Catalog language filter, reduced motion and touch controls');
  const start=performance.now();await p.evaluate(()=>catalogIndex.search('alice carroll','en'));checks.push('Indexed browser query took '+Math.round(performance.now()-start)+' ms including browser round trip');
  await p.evaluate(()=>$('#toast').classList.remove('on'));
  const a11y=[];
  await p.setViewportSize({width:320,height:640});assert(!await p.locator('#s-library>div').evaluate(e=>e.scrollWidth>e.clientWidth+1));
  const axePath=process.env.AXE_PATH||path.join(require('node:os').homedir(),'.cache/speedready/axe-core-4.10.3.min.js');
  await p.addScriptTag({path:axePath});
  for(const theme of ['light','dark']){
   await p.evaluate(theme=>{S.dark=theme==='dark';applyTheme()},theme);
   for(const [name,width,height] of [['phone',390,844],['tablet',820,1180],['desktop',1440,900]]){
    await p.setViewportSize({width,height});await p.locator('#discover').evaluate(e=>e.scrollIntoView({block:'start'}));
    await p.screenshot({path:path.join(out,theme+'-'+name+'.png')});
    const overflow=await p.locator('#s-library>div').evaluate(e=>e.scrollWidth>e.clientWidth+1);assert(!overflow,theme+' '+name+' overflow');
   }
   a11y.push({theme,surface:'catalog',...(await p.evaluate(async()=>{
    const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});
    return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))};
   }))});
   await p.keyboard.press('Escape');await p.locator('#b-settings').click();
   a11y.push({theme,surface:'settings',...(await p.evaluate(async()=>{
    const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))};
   }))});
   await p.keyboard.press('Escape');await p.locator('#b-library').click();
  }
  await p.keyboard.press('Escape');await p.setViewportSize({width:390,height:844});
  for(const [lang,text] of [['ar','مَرْحَبًا بالعالم. هذه قصة قصيرة.'],['ja','私は本を読みます。楽しい物語です。'],['zh','我喜欢读书。这是一本有趣的书。'],['hi','नमस्ते दुनिया। यह एक कहानी है।']]){
   await p.evaluate(async({lang,text})=>{await loadBook(textToBook(text,lang,'audit:'+lang,lang))},{lang,text});
   await p.screenshot({path:path.join(out,lang+'.png')});
  }
  await p.evaluate(async()=>{await loadBook(textToBook('super'.repeat(35),'Long word','audit:word'));setMode('rsvp')});
  assert(await p.locator('#rsvp-word').evaluate(e=>e.scrollWidth<=e.clientWidth+1));checks.push('Arabic/Japanese/Chinese/Hindi reading and a long RSVP word');
  await p.evaluate(async()=>{
   const entry=lib().find(b=>b.title==='A & B');await loadBook(await libraryBook(entry.id));await navigator.serviceWorker.ready;
  });
  await p.waitForFunction(()=>navigator.serviceWorker.controller!==null);
  await context.setOffline(true);await p.reload();await p.locator('#splash').waitFor({state:'hidden'});
  assert.equal(await p.evaluate(()=>S.book.title),'A & B');
  await p.locator('#b-library').click();await p.locator('#discover summary').first().click();await p.waitForFunction(()=>catalogIndex!==null);
  checks.push('Saved book and previously loaded catalog reopen offline with updated app assets');
  await context.setOffline(false);
  assert.equal(errors.length,0,errors.join('\n'));await fs.writeFile(path.join(out,'results.json'),JSON.stringify({checks,a11y,errors},null,2));
  const violations=a11y.flatMap(r=>r.violations.map(v=>({theme:r.theme,surface:r.surface,...v})));console.log(JSON.stringify({checks,violations},null,2));
  assert.equal(violations.length,0,'Accessibility violations: '+violations.map(v=>v.id).join(', '));
  // A failed optional dictionary must not block reading.
  const fallback=await browser.newContext();await fallback.route('**/dict-de-pt.json',r=>r.fulfill({status:503,body:'unavailable'}));
  await fallback.route('https://cyoren.github.io/**',r=>r.abort());const f=await fallback.newPage();await f.goto(base);await f.locator('#splash').waitFor({state:'hidden'});assert(await f.evaluate(()=>S.book.words.length>0));console.log('Dictionary failure leaves reader available');await fallback.close();
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
