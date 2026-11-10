# Workflow reference

## Semantic project map

| Purpose | Path |
|---|---|
| Workspace | 仓库根目录（可用 `PBZ_WORKSPACE_ROOT` 覆盖） |
| Current project | `Pipeline\native-zero` |
| Native reference data | `Pipeline\native-zero\reference` |
| Source input | `Pipeline\native-zero\model\zero` and `source` |
| UE project | `Pipeline\native-zero\unreal\ProjectPBZ` |
| Current build | `Builds\current` |
| Reusable scripts | `.agents\skills\phantom-blade-zero-mod\scripts` |
| Installer | `Release\PBZModKit-cli.exe` |
| Delivery package | `Release\Mods\zzz_NteZeroNative_P` |
| Blender | `Tools\blender\blender-4.5.15-windows-x64\blender.exe` |
| Extractor | `Tools\SkelDump\out\SkelDump.exe` |

## Investigation

```powershell
& Release\PBZModKit-cli.exe status
& Release\PBZModKit-cli.exe list
& Tools\SkelDump\out\SkelDump.exe find <game-paks> <aes> <usmap> Hun_Body_Simple
& Tools\SkelDump\out\SkelDump.exe meshrich <provider> <aes> <usmap> <package> <out.json>
& Tools\SkelDump\out\SkelDump.exe props <provider> <aes> <usmap> <package> <out.json>
```

Use `SKELDUMP_REFERENCE_PAKS` to provide original Paks as read-only reference data while auditing an isolated current container. Compare bone names and parents by name, then preserve the native spelling in the asset.

## Build stages

The canonical scripts are in `scripts/`:

- `bone_roles.py`, `build_native_mesh.py`, `fit_native_proportions.py`
- `build_texture_atlas.py`, `clean_native_asset.py`
- `refine_hand_weights.py`, `refine_neck_deformation_and_finger_length.py`, `audit_fingertip_axes.py`
- `audit_source_mesh.py`, `assemble_native_assets.py`, `package_native.py`
- `review_cooked_skin.py`, `audit_grip_deformation.py`, `review_grip_detail.py`
- `validate_cooked_mesh.py`, `validate_neck_deformation_and_finger_length.py`, `compare_cooked_grip.py`, `validate_grip_regression.py`
- `import_native_mesh.py`, `render_source_materials.py`, `make_native_blank.py`
- `stage_release.py`, `verify_installation.py`, `build_installer.ps1`, `watch_loader_log.py`

The current source checkpoint is `Pipeline\native-zero\source\SK_ZeroBody_posed.blend`. The actual native reference JSON is under `Pipeline\native-zero\reference`.

## UE and packaging

Use a fresh import name for every changed FBX. Select the native Skeleton at import, use the intended FBX importer, apply raw native reference transforms, and set full-precision UVs. Keep `ChaosClothAsset` and `StaticMesh` classes intact. Keep native Skeleton, PA, and MIs as dependencies and exclude them from the allowlist.

Cook the UE project under `Pipeline\native-zero\unreal`. Package the cooked allowlist into a three-file IoStore patch. Copy original global IoStore data into the current build directory only for offline parsing. Reverse-extract the final container before installation.

## Install and rollback

```powershell
if (Get-Process -Name PBZ -ErrorAction SilentlyContinue) { throw 'Exit game first' }
& Release\PBZModKit-cli.exe clean
& Release\PBZModKit-cli.exe install zzz_NteZeroNative_P
& Release\PBZModKit-cli.exe status
```

The installed directory must contain exactly `.pak`, `.utoc`, and `.ucas`. Compare SHA-256 across `Builds/current`, `Release/Mods`, and the game `~mods` directory. Keep a current manifest and a restore path through PBZModKit.
