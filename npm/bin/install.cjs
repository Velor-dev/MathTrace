#!/usr/bin/env node
'use strict';
const path = require('node:path');
const {options, select} = require('../lib/selection.cjs');
async function main() {
  if (Number(process.versions.node.split('.')[0]) < 22) throw Error('Node 22+ is required');
  const args = options(process.argv.slice(2));
  if (args.help) {
    console.log('MathTrace project installer: [--harness <id>] [--python <executable>] [--host-executable <installed host>] [--codex-skills .codex/skills|.agents/skills]');
    return;
  }
  const {loadBundle, install} = require('../lib/install.cjs');
  const bundle = loadBundle(path.resolve(__dirname, '..'));
  args.harness ||= await select(bundle.manifest.harnesses);
  if (!args.harness) { console.log('Installation cancelled'); return; }
  const result = install(process.cwd(), bundle, args);
  console.log(JSON.stringify(result, null, 2));
}
main().catch(error => { console.error('MathTrace installation stopped: ' + error.message); process.exitCode = 1; });
