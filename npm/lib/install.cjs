'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const F=require('./files.cjs'),P=require('./prerequisites.cjs');
function bind(bytes,source,destination) {
  let text=bytes.toString('utf8');
  if(!source.endsWith('.md'))return bytes;
  // Worker prompts are exact mathematical inputs, never deployment templates.
  if(source.includes('/roles/') || /\/agents\//.test(source))return bytes;
  // Development governance is deliberately not part of an installed campaign.
  text=text.split('\n').filter(line=>!line.includes('[OpenSpec specifications]')&&!line.includes('[root development instructions]')&&!line.includes('govern development and maintenance of MathTrace itself')).join('\n');
  text=text.replaceAll('python -m mathtrace','node .mathtrace/run.cjs');
  text=text.replace(/\]\(([^)]+)\)/g,(whole,link)=>{
    if(link.includes('://')||link.startsWith('#'))return whole;
    const origin=source.startsWith('coding-harnesses/antigravity/.agents/')?destination:source;
    const resolved=path.posix.normalize(path.posix.join(path.posix.dirname(origin),link));
    if(resolved.startsWith('docs/'))return ']('+path.posix.relative(path.posix.dirname(destination),'.mathtrace/'+resolved)+')';
    return whole;
  });
  text=text.replaceAll('`python tools/setup_execution.py`','external Lean verification engine setup');
  return Buffer.from(text);
}
function mapping(root,bundle,args,old) {
  const h=bundle.manifest.harnesses.find(h=>h.id===args.harness);
  if(!h)throw Error('Unknown harness: '+args.harness);
  if(old && old.harness!==h.id)throw Error('Harness switch requires explicit manual reconciliation; active deployment preserved');
  let codexSkills=args.codexSkills || old?.codexSkills;
  if(h.id==='codex') {
    const skills=Object.keys(bundle.manifest.files).filter(n=>n.startsWith('payload/coding-harnesses/shared/skills/')&&n.endsWith('/SKILL.md')).map(n=>n.split('/').at(-2));
    const has=dir=>skills.some(n=>fs.existsSync(F.safe(root,dir+'/'+n+'/SKILL.md')));
    const codex=has('.codex/skills'),compat=has('.agents/skills');
    if(codex&&compat)throw Error('Duplicate Codex/compatibility MathTrace skills already exist; reconcile names before installing');
    codexSkills ||= compat?'.agents/skills':'.codex/skills';
    if((codex&&codexSkills!=='.codex/skills')||(compat&&codexSkills!=='.agents/skills'))throw Error('Codex skill location conflicts with existing layout');
    if(codexSkills==='.agents/skills' && fs.existsSync(F.safe(root,'.agents/math-runtime-manifest.json')))throw Error('Preserve the managed Antigravity .agents projection; choose Codex skills without collisions');
  }
  if(h.id==='antigravity' && fs.existsSync(F.safe(root,'.agents/math-runtime-manifest.json')) && !old)throw Error('Existing native ownership requires reconciliation with the native installer; it is not adopted automatically');
  const desired={};
  const add=(source,destination)=>{desired[destination]=bind(F.read(bundle.base,'payload/'+source),source,destination);};
  for(const name of Object.keys(bundle.manifest.files)) {
    if(!name.startsWith('payload/'))continue;
    const source=name.slice(8);
    if(source.startsWith('coding-harnesses/shared/') || ['coding-harnesses/catalog.json'].includes(source))add(source,source);
    else if(source.startsWith('docs/'))add(source,'.mathtrace/'+source);
    else if(source.startsWith(`coding-harnesses/${h.id}/`)) {
      const local=source.slice(`coding-harnesses/${h.id}/`.length);
            if(local.startsWith('.')) {
        if(h.id==='codex' && (local.startsWith('.codex/skills/')||local.startsWith('.agents/skills/')) && !local.startsWith(codexSkills+'/'))continue;
        add(source,local);
      } else add(source,source);
    }
  }
  desired['coding-harnesses/README.md']=Buffer.from(`# Installed MathTrace integration\n\nSee [${h.name}](${h.id}/README.md) and [shared policy](shared/POLICY.md).\nRuntime: \`node .mathtrace/run.cjs\`. External host prerequisites are configured separately.\n\nMathTrace public project author/developer: [Velor-dev](https://github.com/Velor-dev).\nCopyright © 2026 Velor-dev. See [license](../.mathtrace/docs/LICENSE).\n`);
  for(const name of ['LICENSE'])desired['.mathtrace/docs/'+name]=F.read(bundle.base,name);
  desired['.mathtrace/run.cjs']=F.read(bundle.base,'lib/run.cjs');
  desired['.mathtrace/lib/bootstrap.py']=F.read(bundle.base,'lib/bootstrap.py');
  // All execution binding is root-side; native role bytes stay authoritative.
  const instruction=F.read(bundle.base,'payload/coding-harnesses/shared/project-instructions.md').toString().replace(/^# .*\n\nMerge this section[^\n]*\n\n/,'');
  const content=bind(Buffer.from(instruction),'coding-harnesses/shared/project-instructions.md','AGENTS.md').toString()+`\nInstalled harness: ${h.id}. Run existing operations with \`node .mathtrace/run.cjs <operation>\` from the project root. This launcher selects the owned runtime; it adds no mathematical workflow.\n`;
  const merged=F.instructionSection(F.read(root,'AGENTS.md'),content,old?.sectionHash);
  return {h,desired,merged,codexSkills};
}
function identity(exec,python,root) {
  return JSON.parse(exec(python,['-I','-m','mathtrace','identity'],{cwd:root})).result;
}
function checkRuntime(exec,python,root,bundle,runtime) {
  const observed=identity(exec,python,root);
  const location=path.resolve(observed.module);
  if(observed.version!==bundle.manifest.version || !location.startsWith(runtime+path.sep))throw Error('Installed runtime identity differs from bundled wheel');
  const code='import sys,zipfile,pathlib; import mathtrace; root=pathlib.Path(mathtrace.__file__).parent; z=zipfile.ZipFile(sys.argv[1]); expected={n[10:]:z.read(n) for n in z.namelist() if n.startswith("mathtrace/")}; actual={p.name:p.read_bytes() for p in root.iterdir() if p.is_file()}; assert actual==expected,"Installed runtime files differ"';
  exec(python,['-I','-c',code,F.safe(bundle.base,bundle.manifest.wheel)],{cwd:root});
  return observed;
}
function checkTree(root,relative) {
  const p=F.safe(root,relative);
  if(fs.existsSync(p)&&fs.statSync(p).isDirectory())for(const n of fs.readdirSync(p))checkTree(root,relative+'/'+n);
}
function install(project,bundle,args,deps={}) {
  const root=path.resolve(project);
  if(fs.realpathSync(root)!==root)throw Error('Refusing redirected project root');
  if(F.read(root,'.mathtrace/journal.json')) {
    const lock=F.safe(root,'.mathtrace/install.lock');
    if(fs.existsSync(lock))throw Error('Retained installation lock: verify the installer has stopped, remove .mathtrace/install.lock, then rerun recovery');
    const recoveryLock=fs.openSync(lock,'wx');
    try{F.recover(root);}finally{fs.closeSync(recoveryLock);fs.unlinkSync(lock);}
    throw Error('Interrupted file deployment restored; rerun to recompute the installation plan. Campaign history was retained.');
  }
  const exec=deps.execute || P.execute;
  const mode='direct';
  P.target(mode);
  const probe=P.python(args.python,exec);
  const old=F.receipt(root);
  const map=mapping(root,bundle,args,old);
  // Reject redirects beneath every runtime/state destination before provisioning.
  checkTree(root,'.math');
  for(const name of ['.mathtrace/runtime','.mathtrace/tmp','.mathtrace/install.lock','.mathtrace/journal.json'])F.safe(root,name);
  F.safe(root,'.mathtrace/backups');
  const planned=F.plan(root,map.desired,old);
  const instructionBefore=F.read(root,'AGENTS.md');
  if(!instructionBefore?.equals(map.merged.bytes))planned.changes.push({name:'AGENTS.md',before:instructionBefore,after:map.merged.bytes});
  const lock=F.safe(root,'.mathtrace/install.lock');
  fs.mkdirSync(path.dirname(lock),{recursive:true});
  let fd;try{fd=fs.openSync(lock,'wx');}catch{throw Error('Another installation or retained lock exists. Verify no installer is running before removing .mathtrace/install.lock and rerunning.');}
  try {
    fs.writeFileSync(fd,JSON.stringify({pid:process.pid}));
    if(F.read(root,'.mathtrace/journal.json')) {
      F.recover(root);
      throw Error('Previous interrupted deployment restored. Rerun installation to recompute the file plan. Campaign provisioning history was retained.');
    }
    let relative=old?.runtime;
    if(!relative || old.wheel!==bundle.manifest.files[bundle.manifest.wheel] || old.project!==root || old.basePython!==probe.base)relative=`.mathtrace/runtime/${bundle.manifest.version}-${bundle.manifest.files[bundle.manifest.wheel].slice(0,12)}-${crypto.randomUUID()}`;
    const runtime=F.safe(root,relative),python=path.join(runtime,process.platform==='win32'?'Scripts/python.exe':'bin/python');
    const temp=F.safe(root,'.mathtrace/tmp');fs.mkdirSync(temp,{recursive:true});
    const env={...process.env,TMPDIR:temp,TEMP:temp,TMP:temp,PIP_CACHE_DIR:temp,PIP_DISABLE_PIP_VERSION_CHECK:'1',PYTHONDONTWRITEBYTECODE:'1'};
    if(!fs.existsSync(runtime)) {
      exec(probe.executable,['-I','-m','venv',runtime],{cwd:root,env,timeout:120000});
      exec(python,['-I','-m','pip','--isolated','install','--no-index','--no-deps','--no-cache-dir',F.safe(bundle.base,bundle.manifest.wheel)],{cwd:root,env,timeout:120000});
    }
    const observed=checkRuntime(exec,python,root,bundle,runtime);
    const helper=F.safe(bundle.base,'lib/bootstrap.py');
    const bootArgs=['-I',helper,bundle.manifest.lean,mode];
    const provision=JSON.parse(exec(python,bootArgs,{cwd:root,env,timeout:1200000}));
    if(!provision.health?.ok)throw Error('Campaign health verification failed');
    const receipt={schema:1,project:root,version:bundle.manifest.version,harness:map.h.id,codexSkills:map.codexSkills,runtime:relative,basePython:probe.base,wheel:bundle.manifest.files[bundle.manifest.wheel],sectionHash:map.merged.sectionHash,files:planned.owned,...provision,mode};
    const raw=Buffer.from(JSON.stringify(receipt,null,2)+'\n');
    const before=F.read(root,'.mathtrace/install.json');
    if(!before?.equals(raw))planned.changes.push({name:'.mathtrace/install.json',before,after:raw});
    F.deploy(root,planned.changes,(phase,index)=>{
      deps.hook?.(phase,index);
      if(phase==='activated') {
        for(const [name,bytes] of Object.entries(map.desired))if(!F.read(root,name)?.equals(bytes))throw Error('Installed payload verification failed: '+name);
        checkRuntime(exec,python,root,bundle,runtime);
        const verified=JSON.parse(exec(python,[...bootArgs,'--verify'],{cwd:root,env,timeout:1200000}));
        if(!verified.health?.ok||verified.toolchain!==receipt.toolchain)throw Error('Final toolchain/state verification failed');
      }
    });
    return {installed:true,harness:map.h.id,version:observed.version,runtime:relative,toolchain:receipt.toolchain,mode,changedFiles:planned.changes.length,limits:map.h.limits};
  }catch(error){throw Error(error.message+'\nInstallation incomplete. Existing mathematical history and any valid provisioning records are retained; fix the reported prerequisite/conflict and rerun.');}
  finally {if(fd!==undefined)fs.closeSync(fd);fs.unlinkSync(lock);}
}
module.exports={loadBundle:F.loadBundle,install,mapping,bind,checkRuntime};
