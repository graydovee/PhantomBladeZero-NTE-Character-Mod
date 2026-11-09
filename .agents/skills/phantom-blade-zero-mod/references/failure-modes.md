# Current symptom-to-fix guide

| Symptom | Evidence to inspect | Current fix |
|---|---|---|
| A-pose or missing motion | root name, Skeleton compatibility, leader mesh path | use native `Hun_Skin_Skeleton`, root `root`, native leader animation path |
| Reversed head or skinny limbs | cooked root, case-insensitive bone names, scales, raw refpose | keep one native main-bone set, use raw reference data, unit scales of one |
| Body height or limbs wrong | cooked height and native joint landmarks | fit only `AnimationScaled` lengths and retain native rotations/parents |
| Attacks tear at seams | maximum per-edge stretch and affected weights | smooth the local seam, normalize, cap four influences, repeat stress tests |
| Hand grip deforms | palm frame, finger segment axes, thumb-root weights | align palm from joint/spread, aim segments, smooth hand/thumb region, sync coincident vertices |
| Fingertips twist | terminal PCA axis vs native terminal-bone axis | align terminal geometry to the native axis and run terminal-only stress tests |
| Neck looks long | head/neck landmarks and cooked pitch tests | shorten permitted upper-neck/head lengths and translate head geometry together |
| Model has wrong colors | material class, atlas tile, texture compression/colorspace | reuse native MIs, build deterministic atlas tiles, preserve alpha and data map types |
| Original clothing remains | extracted asset classes for every attached part | replace the leader body and preserve each attached asset's native class |
| Container appears unchanged | build/repository/installed hashes, PBZModKit state | update Release repository, run clean/install/status, require three matching hashes |
| Reverse audit disagrees with the build | provider roots and package lookup | audit current container with original Paks as read-only reference, with no live override contamination |

A rest-pose image is insufficient evidence. Every local change requires final cooked validation, asset QA, and a user runtime screenshot for acceptance.
