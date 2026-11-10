"""Restore the neck to native proportions, blend the neck skin weights, and shorten the finger skin."""
import bpy, collections, json, os, shutil
from pathlib import Path
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
QA = ROOT/'Builds/current'
BASE = Path(os.environ.get('PBZ_INPUT_BUILD', str(QA)))
OUT = Path(os.environ['PBZ_BUILD_DIR'])
assert OUT.resolve() != BASE.resolve(), 'Choose a distinct working output directory'
OUT.mkdir(parents=True, exist_ok=True)
TARGET_SCALE = float(os.environ.get('PBZ_NECK_SCALE', '1.0'))
FINGER_SCALE = float(os.environ.get('PBZ_FINGER_SCALE', '0.95'))
assert 0.5 <= TARGET_SCALE <= 1.25 and 0.8 <= FINGER_SCALE <= 1.05

bpy.ops.wm.open_mainfile(filepath=str(BASE/'zero_clean.blend'))
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ref = json.loads((BASE/'mesh_refpose.json').read_text(encoding='utf8'))
source_scale = float(ref.get('local_neck_refinement', {}).get('scale', 1.0))


def native_world(rows):
    world, byname = {}, {}
    for b in rows:
        q = b['quat']
        local = Matrix.LocRotScale(Vector(b['loc']), Quaternion((q[3], *q[:3])), Vector(b['scale']))
        m = world[b['parent']]@local if b['parent'] >= 0 else local
        world[b['idx']] = m
        byname[b['name']] = m
    return world, byname


old_world, old_names = native_world(ref['bones'])
factor = TARGET_SCALE/source_scale
for b in ref['bones']:
    if b['name'] in ('neck_02', 'head'):
        assert ref['modes'][b['name']] == 'AnimationScaled', b['name']
        b['loc'] = [x*factor for x in b['loc']]
new_world, new_names = native_world(ref['bones'])


def blender_point(p):
    return Vector((p.x, -p.y, p.z))


group_names = {g.index: g.name for g in mesh.vertex_groups}
coords = np.array([list(v.co) for v in mesh.data.vertices])
original = coords.copy()
neck_deltas = {n: blender_point(new_names[n].translation-old_names[n].translation) for n in old_names}

moved = np.zeros(len(mesh.data.vertices), dtype=bool)
for v in mesh.data.vertices:
    delta = sum((neck_deltas[group_names[ge.group]]*ge.weight for ge in v.groups), Vector())
    if delta.length > 1e-7:
        coords[v.index] += np.array(delta)
        moved[v.index] = True
head_displacement = neck_deltas['head']
for v, p in zip(mesh.data.vertices, coords):
    v.co = p

# Preserve native orientations and move only the affected descendant bind origins.
old_matrices = {b.name: arm.matrix_world@b.matrix_local for b in arm.data.bones}
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
inv = arm.matrix_world.inverted()
for eb in arm.data.edit_bones:
    eb.use_connect = False
for eb in arm.data.edit_bones:
    m = old_matrices[eb.name].copy()
    m.translation += neck_deltas[eb.name]
    eb.matrix = inv@m
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
mesh.data.update()

# Blend the neck skin from the chest-driven base into head/neck_02/neck_01.
def smoothstep(edge0, edge1, x):
    t = min(1.0, max(0.0, (x-edge0)/(edge1-edge0)))
    return t*t*(3-2*t)


mats = [m.name for m in mesh.data.materials]


def short(name):
    return name.replace('MI_player_051_', '').replace('MI_common_', '').replace('MI_', '')


vmat = collections.defaultdict(collections.Counter)
for p in mesh.data.polygons:
    for vi in p.vertices:
        vmat[vi][p.material_index] += 1
skin_mats = {i for i, n in enumerate(mats) if short(n) in ('mint_4',)}

neck01 = arm.data.bones['neck_01'].head_local.copy()
head_joint = arm.data.bones['head'].head_local.copy()
axis = (head_joint-neck01).normalized()
span = (head_joint-neck01).length

region = []
for v in mesh.data.vertices:
    c = v.co
    if not (148.5 <= c.z <= 160.5):
        continue
    ctr = vmat[v.index]
    if not ctr or ctr.most_common(1)[0][0] not in skin_mats:
        continue
    rel = Vector(c)-neck01
    along = rel.dot(axis)
    radial = (rel-axis*along).length
    if radial > 7.6 or along < -1.6:
        continue
    region.append((v.index, along, radial))
top_along = max(a for _, a, _ in region)
ramp_span = top_along

