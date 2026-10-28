'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawnSync}=require('node:child_process');
const {sha}=require('./files.cjs');
function execute(command,args,settings={}) {
  // npm's Windows .cmd shims cannot be spawned with shell:false. Resolve only
  // their explicit Node script target; never execute shell text from the shim.
  if(process.platform==='win32' && !/\.(exe|com)$/i.test(command)) {
    const candidates=path.isAbsolute(command)?[command]: (process.env.PATH||'').split(path.delimiter).flatMap(d=>[path.join(d,command),path.join(d,command+'.cmd')]);
    for(const candidate of candidates) {
      if(!fs.existsSync(candidate)||!fs.statSync(candidate).isFile()||!candidate.toLowerCase().endsWith('.cmd'))continue;
      const match=fs.readFileSync(candidate,'utf8').match(/"%dp0%\\([^"\r\n]+\.(?:cjs|mjs|js))"\s+%\*/i);
      if(match){args=[path.resolve(path.dirname(candidate),match[1]),...args];command=process.execPath;break;}
    }
  }
  const r=spawnSync(command,args,{encoding:'utf8',windowsHide:true,maxBuffer:16*1024*1024,timeout:30000,...settings});
  if(r.error || r.status!==0)throw Error('Command failed: '+path.basename(command)+' (check prerequisite/version; no fallback performed)'+(r.stderr?'\n'+r.stderr:''));
  return r.stdout;
}
function python(explicit,exec=execute) {
  const candidates=explicit?[[explicit]]:process.platform==='win32'?[['py','-3'],['python3'],['python']]:[['python3'],['python']];
  for(const candidate of candidates)try {
    const probe=JSON.parse(exec(candidate[0],[...candidate.slice(1),'-I','-c',
      'import sys,json,venv,ensurepip; assert sys.version_info >= (3,11); print(json.dumps({"executable":sys.executable,"base":sys._base_executable,"version":list(sys.version_info[:3])}))']));
    if(probe.version[0]!==3 || probe.version[1]<11 || !probe.executable)continue;
    return probe;
  }catch{}
  throw Error('Python 3.11+ with venv/ensurepip is required. Install Python using your OS provider (Linux may require python3-venv), then rerun; or pass --python <executable>. No Python was installed.');
}
const piHashes={'index.ts':'1d11858d163e2a3a258af51c1923fc55ad825813acd6224462fd25ad61f5401b','agents.ts':'cc85ecd33b89aa575bea3d2a9a9da7654a6305da4de02e5041aa5342a1de29b4'};
function external(harness,root,{home=os.homedir(),env=process.env}={}) {
  if(harness.id==='pi') {
    const folder=path.join(env.PI_CODING_AGENT_DIR || path.join(home,'.pi/agent'),'extensions/subagent');
    for(const [name,digest] of Object.entries(piHashes)) {
      const p=path.join(folder,name);
      if(!fs.existsSync(p)||sha(fs.readFileSync(p))!==digest)throw Error('Pi requires the compatible official subagent extension index.ts and agents.ts in '+folder+'. See packaged Pi SETUP.md; retain agentScope: project and rerun. Unknown extension revisions require compatibility review, not silent acceptance.');
    }
  }
  if(harness.id==='hermes-agent') {
    const config=path.join(env.HERMES_HOME || path.join(home,'.hermes'),'config.yaml');
    if(!fs.existsSync(config))throw Error('Configure Hermes skills.external_dirs in '+config+' to '+path.join(root,'coding-harnesses/hermes-agent/skills')+' before rerunning. No profile file was changed.');
    const content=fs.readFileSync(config,'utf8');
    let dirs;
    try{dirs=JSON.parse(content).skills?.external_dirs;}catch{
      // Accept the documented simple block; complex YAML is deliberately unverifiable.
      const block=content.match(/^skills:\s*\r?\n((?:[ \t]+[^\n]*\r?\n?)*)/m)?.[1];
      const values=block?.match(/^[ \t]+external_dirs:\s*\r?\n((?:[ \t]+-[^\n]*\r?\n?)*)/m)?.[1];
      dirs=values?.split(/\r?\n/).filter(l=>l.trim()).map(l=>l.replace(/^\s*-\s*/,'').trim().replace(/^['"]|['"]$/g,''));
    }
    const expected=path.join(root,'coding-harnesses/hermes-agent/skills');
    const expanded=(Array.isArray(dirs)?dirs:[]).filter(d=>typeof d==='string').map(d=>d.replace(/\$\{MATHTRACE_WORKSPACE\}/g,env.MATHTRACE_WORKSPACE || '').replace(/^~(?=[/\\])/,home));
    if(!Array.isArray(dirs)||!expanded.some(d=>path.isAbsolute(d)&&path.resolve(d)===expected))throw Error('Hermes skills.external_dirs must verifiably include '+expected+'. Set MATHTRACE_WORKSPACE if using the example binding, keep the project as working directory, and rerun. Complex/unrecognized YAML requires an equivalent simple documented setting.');
  }
  if(harness.id==='claude-code') {
    const settingsPath=path.join(env.CLAUDE_CONFIG_DIR || path.join(home,'.claude'),'settings.json');
    let combined=false;
    if(fs.existsSync(settingsPath)) {
      try {const settings=JSON.parse(fs.readFileSync(settingsPath,'utf8'));
        combined=settings.pluginConfigs?.['cc-plugin-agents-md@builtin']?.options?.instructionFiles==='claude-md-and-agents-md'
          && settings.enabledPlugins?.['cc-plugin-agents-md@builtin']!==false;
      }catch{throw Error('Cannot verify Claude user instruction-loading settings; repair the existing settings externally and rerun');}
    }
    let ancestor=root;
    while(true) {
      if(!combined&&['CLAUDE.md','CLAUDE.local.md','.claude/CLAUDE.md'].some(n=>fs.existsSync(path.join(ancestor,n))))throw Error('Existing Claude instruction files may shadow AGENTS.md. Configure claude-md-and-agents-md in the existing user settings externally, then rerun. No CLAUDE.md or settings were changed.');
      const parent=path.dirname(ancestor);if(parent===ancestor)break;ancestor=parent;
    }
  }
  return {scope:'Static installation prerequisites checked; authentication, effective tools/model inheritance and independent capture remain host limitations.'};
}
function target(mode='direct',platform=process.platform,arch=process.arch) {
  if(!['win32','linux','darwin'].includes(platform) || !['x64','arm64'].includes(arch) || platform==='win32'&&arch!=='x64')throw Error('Unsupported native Lean publisher target');
}
function sandbox(mode='direct',exec=execute) {
  // Direct execution is the standard runtime mode.
  return;
}
module.exports={execute,python,external,target,sandbox,piHashes};
