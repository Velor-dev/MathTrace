'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function safe(root, relative) {
  if (typeof relative !== 'string' || !relative || relative.includes('\\') || relative.includes(':') || relative.split('/').some(p => !p || p === '..' || p === '.')) throw Error('Unsafe relative destination: ' + relative);
  const target = path.resolve(root, relative);
  if (!target.startsWith(root + path.sep)) throw Error('Destination escapes project');
  let current = root;
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if (fs.existsSync(current) || (() => {try {fs.lstatSync(current);return true;} catch {return false;}})()) {
      const st = fs.lstatSync(current);
      if (st.isSymbolicLink() || fs.realpathSync(current) !== current) throw Error('Redirected destination: ' + relative);
      if (current !== target && !st.isDirectory()) throw Error('Not a directory: ' + current);
    }
  }
  return target;
}
function read(root, rel) {
  const p=safe(root,rel);
  if (!fs.existsSync(p)) return null;
  if (!fs.statSync(p).isFile()) throw Error('Expected a file: ' + rel);
  return fs.readFileSync(p);
}
function atomic(root, rel, bytes) {
  const p=safe(root,rel); fs.mkdirSync(path.dirname(p),{recursive:true});
  const temp=p+'.mathtrace-'+crypto.randomUUID();
  const fd=fs.openSync(temp,'wx');
  try {fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
  try {fs.renameSync(temp,p);} finally {if(fs.existsSync(temp))fs.unlinkSync(temp);}
}
function loadBundle(base) {
  base=fs.realpathSync(base);
  const manifest=JSON.parse(read(base,'payload/manifest.json'));
  const meta=JSON.parse(read(base,'package.json'));
  if (manifest.version!==meta.version || !meta.private || !/^v\d+\.\d+\.\d+$/.test(manifest.lean) || !manifest.files[manifest.wheel]) throw Error('Invalid or mismatched bundled release');
  if(meta.license!=='SEE LICENSE IN LICENSE'||meta.author!=='Velor-dev'||meta.scripts?.prepublishOnly!==`node -e "throw Error('Publication is outside this change')"`)throw Error('Invalid licensing or publication safeguards');
  for(const name of ['LICENSE']) {
    const source=read(base,name),copy=read(base,'payload/'+name);
    if(!source||!copy||!source.equals(copy)||!manifest.files[name]||!manifest.files['payload/'+name])throw Error('Missing or inconsistent legal file: '+name);
  }
  for (const [name,digest] of Object.entries(manifest.files)) {
    if (!/^[a-f0-9]{64}$/.test(digest) || sha(read(base,name))!==digest) throw Error('Bundled payload integrity failed: '+name);
  }
  return {base,manifest};
}
const BEGIN='<!-- MathTrace:begin -->', END='<!-- MathTrace:end -->';
function instructionSection(existing, content, previousHash) {
  const text=existing?.toString('utf8') || '';
  const start=text.indexOf(BEGIN), end=text.indexOf(END);
  const section=BEGIN+'\n'+content.trim()+'\n'+END;
  if (start<0 && end<0) {
    if (previousHash) throw Error('Owned MathTrace instruction section is missing');
    return {bytes:Buffer.concat([existing || Buffer.alloc(0),Buffer.from((text.endsWith('\n')||!text?'':'\n')+section+'\n')]),sectionHash:sha(section)};
  }
  if(start<0 || end<start || text.indexOf(BEGIN,start+1)>=0 || text.indexOf(END,end+1)>=0) throw Error('Malformed MathTrace instruction section');
  const old=text.slice(start,end+END.length);
  if(!previousHash || sha(old)!==previousHash) throw Error('Unowned or edited MathTrace instruction section');
  return {bytes:Buffer.from(text.slice(0,start)+section+text.slice(end+END.length)),sectionHash:sha(section)};
}
function allowed(rel) {
  return rel==='AGENTS.md' || rel==='.mathtrace/install.json' || rel==='.mathtrace/run.cjs'
    || /^\.mathtrace\/(docs|lib)\/[\w./-]+$/.test(rel)
    || /^coding-harnesses\/[\w./-]+$/.test(rel)
    || /^\.(agents|codex|claude|grok|cursor|opencode|pi|omp|devin|commandcode|cline|kilo|kimi-code|dsh|prime|clinerules)\/[\w./-]+$/.test(rel);
}
// Retain legacy notice destinations only to reconcile prior receipts safely.
function ownedDestination(rel,harness) {
  if(!allowed(rel))return false;
  return /^\.mathtrace\/docs\/(?:LICENSE|NOTICE\.txt|THIRD_PARTY_NOTICES\.txt|(?:coordination|completion|evidence|execution|evaluation|learning|native-capture)\.md)$/.test(rel)
    || rel==='.mathtrace/lib/bootstrap.py' || rel==='.mathtrace/run.cjs'
    || rel==='coding-harnesses/README.md' || rel==='coding-harnesses/catalog.json'
    || /^coding-harnesses\/shared\/(?:POLICY\.md|PROTOCOL\.md|help\.md|project-instructions\.md|skills\/math(?:trace-help|-[\w-]+)\/SKILL\.md|roles\/math-[\w-]+\.md)$/.test(rel)
    || (rel.startsWith(`coding-harnesses/${harness}/`) && /\/(?:README\.md|SETUP\.md|FALLBACK\.md|launch-settings\.json|config\.example\.yaml|skills\/math(?:trace-help|-[\w-]+)\/SKILL\.md)$/.test(rel))
    || /^\.[\w-]+\/(skills\/math(?:trace-help|-[\w-]+)\/SKILL\.md|agents\/math-[\w-]+(?:\/(?:agent\.md)|\.(?:md|toml|yaml))|agent\/skills\/math(?:trace-help|-[\w-]+)\/SKILL\.md)$/.test(rel)
    || rel==='.clinerules/mathtrace.md' || harness==='antigravity'&&['.agents/mcp_config.json','.agents/math/help.md','.agents/math/PROTOCOL.md'].includes(rel);
}
function receipt(root) {
  const raw=read(root,'.mathtrace/install.json'); if(!raw)return null;
  let value;try{value=JSON.parse(raw);}catch{throw Error('Malformed installation receipt');}
  if(value.schema!==1 || !value.files || !value.runtime || !value.harness || !value.project)throw Error('Malformed installation receipt');
  for(const [name,hash] of Object.entries(value.files))if(!ownedDestination(name,value.harness)||!(/^[a-f0-9]{64}$/).test(hash))throw Error('Unbounded installation receipt: '+name);
  safe(root,value.runtime);
  if(!value.runtime.startsWith('.mathtrace/runtime/'))throw Error('Invalid runtime location');
  return value;
}
function plan(root, desired, old) {
  const changes=[],owned={};
  for(const [name,bytes] of Object.entries(desired)) {
    if(!allowed(name))throw Error('Unapproved deployment destination: '+name);
    const current=read(root,name), digest=current && sha(current);
    if(old?.files[name] && digest!==old.files[name]) throw Error('Edited or missing owned file: '+name);
    if(current && !old?.files[name] && !current.equals(bytes))throw Error('Unowned file conflict: '+name);
    if(!current || old?.files[name])owned[name]=sha(bytes);
    if(!current?.equals(bytes))changes.push({name,before:current,after:bytes});
  }
  for(const [name,digest] of Object.entries(old?.files || {})) {
    if(name in desired)continue;
    const current=read(root,name);
    if(!current || sha(current)!==digest)throw Error('Edited obsolete owned file: '+name);
    changes.push({name,before:current,after:null});
  }
  return {changes,owned};
}
function recover(root) {
  const raw=read(root,'.mathtrace/journal.json'); if(!raw)return;
  const journal=JSON.parse(raw);
  if(journal.schema!==1 || !Array.isArray(journal.changes))throw Error('Invalid recovery journal');
  // Validate the entire rollback before restoring a single file.
  const items=journal.changes.map(c=>{
    if(!allowed(c.name))throw Error('Unsafe recovery destination');
    const before=c.before===null?null:Buffer.from(c.before,'base64'), after=c.after===null?null:Buffer.from(c.after,'base64');
    const current=read(root,c.name);
    const equals=(a,b)=>a===null?b===null:b!==null&&a.equals(b);
    if(!equals(current,before)&&!equals(current,after))throw Error('Recovery conflict; preserve local edits and inspect .mathtrace/journal.json: '+c.name);
    return {name:c.name,before};
  });
  for(const c of items.reverse()) {if(c.before===null){const p=safe(root,c.name);if(fs.existsSync(p))fs.unlinkSync(p);}else atomic(root,c.name,c.before);}
  fs.unlinkSync(safe(root,'.mathtrace/journal.json'));
}
function deploy(root,changes,hook=()=>{}) {
  if(changes.length===0){hook('activated');return;}
  const journal={schema:1,changes:changes.map(c=>({name:c.name,before:c.before?.toString('base64')??null,after:c.after?.toString('base64')??null}))};
  atomic(root,'.mathtrace/journal.json',Buffer.from(JSON.stringify(journal)));
  try {
    hook('journal');
    changes.forEach((c,i)=>{
      const current=read(root,c.name);
      if((current===null)!==(c.before===null) || (current && !current.equals(c.before)))throw Error('Destination changed during deployment: '+c.name);
      if(c.after===null)fs.unlinkSync(safe(root,c.name));else atomic(root,c.name,c.after);
      hook('write',i);
    });
    hook('activated');
    atomic(root,'.mathtrace/backups/'+crypto.randomUUID()+'.json',Buffer.from(JSON.stringify(journal)));
    fs.unlinkSync(safe(root,'.mathtrace/journal.json'));
  } catch(error) {recover(root);throw error;}
}
module.exports={sha,safe,read,atomic,loadBundle,instructionSection,receipt,plan,deploy,recover,ownedDestination};