old_weights = {}
for vi, along, radial in region:
    v = mesh.data.vertices[vi]
    old_weights[vi] = {group_names[ge.group]: ge.weight for ge in v.groups if ge.weight > 0}
    s = max(0.0, min(1.0, along/ramp_span))
    w_head = 0.85*smoothstep(0.58, 1.0, s)
    w_neck01 = 1.0-smoothstep(0.08, 0.46, s)
    w_neck02 = max(0.0, 1.0-w_head-w_neck01)
    radial_mask = 1.0-smoothstep(6.0, 7.6, radial)
    base_mask = smoothstep(148.9, 151.0, v.co.z)
    mask = radial_mask*base_mask
    target = {'head': w_head, 'neck_01': w_neck01, 'neck_02': w_neck02}
    blend = {}
    for name, w in old_weights[vi].items():
        blend[name] = blend.get(name, 0.0)+w*(1.0-mask)
    for name, w in target.items():
        if w > 1e-6:
            blend[name] = blend.get(name, 0.0)+w*mask
    blend = {k: max(0.0, x) for k, x in blend.items()}
    top = sorted(blend.items(), key=lambda kv: -kv[1])[:4]
    total = sum(x for _, x in top)
    top = [(k, x/total) for k, x in top if x/total > 1e-4]
    total = sum(x for _, x in top)
    blend = {k: x/total for k, x in top}
    for name in list(old_weights[vi]):
        mesh.vertex_groups[name].remove([vi])
    for name, w in blend.items():
        if w > 1e-4:
            mesh.vertex_groups[name].add([vi], w, 'REPLACE')

# Shorten the skin along each finger chain without touching bone length or the
# palm proportions.
finger_report = []
changed = np.zeros(len(mesh.data.vertices), dtype=bool)
for side in ('l', 'r'):
    for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
        bones = [f'{finger}_0{i}_{side}' for i in (1, 2, 3)]
        origin = arm.data.bones[bones[0]].head_local.copy()
        tip = arm.data.bones[bones[2]].head_local.copy()
        direction = (tip-origin).normalized()
        group_ids = {mesh.vertex_groups[b].index for b in bones}
        affected = []
        for v in mesh.data.vertices:
            blend = sum(ge.weight for ge in v.groups if ge.group in group_ids)
            if blend <= 1e-5:
                continue
            p = Vector(coords[v.index])
            rel = p-origin
            along = rel.dot(direction)
            perp = rel-direction*along
            moved_p = origin+direction*(along*FINGER_SCALE)+perp
            coords[v.index] = coords[v.index]+np.array((moved_p-p)*min(1.0, blend))
            affected.append(v.index)
        for vi in affected:
            moved[vi] = True
        if affected:
            finger_report.append({'chain': f'{finger}_{side}', 'vertices': len(affected),
                                  'skin_scale': FINGER_SCALE,
                                  'max_shift_cm': float(np.linalg.norm(coords[affected]-original[affected], axis=1).max())})

for v, p in zip(mesh.data.vertices, coords):
    v.co = p
mesh.data.update()

changed = np.flatnonzero(np.linalg.norm(coords-original, axis=1) > 1e-6)
assert set(int(i) for i in changed) <= set(int(i) for i in np.flatnonzero(moved)), 'unexpected vertices moved'
max_influences = max(len([g for g in v.groups if g.weight > 0]) for v in mesh.data.vertices)
weight_sums = max(abs(sum(g.weight for g in v.groups)-1.0) for v in mesh.data.vertices)

report = {
    'input_build': str(BASE),
    'neck_scale_before': source_scale,
    'neck_scale': TARGET_SCALE,
    'neck_length_delta_cm': (TARGET_SCALE-source_scale)*4.64485,
    'head_displacement_cm': list(head_displacement),
    'neck_weight_vertices': len(region),
    'neck_weights_changed': True,
    'finger_skin_scale': FINGER_SCALE,
    'fingers': finger_report,
    'changed_vertices': int(len(changed)),
    'max_influences': int(max_influences),
    'max_weight_sum_error': float(weight_sums),
    'uv_topology_unchanged': True,
    'native_rotations_unchanged': True,
    'height_cm': float(coords[:, 2].max()-coords[:, 2].min()),
}
assert max_influences <= 4 and weight_sums < 1e-4, (max_influences, weight_sums)
(OUT/'neck_finger_refinement.json').write_text(json.dumps(report, indent=2), encoding='utf8')
ref['local_neck_refinement'] = {'scale': TARGET_SCALE, 'bones': ['neck_02', 'head']}
ref['local_finger_refinement'] = {'skin_scale': FINGER_SCALE}
(OUT/'mesh_refpose.json').write_text(json.dumps(ref, indent=2), encoding='utf8')
for name in ('build_report.json', 'atlas_report.json', 'production_allowlist.json'):
    if (BASE/name).is_file():
        shutil.copy2(BASE/name, OUT/name)
if (BASE/'textures').is_dir():
    shutil.copytree(BASE/'textures', OUT/'textures', dirs_exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'zero_clean.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'zero_clean.fbx'), use_selection=True, object_types={'MESH', 'ARMATURE'},
                         global_scale=1., apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', add_leaf_bones=False,
                         bake_anim=False, mesh_smooth_type='FACE', use_mesh_modifiers=False, use_armature_deform_only=False,
                         path_mode='STRIP')
print('@@JSON@@'+json.dumps(report))
