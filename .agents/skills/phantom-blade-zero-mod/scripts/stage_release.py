"""Stage the release package, verify its hashes, and rebuild the distribution archives."""
import argparse
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
CONTAINER_FILES = ('zzz_NteZeroNative_P.pak', 'zzz_NteZeroNative_P.utoc', 'zzz_NteZeroNative_P.ucas')
MANUAL_README = r"""Phantom Blade Zero - Zero (Neverness to Everness) protagonist replacement
Manual installation (no installer needed)

1. Fully exit Phantom Blade Zero.
2. Open your game folder, e.g.
   ...\SteamLibrary\steamapps\common\Phantom Blade Zero\
   It must contain ProjectPBZ\Content\Paks
3. Create the folder ProjectPBZ\Content\Paks\~mods if it does not exist.
4. Copy the three files from {mod_id}\ into that ~mods folder:
   {pak}
   {utoc}
   {ucas}
5. Launch the game. The protagonist is now Zero.

Uninstall: delete those three files from ~mods.
"""


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', default=str(ROOT/'Builds/current'))
    ap.add_argument('--release-root', default=str(ROOT/'Release'))
    ap.add_argument('--version', required=True)
    ap.add_argument('--no-zips', action='store_true')
    args = ap.parse_args()
    build = Path(args.build)
    release = Path(args.release_root)
    container = build/'container'
    mod_id = json.loads((release/'Mods/zzz_NteZeroNative_P/mod.json').read_text(encoding='utf-8'))['id']
    target = release/'Mods'/mod_id
    target.mkdir(parents=True, exist_ok=True)

    sums = {}
    for name in CONTAINER_FILES:
        src = container/name
        assert src.is_file(), src
        shutil.copy2(src, target/name)
        sums[name] = digest(src)
        assert digest(target/name) == sums[name], f'copy mismatch {name}'
        recorded = [line.split()[0] for line in (container/'SHA256SUMS.txt').read_text().splitlines()
                    if line.endswith(name)]
        assert recorded and recorded[0] == sums[name], f'container SHA256SUMS disagrees for {name}'
    (target/'SHA256SUMS.txt').write_text(''.join(f'{h}  {n}\n' for n, h in sums.items()), encoding='utf-8')
    shutil.copy2(build/'production_allowlist.json', target/'allowlist.json')
    (target/'README.txt').write_text(MANUAL_README.format(mod_id=mod_id, pak=CONTAINER_FILES[0],
                                                          utoc=CONTAINER_FILES[1],
                                                          ucas=CONTAINER_FILES[2]), encoding='utf-8')

    meta_path = target/'mod.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else {}
    meta.update({'id': mod_id, 'version': args.version, 'author': 'graydovee', 'target': 'hero',
                 'bones': 264, 'source_build': 'Builds/current',
                 'files': list(CONTAINER_FILES)})
    meta.pop('updated', None)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for name in CONTAINER_FILES:
        assert digest(target/name) == sums[name]
    print('[ok] staged ' + str(target) + ' version ' + args.version)

    if args.no_zips:
        return
    def write_zip(path, entries):
        path.unlink(missing_ok=True)
        for source, arcname in entries:
            source = Path(source)
            assert source.is_file(), source
            with zipfile.ZipFile(path, 'a', zipfile.ZIP_DEFLATED) as archive:
                archive.write(source, arcname)
        print('[ok] ' + path.name)

    write_zip(ROOT/f'{mod_id}-v{args.version}.zip',
              [(p, f'{mod_id}/{p.name}') for p in [target/'allowlist.json', target/'mod.json',
                                                   target/'README.md', target/'SHA256SUMS.txt']
               + [target/n for n in CONTAINER_FILES]])
    mod_archive = [target/'allowlist.json', target/'mod.json', target/'README.md', target/'SHA256SUMS.txt'] \
        + [target/n for n in CONTAINER_FILES]
    reference = release/'Mods/zzz_Hcxmmx2B_Retarget_P'
    write_zip(ROOT/f'PhantomBladeZero-NTE-Zero-Mod-v{args.version}.zip',
              [(release/'PBZModKit.exe', 'PBZModKit.exe'),
               (release/'PBZModKit-cli.exe', 'PBZModKit-cli.exe'),
               (release/'使用说明.md', '使用说明.md')]
              + [(p, f'Mods/{mod_id}/{p.name}') for p in mod_archive]
              + [(p, f'Mods/{reference.name}/{p.name}') for p in sorted(reference.iterdir()) if p.is_file()])
    write_zip(ROOT/f'PhantomBladeZero-NTE-Zero-Nexus-v{args.version}.zip',
              [(release/'PBZModKit.exe', 'PBZModKit.exe')]
              + [(p, f'Mods/{mod_id}/{p.name}') for p in [target/'allowlist.json', target/'mod.json',
                                                          target/'README.md', target/'SHA256SUMS.txt']
                 + [target/n for n in CONTAINER_FILES]])
    for path, prefix in ((ROOT/f'{mod_id}-v{args.version}.zip', f'{mod_id}/'),
                         (ROOT/f'PhantomBladeZero-NTE-Zero-Mod-v{args.version}.zip', f'Mods/{mod_id}/'),
                         (ROOT/f'PhantomBladeZero-NTE-Zero-Nexus-v{args.version}.zip', f'Mods/{mod_id}/')):
        with zipfile.ZipFile(path) as archive:
            inside = hashlib.sha256(archive.read(prefix+CONTAINER_FILES[0])).hexdigest()
        assert inside == sums[CONTAINER_FILES[0]], path
    print('[ok] archives written for ' + args.version)



if __name__ == '__main__':
    main()
