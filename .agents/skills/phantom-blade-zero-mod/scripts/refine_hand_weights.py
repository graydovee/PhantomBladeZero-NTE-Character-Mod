"""Smooth local hand/thumb weights and synchronize coincident skin vertices."""
import bpy,json,os,sys,runpy,shutil
from pathlib import Path
from collections import defaultdict
import numpy as np
from mathutils.kdtree import KDTree

ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]));QA=ROOT/'Builds'/os.environ.get('PBZ_MOD','zero')/'current'
BASE=Path(os.environ.get('PBZ_INPUT_BUILD',str(QA)))
OUT=Path(os.environ['PBZ_BUILD_DIR'])
assert OUT.resolve()!=BASE.resolve(),'Choose a distinct working output directory'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'zero_clean.blend'))
mesh=next(o for o in bpy.data.objects if o.type=='MESH');arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
names=[g.name for g in mesh.vertex_groups];index={n:i for i,n in enumerate(names)}
original=np.zeros((len(mesh.data.vertices),len(names)),dtype=np.float64)
for v in mesh.data.vertices:
    for g in v.groups:original[v.index,g.group]=g.weight
coords=np.array([list(v.co) for v in mesh.data.vertices]);adj=defaultdict(set)
for e in mesh.data.edges:
    a,b=e.vertices;adj[a].add(b);adj[b].add(a)
# transfer across overlapping skin/glove surfaces or across adjacent fingers.
kd=KDTree(len(coords))
for i,p in enumerate(coords):kd.insert(p,i)
kd.balance()
duplicates={}
for i,p in enumerate(coords):
    match=sorted(j for _,j,_ in kd.find_range(p,1e-4))
    if len(match)>1:duplicates[tuple(match)]=match
    for j in match:
        if j!=i:adj[i].add(j)
regions={}
for side in ('l','r'):
    cols=[index[n+'_'+side] for n in ('hand','thumb_01','thumb_02','thumb_03')]
    thumb=original[:,cols[1:]].sum(axis=1)
    allowed=original[:,cols].sum(axis=1)>.99999
    active=set(np.flatnonzero((thumb>.005)&allowed).tolist())
    for _ in range(2):
        active|={j for i in list(active) for j in adj[i] if allowed[j]}
    seams=[ids for ids in duplicates.values() if all(i in active for i in ids)]
    regions[side]={'cols':cols,'verts':sorted(active),'thumb':thumb,'seams':seams}
def normalized(a):
    # Preserve a four-influence budget and original byte quantization behavior.
    keep=np.argsort(a,axis=1)[:,-4:];out=np.zeros_like(a)
    np.put_along_axis(out,keep,np.take_along_axis(a,keep,axis=1),axis=1)
    out/=out.sum(axis=1,keepdims=True)
    return out
def smooth(steps,strength):
    a=original.copy()
    for _ in range(steps):
        prev=a.copy()
        for side,r in regions.items():
            c=r['cols'];active=set(r['verts'])
            for i in active:
                neighbors=[j for j in adj[i] if j in active]
                if not neighbors:continue
                # Pin the far end of each phalanx and the unaffected palm.
                mixed=1-float(prev[i,c].max())
                blend=strength*min(1,mixed*4+.15)
                a[i,c]=prev[i,c]*(1-blend)+prev[neighbors][:,c].mean(axis=0)*blend
            # UV/normal splits must receive exactly the same field, regardless
            # of their separate polygon neighborhoods. Prevent posed cracks.
            for ids in r['seams']:
                a[np.ix_(ids,c)]=a[np.ix_(ids,c)].mean(axis=0)
    return normalized(a)
