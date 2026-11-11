import bpy,os
from pathlib import Path
from mathutils import Matrix
ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
OUT=Path(os.environ.get('PBZ_BUILD_DIR',str(ROOT/'Builds'/os.environ.get('PBZ_MOD','zero')/'current')))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'zero_clean.blend'))
mesh=next(o for o in bpy.data.objects if o.type=='MESH')
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
md=bpy.data.meshes.new('NativeInvisiblePart'); md.from_pydata([(0,0,0),(.01,0,0),(0,.01,0)],[],[(0,1,2)]); md.update()
mesh.data=md; mesh.name='NativeInvisiblePart'
for g in list(mesh.vertex_groups): mesh.vertex_groups.remove(g)
mesh.vertex_groups.new(name='pelvis').add([0,1,2],1,'REPLACE')
md.materials.append(bpy.data.materials['eye_bantou'])
uv=md.uv_layers.new(name='UVMap')
for i in range(3): uv.data[i].uv=(.12+(i==1)*.001,.62+(i==2)*.001)
bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'native_blank.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},global_scale=1.,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,bake_anim=False,
    mesh_smooth_type='FACE',use_mesh_modifiers=False,use_armature_deform_only=False,path_mode='STRIP')
bpy.ops.object.select_all(action='DESELECT')
static_md=bpy.data.meshes.new('InvisibleStatic')
static_md.from_pydata([(0,0,0),(1,0,0),(0,1,0)],[],[(0,1,2)]); static_md.update()
static_md.materials.append(bpy.data.materials['eye_bantou'])
static_uv=static_md.uv_layers.new(name='UVMap')
for i in range(3): static_uv.data[i].uv=(.12+(i==1)*.001,.62+(i==2)*.001)
static_ob=bpy.data.objects.new('InvisibleStatic',static_md)
bpy.context.collection.objects.link(static_ob); static_ob.select_set(True)
bpy.context.view_layer.objects.active=static_ob
bpy.ops.export_scene.fbx(filepath=str(OUT/'native_blank_static.fbx'),use_selection=True,
    object_types={'MESH'},global_scale=1.,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',bake_anim=False,mesh_smooth_type='FACE',
    use_mesh_modifiers=True,path_mode='STRIP')
