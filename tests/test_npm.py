"""Inspect the packed archive and exercise its standalone runtime assets."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from tools.build_npm import assemble, validate_archive
from tools.package_runtime import ROOT, LEGAL_FILES


class NpmPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.package = assemble(cls.root / 'release')
        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        result = subprocess.run([npm, 'pack', '--ignore-scripts', '--json', '--cache', str(cls.root / 'cache')],
                                cwd=cls.package, capture_output=True, text=True, check=True)
        cls.archive = cls.package / json.loads(result.stdout)[0]['filename']
        validate_archive(cls.archive)
        cls.extracted = cls.root / 'extracted'
        with tarfile.open(cls.archive) as archive:
            archive.extractall(cls.extracted, filter='data')

    def test_actual_tarball_has_hidden_assets_and_no_workspace_data(self):
        with tarfile.open(self.archive) as z:
            names = z.getnames()
        self.assertIn('package/payload/coding-harnesses/codex/.codex/agents/math-prover.toml', names)
        self.assertIn('package/payload/coding-harnesses/codex/.codex/skills/math-intake/SKILL.md', names)
        self.assertFalse(any('/.math/' in n or '/work/' in n or '/.venv/' in n or '/.kimi/' in n or 'openspec-' in n or '/__pycache__/' in n or n.endswith(('.pyc', '.pyo')) for n in names))
        self.assertNotIn(b'\r\n', (self.extracted / 'package/bin/install.cjs').read_bytes())
        for obsolete in ('NOTICE.txt', 'THIRD_PARTY_NOTICES.txt', 'THIRD_PARTY_NOTICES.md'):
            self.assertFalse((self.extracted / ('package/' + obsolete)).exists())
            self.assertFalse((self.extracted / ('package/payload/' + obsolete)).exists())
        for name in LEGAL_FILES:
            for prefix in ('package/', 'package/payload/'):
                self.assertEqual((self.extracted / (prefix + name)).read_bytes(), (ROOT / name).read_bytes())

    def test_legal_files_metadata_and_safeguards_with_rehashed_archive(self):
        import hashlib
        import io
        with tarfile.open(self.archive) as z:
            original = {m.name: z.extractfile(m).read() for m in z.getmembers()}
        mutations = []
        for name in LEGAL_FILES:
            for prefix in ('package/', 'package/payload/'):
                mutations.extend([(prefix + name, None), (prefix + name, b'changed terms')])
        meta = json.loads(original['package/package.json'])
        for key, value in [('license', 'MIT'), ('author', 'Other'), ('private', True),
                           ('scripts', {**meta['scripts'], 'prepublishOnly': 'echo publish'})]:
            mutations.append(('package/package.json', json.dumps({**meta, key: value}).encode()))
        # A changed nested wheel must fail even if its npm manifest hash is valid.
        import zipfile
        wheel_name = 'package/' + json.loads(original['package/payload/manifest.json'])['wheel']
        data = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(original[wheel_name])) as source, zipfile.ZipFile(data, 'w') as target:
            for name in source.namelist():
                content = source.read(name)
                if name.endswith('/licenses/LICENSE'):
                    content = b'changed terms'
                target.writestr(name, content)
        mutations.append((wheel_name, data.getvalue()))
        for member, content in mutations:
            with self.subTest(member=member, content=content if member.endswith('json') else bool(content)):
                files = dict(original)
                if content is None:
                    del files[member]
                else:
                    files[member] = content
                manifest = json.loads(files['package/payload/manifest.json'])
                manifest['files'] = {n.removeprefix('package/'): hashlib.sha256(b).hexdigest()
                                     for n, b in files.items() if n != 'package/payload/manifest.json'}
                files['package/payload/manifest.json'] = json.dumps(manifest).encode()
                path = self.root / 'bad.tgz'
                with tarfile.open(path, 'w:gz') as z:
                    for name, data in files.items():
                        item = tarfile.TarInfo(name); item.size = len(data)
                        z.addfile(item, io.BytesIO(data))
                with self.assertRaises(ValueError):
                    validate_archive(path)

    def test_bundle_integrity_and_version_mismatch(self):
        script = "const f=require(process.argv[1]); f.loadBundle(process.argv[2]);"
        module = str(self.extracted / 'package/lib/files.cjs')
        subprocess.run(['node', '-e', script, module, str(self.extracted / 'package')], check=True)
        meta = self.extracted / 'package/package.json'
        original = meta.read_bytes()
        for field, value in [('version', '9.0.0'), ('private', True),
                             ('scripts', {'prepublishOnly': 'echo publish'})]:
            with self.subTest(field=field):
                data = json.loads(original); data[field] = value; meta.write_text(json.dumps(data))
                try:
                    result = subprocess.run(['node', '-e', script, module, str(self.extracted / 'package')], capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
                finally:
                    meta.write_bytes(original)

    def test_publication_requires_assembled_verified_payload(self):
        meta = json.loads((ROOT / 'npm/package.json').read_text())
        self.assertIs(meta['private'], False)
        self.assertEqual(meta['publishConfig']['registry'], 'https://registry.npmjs.org/')
        self.assertEqual(meta['publishConfig']['access'], 'public')
        command = "require('./lib/files.cjs').loadBundle(process.cwd())"
        self.assertEqual(meta['scripts']['prepublishOnly'], 'node -e "' + command + '"')
        result = subprocess.run(['node', '-e', command], cwd=ROOT / 'npm', capture_output=True)
        self.assertNotEqual(result.returncode, 0)  # Source directory has no assembled payload.
        result = subprocess.run(['node', '-e', command], cwd=self.extracted / 'package', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_every_harness_mapping_and_required_guide_resolves(self):
        script = r"""
