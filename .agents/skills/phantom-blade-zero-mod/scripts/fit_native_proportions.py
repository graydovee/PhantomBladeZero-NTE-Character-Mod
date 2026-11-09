"""Fit AnimationScaled lengths and palm/finger directions using native data."""
import json,math
from pathlib import Path
import bpy
import os
from mathutils import Matrix,Vector,Quaternion

def fit(donor,source,main,out):
    qa=Path(os.environ.get('PBZ_WORKSPACE_ROOT', Path(__file__).resolve().parents[4]))/'Pipeline'/'native-zero'/'reference'
    raw=json.loads((qa/'native_body_mesh.json').read_text())['bones']
    skeleton=next(x for x in json.loads((qa/'native_skeleton_props.json').read_text(encoding='utf8')) if x['Type']=='Skeleton')
    modes={b['Name'].lower():m.get('TranslationRetargetingMode','Animation').split('::')[-1]
           for b,m in zip(skeleton['ReferenceSkeleton']['FinalRefBoneInfo'],skeleton['Properties']['BoneTree'])}
    old={b.name:donor.matrix_world@b.matrix_local for b in donor.data.bones}
    src={g:source.matrix_world@source.pose.bones[z].head for g,z in main.items() if z in source.pose.bones}
    native={r['name']:r for r in raw}
    ratios={}
    def length(g,p):return (src[g]-src[p]).length
    def native_length(n):return Vector(native[n]['loc']).length
    ratios['pelvis']=src['pelvis'].z/(old['pelvis'].translation.z)
    for n,p in [('spine_01','pelvis'),('spine_02','spine_01'),('spine_03','spine_02')]:ratios[n]=length(n,p)/native_length(n)
    ratio=length('neck_01','spine_03')/sum(native_length(n) for n in ('spine_04','spine_05','neck_01'))
    for n in ('spine_04','spine_05','neck_01'):ratios[n]=ratio
    ratio=length('head','neck_01')/sum(native_length(n) for n in ('neck_02','head'))
    ratios['neck_02']=ratios['head']=ratio
    for side in ('l','r'):
        ratios['clavicle_'+side]=abs(src['clavicle_'+side].x)/abs(old['clavicle_'+side].translation.x)
        for n,p in [('upperarm','clavicle'),('lowerarm','upperarm'),('hand','lowerarm'),('calf','thigh'),('foot','calf'),('ball','foot')]:
            ratios[n+'_'+side]=length(n+'_'+side,p+'_'+side)/native_length(n+'_'+side)
        ratios['thigh_'+side]=length('thigh_'+side,'pelvis')/native_length('thigh_'+side)
    # Source pose has small asymmetric shoulder offsets. Bone lengths remain
    # bilateral so a bind checkpoint does not bake asymmetry into proportions.
    for n in ('clavicle','upperarm','lowerarm','hand','thigh','calf','foot','ball'):
        avg=.5*(ratios[n+'_l']+ratios[n+'_r'])
        ratios[n+'_l']=ratios[n+'_r']=avg
    world={}; custom=[]; skipped={}
    for row in raw:
        n=row['name']; r=ratios.get(n,1.)
        if modes.get(n.lower())!='AnimationScaled' and r!=1:
            skipped[n]={'mode':modes.get(n.lower()),'requested_ratio':r};r=1.
        b=dict(row);b['loc']=[x*r for x in row['loc']];custom.append(b)
        q=b['quat'];local=Matrix.LocRotScale(Vector(b['loc']),Quaternion((q[3],*q[:3])),Vector(b['scale']))
        world[b['idx']]=world[b['parent']]@local if b['parent']>=0 else local
    target={b['name']:Vector((world[b['idx']].translation.x,-world[b['idx']].translation.y,world[b['idx']].translation.z)) for b in custom}
    bpy.context.view_layer.objects.active=donor
    bpy.ops.object.mode_set(mode='EDIT')
    inv=donor.matrix_world.inverted()
    for eb in donor.data.edit_bones:
        eb.use_connect=False
    for eb in donor.data.edit_bones:
        m=old[eb.name].copy();m.translation=target[eb.name];eb.matrix=inv@m
    bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()
    def aim(pb,a,b):
        q=a.normalized().rotation_difference(b.normalized())
        h=pb.matrix.translation.copy();pb.matrix=Matrix.Translation(h)@q.to_matrix().to_4x4()@Matrix.Translation(-h)@pb.matrix
        bpy.context.view_layer.update()
    # A single direction leaves palm roll underdetermined; use middle knuckle
    # and index-to-pinky spread to define the full orientation on each hand.
    for side in ('l','r'):
        z=main['hand_'+side];hand=source.pose.bones[z]
        def srcpos(g):return source.pose.bones[main[g+'_'+side]].head.copy()
        sh=hand.head.copy();dh=donor.data.bones['hand_'+side].head_local
        def frame(fwd,spread):
            y=fwd.normalized();x=(spread-y*spread.dot(y)).normalized();z=x.cross(y).normalized()
            return Matrix((x,y,z)).transposed()
        sf=frame(srcpos('middle_01')-sh,srcpos('index_01')-srcpos('pinky_01'))
        df=frame(donor.data.bones['middle_01_'+side].head_local-dh,
                 donor.data.bones['index_01_'+side].head_local-donor.data.bones['pinky_01_'+side].head_local)
        rotation=df@sf.inverted();h=hand.matrix.translation.copy()
        hand.matrix=Matrix.Translation(h)@rotation.to_4x4()@Matrix.Translation(-h)@hand.matrix
        bpy.context.view_layer.update()
        for finger in ('thumb','index','middle','ring','pinky'):
            for a,b in (('01','02'),('02','03')):
                g=f'{finger}_{a}_{side}';ch=f'{finger}_{b}_{side}'
                pb=source.pose.bones[main[g]]
                aim(pb,source.pose.bones[main[ch]].head-pb.head,
                    donor.data.bones[ch].head_local-donor.data.bones[g].head_local)
            g=f'{finger}_03_{side}';pb=source.pose.bones[main[g]]
            children=list(pb.children)
            if children:
                prev=donor.data.bones[f'{finger}_02_{side}'].head_local
                aim(pb,children[0].head-pb.head,donor.data.bones[g].head_local-prev)
    bpy.context.view_layer.update()
    (out/'mesh_refpose.json').write_text(json.dumps({'bones':custom,'modes':modes,'ratios':ratios,'unscaled_animation_bones':skipped},indent=2),encoding='utf8')
    return {'ratios':ratios,'unscaled_animation_bones':skipped,'reference':'native rotations and hierarchy; AnimationScaled lengths only'}
