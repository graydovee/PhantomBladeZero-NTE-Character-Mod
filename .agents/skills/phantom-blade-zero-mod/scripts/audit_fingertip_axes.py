"""Measure source mesh terminal axes and export a quantized deformation proxy."""
import bpy,json,os,sys,runpy
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion,Matrix
ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]));QA=ROOT/'Builds'/os.environ.get('PBZ_MOD','zero')/'current'
OUT=Path(os.environ.get('PBZ_BUILD_DIR',str(QA)))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'zero_clean.blend'))
mesh=next(o for o in bpy.data.objects if o.type=='MESH');arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
ref=json.loads((OUT/'mesh_refpose.json').read_text())['bones'];lookup={b['name']:b['idx'] for b in ref}
groups={g.index:g.name for g in mesh.vertex_groups};rows=[]
for v in mesh.data.vertices:
    pairs=[(lookup[groups[g.group]],g.weight) for g in v.groups if g.weight>1e-8]
    w=np.array([p[1] for p in pairs]);raw=w/w.sum()*255;ints=np.floor(raw).astype(int)
    for j in np.argsort(raw-ints)[::-1][:255-int(ints.sum())]:ints[j]+=1
    rows.append([float(v.co.x),float(-v.co.y),float(v.co.z),[[p[0],int(i)] for p,i in zip(pairs,ints) if i]])
proxy={'use16BitBoneWeight':False,'bones':ref,'vertices':rows,'indices':[v for p in mesh.data.polygons for v in p.vertices],
       'sections':[{'baseVertex':0,'numVertices':len(rows),'boneMap':list(range(264))}]}
(OUT/'source_proxy.json').write_text(json.dumps(proxy,separators=(',',':')))
sys.argv=['audit','--',str(OUT/'source_proxy.json'),str(OUT/'source_audit')]
runpy.run_path(str(Path(__file__).resolve().parent/'audit_grip_deformation.py'))
axis_report=[]
for side in ('l','r'):
    for f in ('thumb','index','middle','ring','pinky'):
        n=f+'_03_'+side;g=mesh.vertex_groups[n].index;h=arm.data.bones[n].head_local
        a=np.array([list(v.co-h) for v in mesh.data.vertices if any(x.group==g and x.weight>.7 for x in v.groups)])
        values,vectors=np.linalg.eigh(np.cov(a.T));axis=Vector(vectors[:,-1])
        if axis.dot(Vector(a.mean(axis=0)))<0:axis=-axis
        forward=(h-arm.data.bones[f+'_02_'+side].head_local).normalized()
        axis_report.append({'bone':n,'axis_error_deg':float(np.degrees(axis.angle(forward))),
                            'max_radius_cm':float(np.linalg.norm(a-(a@np.array(forward))[:,None]*np.array(forward),axis=1).max())})
(OUT/'terminal_axis_report.json').write_text(json.dumps(axis_report,indent=2))
print('TIP_AXES',json.dumps(axis_report))
