const assert=require('node:assert/strict'),C=require('../web/catalog.js'),E=require('../web/epub.js');
(async()=>{
 const rows=[[1,'Les Misérables','Victor Hugo',['fr']],[2,'日本の物語','作家',['ja']],[3,'قصة','كاتب',['ar']]];
 const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
 const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
 const source=html.slice(html.indexOf('function textToBook('),html.indexOf('// --- epub via'));
 const textToBook=vm.runInNewContext('('+source.trim()+')',{Reading:require('../web/reading.js'),TextClean:require('../web/textclean.js')});
 assert.equal(textToBook('read '.repeat(160000),'Large text','large').words.length,160000);
 const index=await C.createIndex(rows);
 assert.deepEqual(index.search('miserables hugo'),[rows[0]]);
 assert.deepEqual(index.search('日本','ja'),[rows[1]]);
 assert.deepEqual(index.search('日本','fr'),[]);assert.deepEqual(index.search('كاتب','ar'),[rows[2]]);
 await assert.rejects(E.open(new Blob(['not an epub'])),/Invalid EPUB/);
 console.log('Indexed accent/multilingual search and invalid archive checks passed');
})().catch(e=>{console.error(e);process.exitCode=1});
