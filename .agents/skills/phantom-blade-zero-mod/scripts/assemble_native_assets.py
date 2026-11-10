"""Assemble native body, class-correct blank parts, and the package allowlist."""
import json,hashlib,os
from pathlib import Path
import unreal as u
ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4])); QA=ROOT/'Builds/current'; OUT=Path(os.environ.get('PBZ_BUILD_DIR',str(QA)))
qa_file=OUT/'clean_asset_report.json'
if not qa_file.exists():qa_file=OUT/'source_asset_qa.json'
assert json.loads(qa_file.read_text(encoding='utf8'))['asset_qa']['pass']
record=json.loads((OUT/'refpose_validation.json').read_text(encoding='utf8'))
assert not record['bad_refpose'] and record['root']=='root' and record['bones']==264
EAL=u.EditorAssetLibrary; AT=u.AssetToolsHelpers.get_asset_tools()
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game','/HuaShira'],True)
native=u.load_asset('/HuaShira/Characters/Hero/Hero_Hun/Hun_Skin_Skeleton')
mi=u.load_asset('/Game/PBZContent/Characters/Hero/Hun_New_V2b/Material/MI_ZeroHun_Cap_01_b')
source=u.load_asset(record['mesh']); assert source and source.skeleton==native
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.SyncToBrowser 0')
def drop(path):
    if EAL.does_asset_exist(path):
        assert EAL.delete_asset(path),path
        u.SystemLibrary.collect_garbage()
def refpose(mesh):
    mod=u.SkeletonModifier(); assert mod.set_skeletal_mesh(mesh)
    names={str(n).lower():str(n) for n in mod.get_all_bone_names()}; ns=[]; ts=[]
    for row in json.loads((ROOT/'Pipeline/native-zero/reference/native_body_mesh.json').read_text())['bones']:
        t=u.Transform(); t.translation=u.Vector(*row['loc']); t.rotation=u.Quat(*row['quat']); t.scale3d=u.Vector(1,1,1)
        ns.append(names[row['name'].lower()]); ts.append(t)
    assert mod.set_bones_transforms(ns,ts,False); mod.commit_skeleton_to_skeletal_mesh()
    assert mesh.skeleton==native
def import_blank(is_static=False):
    filename=ROOT/'Pipeline/native-zero/source'/('native_blank_static.fbx' if is_static else 'native_blank.fbx')
    name=('EmptyStatic_' if is_static else 'EmptyPart_')+hashlib.sha256(filename.read_bytes()).hexdigest()[:10]
    path='/Game/NativeZero/'+name
    if not EAL.does_asset_exist(path):
        opts=u.FbxImportUI(); opts.automated_import_should_detect_type=False
        opts.import_as_skeletal=not is_static; opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH if is_static else u.FBXImportType.FBXIT_SKELETAL_MESH
        opts.import_materials=False; opts.import_textures=False; opts.import_animations=False; opts.create_physics_asset=False
        if not is_static: opts.skeleton=native
        data=opts.static_mesh_import_data if is_static else opts.skeletal_mesh_import_data
        data.set_editor_property('convert_scene',True); data.set_editor_property('convert_scene_unit',True)
        if is_static:
            opts.static_mesh_import_data.set_editor_property('remove_degenerates',False)
        task=u.AssetImportTask(); task.filename=str(filename); task.destination_path='/Game/NativeZero'; task.destination_name=name
        task.automated=True; task.replace_existing=True; task.save=True; task.options=opts
        AT.import_asset_tasks([task])
    mesh=u.load_asset(path); assert mesh
    if is_static:
        assert mesh.get_class().get_name()=='StaticMesh'
        mesh.set_material(0,mi)
    else:
        assert mesh.get_class().get_name()=='SkeletalMesh'
        refpose(mesh)
        mesh.set_editor_property('post_process_anim_blueprint',None)
        mesh.set_editor_property('physics_asset',None)
        mesh.set_editor_property('materials',[u.SkeletalMaterial(material_interface=mi,material_slot_name='Invisible',uv_channel_data=u.MeshUVChannelInfo())])
    assert EAL.save_loaded_asset(mesh,False)
    return path
blank=import_blank(); static_blank=import_blank(True)
rows=json.loads((ROOT/'Pipeline/native-zero/reference/native_asset_classes.json').read_text())
rows+=json.loads((ROOT/'Pipeline/native-zero/reference/native_static_cape_class.json').read_text())
assembly=[]; allow=[]
def package_path(file):
    if file.startswith('ProjectPBZ/Plugins/HuaShira/Content/'):
        return '/HuaShira/'+file.split('/Content/',1)[1][:-7]
    assert file.startswith('ProjectPBZ/Content/')
    return '/Game/'+file[len('ProjectPBZ/Content/'):-7]
for row in rows:
    typ=row['type']
    if typ not in ('SkeletalMesh','ChaosClothAsset','StaticMesh'): continue
    path=package_path(row['path'])
    if typ=='ChaosClothAsset':
        asset=u.load_asset(path) if EAL.does_asset_exist(path) else None
        if asset is not None and asset.get_class().get_name()!='ChaosClothAsset':
            drop(path); asset=None
        if asset is None:
            asset=AT.create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.ChaosClothAsset,u.ChaosClothAssetFactory())
        assert asset
    else:
        asset=None
        drop(path)
        src=record['mesh'] if row['name']=='Hun_Body_Simple' else (static_blank if typ=='StaticMesh' else blank)
        assert EAL.duplicate_asset(src,path),path
        asset=u.load_asset(path)
    assert asset.get_class().get_name()==typ,(path,typ,asset.get_class().get_name())
    assert EAL.save_loaded_asset(asset,False),path
    allow.append(row['path'][len('ProjectPBZ/'):])
    assembly.append({'path':path,'original_class':typ,'replacement_class':asset.get_class().get_name(),'action':'body' if row['name']=='Hun_Body_Simple' else 'blank'})
for suffix in ('BC','N','ARM'):
    allow.append('Content/PBZContent/Characters/Hero/Hun_New_V2b/Textures/T_ZeroHun_Cap_V02_'+suffix+'.uasset')
assert len(allow)==len(set(allow))
(OUT/'production_allowlist.json').write_text(json.dumps(allow,indent=2),encoding='utf8')
(OUT/'assembly_report.json').write_text(json.dumps({'source':record['mesh'],'assets':assembly,'native_skeleton_shipped':False,'native_physics_shipped':False,'material_instances_shipped':False},indent=2),encoding='utf8')
print('@@JSON@@'+json.dumps({'assets':len(assembly),'allowlist':len(allow)}))
