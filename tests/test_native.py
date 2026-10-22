import json
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

from mathtrace.native import runtime_files, ROLES, SKILLS, ROOT_PROTOCOL, HELP_GUIDE
from tools.install_native import install


class NativeProjectionTests(unittest.TestCase):
    def test_entry_points_read_guide_without_changing_existing_contracts(self):
        files = runtime_files()
        self.assertEqual(files['math/PROTOCOL.md'], ROOT_PROTOCOL)
        self.assertEqual(files['math/help.md'], HELP_GUIDE)
        for name, (description, mandate) in SKILLS.items():
            text = files[f'skills/{name}/SKILL.md']
            self.assertTrue(text.endswith(mandate + '\n'))
            if name in {'math-intake', 'math-progress'}:
                self.assertIn('Read `.agents/math/PROTOCOL.md`', text)
                self.assertIn('Read `.agents/math/help.md` directly from the project root', text)
                self.assertIn('current request and campaign state', text)
                self.assertIn('no mandatory sequence', text)
                self.assertIn("does not expand the request's scope", text)
                self.assertIn('Do not invoke `mathtrace-help` for discovery', text)
            else:
                body = (mandate if name == 'mathtrace-help' else
                        f'# {description}\n\nRead `.agents/math/PROTOCOL.md` for the root execution contract.\n\n{mandate}')
                self.assertEqual(text.split('---\n\n', 1)[1], body + '\n')
        for path, text in files.items():
            if path.startswith('agents/'):
                self.assertNotIn('math/help.md', text)

    def test_all_workers_are_tool_free_and_inherit_host_model(self):
        files = runtime_files()
        agents = {p: text for p, text in files.items() if p.startswith('agents/')}
        self.assertEqual(len(agents), len(ROLES))
        for text in agents.values():
            frontmatter = text.split('---', 2)[1]
            self.assertIn('tools: []', frontmatter)
            self.assertIn('subagent: true', frontmatter)
            self.assertNotIn('model:', frontmatter)
            self.assertNotIn('invoke_subagent', frontmatter)

    def test_owned_install_has_no_stock_execution_paths(self):
        files = runtime_files()
        self.assertEqual(len([p for p in files if p.startswith('skills/')]), len(SKILLS))
        for text in files.values():
            for forbidden in ['gsd-core/bin', 'mempalace-', 'gsd-planner', 'model_profile', 'npx -y']:
                self.assertNotIn(forbidden, text)
        self.assertEqual(json.loads(files['mcp_config.json']), {'mcpServers': {}})

    def test_reinstall_preserves_bytes_and_archives_previous_owned_projection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = install(root)
            self.assertIsNone(first['archive'])
            expected = {p.relative_to(root / '.agents').as_posix(): p.read_bytes()
                        for p in (root / '.agents').rglob('*') if p.is_file()}
            second = install(root)
            with zipfile.ZipFile(second['archive']) as archive:
                self.assertEqual(set(archive.namelist()), set(expected))
                for path, content in expected.items():
                    self.assertEqual(archive.read(path), content)

    def test_unowned_changes_are_not_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install(root)
            custom = root / '.agents/keep-my-note.txt'
            custom.write_text('user work', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unreconciled'):
                install(root)
            self.assertEqual(custom.read_text(encoding='utf-8'), 'user work')

    def test_historical_stock_inventory_cannot_authorize_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            import hashlib
            root = Path(temp)
            note = root / '.agents/user-file.txt'
            note.parent.mkdir()
            note.write_text('user work', encoding='utf-8')
            baseline = root / '.planning/research/evidence/installation-baseline.json'
            baseline.parent.mkdir(parents=True)
            baseline.write_text(json.dumps([{'path': 'user-file.txt',
                'sha256': hashlib.sha256(note.read_bytes()).hexdigest()}]), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'unmanaged'):
                install(root)
            self.assertEqual(note.read_text(encoding='utf-8'), 'user work')

    def test_failed_replacement_restores_archived_projection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install(root)
            before = {p.relative_to(root / '.agents').as_posix(): p.read_bytes()
                      for p in (root / '.agents').rglob('*') if p.is_file()}
            with patch('tools.install_native.shutil.move', side_effect=OSError('simulated move failure')):
                with self.assertRaises(OSError):
                    install(root)
            after = {p.relative_to(root / '.agents').as_posix(): p.read_bytes()
                     for p in (root / '.agents').rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_failed_archive_write_leaves_projection_and_no_invalid_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install(root)
            before = {p.relative_to(root / '.agents').as_posix(): p.read_bytes()
                      for p in (root / '.agents').rglob('*') if p.is_file()}
            with patch('tools.install_native.zipfile.ZipFile.write', side_effect=OSError('archive write failure')):
                with self.assertRaises(OSError):
                    install(root)
            self.assertEqual(list((root / 'work/archives').glob('*.zip')), [])
            self.assertEqual(before, {p.relative_to(root / '.agents').as_posix(): p.read_bytes()
                                     for p in (root / '.agents').rglob('*') if p.is_file()})

    def test_managed_descendant_redirect_is_rejected_before_archiving(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install(root)
            managed = root / '.agents/mcp_config.json'
            original_is_symlink = Path.is_symlink
            with patch.object(Path, 'is_symlink', lambda p: p == managed or original_is_symlink(p)):
                with self.assertRaisesRegex(ValueError, 'Redirected descendant'):
                    install(root)
            self.assertFalse((root / 'work/archives').exists())

    def test_manifest_edits_cannot_claim_ownership_of_user_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install(root)
            custom = root / '.agents/user-file.txt'
            custom.write_text('user data', encoding='utf-8')
            manifest_path = root / '.agents/math-runtime-manifest.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            import hashlib
            manifest['files']['user-file.txt'] = hashlib.sha256(custom.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'manifest changed'):
                install(root)
            self.assertTrue(custom.is_file())

    def test_unknown_empty_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install(root)
            custom = root / '.agents/user-empty'
            custom.mkdir()
            with self.assertRaisesRegex(ValueError, 'Unreconciled'):
                install(root)
            self.assertTrue(custom.is_dir())

    def test_partial_replacement_failure_cleans_new_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install(root)
            def partial(source, destination):
                Path(destination).mkdir()
                (Path(destination) / 'partial-new.txt').write_text('partial')
                raise OSError('partial transfer failure')
            with patch('tools.install_native.shutil.move', side_effect=partial):
                with self.assertRaises(OSError):
                    install(root)
            self.assertFalse((root / '.agents/partial-new.txt').exists())
            self.assertEqual(list((root / 'work').glob('native-stage-*')), [])
