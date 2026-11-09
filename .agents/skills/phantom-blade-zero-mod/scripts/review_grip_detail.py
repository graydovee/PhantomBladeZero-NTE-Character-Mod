"""Render hand details for synthetic finger stress poses."""
import bpy,json,sys,math,types,os
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector,Quaternion
args=sys.argv[sys.argv.index('--')+1:];BLEND=Path(args[0]);OUT=Path(args[1]);OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
mesh=bpy.data.objects['InstalledBody'];arm=bpy.data.objects['CookedRig']
skills=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))/'.agents/skills/blender-asset-qa/scripts';sys.path.insert(0,str(skills))
review=types.ModuleType('review_45');review.__file__=str(skills/'review_shots.py')
code=(skills/'review_shots.py').read_text(encoding='utf8').replace('        r.image_settings.media_type = "IMAGE"\n','')
exec(compile(code,review.__file__,'exec'),review.__dict__)
gn={g.index:g.name for g in mesh.vertex_groups};faces={}
for side in ('l','r'):
    ids={v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if gn[g.group].endswith('_'+side) and gn[g.group].startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')))>.8}
    faces[side]=[tuple(p.vertices) for p in mesh.data.polygons if all(v in ids for v in p.vertices)]
rows=[]
for label,deg in [('rest',(0,0,0)),('curl',(60,85,70)),('reverse',(-60,-85,-70))]:
    for pb in arm.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    for side,sign in [('l',1),('r',-1)]:
        for finger in ('thumb','index','middle','ring','pinky'):
            for seg,angle in zip(('01','02','03'),deg):
                pb=arm.pose.bones[f'{finger}_{seg}_{side}'];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion((0,0,1),math.radians(angle*sign))
    bpy.context.view_layer.update()
    ob=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ob.to_mesh();pts=[v.co.copy() for v in em.vertices];ob.to_mesh_clear()
    for side in ('l','r'):
        original=faces[side];vi=sorted({v for p in original for v in p});remap={v:i for i,v in enumerate(vi)}
        md=bpy.data.meshes.new('HandDetail');md.from_pydata([pts[v] for v in vi],[],[tuple(remap[v] for v in p) for p in original]);md.update()
        detail=bpy.data.objects.new('HandDetail',md);bpy.context.collection.objects.link(detail)
        for p in md.polygons:p.use_smooth=True
        wrist=arm.data.bones['hand_'+side].head_local
        fwd=(arm.data.bones['middle_01_'+side].head_local-wrist).normalized()
        spread=(arm.data.bones['index_01_'+side].head_local-arm.data.bones['pinky_01_'+side].head_local).normalized()
        normal=spread.cross(fwd).normalized()
        review.DIRS.update({'palm':tuple(normal),'oblique':tuple((normal+spread*.5+fwd*.15).normalized()),'back':tuple(-normal),'side':tuple(spread)})
        sheet=review.run(objects=[detail.name],views=['palm','back','side','oblique'],out=str(OUT/f'{label}_{side}.png'),mode='solid',res=640)
        rows.append({'pose':label,'side':side,'sheet':sheet['sheet']})
        if label=='curl' and side=='r':review.run(objects=[detail.name],views=['palm','oblique'],out=str(OUT/'curl_r_wire.png'),mode='wire',res=640)
        bpy.data.objects.remove(detail,do_unlink=True);bpy.data.meshes.remove(md)
(OUT/'review_index.json').write_text(json.dumps(rows,indent=2))
print('@@JSON@@'+json.dumps(rows))
