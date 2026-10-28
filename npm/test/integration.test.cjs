const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{spawnSync}=require('node:child_process');
const packageDir=process.env.MATHTRACE_TEST_PACKAGE;
test('packed installer: every harness, independent runtime, repeat/update and preservation',{skip:!packageDir,timeout:600000},t=>{
 const {install,loadBundle}=require(path.join(packageDir,'lib/install.cjs'));
 const P=require(path.join(packageDir,'lib/prerequisites.cjs'));
 const F=require(path.join(packageDir,'lib/files.cjs'));
 const base=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'MathTrace independent ')));
 t.after(()=>fs.rmSync(base,{recursive:true,force:true}));
 const home=path.join(base,'external home');fs.mkdirSync(home);
 const extension=path.join(home,'.pi/agent/extensions/subagent');fs.mkdirSync(extension,{recursive:true});
 const saved={...P.piHashes};t.after(()=>Object.assign(P.piHashes,saved));
 for(const name of Object.keys(P.piHashes)){fs.writeFileSync(path.join(extension,name),'test extension fixture');P.piHashes[name]=F.sha('test extension fixture');}
 const bundle=loadBundle(packageDir);
 const projects=[];
 for(const h of bundle.manifest.harnesses){
  const root=path.join(base,h.id+' project');fs.mkdirSync(root);projects.push(root);
  fs.writeFileSync(path.join(root,'AGENTS.md'),'Owner instructions\r\n');
  fs.writeFileSync(path.join(root,'LICENSE'),'Owner license');
  fs.mkdirSync(path.join(root,'docs'));fs.writeFileSync(path.join(root,'docs/owner.md'),'owner docs');
  const profile=path.join(home,'.hermes');fs.mkdirSync(profile,{recursive:true});
  fs.writeFileSync(path.join(profile,'config.yaml'),JSON.stringify({skills:{external_dirs:[path.join(root,'.mathtrace/harness/skills')]}}));
  const execute=(command,args,settings)=>{
   if(args.length===1&&args[0]==='--version')return h.id==='opencode'?'1.0.0':'2.1.285';
   if(args[0]==='-I' && args[1]?.endsWith('bootstrap.py'))return P.execute(command,['-I',process.env.MATHTRACE_TEST_TOOLCHAIN,...args.slice(1)],settings);
   return P.execute(command,args,settings);
  };
  const deps={execute,home,env:{}};
  const args={harness:h.id,mode:'direct',python:process.env.MATHTRACE_TEST_PYTHON};
  assert.equal(install(root,bundle,args,deps).installed,true,h.id);
  assert.equal(install(root,bundle,args,deps).changedFiles,0,h.id+' repeat');
  assert.equal(fs.existsSync(path.join(root,'coding-harnesses')),false,h.id+' no root coding-harnesses');
  for(const name of ['LICENSE'])assert.deepEqual(fs.readFileSync(path.join(root,'.mathtrace/docs',name)),fs.readFileSync(path.join(packageDir,name)));
  assert.equal(fs.readFileSync(path.join(root,'LICENSE'),'utf8'),'Owner license');
  if(h.id==='codex'){
   // Model a previous notice-only deployment with unchanged owned notice bytes.
   const receiptPath=path.join(root,'.mathtrace/install.json');
   const receipt=JSON.parse(fs.readFileSync(receiptPath));
   for(const name of ['LICENSE']){
    const rel='.mathtrace/docs/'+name;fs.unlinkSync(path.join(root,rel));delete receipt.files[rel];
   }
   const notice='.mathtrace/docs/NOTICE.txt',prior=Buffer.from('prior rights-reserved notice');
   fs.writeFileSync(path.join(root,notice),prior);receipt.files[notice]=F.sha(prior);
   const legacy='.mathtrace/docs/THIRD_PARTY_NOTICES.txt';fs.writeFileSync(path.join(root,legacy),prior);receipt.files[legacy]=F.sha(prior);
   fs.writeFileSync(receiptPath,JSON.stringify(receipt));
   fs.writeFileSync(path.join(root,legacy),'owner edit');assert.throws(()=>install(root,bundle,args,deps),/Edited/);fs.writeFileSync(path.join(root,legacy),prior);
   // Unowned conflicting legal files must not be overwritten.
   const licensePath=path.join(root,'.mathtrace/docs/LICENSE');
   fs.writeFileSync(licensePath,'owner legal file');
   assert.throws(()=>install(root,bundle,args,deps),/Unowned/);
   assert.equal(fs.readFileSync(licensePath,'utf8'),'owner legal file');fs.unlinkSync(licensePath);
   // Failure after activation restores notice and removes newly added files.
   assert.throws(()=>install(root,bundle,args,{...deps,hook:p=>{if(p==='activated')throw Error('legal recovery fixture');}}),/legal recovery fixture/);
   assert.deepEqual(fs.readFileSync(path.join(root,notice)),prior);
   assert.equal(fs.existsSync(licensePath),false);
   assert.ok(install(root,bundle,args,deps).changedFiles>0);
   assert.equal(install(root,bundle,args,deps).changedFiles,0);
   assert.equal(fs.existsSync(path.join(root,notice)),false);assert.equal(fs.existsSync(path.join(root,legacy)),false);
   for(const name of ['LICENSE']){
    const file=path.join(root,'.mathtrace/docs',name),original=fs.readFileSync(file);
    fs.writeFileSync(file,'owner edit');assert.throws(()=>install(root,bundle,args,deps),/Edited/);
    assert.equal(fs.readFileSync(file,'utf8'),'owner edit');fs.writeFileSync(file,original);
   }
  }
  fs.writeFileSync(path.join(root,'.mathtrace/install.lock'),'retained test lock');
  assert.throws(()=>install(root,bundle,args,deps),/lock exists/);
  fs.unlinkSync(path.join(root,'.mathtrace/install.lock'));
  assert.equal(fs.readFileSync(path.join(root,'docs/owner.md'),'utf8'),'owner docs');
  assert.ok(fs.readFileSync(path.join(root,'AGENTS.md'),'utf8').startsWith('Owner instructions\r\n'));
  const launch=spawnSync(process.execPath,[path.join(root,'.mathtrace/run.cjs'),'identity'],{cwd:root,encoding:'utf8'});
  assert.equal(launch.status,0,launch.stderr);assert.equal(JSON.parse(launch.stdout).result.version,bundle.manifest.version);
  const invalid=spawnSync(process.execPath,[path.join(root,'.mathtrace/run.cjs'),'nonexistent'],{cwd:root});assert.notEqual(invalid.status,0);
  // Update a root-side payload via a new verified bundle fixture; role bytes stay fixed.
  if(h.id==='codex'){
   const rel='payload/coding-harnesses/shared/skills/math-progress/SKILL.md';const p=path.join(packageDir,rel);const original=fs.readFileSync(p);
   fs.writeFileSync(p,Buffer.concat([original,Buffer.from('\nFixture release update\n')]));
   const updated={...bundle,manifest:{...bundle.manifest,files:{...bundle.manifest.files,[rel]:F.sha(fs.readFileSync(p))}}};
   try{assert.ok(install(root,updated,args,deps).changedFiles>0);assert.equal(install(root,updated,args,deps).changedFiles,0);}finally{fs.writeFileSync(p,original);}
   const agent=path.join(root,'.codex/agents/math-prover.toml');const owner=fs.readFileSync(agent,'utf8')+'\n# owner customization\n';fs.writeFileSync(agent,owner);
   assert.throws(()=>install(root,bundle,args,deps),/Edited/);assert.equal(fs.readFileSync(agent,'utf8'),owner);
  }
 }
 // Original package location is unavailable after installation.
 const unavailable=packageDir+'-unavailable';fs.renameSync(packageDir,unavailable);
 try{for(const root of projects){
  const r=spawnSync(process.execPath,[path.join(root,'.mathtrace/run.cjs'),'health'],{cwd:root,encoding:'utf8'});assert.equal(r.status,0,r.stderr);assert.equal(JSON.parse(r.stdout).result.ok,true);
  for(const name of ['LICENSE'])assert.deepEqual(fs.readFileSync(path.join(root,'.mathtrace/docs',name)),fs.readFileSync(path.join(unavailable,name)));
  assert.equal(fs.readFileSync(path.join(root,'LICENSE'),'utf8'),'Owner license');
 }}
 finally{fs.renameSync(unavailable,packageDir);}
});
