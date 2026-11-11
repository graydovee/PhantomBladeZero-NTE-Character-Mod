"""Package the declared cooked assets as an IoStore patch and SHA-256 manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import mod_profile

WORKSPACE = mod_profile.ROOT
ROOT = WORKSPACE / "Pipeline" / "native-zero"
PROJECT = ROOT / "unreal" / "ProjectPBZ"
COOKED = PROJECT / "Saved" / "Cooked" / "Windows"


def main() -> int:
    profile = mod_profile.load()
    ap = argparse.ArgumentParser()
    ap.add_argument("--unreal-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=None,
                    help="container output directory (default: <build>/container)")
    ap.add_argument("--allowlist", type=Path, default=None,
                    help="allowlist (default: <build>/production_allowlist.json, else tools/cook-allowlist.json)")
    ap.add_argument("--version", required=True)
    args = ap.parse_args()

    output = args.output or profile.container_dir
    allowlist = args.allowlist
    if allowlist is None:
        staged = profile.build / "production_allowlist.json"
        allowlist = staged if staged.is_file() else ROOT / "tools" / "cook-allowlist.json"

    exe = args.unreal_root / "Engine" / "Binaries" / "Win64" / "UnrealPak.exe"
    if not exe.is_file():
        raise SystemExit("UnrealPak not found: %s" % exe)
    if not COOKED.is_dir():
        raise SystemExit("cooked dir not found: %s" % COOKED)
    if not allowlist.is_file():
        raise SystemExit("allowlist not found: %s" % allowlist)

    name = profile.mod_id
    allow = json.loads(allowlist.read_text(encoding="utf-8"))
    if not isinstance(allow, list) or not allow or len(allow) != len(set(allow)):
        raise SystemExit("allowlist must be a nonempty list without duplicates")
    for rel in allow:
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts or not rel.endswith('.uasset'):
            raise SystemExit("invalid allowlist path: " + rel)
        if path.stem.startswith(('MI_', 'MA_', 'MAI_')) or path.stem.endswith(('_Skeleton', 'PhysicsAsset')) or path.stem == mod_profile.CONTRACT['physics_asset']:
            raise SystemExit("native dependency path is outside the release allowlist: " + rel)
    output.mkdir(parents=True, exist_ok=True)
    missing = []
    files = []
    for rel in allow:
        f = COOKED / "ProjectPBZ" / rel
        if not f.is_file():
            missing.append(rel)
            continue
        files.append(f)
        for ext in (".uexp", ".ubulk", ".uptnl"):
            side = f.with_suffix(ext)
            if side.is_file():
                files.append(side)
    if missing:
        raise SystemExit("allowlisted assets were not cooked: " + ", ".join(missing))
    if not files:
        raise SystemExit("nothing to package")

    with tempfile.TemporaryDirectory(prefix="character-mod-package-") as tmp:
        t = Path(tmp)
        stage = t / "stage" / "ProjectPBZ" / "Content" / "Paks" / "~mods"
        stage.mkdir(parents=True, exist_ok=True)

        response = t / "response.txt"
        response.write_text("\n".join(
            f'"{f.as_posix()}" "../../../{f.relative_to(COOKED).as_posix()}"' for f in files),
            encoding="utf-8")
        commands = t / "commands.txt"
        commands.write_text(
            f'-Output="{(stage / (name + ".utoc")).as_posix()}" -ContainerName={name} '
            f'-ResponseFile="{response.as_posix()}"\n', encoding="utf-8")

        cmd = [str(exe), str(PROJECT / "ProjectPBZ.uproject"),
               f"-CreateGlobalContainer={t / 'global.utoc'}",
               f"-CookedDirectory={COOKED}",
               f"-Commands={commands}",
               f"-PackageStoreManifest={COOKED / 'ProjectPBZ/Metadata/packagestore.manifest'}",
               f"-ScriptObjects={COOKED / 'ProjectPBZ/Metadata/scriptobjects.bin'}",
               "-TargetPlatform=Windows", "-unattended"]
        print("[1/2] UnrealPak -CreateGlobalContainer")
        subprocess.run(cmd, check=True)

        marker = t / "marker.txt"
        marker.write_text(name + " " + args.version + "\n", encoding="utf-8")
        mr = t / "marker-response.txt"
        mr.write_text(f'"{marker.as_posix()}" "../../../ProjectPBZ/Content/NativeZero/marker.txt"\n',
                      encoding="utf-8")
        print("[2/2] UnrealPak marker pak")
        subprocess.run([str(exe), str(stage / (name + ".pak")), f"-Create={mr}"], check=True)

        produced = sorted(stage.glob(name + ".*"))
        if len(produced) < 3:
            raise SystemExit("incomplete output: %s" % [p.name for p in produced])
        for p in produced:
            shutil.copy2(p, output / p.name)
            print("[ok] %s %.2f MB" % (p.name, p.stat().st_size / 1024 / 1024))

    container = profile.container_files
    for suffix in (".pak", ".utoc", ".ucas"):
        for p in output.glob("*" + suffix):
            if p.name not in container:
                p.unlink()
                print("[--] removed stale container file %s" % p.name)
    sums = output / "SHA256SUMS.txt"
    with sums.open("w", encoding="utf-8") as fh:
        for p in sorted(output.glob(name + ".*")):
            fh.write("%s  %s\n" % (hashlib.sha256(p.read_bytes()).hexdigest(), p.name))
    print("[ok] SHA256SUMS.txt")
    print("[ok] container %s -> %s" % (name, output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
