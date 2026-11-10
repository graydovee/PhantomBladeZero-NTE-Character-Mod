"""Compose atlas textures and map source material UVs to their declared tiles."""
import json, sys, os
from pathlib import Path
ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
OUT=Path(os.environ.get('PBZ_BUILD_DIR',str(ROOT/'Builds/current')))
TEX=ROOT/'Pipeline/native-zero/model/zero/textures'
# Each source material has its own atlas tile. Body2 has two repeated tiles,
TILES={0:(0,2),1:(1,1),2:(2,1),3:(3,1),4:(0,2),5:(1,2),6:(0,0),7:(2,0),8:(3,0),9:(0,1)}
FILES={1:'T_player_051_female_face_d.png',2:'T_player_051_female_eye_d.png',
       3:'T_player_051_female_face_d.png',6:'T_player_051_female_1_d.png',
       7:'T_player_051_female_2_d.png',8:'T_player_009_female_hair_01_d.png',
       9:'T_player_009_female_hair_02_d.png'}
if 'textures' in sys.argv:
    from PIL import Image
    td=OUT/'textures'; td.mkdir(exist_ok=True)
    size=4096; tile=size//4
    bc=Image.new('RGBA',(size,size),(0,0,0,0))
    n=Image.new('RGB',(size,size),(128,128,255))
    arm=Image.new('RGB',(size,size),(255,180,0))
    def paste(canvas,im,xy):
        canvas.paste(im.resize((tile,tile),Image.Resampling.LANCZOS),(xy[0]*tile,(3-xy[1])*tile))
    for i,name in FILES.items():
        im=Image.open(TEX/name).convert('RGBA'); paste(bc,im,TILES[i])
        if i==7: paste(bc,im,(1,0))
        normal={6:'T_player_051_female_1_n.png',7:'T_player_051_female_2_n.png'}.get(i)
        if normal:
            normalim=Image.open(TEX/normal).convert('RGB'); paste(n,normalim,TILES[i])
            if i==7: paste(n,normalim,(1,0))
    paste(bc,Image.new('RGBA',(tile,tile),(255,255,255,255)),TILES[5])
    for name,im in [('BC',bc),('N',n),('ARM',arm)]: im.save(td/('T_ZeroHun_Cap_V02_'+name+'.png'))
    print('Atlas textures written:',td)
    sys.exit(0)
import bpy
bpy.ops.wm.open_mainfile(filepath=str(OUT/'zero_consistent.blend'))
mesh=next(o for o in bpy.data.objects if o.type=='MESH')
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
uv=mesh.data.uv_layers[0]
for p in mesh.data.polygons:
    i=p.material_index; x,y=TILES[i]
    for li in p.loop_indices:
        u,v=uv.data[li].uv
        if i==7:
            assert -1.001<=u<=1.001 and -.001<=v<=1.001
        else: assert -.001<=u<=1.001 and -.001<=v<=1.001,(i,u,v)
        uv.data[li].uv=((u+x)/4,(v+y)/4)
for name in [layer.name for layer in mesh.data.uv_layers][1:]:
    mesh.data.uv_layers.remove(mesh.data.uv_layers[name])
mesh.data.uv_layers[0].name='UVMap'
image=bpy.data.images.load(str(OUT/'textures/T_ZeroHun_Cap_V02_BC.png'),check_existing=True)
image.colorspace_settings.name='sRGB'
for mat in mesh.data.materials:
    mat.use_nodes=True; nodes=mat.node_tree.nodes; nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial'); bsdf=nodes.new('ShaderNodeBsdfPrincipled')
    tx=nodes.new('ShaderNodeTexImage'); tx.image=image
    mat.node_tree.links.new(tx.outputs['Color'],bsdf.inputs['Base Color'])
    mat.node_tree.links.new(tx.outputs['Alpha'],bsdf.inputs['Alpha'])
    bsdf.inputs['Roughness'].default_value=.7
    mat.node_tree.links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    mat.surface_render_method='DITHERED'
mesh.data.update()
bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'zero_atlas.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'zero_atlas.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},global_scale=1.,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,bake_anim=False,
    mesh_smooth_type='FACE',use_mesh_modifiers=False,use_armature_deform_only=False,path_mode='STRIP')
report={'grid':[4,4],'texture_size':4096,'source_material_tiles':TILES,
        'negative_u_policy':'body2 adjacent repeated tiles, no vertex folding',
        'transparent_effect_layers':['eye_bantou','MI_common_face_mask'],
        'vertices':len(mesh.data.vertices),'triangles':len(mesh.data.polygons),
        'uv_layers':len(mesh.data.uv_layers),'skeleton':'native Hun_Skin_Skeleton'}
(OUT/'atlas_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('@@JSON@@'+json.dumps(report))
