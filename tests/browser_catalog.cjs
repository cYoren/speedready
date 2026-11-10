// Start tools/serve.cjs first. Requires Playwright; CHROMIUM may point to an existing browser.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM});const page=await browser.newPage();const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765');await page.locator('#splash').waitFor({state:'hidden'});
 await page.locator('#b-library').click();await page.locator('#discover summary').first().click();
 await page.waitForFunction(()=>document.querySelector('#catalog-results').children.length>0);
 await page.locator('#catalog-language').selectOption('zh');
 await page.waitForFunction(()=>[...document.querySelectorAll('#catalog-results small')].every(e=>e.textContent.includes('Chinese')));
 console.log('Chinese search:',await page.locator('#catalog-status').innerText());
 await fs.mkdir(require('node:path').resolve(__dirname,'../dist/language-preview'),{recursive:true});
 for(const [name,width,height] of [['phone',390,844],['tablet',820,1180],['desktop',1440,900]]){
   await page.setViewportSize({width,height});await page.locator('#discover').evaluate(e=>e.scrollIntoView({block:'start'}));
   await page.screenshot({path:`${require('node:path').resolve(__dirname,'../dist/language-preview')}/${name}.png`});
   const overflow=await page.evaluate(()=>[...document.querySelectorAll('#discover *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>e.id||e.tagName));
   if(overflow.length)throw Error('Overflow '+name+': '+overflow);
 }
 await page.locator('#catalog-language').selectOption('en');await page.locator('#catalog-query').fill('alice carroll');await page.locator('#catalog-form button').click();
 await page.waitForFunction(()=>document.querySelector('#catalog-status').textContent.includes('books found'));
 const result=page.locator('#catalog-results .book').filter({has:page.locator('a[href="https://www.gutenberg.org/ebooks/11"]')});
 await result.locator('button').click();
 await page.waitForFunction(()=>S.book.id==='gutenberg:11',{},{timeout:65000});
 console.log('Live Gutenberg import:',await page.evaluate(()=>({title:S.book.title,lang:S.book.lang,words:S.book.words.length})));
 await page.reload();await page.locator('#splash').waitFor({state:'hidden'});
 if(await page.evaluate(()=>S.book.id)!=='gutenberg:11')throw Error('Saved book did not reopen');
 await page.context().setOffline(true);await page.reload();await page.locator('#splash').waitFor({state:'hidden'});
 if(await page.evaluate(()=>S.book.id)!=='gutenberg:11')throw Error('Offline book did not reopen');
 console.log('Offline reopen passed');await page.context().setOffline(false);
 for(const [lang,text] of [['ar','مَرْحَبًا بالعالم. هذه قصة قصيرة.'],['ja','私は本を読みます。楽しい物語です。'],['zh','我喜欢读书。这是一本有趣的书。']]){
  const data=await page.evaluate(async({lang,text})=>{const b=textToBook(text,'Test '+lang,'test:'+lang,lang);await saveBook(b);await loadBook(b);return {lang:S.book.lang,dir:page.dir,words:b.words.length,text:b.words.join('')}} ,{lang,text});
  console.log('Reading:',data);await page.screenshot({path:`${require('node:path').resolve(__dirname,'../dist/language-preview')}/${lang}.png`});
 }
 if(errors.length)throw Error(errors.join('\n'));
 console.log('Browser checks passed');await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
