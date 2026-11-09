"""Compare a hand-weight build against the selected input build."""
import json,sys,os
from pathlib import Path
QA=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))/'Builds/current';BASE=Path(os.environ.get('PBZ_INPUT_BUILD',str(QA)));OUT=Path(sys.argv[1])
a=json.loads((BASE/'cooked_mesh.json').read_text());b=json.loads((OUT/'cooked_mesh.json').read_text())
assert a['bones']==b['bones'],'hand tuning must preserve skeleton and bind proportions'
assert a['indices']==b['indices'] and a['vertex_uvs']==b['vertex_uvs']
assert len(a['vertices'])==len(b['vertices']) and all(x[:3]==y[:3] for x,y in zip(a['vertices'],b['vertices']))
def influences(d):
    out=[None]*len(d['vertices'])
    for s in d['sections']:
        for vi in range(s['baseVertex'],s['baseVertex']+s['numVertices']):
            out[vi]={d['bones'][s['boneMap'][i]]['name']:w for i,w in d['vertices'][vi][3]}
    assert all(r is not None for r in out)
    return out
old,new=influences(a),influences(b)
allowed={n+'_'+s for s in ('l','r') for n in ('hand','thumb_01','thumb_02','thumb_03')}
changed=[];groups=set()
for vi,(x,y) in enumerate(zip(old,new)):
    assert sum(y.values())==255 and len(y)<=4
    for n in x.keys()|y.keys():
        if x.get(n,0)!=y.get(n,0):
            assert n in allowed,(vi,n,'non-thumb weight changed')
            groups.add(n)
    if x!=y:changed.append(vi)
assert changed,'build has no actual skin-weight change'
baseline_path=Path(os.environ.get('PBZ_BASELINE_GRIP_REPORT',str(QA/'grip_audit/grip_edge_audit.json')))
before=json.loads(baseline_path.read_text())['cases']
after=json.loads((OUT/'grip_audit/grip_edge_audit.json').read_text())['cases']
comparison={}
for label,r in after.items():
    previous=before[label]['finger_max_edge_increase_cm'];current=r['finger_max_edge_increase_cm']
    assert current<previous*.8,(label,previous,current)
    assert r['coincident_hand_vertex_max_gap_cm']<.005,(label,'UV split seam opens')
    comparison[label]={'baseline_cm':previous,'build_cm':current,'coincident_seam_gap_cm':r['coincident_hand_vertex_max_gap_cm']}
props=lambda p:next(x for x in json.loads(p.read_text(encoding='utf8')) if x['Type']=='SkeletalMesh')
op,np=props(BASE/'cooked_props.json'),props(OUT/'cooked_props.json')
for field in ('Skeleton','PhysicsAsset','PostProcessAnimBlueprint'):assert op['Properties'].get(field)==np['Properties'].get(field)
assert [r['Material'] for r in op['SkeletalMaterials']]==[r['Material'] for r in np['SkeletalMaterials']]
result={'pass':True,'runtime_verified':False,'geometry_uv_triangles_and_skeleton_identical':True,
        'non_thumb_weights_identical':True,'changed_cooked_vertices':len(changed),'changed_groups':sorted(groups),'stress_comparison':comparison}
(OUT/'regression_validation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
