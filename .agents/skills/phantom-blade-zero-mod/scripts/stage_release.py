"""Stage the release package, verify its hashes, and rebuild the distribution archives."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import mod_profile

ROOT = mod_profile.ROOT

MANUAL_README = r"""{title} ({mod_id}) {version}
{description}

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
5. Launch the game. The protagonist is replaced.

Uninstall: delete those three files from ~mods.

Only one protagonist replacement can be installed at a time: uninstall the other
character MOD first (they share the same hero slot).
"""

MANUAL_README_MD = r"""# {title}

{description}

- MOD id: `{mod_id}`
- version: `{version}`
- target: `hero`

## Install / 安装

1. 完全退出游戏（Phantom Blade Zero）。
2. 打开游戏目录（需包含 `ProjectPBZ\Content\Paks`）。
3. 若无 `ProjectPBZ\Content\Paks\~mods` 目录则新建。
4. 把 `{mod_id}` 目录下的三个文件复制进 `~mods`：
   `{pak}`、`{utoc}`、`{ucas}`。
5. 启动游戏即生效。也可用 `PBZModKit.exe` 安装。

卸载：删除 `~mods` 下的这三个文件，或用 PBZModKit 卸载。

同一时间只能安装一个主角替换 MOD（同属 `hero` 槽位），切换角色前先卸载另一个。
"""


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    profile = mod_profile.load()
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', default=None, help='build directory (default: profile build)')
    ap.add_argument('--release-root', default=str(ROOT / 'Release'))
    ap.add_argument('--version', required=True)
    ap.add_argument('--no-zips', action='store_true')
    args = ap.parse_args()
    build = Path(args.build) if args.build else mod_profile.build_dir(profile)
    release = Path(args.release_root)
    container = build / 'container'
    mod_id = profile.mod_id
    files = profile.container_files
    target = release / 'Mods' / mod_id
    target.mkdir(parents=True, exist_ok=True)

    sums = {}
    for name in files:
        src = container / name
        assert src.is_file(), src
        shutil.copy2(src, target / name)
        sums[name] = digest(src)
        assert digest(target / name) == sums[name], f'copy mismatch {name}'
        recorded = [line.split()[0] for line in (container / 'SHA256SUMS.txt').read_text().splitlines()
                    if line.endswith(name)]
        assert recorded and recorded[0] == sums[name], f'container SHA256SUMS disagrees for {name}'
    for stale in sorted(target.iterdir()):
        if stale.is_file() and stale.suffix.lower() in ('.pak', '.utoc', '.ucas') and stale.name not in files:
            stale.unlink()
            print('[--] removed stale container file ' + stale.name)
    with (target / 'SHA256SUMS.txt').open('w', encoding='utf-8') as fh:
        for n, h in sums.items():
            fh.write(h + '  ' + n + chr(10))
    shutil.copy2(build / 'production_allowlist.json', target / 'allowlist.json')
    fields = dict(title=profile.title, mod_id=mod_id, version=args.version, description=profile.description,
                  pak=files[0], utoc=files[1], ucas=files[2])
    (target / 'README.txt').write_text(MANUAL_README.format(**fields), encoding='utf-8')
    (target / 'README.md').write_text(MANUAL_README_MD.format(**fields), encoding='utf-8')

    meta_path = target / 'mod.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else {}
    meta.update({'id': mod_id, 'name': profile.title, 'description': profile.description,
                 'version': args.version, 'author': mod_profile.CONTRACT['author'],
                 'target': mod_profile.CONTRACT['target'],
                 'requires_build': mod_profile.CONTRACT['requires_build'],
                 'bones': mod_profile.CONTRACT['bones'], 'source_build': profile.build_rel,
                 'files': list(files)})
    meta.pop('updated', None)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + chr(10), encoding='utf-8')
    for name in files:
        assert digest(target / name) == sums[name]
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

    names = profile.zip_names(args.version)
    mod_archive = [target / 'allowlist.json', target / 'mod.json', target / 'README.md',
                   target / 'README.txt', target / 'SHA256SUMS.txt'] + [target / n for n in files]
    write_zip(ROOT / names['mod'], [(p, f'{mod_id}/{p.name}') for p in mod_archive])
    reference = release / 'Mods/zzz_Hcxmmx2B_Retarget_P'
    bundle = [(release / 'PBZModKit.exe', 'PBZModKit.exe'),
              (release / 'PBZModKit-cli.exe', 'PBZModKit-cli.exe'),
              (release / '使用说明.md', '使用说明.md')] + [(p, f'Mods/{mod_id}/{p.name}') for p in mod_archive]
    if reference.is_dir():
        bundle += [(p, f'Mods/{reference.name}/{p.name}') for p in sorted(reference.iterdir()) if p.is_file()]
    write_zip(ROOT / names['bundle'], bundle)
    write_zip(ROOT / names['nexus'],
              [(release / 'PBZModKit.exe', 'PBZModKit.exe')]
              + [(p, f'Mods/{mod_id}/{p.name}') for p in mod_archive])
    for key, prefix in (('mod', f'{mod_id}/'), ('bundle', f'Mods/{mod_id}/'), ('nexus', f'Mods/{mod_id}/')):
        path = ROOT / names[key]
        with zipfile.ZipFile(path) as archive:
            inside = hashlib.sha256(archive.read(prefix + files[0])).hexdigest()
        assert inside == sums[files[0]], path
    print('[ok] archives written for ' + args.version)


if __name__ == '__main__':
    main()
