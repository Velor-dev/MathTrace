"""Portable staging contracts; no host inference or installation."""
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from mathtrace.native import SKILLS


SOURCE = Path(__file__).resolve().parents[1] / "coding-harnesses"


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


class HarnessPayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "coding-harnesses"
        shutil.copytree(SOURCE, self.root)

    def render(self, *args):
        return subprocess.run([sys.executable, str(self.root / "render.py"), *args],
                              capture_output=True, text=True, encoding="utf-8")

    def test_entry_point_discovery_resolves_through_every_shared_adapter(self):
        harnesses = json.loads((self.root / 'research.json').read_text())['harnesses']
        for rendered in (False, True):
            if rendered:
                result = self.render()
                self.assertEqual(result.returncode, 0, result.stderr)
            for harness in harnesses:
                slug = harness['id']
                if slug == 'antigravity':
                    continue  # Native snapshot resolution has its own integrity check.
                locations = {harness['skill_dir']}
                if slug == 'codex':
                    locations.update({'.codex/skills', '.agents/skills'})
                for location in locations:
                    for name in ('math-intake', 'math-progress'):
                        with self.subTest(harness=slug, location=location, skill=name, rendered=rendered):
                            wrapper = (self.root / slug / location / name / 'SKILL.md').read_text()
                            shared_path = f'coding-harnesses/shared/skills/{name}/SKILL.md'
                            self.assertIn(f'then follow `{shared_path}`', wrapper)
                            self.assertIn('from the project root', wrapper)
                            self.assertIn('exact user arguments', wrapper)
                            self.assertIn('Use only the documented host binding', wrapper)
                            # Resolve references against the deployed target project, not the skill directory.
                            shared = (self.root.parent / shared_path).read_text()
                            for reference in re.findall(r'Read `([^`]+)`', shared):
                                self.assertTrue((self.root.parent / reference).is_file(), reference)
                            self.assertIn('Read `coding-harnesses/shared/PROTOCOL.md`', shared)
                            self.assertIn('Read `coding-harnesses/shared/help.md` directly from the project root', shared)
                            self.assertIn('current request and campaign state', shared)
                            self.assertIn('no mandatory sequence', shared)
                            self.assertIn("does not expand the request's scope", shared)
                            self.assertIn('Do not invoke `mathtrace-help` for discovery', shared)
                            self.assertTrue(shared.rstrip().endswith(SKILLS[name][1]))
        for role in (self.root / 'shared/roles').glob('*.md'):
            self.assertNotIn('shared/help.md', role.read_text())

    def test_antigravity_entry_point_paths_and_integrity(self):
        # Treat the staged payload as deployed at a target project's root.
        project = self.root / 'antigravity'
        manifest = json.loads((project / '.agents/math-runtime-manifest.json').read_text())
        for name in ('math-intake', 'math-progress'):
            with self.subTest(skill=name):
                relative = f'skills/{name}/SKILL.md'
                path = project / '.agents' / relative
                text = path.read_text()
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest['files'][relative])
                self.assertIn('Read `.agents/math/PROTOCOL.md`', text)
                self.assertIn('Read `.agents/math/help.md` directly from the project root', text)
                for reference in re.findall(r'Read `([^`]+)`', text):
                    self.assertTrue((project / reference).is_file(), reference)
                self.assertIn('no mandatory sequence', text)
                self.assertIn("does not expand the request's scope", text)
                self.assertIn('Do not invoke `mathtrace-help` for discovery', text)
                self.assertTrue(text.rstrip().endswith(SKILLS[name][1]))

    def test_native_profiles_preserve_roles_and_permission_dialects(self):
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        catalog = json.loads((self.root / "catalog.json").read_text())
        for slug, native, suffix in [("cline-cli", ".cline", ".yaml"),
                                     ("kimi-code", ".kimi-code", ".md"),
                                     ("opencode", ".opencode", ".md"),
                                     ("opencode-v2", ".opencode", ".md"),
                                     ("kilo", ".kilo", ".md"),
                                     ("devin", ".devin", ".md")]:
            agent_dir = self.root / slug / native / "agents"
            self.assertEqual({p.stem for p in agent_dir.glob("*" + suffix)}, set(catalog["roles"]))
            self.assertEqual(len(list((self.root / slug / native / "skills").glob("*/SKILL.md"))), 8)
            for role in catalog["roles"]:
                content = (agent_dir / (role + suffix)).read_text(encoding="utf-8")
                _, header, body = content.split("---\n", 2)
                self.assertEqual(body.lstrip("\n"), (self.root / "shared/roles" / (role + ".md")).read_text(encoding="utf-8"))
                for forbidden in ["providerId:", "modelId:", "reasoningEffort:", "skills:", "mainAgent:"]:
                    self.assertNotIn(forbidden, header)
                if slug in ("cline-cli", "kimi-code"):
                    self.assertIn("tools: []", header)
                if slug == "kimi-code":
                    self.assertIn("subagents: []", header)
                if slug == "opencode-v2":
                    self.assertIn('permissions:\n  - action: "*"\n    resource: "*"\n    effect: deny', header)
                    self.assertNotIn("permission:", header)
                if slug in ("opencode", "kilo"):
                    self.assertIn('permission:\n  "*": deny', header)
                    self.assertNotIn("permissions:", header)

    def test_codex_layout_and_owner_customizations_survive(self):
        result = self.render('--harness', 'codex')
        self.assertEqual(result.returncode, 0, result.stderr)
        for skill in (self.root / 'codex/.codex/skills').glob('*/SKILL.md'):
            companion = self.root / 'codex/.agents/skills' / skill.parent.name / 'SKILL.md'
            self.assertEqual(skill.read_text(), companion.read_text())
        import tomllib
        for agent in (self.root / 'codex/.codex/agents').glob('*.toml'):
            data = tomllib.loads(agent.read_text(encoding='utf-8'))
            self.assertEqual(set(data), {'name','description','developer_instructions'})
            shared = (self.root/'shared/roles'/agent.with_suffix('.md').name).read_text(encoding='utf-8')
            self.assertEqual(data['developer_instructions'], shared)
            self.assertIn('<codex_agent_role>', agent.with_suffix('.md').read_text())
        agent = self.root/'codex/.codex/agents/math-prover.toml'
        agent.write_text(agent.read_text() + '\n# Owner customization\n')
        content = agent.read_bytes()
        result = self.render('--harness','codex')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Preserved conflicting owner Codex payload',result.stderr)
        self.assertEqual(agent.read_bytes(),content)

    def test_render_is_repeatable_and_selected_render_preserves_other_harnesses(self):
        frozen = snapshot(self.root / "antigravity/.agents")
        shared = snapshot(self.root / "shared")
        self.assertEqual(self.render().returncode, 0)
        first = snapshot(self.root)
        self.assertEqual(self.render().returncode, 0)
        self.assertEqual(snapshot(self.root), first)
        # Make an unselected generated file observably different; it must survive selection.
        sentinel = self.root / "kimi-code/.kimi-code/agents/math-referee.md"
        sentinel.write_text("Unselected operator change", encoding="utf-8")
        before = snapshot(self.root)
        self.assertEqual(self.render("--harness", "cline-cli").returncode, 0)
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(snapshot(self.root / "antigravity/.agents"), frozen)
        self.assertEqual(snapshot(self.root / "shared"), shared)
