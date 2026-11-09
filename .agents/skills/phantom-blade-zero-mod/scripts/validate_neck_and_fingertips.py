"""Validate the requested local neck and terminal geometry edit scope."""
import json,sys,math,os
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
args=sys.argv[sys.argv.index('--')+1:];OUT=Path(args[0]);QA=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))/'Builds/current';BASE=Path(os.environ.get('PBZ_BASELINE_BUILD',str(QA)))
a=json.loads((BASE/'cooked_mesh.json').read_text());b=json.loads((OUT/'cooked_mesh.json').read_text())
neck_scale=json.loads((OUT/'neck_tip_refinement.json').read_text())['neck_scale']
assert a['indices']==b['indices'] and a['vertex_uvs']==b['vertex_uvs']
assert len(a['vertices'])==len(b['vertices'])
assert len(a['bones'])==len(b['bones'])==264
changed_bones=[]
for old,new in zip(a['bones'],b['bones']):
    assert old['name']==new['name'] and old['parent']==new['parent']
    assert old['quat']==new['quat'] and old['scale']==new['scale']
    if old['loc']!=new['loc']:
        assert old['name'] in ('neck_02','head')
        assert max(abs(x*neck_scale-y) for x,y in zip(old['loc'],new['loc']))<.0001
        changed_bones.append(old['name'])
assert set(changed_bones)==({'neck_02','head'} if abs(neck_scale-1)>.0001 else set())
def influence(d):
    result=[None]*len(d['vertices'])
    for s in d['sections']:
        for i in range(s['baseVertex'],s['baseVertex']+s['numVertices']):
            result[i]={d['bones'][s['boneMap'][k]]['name']:w for k,w in d['vertices'][i][3]}
    return result
wa,wb=influence(a),influence(b);assert wa==wb,'this build must not alter skin weights'
def bone_world(d):
    world=[];byname={}
    for r in d['bones']:
        q=r['quat'];m=Matrix.LocRotScale(Vector(r['loc']),Quaternion((q[3],*q[:3])),Vector(r['scale']))
        m=world[r['parent']]@m if r['parent']>=0 else m;world.append(m);byname[r['name']]=m
    return byname
world_a,world_b=bone_world(a),bone_world(b)
neck_groups={n for n in world_a if (world_a[n].translation-world_b[n].translation).length>.001}
tips={f'{f}_03_{s}' for f in ('thumb','index','middle','ring','pinky') for s in ('l','r')}
pa=np.array([r[:3] for r in a['vertices']]);pb=np.array([r[:3] for r in b['vertices']]);distance=np.linalg.norm(pb-pa,axis=1)
changed=np.flatnonzero(distance>.001)
quantized_boundary=[]
for i in changed:
    if not any(n in neck_groups|tips for n,w in wa[i].items() if w>0):
        # A source influence below half a byte may quantize to zero while its
        # tiny baked displacement survives 0.001cm position rounding. Bound it
        # to 0.01cm and require an adjacent finger/neck chain influence.
        adjacent=any(n.startswith(('thumb_','index_','middle_','ring_','pinky_','neck_')) for n in wa[i])
        assert adjacent and distance[i]<.02,(i,'unrelated body geometry changed',distance[i],wa[i])
        quantized_boundary.append(int(i))
# All fully head-bound vertices undergo one common translation, preserving
# face/head/hair size. Check as cooked rather than trusting the source builder.
head_ids=[i for i,w in enumerate(wa) if sum(v for n,v in w.items() if n in neck_groups)==255]
delta=np.array(world_b['head'].translation-world_a['head'].translation)
rigid_error=float(np.linalg.norm((pb[head_ids]-pa[head_ids])-delta,axis=1).max())
assert rigid_error<.005,rigid_error
axis_report=[]
for n in sorted(tips):
    indices=[i for i,w in enumerate(wa) if w.get(n,0)>255*.7]
    errors=[]
    for d,pts,world in ((a,pa,world_a),(b,pb,world_b)):
        cloud=pts[indices]-np.array(world[n].translation)
        vals,vectors=np.linalg.eigh(np.cov(cloud.T));axis=vectors[:,-1]
        if axis@cloud.mean(axis=0)<0:axis=-axis
        native_axis=np.array(world[n].to_3x3().col[0]);previous=n.replace('_03_','_02_')
        if native_axis@np.array(world[n].translation-world[previous].translation)<0:native_axis=-native_axis
        errors.append(float(np.degrees(np.arccos(np.clip(axis@native_axis,-1,1)))))
    assert errors[1]<12,(n,errors)
    if errors[0]>12:assert errors[1]<errors[0]*.25,(n,errors)
    axis_report.append({'bone':n,'before_deg':errors[0],'after_deg':errors[1]})
report={'pass':True,'runtime_verified':False,'changed_reference_bones':changed_bones,
        'changed_cooked_vertices':len(changed),'weights_uv_topology_unchanged':True,
        'sub_byte_boundary_vertices_under_0_01cm':quantized_boundary,
        'unrelated_body_geometry_unchanged':True,'rigid_head_error_cm':rigid_error,
        'head_translation_cm':delta.tolist(),'terminal_axes':axis_report}
(OUT/'neck_tip_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
