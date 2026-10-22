const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const P=require('../lib/prerequisites.cjs');
const harnesses=require('../../coding-harnesses/research.json').harnesses;
test('Python probing rejects missing/old/broken prerequisites',()=>{
 for(const answer of [()=>{throw Error('missing');},()=>JSON.stringify({version:[3,10,0],executable:'python'}),()=>'{bad'])assert.throws(()=>P.python(null,answer),/Python 3.11/);
 assert.equal(P.python('chosen',()=>JSON.stringify({version:[3,11,0],executable:'chosen',base:'base'})).executable,'chosen');
});
test('all harness contracts check versions and preserve external files',t=>{
 const home=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'mathtrace-host-')));t.after(()=>fs.rmSync(home,{recursive:true,force:true}));
 for(const h of harnesses) {
   assert.throws(()=>P.external(h,home,{home,exec:()=>{throw Error('not installed');}}),/Cannot verify/);
   if(['pi','hermes-agent'].includes(h.id))assert.throws(()=>P.external(h,home,{home,exec:()=> '2.1.285'}),/requires|Configure Hermes/);
   else assert.ok(P.external(h,home,{home,exec:()=> h.id==='opencode'?'1.0.0':'2.1.285'}).scope);
 }
 assert.deepEqual(fs.readdirSync(home),[]);
 fs.mkdirSync(path.join(home,'.hermes'));const config=path.join(home,'.hermes/config.yaml');
 const content=JSON.stringify({skills:{external_dirs:[path.join(home,'coding-harnesses/hermes-agent/skills')]},token:'do not log'});fs.writeFileSync(config,content);
 assert.ok(P.external(harnesses.find(h=>h.id==='hermes-agent'),home,{home,exec:()=> '0.1.0'}));
 assert.equal(fs.readFileSync(config,'utf8'),content);
 fs.writeFileSync(config,JSON.stringify({skills:{external_dirs:'invalid scalar'}}));
 assert.throws(()=>P.external(harnesses.find(h=>h.id==='hermes-agent'),home,{home,exec:()=> '0.1.0'}),/skills.external_dirs must/);
});
test('native platforms and sandbox availability are separate',()=>{
 for(const [platform,arch] of [['win32','x64'],['linux','x64'],['linux','arm64'],['darwin','x64'],['darwin','arm64']])P.target('direct',platform,arch);
 assert.throws(()=>P.target('direct','win32','arm64'));assert.throws(()=>P.target('bubblewrap','darwin','arm64'));
 P.sandbox('direct',()=>{throw Error('must not probe');});assert.throws(()=>P.sandbox('bubblewrap',()=>{throw Error();}),/not substituted/);
});
test('Claude combined loading honors existing user settings without modifying them',t=>{
 const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'mathtrace-claude-')));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 fs.writeFileSync(path.join(root,'CLAUDE.md'),'owner');fs.mkdirSync(path.join(root,'.claude'));
 const h=harnesses.find(h=>h.id==='claude-code');
 assert.throws(()=>P.external(h,root,{home:root,env:{},exec:()=> '2.1.285'}),/shadow/);
 const settings=JSON.stringify({pluginConfigs:{'cc-plugin-agents-md@builtin':{options:{instructionFiles:'claude-md-and-agents-md'}}}});
 fs.writeFileSync(path.join(root,'.claude/settings.json'),settings);
 assert.ok(P.external(h,root,{home:root,env:{},exec:()=> '2.1.285'}));
 assert.equal(fs.readFileSync(path.join(root,'.claude/settings.json'),'utf8'),settings);assert.equal(fs.readFileSync(path.join(root,'CLAUDE.md'),'utf8'),'owner');
});
