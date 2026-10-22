const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{spawnSync}=require('node:child_process');
test('launcher reports moved projects and missing interpreter without activation',t=>{
 const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'mathtrace-launch-')));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 fs.mkdirSync(path.join(root,'.mathtrace'));const script=path.join(root,'.mathtrace/run.cjs');fs.copyFileSync(path.join(__dirname,'../lib/run.cjs'),script);
 const receipt={project:root,runtime:'.mathtrace/runtime/test',basePython:path.join(root,'missing')};
 const check=()=>spawnSync(process.execPath,[script,'identity'],{cwd:root,encoding:'utf8'});
 fs.writeFileSync(path.join(root,'.mathtrace/install.json'),JSON.stringify(receipt));assert.match(check().stderr,/Python is unavailable/);
 receipt.project=root+'-moved';fs.writeFileSync(path.join(root,'.mathtrace/install.json'),JSON.stringify(receipt));assert.match(check().stderr,/Project moved/);
 assert.deepEqual(fs.readdirSync(root),['.mathtrace']);
});
