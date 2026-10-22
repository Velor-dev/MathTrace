#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
try {
  const root=path.resolve(__dirname,'..');
  const receipt=JSON.parse(fs.readFileSync(path.join(__dirname,'install.json'),'utf8'));
  if(receipt.project!==fs.realpathSync(root))throw Error('Project moved; recreate its private runtime by rerunning the installer');
  const runtime=path.resolve(root,receipt.runtime);
  if(!runtime.startsWith(path.join(root,'.mathtrace/runtime')+path.sep))throw Error('Invalid runtime location');
  const executable=path.join(runtime,process.platform==='win32'?'Scripts/python.exe':'bin/python');
  if(!fs.existsSync(executable)||!fs.existsSync(receipt.basePython))throw Error('Owned/base Python is unavailable; recreate the private runtime by reinstalling');
  const result=spawnSync(executable,['-I','-m','mathtrace',...process.argv.slice(2)],{cwd:root,stdio:'inherit',windowsHide:true});
  if(result.error)throw result.error;
  process.exitCode=result.status ?? 1;
}catch(error){console.error(error.message);process.exitCode=1;}
