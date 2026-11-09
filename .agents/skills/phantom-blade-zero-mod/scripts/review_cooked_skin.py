"""Reconstruct cooked skin and render deterministic deformation review sheets."""
import json
import os
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
OUT = Path(os.environ.get('PBZ_BUILD_DIR',str(ROOT/'Builds/current')))
SRC = OUT / 'cooked_mesh.json'
SKILLS = ROOT / '.agents/skills/blender-asset-qa/scripts'
sys.path.insert(0, str(SKILLS))
import review_shots
# Skill renderer targets Blender 5.x; use a local compatibility wrapper for 4.5.
if not hasattr(bpy.context.scene.render.image_settings, 'media_type'):
    import types
    compatible = types.ModuleType('review_45')
    compatible.__file__ = str(SKILLS / 'review_shots.py')
    source = (SKILLS / 'review_shots.py').read_text(encoding='utf-8')
    source = source.replace('        r.image_settings.media_type = "IMAGE"\n', '')
    exec(compile(source, compatible.__file__, 'exec'), compatible.__dict__)
    review_shots = compatible
# These dumps are UE component coordinates, whose native feet face +Y.
# Blender's generic QA renderer assumes a -Y front; label views accurately.
review_shots.DIRS.update({'front':(0,1,.15),'back':(0,-1,.15),'three_quarter':(1,1,.6)})
if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
    if args:
        SRC = Path(args[0])
    if len(args) > 1:
        OUT = Path(args[1])
        OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
data = json.loads(SRC.read_text(encoding='utf-8'))
verts = np.array([v[:3] for v in data['vertices']], dtype=float) * .01
faces = np.asarray(data['indices'], dtype=int).reshape(-1, 3)
md = bpy.data.meshes.new('InstalledBody')
md.from_pydata(verts.tolist(), [], faces.tolist())
md.update()
mesh = bpy.data.objects.new('InstalledBody', md)
bpy.context.collection.objects.link(mesh)
ad = bpy.data.armatures.new('CookedRig')
arm = bpy.data.objects.new('CookedRig', ad)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
world = {}
bone_names = {}
for row in data['bones']:
    i = row['idx']
    q = row['quat']
    local = Matrix.LocRotScale(Vector(row['loc']) * .01,
                              Quaternion((q[3], q[0], q[1], q[2])),
                              Vector(row['scale']))
    parent = row['parent']
    w = world[parent] @ local if parent >= 0 else local
    world[i] = w
    eb = ad.edit_bones.new(row['name'])
    eb.matrix = w
    eb.length = .025
    if parent >= 0:
        eb.parent = ad.edit_bones[bone_names[parent]]
    bone_names[i] = eb.name
bpy.ops.object.mode_set(mode='OBJECT')
vg = {i: mesh.vertex_groups.new(name=n) for i, n in bone_names.items()}
precision = 65535 if data['use16BitBoneWeight'] else 255
bad = []
sums = []
for sec in data['sections']:
    for vi in range(sec['baseVertex'], sec['baseVertex'] + sec['numVertices']):
        influences = data['vertices'][vi][3]
        total = sum(w for _, w in influences)
        sums.append(total)
        if total <= 0:
            bad.append(vi)
            continue
        for bi, w in influences:
            assert 0 <= bi < len(sec['boneMap']), (vi, bi)
            vg[sec['boneMap'][bi]].add([vi], w / total, 'REPLACE')
mod = mesh.modifiers.new('Armature', 'ARMATURE')
mod.object = arm

def evaluated():
    bpy.context.view_layer.update()
    ob = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ob.to_mesh()
    a = np.empty((len(me.vertices), 3), dtype=np.float64)
    me.vertices.foreach_get('co', a.ravel())
    ob.to_mesh_clear()
    return a

rest = evaluated()
edge = np.array([tuple(e.vertices) for e in md.edges], dtype=int)
rest_len = np.linalg.norm(rest[edge[:, 0]] - rest[edge[:, 1]], axis=1)
cases = {
    'rest': [],
    'elbows': [('lowerarm_l', (0, 0, 1), 90), ('lowerarm_r', (0, 0, 1), -90)],
    'knee': [('calf_l', (1, 0, 0), 90)],
    'head': [('head', (0, 0, 1), 45)],
    'head_pitch': [('neck_01', (1, 0, 0), 20),('head', (1, 0, 0), 25)],
    'head_reverse_pitch': [('neck_01', (1, 0, 0), -20),('head', (1, 0, 0), -25)],
    'elbows_140': [('lowerarm_l', (0, 0, 1), 140), ('lowerarm_r', (0, 0, 1), -140)],
    'knee_150': [('calf_l', (1, 0, 0), 150)],
    'shoulders': [('upperarm_l', (0, 1, 0), -70), ('upperarm_r', (0, 1, 0), 70)],
}
report = {'input': str(SRC), 'vertices': len(verts), 'triangles': len(faces),
          'bones': len(bone_names), 'unweighted': len(bad),
          'root':data['bones'][0],
          'raw_weight_precision': precision,
          'rest_skin_error_cm': float(np.max(np.linalg.norm(rest - verts, axis=1)) * 100),
          'bounds_cm': ((verts.max(axis=0) - verts.min(axis=0)) * 100).tolist(),
          'cases': {}}
# Finger rotations must be tested explicitly: limb-only stress misses a finger
for label,angles in [('fist',(60,85,70)),('finger_open',(-30,-20,-15))]:
    cases[label]=[]
    for side,sign in [('l',1),('r',-1)]:
        for finger in ('thumb','index','middle','ring','pinky'):
            for seg,deg in zip(('01','02','03'),angles):
                cases[label].append((f'{finger}_{seg}_{side}',None,deg*sign))
for label, operations in cases.items():
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for name, axis, deg in operations:
        pb = arm.pose.bones.get(name)
        assert pb is not None, name
        if axis is None:
            pb.rotation_mode='QUATERNION'
            pb.rotation_quaternion=Quaternion((0,0,1),math.radians(deg))
        else:
            h = pb.head.copy()
            pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis)) @ Matrix.Translation(-h) @ pb.matrix
        bpy.context.view_layer.update()
    posed = evaluated()
    lengths = np.linalg.norm(posed[edge[:, 0]] - posed[edge[:, 1]], axis=1)
    report['cases'][label] = {
        'max_displacement_cm': float(np.linalg.norm(posed - rest, axis=1).max() * 100),
        'max_edge_length_increase_cm': float((lengths - rest_len).max() * 100),
    }
    report['cases'][label]['sheet'] = review_shots.run(
        objects=[mesh.name], views=['front', 'back', 'right', 'three_quarter'],
        out=str(OUT / (label + '_installed.png')), mode='solid', res=640)['sheet']
(OUT / 'cooked_skin_review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'installed_body_review.blend'))
print('@@JSON@@' + json.dumps(report))