const fs=require('node:fs'),path=require('node:path');
const base=process.argv[1],root=fs.realpathSync(process.argv[2]);
const {loadBundle,mapping}=require(path.join(base,'lib/install.cjs'));
const {ownedDestination}=require(path.join(base,'lib/files.cjs'));
const b=loadBundle(base);
for(const h of b.manifest.harnesses){
 const {desired,merged}=mapping(root,b,{harness:h.id},null);
 for(const name of ['LICENSE']){
  if(!desired['.mathtrace/docs/'+name]?.equals(fs.readFileSync(path.join(base,name))))throw Error('legal file differs: '+h.id+' '+name);
 }
 for(const link of desired['coding-harnesses/README.md'].toString().matchAll(/\]\(([^)]+)\)/g)){
  if(link[1].includes('://'))continue;
  const target=path.posix.normalize(path.posix.join('coding-harnesses',link[1]));
  if(!desired[target])throw Error('installed overview reference missing '+target);
 }
 let references=0;
 for(const [name,bytes] of Object.entries(desired)){
  if(!ownedDestination(name,h.id))throw Error('unbounded '+h.id+' destination '+name);
  if(!name.endsWith('.md'))continue;
  for(const m of bytes.toString().matchAll(/(?:Read|follow) `([^`]+(?:SKILL|PROTOCOL|help|POLICY|README)\.md)`/g)){
   references++;
   if(!desired[m[1]])throw Error(h.id+' missing root reference '+m[1]);
  }
 }
 if(references<8)throw Error('No meaningful guide reference coverage for '+h.id);
 if(h.id==='codex' && Object.keys(desired).some(n=>n.startsWith('.agents/skills/')))throw Error('duplicate compatibility skills');
 if(h.id==='antigravity'){
  const help='.agents/math/help.md';
  for(const match of desired[help].toString().matchAll(/\]\(([^)]+)\)/g)){
   if(match[1].includes('://')||match[1].startsWith('#'))continue;
   const target=path.posix.normalize(path.posix.join(path.posix.dirname(help),match[1]));
   if(!desired[target]&&!(target==='AGENTS.md'&&merged.bytes.length))throw Error('native guide link missing '+target);
  }
  for(const name of Object.keys(desired).filter(n=>n.startsWith('.agents/agents/'))){
   const source=fs.readFileSync(path.join(base,'payload/coding-harnesses/antigravity',name));
   if(!source.equals(desired[name]))throw Error('changed native role');
  }
 }
}
"""
        project = self.root / 'mapping project'; project.mkdir(exist_ok=True)
        subprocess.run(['node', '-e', script, str(self.extracted / 'package'), str(project)], check=True)

    def test_packed_installer_in_independent_projects(self):
        environment = dict(os.environ, MATHTRACE_TEST_PACKAGE=str(self.extracted / 'package'),
                           MATHTRACE_TEST_PYTHON=sys.executable,
                           MATHTRACE_TEST_TOOLCHAIN=str(ROOT / 'tests/fixtures/installer_toolchain.py'))
        result = subprocess.run(['node', '--test', str(ROOT / 'npm/test/integration.test.cjs')],
                                env=environment, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_codex_compatibility_native_conflicts_and_harness_switches(self):
        script = r"""
const fs=require('node:fs'),path=require('node:path');
const {loadBundle,mapping}=require(path.join(process.argv[1],'lib/install.cjs'));
const F=require(path.join(process.argv[1],'lib/files.cjs'));
const root=fs.realpathSync(process.argv[2]),bundle=loadBundle(process.argv[1]);
const name='.agents/skills/math-intake/SKILL.md';
F.atomic(root,name,F.read(bundle.base,'payload/coding-harnesses/codex/'+name));
const m=mapping(root,bundle,{harness:'codex'},null);
if(m.codexSkills!=='.agents/skills'||Object.keys(m.desired).some(n=>n.startsWith('.codex/skills/')))throw Error('compatibility location not preserved');
const agent='.codex/agents/math-prover.toml';F.atomic(root,agent,Buffer.from('owner customized agent'));
let rejected=false;try{F.plan(root,m.desired,null);}catch(e){rejected=/Unowned/.test(e.message);}if(!rejected)throw Error('owner conflict missed');
if(F.read(root,agent).toString()!=='owner customized agent')throw Error('owner changed');
F.atomic(root,'.agents/math-runtime-manifest.json',Buffer.from('{}'));
for(const harness of ['codex','antigravity']){
 let caught=false;try{mapping(root,bundle,{harness},null);}catch{caught=true;}if(!caught)throw Error('managed native collision missed');
}
let caught=false;try{mapping(root,bundle,{harness:'opencode-v2'},{harness:'opencode'});}catch{caught=true;}if(!caught)throw Error('exclusive OpenCode switch permitted');
"""
        project = self.root / 'compatibility project'; project.mkdir(exist_ok=True)
        subprocess.run(['node', '-e', script, str(self.extracted / 'package'), str(project)], check=True)
