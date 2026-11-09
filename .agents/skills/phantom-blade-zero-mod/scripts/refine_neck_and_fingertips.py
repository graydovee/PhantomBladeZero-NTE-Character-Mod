"""Apply the requested neck scale and align terminal phalanx geometry."""
import bpy,json,os,shutil
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]));QA=ROOT/'Builds/current'
BASE=Path(os.environ.get('PBZ_INPUT_BUILD',str(QA)))
OUT=Path(os.environ['PBZ_BUILD_DIR'])
assert OUT.resolve()!=BASE.resolve(),'Choose a distinct working output directory'
OUT.mkdir(parents=True,exist_ok=True)
neck_scale=float(os.environ.get('PBZ_NECK_SCALE','1.0'))
assert .5<=neck_scale<=1.2
bpy.ops.wm.open_mainfile(filepath=str(BASE/'zero_clean.blend'))
mesh=next(o for o in bpy.data.objects if o.type=='MESH');arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
ref=json.loads((BASE/'mesh_refpose.json').read_text(encoding='utf8'))
old_ref=json.loads(json.dumps(ref['bones']));ref['bones']=json.loads(json.dumps(old_ref))
def native_world(rows):
    w={};out={}
    for b in rows:
        q=b['quat'];local=Matrix.LocRotScale(Vector(b['loc']),Quaternion((q[3],*q[:3])),Vector(b['scale']))
        m=w[b['parent']]@local if b['parent']>=0 else local;w[b['idx']]=m;out[b['name']]=m
    return out
oldworld=native_world(old_ref)
for b in ref['bones']:
    if b['name'] in ('neck_02','head'):
        assert ref['modes'][b['name']]=='AnimationScaled'
        b['loc']=[x*neck_scale for x in b['loc']]
newworld=native_world(ref['bones'])
def blender_point(p):return Vector((p.x,-p.y,p.z))
neck_deltas={n:blender_point(newworld[n].translation-oldworld[n].translation) for n in oldworld}
groups={g.index:g.name for g in mesh.vertex_groups}
coords=np.array([list(v.co) for v in mesh.data.vertices]);original=coords.copy();tip_report=[]
# A separate geometric orientation correction per terminal bone, blended only
# by that bone's existing weight. Preserve the phalanx cross-section by rotating
# (slerp), rather than shrinking vectors with a linear coordinate average.
for side in ('l','r'):
    for finger in ('thumb','index','middle','ring','pinky'):
        n=f'{finger}_03_{side}';g=mesh.vertex_groups[n].index
        vi=[];weights=[]
        for v in mesh.data.vertices:
            weight=sum(ge.weight for ge in v.groups if ge.group==g)
            if weight>1e-6:vi.append(v.index);weights.append(weight)
        vi=np.array(vi);weights=np.array(weights)
        head=arm.data.bones[n].head_local.copy();cloud=original[vi[weights>.7]]-np.array(head)
        vals,axes=np.linalg.eigh(np.cov(cloud.T));direction=Vector(axes[:,-1])
        if direction.dot(Vector(cloud.mean(axis=0)))<0:direction=-direction
        target=blender_point(oldworld[n].to_3x3().col[0]).normalized()
        previous=arm.data.bones[f'{finger}_02_{side}'].head_local
        if target.dot(head-previous)<0:target=-target
        angle=direction.angle(target)
        assert vals[-1]/vals[-2]>2.5 and angle<2.2,(n,angle,vals)
        correction=direction.rotation_difference(target)
        for i,w in zip(vi,weights):
            p=Vector(original[i]);q=Quaternion().slerp(correction,float(w))
            coords[i]+=np.array(head+q@(p-head)-p)
        tip_report.append({'bone':n,'affected_vertices':len(vi),'axis_error_before_deg':float(np.degrees(angle)),
            'pca_elongation':float(vals[-1]/vals[-2]),'max_tip_displacement_cm':float(np.linalg.norm(coords[vi]-original[vi],axis=1).max())})
neck_affected=[]
for v in mesh.data.vertices:
    delta=sum((neck_deltas[groups[ge.group]]*ge.weight for ge in v.groups),Vector())
    if delta.length>1e-6:coords[v.index]+=np.array(delta);neck_affected.append(v.index)
for v,p in zip(mesh.data.vertices,coords):v.co=p
# Preserve every native orientation; move only affected descendant bind origins.
old_bone_matrices={b.name:arm.matrix_world@b.matrix_local for b in arm.data.bones}
bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
inv=arm.matrix_world.inverted()
for eb in arm.data.edit_bones:eb.use_connect=False
for eb in arm.data.edit_bones:
    m=old_bone_matrices[eb.name].copy();m.translation+=neck_deltas[eb.name];eb.matrix=inv@m
bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update();mesh.data.update()
changed=np.flatnonzero(np.linalg.norm(coords-original,axis=1)>1e-6)
allowed=set(neck_affected)
for v in mesh.data.vertices:
    if any(groups[ge.group].split('_')[-2:] in (['03','l'],['03','r']) and groups[ge.group].startswith(('thumb_','index_','middle_','ring_','pinky_')) for ge in v.groups):allowed.add(v.index)
assert set(changed)<=allowed
report={'input_build':str(BASE),'neck_scale':neck_scale,'head_displacement_cm':list(neck_deltas['head']),
    'neck_affected_vertices':len(neck_affected),'terminal_phalanges':tip_report,'changed_vertices':len(changed),
    'weights_unchanged':True,'uv_topology_unchanged':True,'native_rotations_unchanged':True,
    'height_cm':float(coords[:,2].max()-coords[:,2].min()),'runtime_verified':False}
(OUT/'neck_tip_refinement.json').write_text(json.dumps(report,indent=2),encoding='utf8')
ref['local_neck_refinement']={'scale':neck_scale,'bones':['neck_02','head']}
(OUT/'mesh_refpose.json').write_text(json.dumps(ref,indent=2),encoding='utf8')
for name in ('build_report.json','atlas_report.json','production_allowlist.json'):
    shutil.copy2(BASE/name,OUT/name)
shutil.copytree(BASE/'textures',OUT/'textures',dirs_exist_ok=True)
bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'zero_clean.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'zero_clean.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},
    global_scale=1.,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,bake_anim=False,
    mesh_smooth_type='FACE',use_mesh_modifiers=False,use_armature_deform_only=False,path_mode='STRIP')
print('@@JSON@@'+json.dumps(report))
