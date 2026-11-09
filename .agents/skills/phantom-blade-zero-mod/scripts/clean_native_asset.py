"""Clean source mesh topology and write the native export and asset QA report."""
import bpy,bmesh,json,sys,types,os
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
OUT=Path(os.environ.get('PBZ_BUILD_DIR',str(ROOT/'Builds/current')))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'zero_atlas.blend'))
mesh=next(o for o in bpy.data.objects if o.type=='MESH')
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
bm=bmesh.new(); bm.from_mesh(mesh.data)
removed=[f for f in bm.faces if f.material_index in (0,4)]
report={'removed_shader_only_faces':len(removed)}
bmesh.ops.delete(bm,geom=removed,context='FACES')
bmesh.ops.dissolve_degenerate(bm,dist=1e-6,edges=list(bm.edges))
tiny=[f for f in bm.faces if f.calc_area()<1e-10]
bmesh.ops.delete(bm,geom=tiny,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
report['tiny_faces_removed']=len(tiny)
# Ensure UV differentials exist even on intentionally solid-color source faces.
# tangents in Unreal's normal-map pipeline.
uv=mesh.data.uv_layers[0]; fixed=0
for p in mesh.data.polygons:
    ls=list(p.loop_indices); a,b,c=[uv.data[i].uv.copy() for i in ls]
    if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<2e-12:
        center=(a+b+c)/3; r=1/8192
        for li,xy in zip(ls,((0,0),(r,0),(0,r))): uv.data[li].uv=center+Vector(xy)
        fixed+=1
report['constant_sample_uv_triangles_repaired']=fixed
vs={v for p in mesh.data.polygons if p.material_index==3 for v in p.vertices}
for i in vs: mesh.data.vertices[i].co+=mesh.data.vertices[i].normal*.05
mesh.data.update()
skills=ROOT/'.agents/skills/blender-asset-qa/scripts'; sys.path.insert(0,str(skills))
module=types.ModuleType('qa_detail'); module.__file__=str(skills/'qa_check.py')
source=(skills/'qa_check.py').read_text(encoding='utf8')
source=source.replace('    zf = _describe(zf_pairs)','    global PAIRS\n    PAIRS = sorted(zf_pairs)\n    zf = _describe(zf_pairs)')
exec(compile(source,module.__file__,'exec'),module.__dict__)
# Resolve the remaining button/strap layers by translating the smaller connected
# island. No welding across clothing layers and no arbitrary face deletion.
adj=defaultdict(set)
for e in mesh.data.edges:
    a,b=e.vertices; adj[a].add(b); adj[b].add(a)
island={}; members=[]
for v in mesh.data.vertices:
    if v.index in island: continue
    todo=[v.index]; idx=len(members); acc=[]; island[v.index]=idx
    while todo:
        k=todo.pop(); acc.append(k)
        for n in adj[k]:
            if n not in island: island[n]=idx; todo.append(n)
    members.append(acc)
area=defaultdict(float)
for p in mesh.data.polygons: area[island[p.vertices[0]]]+=p.area
adjusted=[]
for attempt in range(3):
    qa=module.run(objects=[mesh.name],profile='game',eps=.02,tol=.2)
    if not module.PAIRS: break
    moves={}
    for i,j in module.PAIRS:
        a,b=mesh.data.polygons[i],mesh.data.polygons[j]
        ia,ib=island[a.vertices[0]],island[b.vertices[0]]
        if ia==ib: continue
        target,face=(ia,a) if area[ia]<area[ib] else (ib,b)
        moves.setdefault(target,face.normal.copy()*.05)
    if not moves: break
    for idx,delta in moves.items():
        for vi in members[idx]: mesh.data.vertices[vi].co+=delta
        adjusted.append({'island':idx,'vertices':len(members[idx]),'delta_cm':list(delta)})
    mesh.data.update()
report['detail_island_clearance_adjustments']=adjusted
qa=module.run(objects=[mesh.name],profile='game',eps=.02,tol=.2)
report['asset_qa']=qa
(OUT/'clean_asset_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('@@JSON@@'+json.dumps(report))
bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'zero_clean.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'zero_clean.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},global_scale=1.,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,bake_anim=False,
    mesh_smooth_type='FACE',use_mesh_modifiers=False,use_armature_deform_only=False,path_mode='STRIP')
