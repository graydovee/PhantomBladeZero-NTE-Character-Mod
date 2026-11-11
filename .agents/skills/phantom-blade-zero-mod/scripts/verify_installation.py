"""Check the installed container against the build and the release package, and record the fingerprint."""
import hashlib
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import mod_profile

ROOT = mod_profile.ROOT
RELEASE = ROOT / 'Release'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sums_of(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if line.strip():
            value, name = line.split()
            result[name] = value
    return result


def main():
    profile = mod_profile.load()
    build = mod_profile.require_build_dir(profile)
    mod_id = profile.mod_id
    files = profile.container_files
    config = json.loads((RELEASE / 'data/config.json').read_text(encoding='utf-8'))
    installed_dir = Path(config['game_root']) / 'ProjectPBZ/Content/Paks/~mods'
    package_dir = RELEASE / 'Mods' / mod_id
    meta = json.loads((package_dir / 'mod.json').read_text(encoding='utf-8'))
    assert meta['id'] == mod_id, meta['id']
    build_sums = sums_of(build / 'container/SHA256SUMS.txt')
    release_sums = sums_of(package_dir / 'SHA256SUMS.txt')
    rows = []
    for name in files:
        installed = installed_dir / name
        assert installed.is_file(), installed
        actual = digest(installed)
        rows.append({'file': name, 'bytes': installed.stat().st_size, 'sha256': actual,
                     'matches_build': actual == build_sums[name],
                     'matches_release': actual == release_sums[name]})
    all_match = all(r['matches_build'] and r['matches_release'] for r in rows)
    assert all_match, rows
    extra = sorted(p.name for p in installed_dir.iterdir() if p.suffix.lower() in ('.pak', '.utoc', '.ucas')
                   and p.name not in files)
    report = {'mod_id': mod_id, 'version': meta['version'], 'build': profile.build_rel,
              'installed_dir': str(installed_dir),
              'installed_three_files_match_build_and_release': True,
              'unexpected_container_files': extra, 'files': rows}
    (build / 'installed_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('[ok] installed fingerprint verified for %s %s' % (mod_id, meta['version']))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
