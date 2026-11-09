"""Measure cooked hand deformation, per-finger edge stretch, and coincident seam gaps."""
import json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
args=sys.argv[sys.argv.index('--')+1:]
SRC=Path(args[0]);OUT=Path(args[1]);OUT.mkdir(parents=True,exist_ok=True)
d=json.loads(SRC.read_text());v=np.array([r[:3] for r in d['vertices']],dtype=float)
bones=d['bones'];lookup={b['name']:b['idx'] for b in bones};local=[];world=[]
for b in bones:
    q=b['quat'];m=Matrix.LocRotScale(Vector(b['loc']),Quaternion((q[3],*q[:3])),Vector(b['scale']))
    local.append(m);world.append(world[b['parent']]@m if b['parent']>=0 else m)
wi=np.linalg.inv(np.array(world));pos=np.c_[v,np.ones(len(v))]
weights=np.zeros((len(v),len(bones)),dtype=np.float32)
for s in d['sections']:
    for i in range(s['baseVertex'],s['baseVertex']+s['numVertices']):
        pairs=d['vertices'][i][3];total=sum(w for _,w in pairs)
        for bi,w in pairs:weights[i,s['boneMap'][bi]]=w/total
tris=np.array(d['indices']).reshape(-1,3)
edges=np.unique(np.sort(np.concatenate([tris[:,[0,1]],tris[:,[1,2]],tris[:,[0,2]]]),axis=1),axis=0)
rest=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
fingerbones=[i for i,b in enumerate(bones) if b['name'].startswith(('index_','middle_','ring_','pinky_','thumb_'))]
finger_mask=weights[:,fingerbones].sum(axis=1)>.001
edge_mask=finger_mask[edges].any(axis=1)
coincident={}
for i,p in enumerate(v):
    if finger_mask[i]:coincident.setdefault(tuple(p),[]).append(i)
seams=[ids for ids in coincident.values() if len(ids)>1]
report={'input':str(SRC),'synthetic_stress_only':True,'cases':{}}
for label,axis,angles in [('z_curl',(0,0,1),(60,85,70)),('z_reverse',(0,0,1),(-60,-85,-70)),('y_curl',(0,1,0),(60,85,70)),('y_reverse',(0,1,0),(-60,-85,-70)),('relaxed',(0,0,1),(-30,-20,-15)),('tip_z',(0,0,1),(0,0,75)),('tip_z_reverse',(0,0,1),(0,0,-75)),('tip_y',(0,1,0),(0,0,75)),('tip_y_reverse',(0,1,0),(0,0,-75))]:
    posed=[]
    for b,m in zip(bones,local):
        n=b['name'];p=b['parent'];rot=Matrix.Identity(4)
        if n.startswith(('index_','middle_','ring_','pinky_','thumb_')):
            seg=n.split('_')[-2]
            if seg in ('01','02','03'):
                sign=1 if n.endswith('_l') else -1
                rot=Quaternion(axis,math.radians(angles[int(seg)-1]*sign)).to_matrix().to_4x4()
        posed.append((posed[p] if p>=0 else Matrix.Identity(4))@m@rot)
    matrices=np.array(posed)@wi
    deformed=np.zeros_like(v)
    for i in np.flatnonzero(weights.sum(axis=0)):
        use=weights[:,i]>0
        deformed[use]+=(pos[use]@matrices[i].T)[:,:3]*weights[use,i,None]
    stretch=np.linalg.norm(deformed[edges[:,0]]-deformed[edges[:,1]],axis=1)-rest
    ranked=np.argsort(np.where(edge_mask,stretch,-np.inf))[-15:][::-1]
    worst=[]
    for ei in ranked:
        a,b=edges[ei];worst.append({'edge':[int(a),int(b)],'rest_cm':float(rest[ei]),'increase_cm':float(stretch[ei]),
            'rest_points':[v[a].tolist(),v[b].tolist()],
            'weights':[{bones[i]['name']:round(float(weights[j,i]),4) for i in np.flatnonzero(weights[j])} for j in (a,b)]})
    each={}
    for side in ('l','r'):
        for finger in ('thumb','index','middle','ring','pinky'):
            bs=[i for i,b in enumerate(bones) if b['name'].startswith(finger+'_') and b['name'].endswith('_'+side)]
            mask=(weights[:,bs].sum(axis=1)>.1)[edges].any(axis=1)
            each[finger+'_'+side]=float(stretch[mask].max()) if mask.any() else None
    seam_gaps=[float(np.linalg.norm(deformed[ids]-deformed[ids[0]],axis=1).max()) for ids in seams]
    report['cases'][label]={'finger_max_edge_increase_cm':float(stretch[edge_mask].max()),'per_finger':each,'worst_edges':worst,
        'coincident_hand_vertex_max_gap_cm':max(seam_gaps,default=0.),'coincident_hand_groups':len(seams)}
(OUT/'grip_edge_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
for k,r in report['cases'].items():print(k,r['finger_max_edge_increase_cm'],r['per_finger'])
