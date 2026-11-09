"""Load the current UE mesh and its native dependencies and report asset checks."""
import json,os
from pathlib import Path
import unreal as u

workspace=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
output=Path(os.environ.get('PBZ_BUILD_DIR',str(workspace/'Builds/current')))
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game','/HuaShira'],True)
hero='/HuaShira/Characters/Hero/Hero_Hun'
paths={'mesh':hero+'/SkinParts/Hun_Body_Simple','skeleton':hero+'/Hun_Skin_Skeleton','physics':hero+'/PA_Hun',
       'material':'/Game/PBZContent/Characters/Hero/Hun_New_V2b/Material/MI_ZeroHun_Cap_01_b'}
assets={name:u.load_asset(path) for name,path in paths.items()}
assert all(assets.values()),paths
mesh=assets['mesh'];assert mesh.skeleton==assets['skeleton']
assert mesh.get_editor_property('physics_asset')==assets['physics']
assert all(slot.material_interface==assets['material'] for slot in mesh.get_editor_property('materials'))
modifier=u.SkeletonModifier();assert modifier.set_skeletal_mesh(mesh)
names=[str(name) for name in modifier.get_all_bone_names()]
assert len(names)==264 and names[0]=='root'
for row in json.loads((output/'mesh_refpose.json').read_text())['bones']:
    t=modifier.get_bone_transform(row['name'],False)
    assert (t.translation-u.Vector(*row['loc'])).length()<.001,row['name']
report={'pass':True,'assets':paths,'bones':len(names),'root':names[0],
        'materials':len(mesh.get_editor_property('materials')),'runtime_verified':False}
(output/'project_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('@@JSON@@'+json.dumps(report))
