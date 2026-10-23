"""Build an experimental world-space scalp target; does not operate CC.

Uses the installed Clean Soft alpha as a provisional geometry partition, not a
production anatomical mask. Keeps B face and non-head vertices; zero-mask head
vertices come from A. The accompanying bridge probe checks save/reload error.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from cc_compare_headshot_geometry_v1 import head_ids, mask_weights, read_obj


def build(a_dir, b_dir, output):
    a_dir=Path(a_dir);b_dir=Path(b_dir);output=Path(output)
    ja=json.loads((a_dir/'before_world_mesh.json').read_text())
    jb=json.loads((b_dir/'before_world_mesh.json').read_text())
    for label, capture in (('A', ja), ('B', jb)):
        if capture.get('working_subdivision_level') != 0 or capture.get('world_target_eligible') is not True:
            raise ValueError(label + ' requires a fresh world capture explicitly verified at working SubD 0')
    a=np.asarray(ja['vertices']);b=np.asarray(jb['vertices'])
    for key in ('rotation','s'):
        if ja['avatar_transform'][key] != jb['avatar_transform'][key]:
            raise ValueError('Root rotation/scale differ; resolve coordinate system first')
    ta=np.array([ja['avatar_transform']['translation'][k] for k in 'xyz'])
    tb=np.array([jb['avatar_transform']['translation'][k] for k in 'xyz'])
    a=a-ta+tb
    _,ua,fa=read_obj(a_dir/'before_body.obj');_,uv,faces=read_obj(b_dir/'before_body.obj')
    if fa!=faces or not np.array_equal(ua,uv):
        raise ValueError('Reference topology/UV mismatch')
    h=head_ids();w,mask=mask_weights(uv,faces);w[w<=.01]=0;w[w>=.99]=1
    target=b.copy();target[h]=a[h]*(1-w[h,None])+b[h]*w[h,None]
    lines=(b_dir/'before_body.obj').read_text(encoding='utf-8-sig').splitlines(True)
    group='';ids=set()
    for line in lines:
        p=line.split()
        if p and p[0] in ('g','o'):group=p[1]
        elif p and p[0]=='f' and group=='CC_Base_Body':
            ids.update(int(t.split('/')[0])-1 for t in p[1:])
    offset=min(ids)
    if len(ids)!=14164 or sorted(ids)!=list(range(offset,offset+14164)):
        raise ValueError('Unexpected OBJ body index layout')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',encoding='utf-8') as file:
        vi=0
        for line in lines:
            if line.startswith('v '):
                if vi in ids:line='v %.12f %.12f %.12f\n'%tuple(target[vi-offset])
                vi+=1
            file.write(line)
    report={'a_capture':str(a_dir),'b_capture':str(b_dir),'target_obj':str(output),
            'scope':'Experimental Clean Soft mask partition includes scalp, ears and neck; not a production scalp-only mask',
            'head_vertices':len(h),'fixed_region_vertices':int((w[h]==0).sum()),
            'preserved_face_vertices':int((w[h]==1).sum()),'transition_vertices':int(((w[h]>0)&(w[h]<1)).sum()),
            'root_translation_correction_cm':(tb-ta).tolist(),
            'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a_dir/'before_world_mesh.json',b_dir/'before_world_mesh.json',b_dir/'before_body.obj',mask]},
            'target_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--a-dir',required=True);p.add_argument('--b-dir',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    print(json.dumps(build(args.a_dir,args.b_dir,args.output),indent=2))
