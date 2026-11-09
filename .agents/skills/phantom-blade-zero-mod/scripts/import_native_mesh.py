"""Import the character with its native Skeleton, reference pose, and texture settings."""
import json, hashlib, os
from pathlib import Path
import unreal as u

ROOT=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))
OUT=Path(os.environ.get('PBZ_BUILD_DIR',str(ROOT/'Builds/current')))
asset_name='NativeMesh_'+hashlib.sha256((OUT/'zero_clean.fbx').read_bytes()).hexdigest()[:10]
mesh_path='/Game/NativeZero/'+asset_name
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/HuaShira','/Game'],True)
native_path='/HuaShira/Characters/Hero/Hero_Hun/Hun_Skin_Skeleton'
native=u.load_asset(native_path)
assert native
mesh=u.load_asset(mesh_path) if u.EditorAssetLibrary.does_asset_exist(mesh_path) else None
if mesh is None:  # Each changed FBX uses a fresh QA name; existing binding is checked.
    opts=u.FbxImportUI()
    opts.import_as_skeletal=True
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opts.automated_import_should_detect_type=False
    opts.skeleton=native
    opts.import_materials=False
    opts.import_textures=False
    opts.import_animations=False
    opts.create_physics_asset=False
    opts.skeletal_mesh_import_data.set_editor_property('convert_scene',True)
    opts.skeletal_mesh_import_data.set_editor_property('convert_scene_unit',True)
    opts.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    task=u.AssetImportTask()
    task.filename=str(OUT/'zero_clean.fbx')
    task.destination_path='/Game/NativeZero'
    task.destination_name=asset_name
    task.automated=True
    task.replace_existing=True
    task.options=opts
    task.save=True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(mesh_path)
assert mesh
assert mesh.skeleton == native, str(mesh.skeleton)
build=u.SkeletalMeshEditorSubsystem.get_lod_build_settings(mesh,0)
build.set_editor_property('use_full_precision_u_vs',True)
build.set_editor_property('threshold_uv',.00001)
u.SkeletalMeshEditorSubsystem.set_lod_build_settings(mesh,0,build)
ref_file=OUT/'mesh_refpose.json'
if not ref_file.exists():ref_file=ROOT/'Pipeline/native-zero/reference/native_body_mesh.json'
ref=json.loads(ref_file.read_text(encoding='utf-8'))['bones']
mod=u.SkeletonModifier()
assert mod.set_skeletal_mesh(mesh)
names=[str(n) for n in mod.get_all_bone_names()]
lookup={n.lower():n for n in names}
dst=[]
transforms=[]
for row in ref:
    name=lookup.get(row['name'].lower())
    assert name is not None, row['name']
    t=u.Transform()
    t.translation=u.Vector(*row['loc'])
    t.rotation=u.Quat(*row['quat'])
    t.scale3d=u.Vector(1,1,1)
    dst.append(name)
    transforms.append(t)
assert mod.set_bones_transforms(dst,transforms,False)
mod.commit_skeleton_to_skeletal_mesh()
assert mesh.skeleton == native
mesh.set_editor_property('post_process_anim_blueprint',None)
mi=u.load_asset('/Game/PBZContent/Characters/Hero/Hun_New_V2b/Material/MI_ZeroHun_Cap_01_b')
assert mi
slots=mesh.get_editor_property('materials')
mesh.set_editor_property('materials',[u.SkeletalMaterial(material_interface=mi,
    material_slot_name=s.material_slot_name,uv_channel_data=u.MeshUVChannelInfo()) for s in slots])
pa=u.load_asset('/HuaShira/Characters/Hero/Hero_Hun/PA_Hun')
assert pa
mesh.set_editor_property('physics_asset',pa)
assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
# Reopen the modifier to validate persistence, including centimetres and scale.
check=u.SkeletonModifier()
assert check.set_skeletal_mesh(mesh)
bad=[]
for name,t in zip(dst,transforms):
    got=check.get_bone_transform(name,False)
    dt=(got.translation-t.translation).length()
    dot=abs(got.rotation.x*t.rotation.x+got.rotation.y*t.rotation.y+got.rotation.z*t.rotation.z+got.rotation.w*t.rotation.w)
    if dt>.001 or dot<.99999: bad.append({'bone':name,'translation_cm':dt,'quat_dot':dot})
assert not bad, bad[:5]
registry=u.AssetRegistryHelpers.get_asset_registry()
opts=u.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=False)
rawdeps=registry.get_dependencies(mesh_path,opts)
deps=[str(x) for x in rawdeps] if rawdeps else []
report={'mesh':mesh_path,'skeleton':mesh.skeleton.get_path_name(),
        'bones':len(dst),'root':names[0],'bad_refpose':bad,'hard_dependencies':deps,
        'runtime_verified':False}
(OUT/'refpose_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Use game's existing material/shaders. Only these texture packages are shipped.
texdir='/Game/PBZContent/Characters/Hero/Hun_New_V2b/Textures'
textures=[]
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.PNG 0')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.SyncToBrowser 0')
for suffix in ('BC','N','ARM'):
    name='T_ZeroHun_Cap_V02_'+suffix
    task=u.AssetImportTask(); task.filename=str(OUT/'textures'/f'{name}.png')
    task.destination_path=texdir; task.destination_name=name
    task.automated=True; task.replace_existing=True; task.save=True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(texdir+'/'+name); assert tex
    tex.set_editor_property('srgb',suffix=='BC')
    tex.set_editor_property('compression_settings',{'BC':u.TextureCompressionSettings.TC_DEFAULT,
        'N':u.TextureCompressionSettings.TC_NORMALMAP,'ARM':u.TextureCompressionSettings.TC_MASKS}[suffix])
    tex.set_editor_property('virtual_texture_streaming',True)
    assert u.EditorAssetLibrary.save_loaded_asset(tex,False)
    textures.append(tex.get_path_name())
report['textures']=textures
(OUT/'refpose_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('@@JSON@@'+json.dumps(report))
