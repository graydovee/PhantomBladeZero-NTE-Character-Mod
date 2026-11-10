"""Check the installed container against the build and the release package, and record the fingerprint."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
BUILD = Path(os.environ.get('PBZ_BUILD_DIR', str(ROOT/'Builds/current')))
RELEASE = ROOT/'Release'
MOD_ID = 'zzz_NteZeroNative_P'
FILES = ('zzz_NteZeroNative_P.pak', 'zzz_NteZeroNative_P.utoc', 'zzz_NteZeroNative_P.ucas')


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


config = json.loads((RELEASE/'data/config.json').read_text(encoding='utf-8'))
installed_dir = Path(config['game_root'])/'ProjectPBZ/Content/Paks/~mods'
package_dir = RELEASE/'Mods'/MOD_ID
meta = json.loads((package_dir/'mod.json').read_text(encoding='utf-8'))
build_sums = sums_of(BUILD/'container/SHA256SUMS.txt')
release_sums = sums_of(package_dir/'SHA256SUMS.txt')
rows = []
for name in FILES:
    installed = installed_dir/name
    assert installed.is_file(), installed
    actual = digest(installed)
    rows.append({'file': name, 'bytes': installed.stat().st_size, 'sha256': actual,
                 'matches_build': actual == build_sums[name],
                 'matches_release': actual == release_sums[name]})
all_match = all(r['matches_build'] and r['matches_release'] for r in rows)
assert all_match, rows
extra = sorted(p.name for p in installed_dir.iterdir() if p.suffix.lower() in ('.pak', '.utoc', '.ucas')
               and p.name not in FILES)
report = {'version': meta['version'], 'installed_dir': str(installed_dir),
          'installed_three_files_match_build_and_release': True,
          'unexpected_container_files': extra, 'files': rows}
(BUILD/'installed_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('[ok] installed fingerprint verified for version ' + meta['version'])
print(json.dumps(report, ensure_ascii=False))
