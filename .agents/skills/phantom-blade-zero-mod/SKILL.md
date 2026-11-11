---
name: phantom-blade-zero-mod
description: Build, repair, validate, package, install, and document UE5 Phantom Blade Zero character replacement mods with the native game skeleton. Use for skeletal mesh retargeting, materials, carrier assets, IoStore packaging, PBZModKit installation, and runtime evidence.
---

# Phantom Blade Zero Mod

Use this skill for the complete character replacement workflow in Phantom Blade Zero. The result includes the character mesh, native skeleton compatibility, animation deformation, materials, weapon interaction, class-correct carrier assets, IoStore package, PBZModKit installation, and runtime evidence.

Read `AGENTS.md`, `Docs/current-state.md`, and `Docs/task.md` before changing files. Each character is a profile under `Pipeline/native-zero/mods/<profile>.json`, written to `Builds/<profile>/current`; use this skill's `scripts/` as the reusable script entrypoint. The user supplies runtime screenshots; the skill handles assets, offline QA, packaging, and installer commands.

## Characters and profiles

- `mod_profile.py` is the single source of truth: MOD id, character title, build directory, release directory, source model, pose checkpoint, mesh object, atlas layout, and the shared native contract (skeleton, PhysicsAsset, material instance, texture stem, bone count).
- `PBZ_MOD` selects the profile (default `zero`); `PBZ_BUILD_DIR` overrides its build directory. Every script resolves paths through the profile, so one pipeline serves every character.
- MOD ids match `^zzz_Nte_[A-Za-z]+_P$`, releases live in `Release/Mods/<MOD id>/`, and distribution archives are named by `Profile.zip_names()`.
- Only one character MOD can be installed at a time: all of them replace the same hero. Uninstall the current one before installing another.

## Current design

- Use the game's native `Hun_Skin_Skeleton` and playable leader path.
- Keep native Skeleton, PhysicsAsset, and game material instances as dependencies.
- Reuse the single verified material route: the game's `MI_ZeroHun_Cap_01_b` with `T_ZeroHun_Cap_V02_{BC,N,ARM}` paths; only the texture contents change per character.
- Treat runtime screenshots and loader evidence as acceptance evidence. Offline reports are release gates.

## Workflow

1. Inventory the clean game Paks and extract exact package classes, native reference bones, section BoneMaps, raw weights, materials, and Skeleton translation modes.
2. Prepare the artist-weighted source mesh in centimetres, export one `root` armature, preserve authored volume, keep one UV layer, apply transforms, and map native bone roles deterministically.
3. Fit only the native `AnimationScaled` bone lengths, preserve native rotations/parents and `Animation` translations, orient palms with joint direction plus finger spread, and aim each finger segment by joint positions.
4. Keep four or fewer normalized influences. Smooth only the affected hand/finger seams and synchronize coincident UV/normal split vertices.
5. Build a deterministic single UV atlas over the game's real material instances. Preserve alpha and data-map color spaces.
6. Import fresh skeletal assets with the native Skeleton, apply raw native reference transforms, set full-precision UVs, and create class-correct skeletal/static/Chaos Cloth assets.
7. Cook only intended paths. Package with a fail-closed allowlist, marker, and SHA-256 manifest. Reverse-extract the final IoStore using original Paks as read-only reference data.
8. Validate cooked bones by name and parent, dependencies, BoneMaps, raw precision, weights, UVs, height, asset classes, geometry invariants, and Blender QA. Run elbow, knee, shoulder, head, hand, fist, finger, and terminal-tip stress tests.
9. Confirm PBZ has exited, update `Release/Mods/<MOD id>`, run PBZModKit `clean`/`install`/`status`, and compare build/repository/installed hashes.
10. Ask for runtime evidence covering appearance, idle, movement, attacks, hit, dodge, stairs/jump, weapon grip/sheath, and stability, and record what the user confirmed in the delivery notes.

## Official references

- Epic, [Animation Retargeting](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-retargeting-in-unreal-engine): “It is important to note that the retargeting system only retargets the bone's translation component. The bone's rotation always comes from the animation data.”
- Epic, [Working with Modular Characters](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine): “Set Leader Pose Component constructs the character by parenting skeletal mesh objects to a parent skeletal mesh object, and runs the animations exclusively on the parent.”
- Epic, [FBX Import Options Reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-import-options-reference-in-unreal-engine): “If enabled, this will update the Reference Pose of Skeleton Asset of the Skeletal Mesh/Animation being imported, to the reference pose in the FBX file being imported.”
- Blender, [Weight Paint – Editing](https://docs.blender.org/manual/en/4.5/sculpt_paint/weight_paint/editing.html): “The Smooth operator blends the weights of selected vertices based on the average of adjacent vertices,”.

Read the supporting references only when needed:

- [references/workflow.md](references/workflow.md) for the semantic project map and commands.
- [references/failure-modes.md](references/failure-modes.md) for current symptom-to-fix decisions.
- [references/validation.md](references/validation.md) for release gates and evidence layout.

The reusable implementation is in [scripts/](scripts/). Each filename describes one operation. Set `PBZ_WORKSPACE_ROOT` to relocate the workspace, `PBZ_MOD` to choose a character profile, and `PBZ_BUILD_DIR` to select a working output directory. Local refinements take the source build from `PBZ_INPUT_BUILD` and write to a distinct output directory. Set `PBZ_NECK_SCALE` explicitly for a neck adjustment.
