"""Compare exported CC3+ bodies using installed head topology and Clean Soft alpha.

Offline only. Output regions are UV-mask regions, not anatomical claims.
The input OBJ must contain a CC_Base_Body group with 14164 vertices.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

RESOURCE = Path(r"D:\CharacterCreator\Character Creator 5\Resource\CCHeadshot")


def read_obj(path):
    vertices, uv, faces, group = [], [], [], ""
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            vertices.append(list(map(float, p[1:4])))
        elif p[0] == "vt":
            uv.append(list(map(float, p[1:3])))
        elif p[0] in ("g", "o"):
            group = p[1]
        elif p[0] == "f" and group == "CC_Base_Body":
            faces.append([(int(v.split('/')[0])-1, int(v.split('/')[1])-1) for v in p[1:]])
    ids = sorted({v for f in faces for v, t in f})
    if len(ids) != 14164 or ids != list(range(ids[0], ids[0]+14164)):
        raise ValueError("Unexpected CC3+ Body topology")
    offset = ids[0]
    return np.array(vertices)[ids], np.array(uv), [[(v-offset,t) for v,t in f] for f in faces]


def head_ids():
    source = (RESOURCE/'CreateHead.ini').read_text(encoding='utf-8-sig')
    ranges = re.search(r'^G3Plus_HeadVertices = "([^"]+)"', source, re.M).group(1)
    result = []
    for item in ranges.split(','):
        ends = [int(x.strip()) for x in item.split('..')]
        result.extend(range(ends[0]-1, ends[-1]))
    return np.array(sorted(set(result)))


def mask_weights(uv, faces):
    path = RESOURCE/'TexturePreset/G3Plus/Mask/Face/Mask_Even_High_Features.png'
    alpha = np.asarray(Image.open(path).getchannel('A'), dtype=float)/255
    weights = np.zeros(14164)
    for face in faces:
        for v,t in face:
            u,w = uv[t]
            x = int(np.clip(round(u*(alpha.shape[1]-1)),0,alpha.shape[1]-1))
            y = int(np.clip(round((1-w)*(alpha.shape[0]-1)),0,alpha.shape[0]-1))
            weights[v] = max(weights[v],alpha[y,x])
    return weights, path


def stats(a,b,indices):
    delta = np.linalg.norm(b[indices]-a[indices],axis=1)*10
    return {'vertex_count':len(indices),'max_displacement_mm':float(delta.max()),
            'mean_displacement_mm':float(delta.mean()),'p95_displacement_mm':float(np.percentile(delta,95)),
            'vertices_above_1mm':int((delta>1).sum()),'vertices_above_3mm':int((delta>3).sum()),
            'a_bounds_cm':[a[indices].min(0).tolist(),a[indices].max(0).tolist()],
            'b_bounds_cm':[b[indices].min(0).tolist(),b[indices].max(0).tolist()],
            'a_extents_cm':np.ptp(a[indices],axis=0).tolist(),
            'b_extents_cm':np.ptp(b[indices],axis=0).tolist()}


def compare(a_path,b_path,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    a,uv,faces=read_obj(a_path);b,uvb,fb=read_obj(b_path)
    if faces!=fb or not np.array_equal(uv,uvb):
        raise ValueError('OBJ topology or UV mapping differs')
    ids=head_ids();w,mask=mask_weights(uv,faces)
    groups={'head':ids,'scalp_mask_zero':ids[w[ids]<=0.01],
            'face_mask_full':ids[w[ids]>=0.99],
            'transition':ids[(w[ids]>.01)&(w[ids]<.99)],
            'body_outside_head':np.setdiff1d(np.arange(14164),ids)}
    report={'a_obj':str(a_path),'b_obj':str(b_path),'unit':'cm, displacement reported in mm',
            'registration':'same exported CC body coordinates; no skull best-fit registration to hide size/position differences',
            'topology_uv_identical':True,'mask_path':str(mask),
            'mask_sha256':hashlib.sha256(mask.read_bytes()).hexdigest(),
            'region_definition':'Installed CC3+ head vertex set, split by Clean Soft face-blend alpha. Zero-alpha region includes scalp/ears/neck; requires visual inspection for hair-specific coverage.',
            'regions':{name:stats(a,b,i) for name,i in groups.items() if len(i)}}
    (output/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (output/'regions.json').write_text(json.dumps({k:v.tolist() for k,v in groups.items()}),encoding='utf-8')
    np.savez_compressed(output/'geometry.npz',a=a,b=b,weights=w,head_ids=ids)
    # An inspectable 3D artifact with no remote JS dependency.
    import plotly.graph_objects as go
    tris=[]
    headset=set(ids.tolist())
    for face in faces:
        f=[v for v,t in face]
        if all(v in headset for v in f):
            tris.extend([[f[0],f[j],f[j+1]] for j in range(1,len(f)-1)])
    tri=np.array(tris);delta=np.linalg.norm(b-a,axis=1)*10
    fig=go.Figure()
    fig.add_trace(go.Mesh3d(x=a[:,0],y=a[:,1],z=a[:,2],i=tri[:,0],j=tri[:,1],k=tri[:,2],
                           intensity=delta,colorscale='Viridis',colorbar={'title':'delta mm'},name='A: displacement heatmap'))
    fig.add_trace(go.Mesh3d(x=b[:,0],y=b[:,1],z=b[:,2],i=tri[:,0],j=tri[:,1],k=tri[:,2],
                           color='orange',opacity=.35,name='B overlay',visible='legendonly'))
    bounds=np.concatenate([a[ids],b[ids]])
    scene={'aspectmode':'data'}
    for axis,col in zip('xyz',range(3)):
        scene[axis+'axis']={'range':[float(bounds[:,col].min()-1),float(bounds[:,col].max()+1)]}
    fig.update_layout(title='Headshot geometry comparison (exported mesh)',scene=scene,height=850)
    fig.write_html(str(output/'comparison.html'),include_plotlyjs=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--a',required=True);p.add_argument('--b',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    result=compare(args.a,args.b,args.output)
    print(json.dumps(result['regions'],indent=2))
