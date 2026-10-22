const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const F=require('../lib/files.cjs');
const {spawnSync}=require('node:child_process');
function fixture(t){const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'mathtrace-files-')));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));return root;}
const name='.codex/skills/math-intake/SKILL.md';
test('ownership conflicts, identical foreign content and bounded receipt',t=>{
 const root=fixture(t);F.atomic(root,name,Buffer.from('owner'));
 assert.throws(()=>F.plan(root,{[name]:Buffer.from('new')},null),/Unowned/);
 assert.deepEqual(F.plan(root,{[name]:Buffer.from('owner')},null).owned,{});
 assert.throws(()=>F.plan(root,{[name]:Buffer.from('new')},{files:{[name]:F.sha('old')}}),/Edited/);
 assert.throws(()=>F.safe(root,'../outside'));
 F.atomic(root,'.mathtrace/install.json',Buffer.from('{}'));assert.throws(()=>F.receipt(root),/Malformed/);
});
test('managed instruction sections preserve surrounding bytes and detect edits',()=>{
 const original=Buffer.from('owner\r\n');const first=F.instructionSection(original,'workflow');
 assert.ok(first.bytes.subarray(0,original.length).equals(original));
 const edited=Buffer.concat([first.bytes,Buffer.from('outside\r\n')]);
 const next=F.instructionSection(edited,'updated',first.sectionHash);
 assert.ok(next.bytes.toString().endsWith('outside\r\n'));
 assert.throws(()=>F.instructionSection(first.bytes,'changed','0'.repeat(64)),/edited/);
});
test('every deployment failure restores old bytes, including after receipt activation',t=>{
 const root=fixture(t);F.atomic(root,name,Buffer.from('old'));
 for(const phase of ['journal','write','activated']) {
   assert.throws(()=>F.deploy(root,[{name,before:Buffer.from('old'),after:Buffer.from('new')}],p=>{if(p===phase)throw Error('injected');}),/injected/);
   assert.equal(F.read(root,name).toString(),'old');assert.equal(F.read(root,'.mathtrace/journal.json'),null);
 }
});
test('interrupted update recovers; subsequent user edits block rollback',t=>{
 const root=fixture(t);F.atomic(root,name,Buffer.from('after'));
 const journal={schema:1,changes:[{name,before:Buffer.from('before').toString('base64'),after:Buffer.from('after').toString('base64')}]};
 F.atomic(root,'.mathtrace/journal.json',Buffer.from(JSON.stringify(journal)));F.recover(root);assert.equal(F.read(root,name).toString(),'before');
 F.atomic(root,'.mathtrace/journal.json',Buffer.from(JSON.stringify(journal)));F.atomic(root,name,Buffer.from('local edit'));
 assert.throws(()=>F.recover(root),/Recovery conflict/);assert.equal(F.read(root,name).toString(),'local edit');
});
test('symlink/junction destinations cannot redirect writes',t=>{
 const root=fixture(t);const external=fixture(t);
 fs.symlinkSync(external,path.join(root,'.codex'),process.platform==='win32'?'junction':'dir');
 assert.throws(()=>F.safe(root,name),/Redirected/);assert.equal(fs.readdirSync(external).length,0);
});
test('abrupt process termination leaves a recoverable durable journal',t=>{
 const root=fixture(t);F.atomic(root,name,Buffer.from('old'));
 const code=`const f=require(process.argv[1]);f.deploy(process.argv[2],[{name:${JSON.stringify(name)},before:Buffer.from('old'),after:Buffer.from('new')}],p=>{if(p==='write')process.exit(87);});`;
 const result=spawnSync(process.execPath,['-e',code,path.resolve(__dirname,'../lib/files.cjs'),root]);assert.equal(result.status,87);
 assert.equal(F.read(root,name).toString(),'new');F.recover(root);assert.equal(F.read(root,name).toString(),'old');
});
test('updates remove only unchanged obsolete owned files',t=>{
 const root=fixture(t);F.atomic(root,name,Buffer.from('old'));F.atomic(root,'.codex/owner.toml',Buffer.from('foreign'));
 const planned=F.plan(root,{}, {files:{[name]:F.sha('old')}});F.deploy(root,planned.changes);
 assert.equal(F.read(root,name),null);assert.equal(F.read(root,'.codex/owner.toml').toString(),'foreign');
 assert.equal(F.receipt(root),null);
});
