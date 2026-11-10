"""Validate the neck deformation blend and the finger skin length change against the frozen baseline."""
import json, os, sys
from pathlib import Path
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
BASE = Path(os.environ.get('PBZ_BASELINE_BUILD', str(ROOT/'Builds/v1.0.0')))
OUT = Path(os.environ.get('PBZ_BUILD_DIR', str(ROOT/'Builds/current')))
a = json.loads(Path(os.environ.get('PBZ_BASELINE_COOKED', str(BASE/'cooked_mesh.json'))).read_text())
b = json.loads((OUT/'cooked_mesh.json').read_text())
refine = json.loads((OUT/'neck_finger_refinement.json').read_text())
neck_factor = refine['neck_scale']/refine['neck_scale_before']
finger_scale = refine['finger_skin_scale']

assert a['indices'] == b['indices'] and a['vertex_uvs'] == b['vertex_uvs'], 'topology or UV changed'
assert len(a['vertices']) == len(b['vertices'])
assert len(a['bones']) == len(b['bones']) == 264
changed_bones = []
for old, new in zip(a['bones'], b['bones']):
    assert old['name'] == new['name'] and old['parent'] == new['parent']
    assert old['quat'] == new['quat'] and old['scale'] == new['scale'], old['name']
    if old['loc'] != new['loc']:
        assert old['name'] in ('neck_02', 'head'), old['name']
        assert max(abs(x*neck_factor-y) for x, y in zip(old['loc'], new['loc'])) < 1e-4
        changed_bones.append(old['name'])
assert set(changed_bones) == {'neck_02', 'head'}


def influence(d):
    result = [None]*len(d['vertices'])
    for s in d['sections']:
        for i in range(s['baseVertex'], s['baseVertex']+s['numVertices']):
            result[i] = {d['bones'][s['boneMap'][k]]['name']: w for k, w in d['vertices'][i][3]}
    return result


def bone_world(d):
    world, byname = [], {}
    for r in d['bones']:
        q = r['quat']
        m = Matrix.LocRotScale(Vector(r['loc']), Quaternion((q[3], *q[:3])), Vector(r['scale']))
        m = world[r['parent']]@m if r['parent'] >= 0 else m
        world.append(m); byname[r['name']] = m
    return byname


wa, wb = influence(a), influence(b)
world_a, world_b = bone_world(a), bone_world(b)
pa = np.array([r[:3] for r in a['vertices']]); pb = np.array([r[:3] for r in b['vertices']])
shift = np.linalg.norm(pb-pa, axis=1)


def neck_region(d, world):
    axis_bone = world['neck_01'].translation.copy()
    up = (world['head'].translation-axis_bone).normalized()
    pts = np.array([r[:3] for r in d['vertices']])
    rel = pts-axis_bone
    along = rel@np.array(up)
    radial = np.linalg.norm(rel-np.outer(along, np.array(up)), axis=1)
    return along, radial


along_b, radial_b = neck_region(b, world_b)
along_a, radial_a = neck_region(a, world_a)
chain_of = {}
for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
    for side in ('l', 'r'):
        for i in (1, 2, 3):
            chain_of[f'{finger}_0{i}_{side}'] = f'{finger}_{side}'
finger_scale_factor = {}
weight_changed = []
for i in range(len(wa)):
    if wa[i] != wb[i]:
        weight_changed.append(i)
        assert 148.0 < pb[i][2] < 162.0, (i, 'weight change outside the neck', pb[i])
        assert radial_b[i] < 8.0 and along_b[i] > -2.0, (i, 'weight change outside the neck column', along_b[i], radial_b[i])
        assert set(wb[i]) <= {'neck_01', 'neck_02', 'head', 'spine_03', 'spine_04', 'spine_05', 'clavicle_l', 'clavicle_r'}, wb[i]
        assert len(wb[i]) <= 4 and abs(sum(wb[i].values())-255) <= 2, (i, wb[i])
        for name in wa[i]:
            if name in chain_of:
                finger_scale_factor[chain_of[name]] = True
neck_groups = {'neck_01', 'neck_02', 'head'}
head_ids = [i for i, w in enumerate(wa) if w.get('head', 0) == 255]
rigid_ids = [i for i in head_ids if i not in set(weight_changed)]
delta = np.array(world_b['head'].translation-world_a['head'].translation)
rigid_error = float(np.linalg.norm((pb[rigid_ids]-pa[rigid_ids])-delta, axis=1).max())
assert rigid_error < 0.05, rigid_error

