"""Validate native compatibility, planned bone lengths, section weights, and UVs."""
import json,math,sys,hashlib,os
from pathlib import Path
WORKSPACE=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
QA=WORKSPACE/'Builds/current'
OUT=Path(sys.argv[1])
d=json.loads((OUT/'cooked_mesh.json').read_text())
native=json.loads((WORKSPACE/'Pipeline/native-zero/reference/native_body_mesh.json').read_text())['bones']
plan=json.loads((OUT/'mesh_refpose.json').read_text())
def dist(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def norm(a):return math.sqrt(sum(x*x for x in a))
assert len(d['bones'])==len(native)==len(plan['bones'])==264
lengths=[]
planned={b['name'].lower():b for b in plan['bones']}; cooked={b['name'].lower():b for b in d['bones']}
for n in native:
    p=planned[n['name'].lower()];b=cooked[n['name'].lower()]
    assert n['name'].lower()==p['name'].lower()==b['name'].lower()
    np=native[n['parent']]['name'].lower() if n['parent']>=0 else None
    pp=plan['bones'][p['parent']]['name'].lower() if p['parent']>=0 else None
    bp=d['bones'][b['parent']]['name'].lower() if b['parent']>=0 else None
    assert np==pp==bp
    assert dist(p['loc'],b['loc'])<.001,(n['name'],'wrong cooked ref')
    assert abs(sum(x*y for x,y in zip(n['quat'],b['quat'])))>.99999
    assert max(abs(x-1) for x in b['scale'])<.00001
    mode=plan['modes'].get(n['name'].lower())
    ratio=norm(p['loc'])/norm(n['loc']) if norm(n['loc'])>1e-6 else 1
    if mode=='AnimationScaled':
        expected=[x*ratio for x in n['loc']]
        assert dist(expected,b['loc'])<.001,(n['name'],'AnimationScaled direction mismatch')
    else:
        assert dist(n['loc'],b['loc'])<.001,(n['name'],'unretargeted translation modified')
    if abs(ratio-1)>.00001:lengths.append({'bone':n['name'],'mode':mode,'ratio':ratio})
uv=d['vertex_uvs'];bad_uv=0;unweighted=0;max_infs=0
for s in d['sections']:
    for vi in range(s['baseVertex'],s['baseVertex']+s['numVertices']):
        infs=d['vertices'][vi][3];assert all(0<=i<len(s['boneMap']) and w>0 for i,w in infs)
        unweighted+=not infs;max_infs=max(max_infs,len(infs))
    ids=d['indices'][s['baseIndex']:s['baseIndex']+s['numTriangles']*3]
    for i in range(0,len(ids),3):
        a,b,c=[uv[x][0] for x in ids[i:i+3]]
        bad_uv+=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))<1e-12
assert not bad_uv and not unweighted and max_infs<=4
v=d['vertices'];height=max(x[2] for x in v)-min(x[2] for x in v)
assert 177<height<183,height
props=next(x for x in json.loads((OUT/'cooked_props.json').read_text(encoding='utf8')) if x['Type']=='SkeletalMesh')
assert props['Properties']['Skeleton']['ObjectPath'].startswith('/HuaShira/Characters/Hero/Hero_Hun/Hun_Skin_Skeleton.')
assert all(x['Material']['ObjectPath'].startswith('/Game/PBZContent/Characters/Hero/Hun_New_V2b/Material/MI_ZeroHun_Cap_01_b.') for x in props['SkeletalMaterials'])
report={'pass':True,'runtime_verified':False,'vertices':len(v),'triangles':len(d['indices'])//3,'bones':264,'height_cm':height,'unweighted':unweighted,'max_influences':max_infs,'zero_uv_faces':bad_uv,'changed_bone_lengths':lengths,'native_rotations_and_hierarchy_preserved':True,'animation_mode_translations_preserved':True}
(OUT/'cooked_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
