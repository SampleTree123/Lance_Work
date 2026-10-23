"""Offline diagnostic of one fixed hair mesh against Headshot A/B scalp surfaces.

This measures mesh clearance, not opacity-aware rendering or all-hairstyle acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from cc_compare_headshot_geometry_v1 import head_ids, mask_weights, read_obj


def world(path):
    return np.asarray(json.loads(Path(path).read_text())["vertices"], dtype=float)


def nearest_surface(points, vertices, triangles, candidates=64):
    """Exact point/triangle distances within centroid-nearest candidate triangles."""
    tri = vertices[triangles]
    centroids = tri.mean(axis=1)
    centroid_norm2 = np.sum(centroids**2, axis=1)
    distances, indices, positions = [], [], []
    for start in range(0, len(points), 256):
        p = points[start:start+256]
        d_centroid = np.sum(p*p,axis=1)[:,None] + centroid_norm2[None,:] - 2*p@centroids.T
        count = min(candidates,len(tri))
        ix = np.argpartition(d_centroid,count-1,axis=1)[:,:count]
        t = tri[ix]
        a, b, c = t[:, :, 0], t[:, :, 1], t[:, :, 2]
        normal = np.cross(b-a, c-a)
        normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-12)
        pp = p[:, None, :]
        projection = pp - np.sum((pp-a)*normal, axis=2, keepdims=True)*normal
        v0, v1, v2 = b-a, c-a, projection-a
        d00 = np.sum(v0*v0, axis=2); d01 = np.sum(v0*v1, axis=2)
        d11 = np.sum(v1*v1, axis=2); d20 = np.sum(v2*v0, axis=2); d21 = np.sum(v2*v1, axis=2)
        den = np.maximum(d00*d11-d01*d01, 1e-20)
        u = (d11*d20-d01*d21)/den; v = (d00*d21-d01*d20)/den
        inside = (u >= 0) & (v >= 0) & (u+v <= 1)
        closest = projection.copy()
        dist2 = np.sum((pp-projection)**2, axis=2)
        dist2[~inside] = np.inf
        for first, last in ((a,b),(b,c),(c,a)):
            edge = last-first
            fraction = np.clip(np.sum((pp-first)*edge,axis=2)/np.maximum(np.sum(edge*edge,axis=2),1e-20),0,1)
            q = first+fraction[:,:,None]*edge
            ed = np.sum((pp-q)**2,axis=2)
            better = ed < dist2
            closest[better] = q[better]; dist2[better] = ed[better]
        best = np.argmin(dist2,axis=1); rows=np.arange(len(p))
        nn = normal[rows,best]
        cp = closest[rows,best]
        # CC winding verified below using top-surface normals; retain actual winding.
        sign = np.sign(np.sum((p-cp)*nn,axis=1))
        distances.extend(np.sqrt(dist2[rows,best])*sign*10)
        indices.extend(ix[rows,best]); positions.extend(cp)
    return np.asarray(distances), np.asarray(indices), np.asarray(positions)


def assess(root, sex, fixed_dir, output, hair_reference_dir=None):
    root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    a_dir=root/(sex+"_A_world_capture");b_dir=root/(sex+"_B_world_capture")
    a=world(a_dir/"before_world_mesh.json");b=world(b_dir/"before_world_mesh.json")
    fixed=world(root/fixed_dir/"after_world_mesh.json")
    _,uv,faces=read_obj(a_dir/"before_body.obj");h=head_ids();w,_=mask_weights(uv,faces)
    hs=set(h.tolist());tri=[]
    for face in faces:
        f=[i for i,t in face]
        if all(i in hs for i in f):
            tri.extend([[f[0],f[j],f[j+1]] for j in range(1,len(f)-1)])
    tri=np.asarray(tri)
    # Remove root translation only, never fit skulls onto each other.
    def translation(directory):
        tf=json.loads((directory/"before_world_mesh.json").read_text())["avatar_transform"]
        assert tf['rotation']=={'w':1.0,'x':0.0,'y':0.0,'z':0.0}
        return np.array([tf['translation'][k] for k in 'xyz'])
    shift=translation(a_dir)-translation(b_dir);b+=shift;fixed+=shift
    hair_reference=root/(hair_reference_dir or sex+"_hair_reference")
    records=json.loads((hair_reference/"hair_world_meshes.json").read_text())
    hair=np.concatenate([np.asarray(m['vertices']) for m in records])
    hair=hair[hair[:,2]>a[h,2].max()-10]
    normals=np.cross(a[tri[:,1]]-a[tri[:,0]],a[tri[:,2]]-a[tri[:,0]])
    top=a[tri].mean(1)[:,2]>a[h,2].max()-2
    assert normals[top,2].mean()>0, 'Unexpected inward mesh winding'
    da,ix,cp=nearest_surface(hair,a,tri)
    db,_,_=nearest_surface(hair,b,tri)
    dc,_,_=nearest_surface(hair,fixed,tri)
    scalp=np.all(w[tri[ix]]<=.01,axis=1)
    usable=scalp&(da>=.1)&(da<=5)
    crossing=usable&(db<-.5)
    # Validate candidate search on all newly crossing points with wider neighborhoods.
    if crossing.any():
        precise,_,_=nearest_surface(hair[crossing],b,tri,candidates=256)
        candidate_error=float(np.max(np.abs(precise-db[crossing])))
        assert candidate_error<.01, 'Nearest-triangle candidate search insufficient'
    else:
        candidate_error=0.0
    report={'sex':sex,'hair':'HB3-17 Sleek Deep Side Part','method':'Fixed A-fitted hair vertices; root translation aligned; closest scalp triangles; signed gap in mm',
        'scope':'Top 10 cm of head, zero face-mask triangles. Mesh evidence includes scalp/hair cards and does not account for opacity or prove all 40 hair styles.',
        'candidate_search_crosscheck_max_mm':candidate_error,'near_scalp_vertices_initially_outside':int(usable.sum()),
        'new_inside_vertices_B_below_minus_0_5mm':int(crossing.sum()),
        'same_vertices_inside_fixed_below_minus_0_5mm':int((usable&(dc<-.5)).sum()),
        'B_min_gap_mm':float(db[usable].min()),'fixed_min_gap_mm':float(dc[usable].min()),
        'max_gap_change_B_mm':float(np.max(np.abs(db[usable]-da[usable]))),
        'max_gap_change_fixed_mm':float(np.max(np.abs(dc[usable]-da[usable]))),
        'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a_dir/'before_world_mesh.json',b_dir/'before_world_mesh.json',root/fixed_dir/'after_world_mesh.json',hair_reference/'hair_world_meshes.json']}}
    if crossing.any():
        idx=np.where(crossing)[0][np.argmin(db[crossing])]
        report['example']={'point_world_cm':hair[idx].tolist(),'A_gap_mm':float(da[idx]),'B_gap_mm':float(db[idx]),'fixed_gap_mm':float(dc[idx])}
    (output/'clearance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    np.savez_compressed(output/'clearance.npz',hair=hair,a=a,b=b,fixed=fixed,triangles=tri,gap_a=da,gap_b=db,gap_fixed=dc,usable=usable)
    import plotly.graph_objects as go
    fig=go.Figure()
    for label,v,col in [('A reference',a,'lightgray'),('B original',b,'orange'),('B scalp fixed',fixed,'deepskyblue')]:
        fig.add_trace(go.Mesh3d(x=v[:,0],y=v[:,1],z=v[:,2],i=tri[:,0],j=tri[:,1],k=tri[:,2],color=col,opacity=.65,name=label,visible=True if label=='B original' else 'legendonly'))
    pts=hair[usable]
    fig.add_trace(go.Scatter3d(x=pts[:,0],y=pts[:,1],z=pts[:,2],mode='markers',marker={'size':2,'color':db[usable],'colorscale':'RdBu','cmin':-5,'cmax':5,'colorbar':{'title':'B gap mm'}},name='Fixed A hair samples'))
    bounds=np.concatenate([a[h],b[h],fixed[h]])
    scene={'aspectmode':'data'}
    for axis,col in zip('xyz',range(3)):
        scene[axis+'axis']={'range':[float(bounds[:,col].min()-1),float(bounds[:,col].max()+1)]}
    fig.update_layout(title=sex+' | Same hair, different head geometry',scene=scene,height=850)
    fig.write_html(str(output/'clearance.html'),include_plotlyjs=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--sex',choices=['male','female'],required=True);parser.add_argument('--fixed-dir',required=True);parser.add_argument('--output',required=True);parser.add_argument('--hair-reference-dir');args=parser.parse_args()
    print(json.dumps(assess(args.root,args.sex,args.fixed_dir,args.output,args.hair_reference_dir),indent=2))