ref=json.loads((BASE/'mesh_refpose.json').read_text(encoding='utf8'))
boneindex={b['name']:b['idx'] for b in ref['bones']}
triangles=[v for p in mesh.data.polygons for v in p.vertices]
def proxy(a,path):
    rows=[]
    for i,p in enumerate(coords):
        active=np.flatnonzero(a[i]>1e-8);ws=a[i,active];raw=ws/ws.sum()*255
        ints=np.floor(raw).astype(int)
        for j in np.argsort(raw-ints)[::-1][:255-int(ints.sum())]:ints[j]+=1
        pairs=[[boneindex[names[j]],int(w)] for j,w in zip(active,ints) if w]
        # Source .blend uses -Y front; cooked UE positions use +Y front.
        # The skin-test refpose is the actual UE dump, so reflect positions too.
        rows.append([float(p[0]),float(-p[1]),float(p[2]),pairs])
    data={'use16BitBoneWeight':False,'bones':ref['bones'],'vertices':rows,'indices':triangles,
          'sections':[{'baseVertex':0,'numVertices':len(coords),'boneMap':list(range(264)),'baseIndex':0,'numTriangles':len(triangles)//3,'mat':0}]}
    path.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
tests=[];variants={}
for label,steps,amount in [('baseline',0,0),('smooth_2',2,.35),('smooth_4',4,.35),('smooth_6',6,.35)]:
    a=smooth(steps,amount) if steps else original.copy();variants[label]=a
    folder=OUT/'experiments'/label;folder.mkdir(parents=True,exist_ok=True)
    proxy(a,folder/'mesh.json')
    saved_argv=sys.argv;sys.argv=['audit','--',str(folder/'mesh.json'),str(folder)]
    try:result=runpy.run_path(str(Path(__file__).resolve().parent/'audit_grip_deformation.py'))['report']
    finally:sys.argv=saved_argv
    scores={k:r['finger_max_edge_increase_cm'] for k,r in result['cases'].items()}
    tests.append({'variant':label,'iterations':steps,'strength':amount,'scores_cm':scores,
                  'seam_gaps_cm':{k:r['coincident_hand_vertex_max_gap_cm'] for k,r in result['cases'].items()},
                  'worst_cm':max(scores.values()),'changed_vertices':int(np.any(abs(a-original)>1e-7,axis=1).sum())})
minimum=min(tests[1:],key=lambda r:r['worst_cm'])
# Prefer the least diffusion within 5% of the best stress result, with a
# sub-centimetre target. This keeps an extra two passes from softening the root.
eligible=[t for t in tests[1:] if t['worst_cm']<1 and t['worst_cm']<=minimum['worst_cm']*1.05]
best=min(eligible,key=lambda r:r['iterations']) if eligible else minimum
reference_path=Path(os.environ.get('PBZ_BASELINE_GRIP_REPORT',str(QA/'grip_audit/grip_edge_audit.json')))
reference=json.loads(reference_path.read_text())
assert all(abs(tests[0]['scores_cm'][k]-r['finger_max_edge_increase_cm'])<.15 for k,r in reference['cases'].items()),'Source proxy must reproduce the cooked baseline before export'
assert best['worst_cm']<tests[0]['worst_cm']*.8,tests
selected=variants[best['variant']]
changed=np.flatnonzero(np.any(abs(selected-original)>1e-7,axis=1))
allowed_cols={c for r in regions.values() for c in r['cols']}
assert not np.any(abs(selected[:,[i for i in range(len(names)) if i not in allowed_cols]]-original[:,[i for i in range(len(names)) if i not in allowed_cols]])>1e-7)
for i in changed:
    for c in np.flatnonzero(original[i]):mesh.vertex_groups[int(c)].remove([int(i)])
    for c in np.flatnonzero(selected[i]>1e-8):mesh.vertex_groups[int(c)].add([int(i)],float(selected[i,c]),'REPLACE')
assert np.array_equal(coords,np.array([list(v.co) for v in mesh.data.vertices]))
report={'baseline':str(BASE/'zero_clean.blend'),'tests':tests,'selected':best,
        'geometry_unchanged':True,'skeleton_unchanged':True,'body_weights_unchanged':True,
        'modified_groups':sorted(names[i] for i in allowed_cols),'changed_vertices':len(changed)}
(OUT/'grip_refinement.json').write_text(json.dumps(report,indent=2),encoding='utf8')
for name in ('mesh_refpose.json','build_report.json','atlas_report.json','production_allowlist.json'):
    shutil.copy2(BASE/name,OUT/name)
shutil.copytree(BASE/'textures',OUT/'textures',dirs_exist_ok=True)
bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);arm.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'zero_clean.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'zero_clean.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},global_scale=1.,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,bake_anim=False,
    mesh_smooth_type='FACE',use_mesh_modifiers=False,use_armature_deform_only=False,path_mode='STRIP')
print('@@JSON@@'+json.dumps(report))
