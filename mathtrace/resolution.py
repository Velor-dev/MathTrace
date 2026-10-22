"""Portable physical roots mapped to the existing exact manifest protocol."""
from copy import deepcopy
from pathlib import PureWindowsPath, PurePosixPath
from .store import StateError


def root_paths(roots, count):
    if not isinstance(roots, dict) or set(roots) != {'platform', 'stage', 'paths'}:
        raise StateError('Missing exact native staging descriptor')
    cls = PureWindowsPath if roots['platform'] == 'windows' else PurePosixPath
    if roots['platform'] not in ('windows', 'linux', 'darwin'):
        raise StateError('Unknown native path platform')
    stage = cls(roots['stage'])
    if not stage.is_absolute() or '..' in stage.parts:
        raise StateError('Invalid native staging root')
    expected = {'/toolchain': str(stage / 'toolchain'), '/replay': str(stage / 'replay')}
    expected.update({f'/libraries/{i}': str(stage / f'library-{i}') for i in range(count)})
    if roots['paths'] != expected:
        raise StateError('Native roots differ from recorder staging layout')
    return cls, expected


def normalized_resolution(report, resolved, roots, count):
    cls, paths = root_paths(roots, count)
    def physical(value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise StateError('Invalid native resolved path')
        p = cls(value)
        if not p.is_absolute() or '..' in p.parts or '.' in p.parts:
            raise StateError('Nonabsolute or traversing native resolved path')
        for role, path in paths.items():
            try:
                relative = p.relative_to(cls(path))
            except ValueError:
                continue
            # Manifest lookup remains exact, including file-name case.
            return role + ('/' + relative.as_posix() if relative.parts else '')
        raise StateError('Resolved path lies outside exact staged roots')
    report, resolved = deepcopy(report), deepcopy(resolved)
    native_channel = 'resolution reconstructed under byte-verified staged roots; not an open-file trace'
    native_binding = 'Lean resolution reconstructed under byte-verified staged roots and checked against staged bytes'
    if report.get('channel') != native_channel:
        raise StateError('Native resolution must disclose byte-verified staged roots')
    report['channel'] = 'resolution reconstructed under immutable roots; not an open-file trace'
    if resolved.get('channel') is not None:
        if resolved['channel'] != native_binding:
            raise StateError('Native binding must disclose staged-byte trust boundary')
        resolved['channel'] = 'Lean resolution reconstructed under immutable roots and checked against staged bytes'
    for value in (report, resolved):
        for key in ('reference_search_roots', 'candidate_search_roots', 'explicit_candidate_roots'):
            if key in value:
                value[key] = [physical(p) for p in value[key]]
    for scope in ('reference', 'candidate'):
        for entry in report[scope]:
            entry['base'] = physical(entry['base'])
            entry['parts'] = {k: physical(v) for k, v in entry['parts'].items()}
    # Bindings use stable role identities, not ephemeral absolute paths.
    return report, resolved