# Every moved vertex must belong to the plan: neck column, a finger chain, or the rigid head block.
allowed = np.zeros(len(pa), dtype=bool)
allowed[np.array(head_ids, dtype=int)] = True
for i in range(len(pa)):
    if (radial_a[i] < 8.0 and along_a[i] > -2.0 and 148.0 < pa[i][2] < 162.0):
        allowed[i] = True
    if any(n in chain_of for n in wa[i]):
        allowed[i] = True
moved = shift > 0.01
unexpected = np.flatnonzero(moved & ~allowed)
assert unexpected.size == 0, [(int(i), float(shift[i]), wa[i]) for i in unexpected[:5]]

axis_report = []
for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
    for side in ('l', 'r'):
        chain = [f'{finger}_0{i}_{side}' for i in (1, 2, 3)]
        origin = np.array(world_b[chain[0]].translation)
        direction = np.array(world_b[chain[2]].translation)-origin
        length = np.linalg.norm(direction); direction = direction/length
        ids = [i for i, w in enumerate(wa) if sum(w.get(n, 0) for n in chain) > 128]
        before = float((((pa[ids]-origin)@direction)).max())
        origin_a = np.array(world_a[chain[0]].translation)
        dir_a = np.array(world_a[chain[2]].translation)-origin_a
        dir_a = dir_a/np.linalg.norm(dir_a)
        before = float((((pa[ids]-origin_a)@dir_a)).max())
        after = float((((pb[ids]-origin)@direction)).max())
        assert abs(after-before*finger_scale) < 0.05, (chain, before, after)
        axis_report.append({'chain': f'{finger}_{side}', 'fingertip_before_cm': before,
                            'fingertip_after_cm': after})

# The blended weights must now drive the upper neck from neck_02 instead of head.
def neck_axis(d, world):
    origin = np.array(world['neck_01'].translation)
    up = np.array(world['head'].translation)-origin
    span = np.linalg.norm(up)
    return origin, up/span, span


origin_a, up_a, span_a = neck_axis(a, world_a)
origin_b, up_b, span_b = neck_axis(b, world_b)
along_a_all = (pa-origin_a)@up_a
along_b_all = (pb-origin_b)@up_b
def share_of(w, ids):
    share = {'head': 0.0, 'neck_01': 0.0, 'neck_02': 0.0}
    for i in ids:
        total = sum(w[i].values()) or 1
        for name in share:
            share[name] += w[i].get(name, 0)/total
    return {k: round(v/max(1, len(ids)), 3) for k, v in share.items()}


bands = [(0.0, 0.35), (0.35, 0.7), (0.7, 1.05)]
band_table = []
for low, high in bands:
    ids = [i for i in weight_changed if low*span_a <= along_a_all[i]/span_a < high*span_a]
    band_table.append({'band': f'{low:.2f}-{high:.2f}', 'vertices': len(ids),
                       'before': share_of(wa, ids), 'after': share_of(wb, ids)})
share_before = share_of(wa, weight_changed)
share_after = share_of(wb, weight_changed)
assert share_after['neck_02'] > 0.5 > share_before['neck_02']+0.3, (share_before, share_after)
assert share_after['head'] < 0.35, share_after
for row in band_table:
    if row['vertices'] < 50:
        continue
    assert row['after']['neck_02'] > row['before']['neck_02']+0.2, row
report = {'pass': True,
          'neck_scale': refine['neck_scale'], 'neck_scale_before': refine['neck_scale_before'],
          'head_translation_cm': delta.tolist(), 'changed_reference_bones': changed_bones,
          'changed_cooked_vertices': int(moved.sum()), 'reweighted_vertices': len(weight_changed),
          'rigid_head_error_cm': rigid_error,
          'neck_column_weight_share_before': share_before, 'neck_column_weight_share_after': share_after,
          'neck_weight_bands': band_table, 'neck_column_vertices': len(weight_changed),
          'finger_skin_scale': finger_scale, 'fingers': axis_report,
          'unrelated_body_geometry_unchanged': True, 'uv_topology_unchanged': True}
(OUT/'neck_deformation_validation.json').write_text(json.dumps(report, indent=2))
print('@@JSON@@'+json.dumps(report))
