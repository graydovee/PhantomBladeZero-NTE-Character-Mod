"""Audit the cleaned source mesh and record the asset QA gate before import."""
import bpy, json, os, sys, types, collections
from pathlib import Path
ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
OUT=Path(os.environ.get('PBZ_BUILD_DIR', str(ROOT/'Builds/current')))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'zero_clean.blend'))
mesh=next(o for o in bpy.data.objects if o.type=='MESH')
# Re-point image datablocks at this build's atlas so the QA gate reads real files.
repaired=[]
for img in bpy.data.images:
    target=OUT/'textures'/Path(img.filepath).name
    if img.filepath and Path(img.filepath)!=target and target.is_file():
        img.filepath=str(target); repaired.append(img.name)
if repaired:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'zero_clean.blend'))
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
skills=ROOT/'.agents/skills/blender-asset-qa/scripts'; sys.path.insert(0,str(skills))
module=types.ModuleType('qa_detail'); module.__file__=str(skills/'qa_check.py')
exec(compile((skills/'qa_check.py').read_text(encoding='utf8'),module.__file__,'exec'),module.__dict__)
qa=module.run(objects=[mesh.name],profile='game',eps=.02,tol=.2)
co=[v.co for v in mesh.data.vertices]
unweighted=0; max_inf=0; worst_sum=0.0
for v in mesh.data.vertices:
    w=[g.weight for g in v.groups if g.weight>0]
    if not w: unweighted+=1
    max_inf=max(max_inf,len(w)); worst_sum=max(worst_sum,abs(sum(w)-1.0))
report={'stage':'source_mesh_audit','blend':str(OUT/'zero_clean.blend'),
        'asset_qa':qa,'unweighted_vertices':unweighted,'max_influences':max_inf,
        'max_weight_sum_error':worst_sum,'uv_layers':len(mesh.data.uv_layers),
        'vertices':len(mesh.data.vertices),'polygons':len(mesh.data.polygons),
        'bones':len(arm.data.bones),'texture_paths_repaired':repaired,'height_cm':max(c.z for c in co)-min(c.z for c in co)}
assert qa['pass'] and unweighted==0 and max_inf<=4 and worst_sum<1e-4 and len(arm.data.bones)==263, report
(OUT/'source_asset_qa.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('@@JSON@@'+json.dumps({k:v for k,v in report.items() if k!='asset_qa'}))
