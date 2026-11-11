"""Build a centimetre-space character mesh using native bones and artist skinning."""
import json
import runpy,os,sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4])) / 'Pipeline' / 'native-zero'
SCRIPT_ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ.get('PBZ_BUILD_DIR',str(ROOT.parents[2]/'Builds'/os.environ.get('PBZ_MOD','zero')/'current')))
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0,str(SCRIPT_ROOT))
from bone_roles import MAIN,FOLD

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'source/SK_ZeroBody_posed.blend'))
donor = bpy.data.objects['GameRig']
source = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o != donor)
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
mapping = {z: g for g, z in MAIN.items() if g in donor.data.bones and z in source.data.bones}
parents = {b.name: b.parent.name if b.parent else None for b in source.data.bones}
def resolve(name):
    seen = set()
    while name and name not in seen:
        seen.add(name)
        if name in mapping:
            return FOLD.get(mapping[name], mapping[name])
        name = parents.get(name)
    return 'pelvis'

groups = {g.index: g.name for g in mesh.vertex_groups}
proportion_fit=None
if os.environ.get('PBZ_FIT_PROPORTIONS')=='1':
    sys.path.insert(0,str(SCRIPT_ROOT))
    from fit_native_proportions import fit
    proportion_fit=fit(donor,source,MAIN,OUT)
weights = []
for v in mesh.data.vertices:
    acc = {}
    for ge in v.groups:
        target = resolve(groups[ge.group])
        acc[target] = acc.get(target, 0) + ge.weight
    top = sorted(((k,w) for k,w in acc.items() if w > 1e-8), key=lambda a:-a[1])[:4]
    total = sum(w for _, w in top)
    weights.append([(k,w/total) for k,w in top] if total else [('pelvis',1.)])

# Evaluate the complete artist-weighted pose, including all source helpers.
dg = bpy.context.evaluated_depsgraph_get()
ev = mesh.evaluated_get(dg)
em = ev.to_mesh()
points = [mesh.matrix_world @ v.co for v in em.vertices]
ev.to_mesh_clear()
offsets = {}
for g, z in MAIN.items():
    if g in donor.data.bones and z in source.pose.bones:
        offsets[g] = donor.matrix_world @ donor.data.bones[g].head_local - source.matrix_world @ source.pose.bones[z].head
# The Biped Head pivot sits at the skull base; Hun Head is inside the skull.
# Matching these pivots stretches the neck by ~8 cm. Preserve the artist's
# whole neck/head vertically by the same offset as the two shoulder joints.
shoulder_dz = .5 * (offsets['upperarm_l'].z + offsets['upperarm_r'].z)
for name in (() if proportion_fit else ('neck_01', 'neck_02', 'head')):
    if name in offsets:
        offsets[name].z = shoulder_dz
for side in (() if proportion_fit else ('l', 'r')):
    for k in offsets:
        if k.endswith('_'+side) and k.startswith(('thumb','index','middle','ring','pinky')):
            offsets[k] = offsets['hand_'+side]
for i, pairs in enumerate(weights):
    points[i] += sum((offsets.get(n, Vector()) * w for n,w in pairs), Vector())
# Hun's toe pivot is on the floor, unlike the source Biped toe pivot. Preserve
# the ankle surface and compress only the sole-to-ankle vertical interval, so
sole_min = min(p.z for p in points)
ankle_z = .5 * ((donor.matrix_world @ donor.data.bones['foot_l'].head_local).z +
                (donor.matrix_world @ donor.data.bones['foot_r'].head_local).z)
if sole_min < 0:
    for p in points:
        if p.z < ankle_z:
            p.z = (p.z-sole_min) * ankle_z / (ankle_z-sole_min)

# Work only on a local copy of the mesh, retaining all UVs and material indices.
newdata = mesh.data.copy()
if newdata.shape_keys:
    # Clear on the original object before replacing its data to keep vertex order.
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    bpy.ops.object.shape_key_remove(all=True)
    newdata = mesh.data.copy()
mesh.modifiers.clear()
mesh.parent = None
mesh.matrix_world = Matrix.Identity(4)
mesh.data = newdata
for v,p in zip(mesh.data.vertices,points):
    v.co = p
for vg in list(mesh.vertex_groups): mesh.vertex_groups.remove(vg)
vg = {b.name:mesh.vertex_groups.new(name=b.name) for b in donor.data.bones}
for i,pairs in enumerate(weights):
    for n,w in pairs: vg[n].add([i],w,'REPLACE')
mesh.data.update()
mesh.name = 'SK_ZeroBody'
donor.name = 'root'
donor.data.name = 'HunNativeRig'
for o in list(bpy.data.objects):
    if o not in (donor, mesh): bpy.data.objects.remove(o, do_unlink=True)
mesh.modifiers.new('NativeSkin','ARMATURE').object = donor
# Single coordinate convention: both bone translations and vertices are cm.
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = .01
bpy.context.view_layer.objects.active = donor
bpy.ops.object.select_all(action='DESELECT')
donor.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
mesh.select_set(True)
mesh.parent = donor
mesh.matrix_parent_inverse = Matrix.Identity(4)
bpy.context.view_layer.update()
assert all(abs(s-1) < 1e-5 for s in donor.scale), tuple(donor.scale)
assert all(abs(s-1) < 1e-5 for s in mesh.scale), tuple(mesh.scale)
outblend = OUT / 'zero_consistent.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(outblend))
bpy.ops.export_scene.fbx(filepath=str(OUT / 'zero_consistent.fbx'),
    use_selection=True, object_types={'MESH','ARMATURE'},
    global_scale=1., apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
    add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE',
    use_mesh_modifiers=False, use_armature_deform_only=False, path_mode='STRIP')
report={'source_checkpoint':str(ROOT / 'source/SK_ZeroBody_posed.blend'),
        'vertices':len(mesh.data.vertices),'triangles':len(mesh.data.polygons),
        'root_object':donor.name,'armature_scale':list(donor.scale),
        'mesh_scale':list(mesh.scale),'scene_unit_scale':.01,
        'dimensions_cm':list(mesh.dimensions),'unweighted':sum(not v.groups for v in mesh.data.vertices),
        'head_neck_vertical_offset_cm':shoulder_dz,
        'proportion_fit':proportion_fit,
        'sole_before_cm':sole_min,'sole_after_cm':min(p.z for p in points),
        'forward_axis_after_ue_import':'+Y (same as native toes)'}
(OUT / 'build_report.json').write_text(json.dumps(report, indent=2),encoding='utf-8')
print('@@JSON@@'+json.dumps(report))
