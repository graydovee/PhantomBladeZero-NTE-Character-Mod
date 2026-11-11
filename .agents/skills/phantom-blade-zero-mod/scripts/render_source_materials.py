import bpy,json,sys,os
from pathlib import Path
from mathutils import Vector
ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
OUT=Path(os.environ.get('PBZ_BUILD_DIR',str(ROOT/'Builds'/os.environ.get('PBZ_MOD','zero')/'current')))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'zero_clean.blend'))
mesh=next(o for o in bpy.data.objects if o.type=='MESH')
sys.path.insert(0,str(ROOT/'.agents/skills/blender-asset-qa/scripts'))
import qa_check
report=qa_check.run(objects=[mesh.name],profile='game',eps=.02,tol=.2)
(OUT/'source_asset_qa.json').write_text(json.dumps(report,indent=2),encoding='utf8')
for mat in mesh.data.materials:
    nodes=mat.node_tree.nodes; tx=next(n for n in nodes if n.type=='TEX_IMAGE')
    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value=(0,0,0,1)
    for link in list(bsdf.inputs['Base Color'].links): mat.node_tree.links.remove(link)
    mat.node_tree.links.new(tx.outputs['Color'],bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value=1
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=8
sc.view_settings.view_transform='Standard'; sc.render.resolution_percentage=100
sc.render.resolution_x=700; sc.render.resolution_y=1000
if sc.world is None: sc.world=bpy.data.worlds.new('AlbedoWorld')
sc.world.color=(.1,.1,.1)
cam=bpy.data.objects.new('AlbedoReviewCamera',bpy.data.cameras.new('AlbedoReviewCamera'))
sc.collection.objects.link(cam); sc.camera=cam; cam.data.type='ORTHO'; cam.data.clip_end=2000
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
head_z=(arm.matrix_world@arm.data.bones['head'].head_local).z
for label,ctr,delta,scale in [('front',(0,0,95),(0,-400,0),215),('back',(0,0,95),(0,400,0),215),('face',(0,0,head_z+8),(0,-400,0),42)]:
    cam.data.ortho_scale=scale; cam.location=Vector(ctr)+Vector(delta)
    cam.rotation_euler=(Vector(ctr)-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=str(OUT/('albedo_'+label+'.png')); bpy.ops.render.render(write_still=True)
print('QA',json.dumps(report))
