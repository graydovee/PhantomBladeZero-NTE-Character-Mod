# Validation and acceptance reference

## Offline gates

At minimum, the final cooked body must report:

- native Skeleton path and root `root`, 264 expected body bones;
- native PA dependency and real MI references, with native Skeleton/PA/MIs excluded from the package;
- zero unweighted vertices, no more than four influences, normalized weights;
- one UV layer, zero cooked UV-zero-area faces, valid section BoneMaps and actual raw weight precision;
- expected height/proportion range measured from cooked vertices;
- native rotations and parent names preserved; only planned `AnimationScaled` translations changed;
- no unintended geometry/index/UV change for a local hand-only refinement;
- Blender asset QA pass plus solid/material/wire review sheets;
- edge stress: elbows, knees, shoulders, head pitch/yaw, both hand directions, fist, finger open, and terminal-only curl.

Measure `(posed edge length - rest edge length)` in cm and record the worst edge, vertex IDs, material/section, and weight pairs. Assess this data together with the pose images.

## Runtime gates

The user must provide evidence for idle, walk, run, attack/combos, hit, dodge, stairs/jump, weapon grip/sheath, face/material appearance, and a stability session. The loader log must be captured for the same run. A basic “model works” screenshot can justify saving a baseline but does not close every acceptance item.

## Current evidence layout

Keep the current build self-contained:

```text
Builds/current/
  zero_clean.blend/.fbx
  production_allowlist.json
  container/*.pak, *.utoc, *.ucas, SHA256SUMS.txt
  cooked_mesh.json, cooked_props.json, cooked_validation.json
  review/, detail/, source_asset_qa.json
  installed_verification.json
  README.md
```

The installer and installable package live in `Release/`. Source checkpoints and native dumps live under `Pipeline/native-zero/`. Reports contain `runtime_verified`, with its value derived from user evidence.

## Delivery gate

A micro-fix advances to installation when its target metrics and local scope pass, the cooked container passes inspection, and PBZ has exited. Full completion requires user evidence for each required runtime item. Before that point, describe the concrete current build and its pending acceptance items.
