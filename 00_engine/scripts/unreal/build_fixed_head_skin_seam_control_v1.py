"""Generate numeric UV correction controls; never edit source diffuse images."""
import argparse
import hashlib
import json
import sys
import heapq
from pathlib import Path
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / '00_engine/scripts/character_creator'))
from cc_audit_headshot_fbx_v1 import read_nodes

def value(node, name):
    return next(c for c in node['children'] if c['name'] == name)['props'][0]

def child(node, name):
    return next(c for c in node['children'] if c['name'] == name)

def linear(rgb):
    x=np.asarray(rgb,dtype=np.float64)/255
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)

def sample(im,uv):
    h,w=im.shape[:2]
    # CC material sections use integer U tile offsets (Body 1.x, Arm 2.x).
    # Each section still samples its individual 0..1 PNG with UE wrap addressing.
    # Clamping the unwrapped coordinates samples the image border, not the skin.
    uv=np.mod(np.asarray(uv,dtype=np.float64),1.)
    x=np.clip(uv[0]*(w-1),0,w-1);y=np.clip((1-uv[1])*(h-1),0,h-1)
    j,i=int(x),int(y);j1=min(j+1,w-1);i1=min(i+1,h-1)
    return (im[i,j]*(1-x+j)*(1-y+i)+im[i,j1]*(x-j)*(1-y+i)+im[i1,j]*(1-x+j)*(y-i)+im[i1,j1]*(x-j)*(y-i))

def build(sex, out, width=6., size=4096):
    root=Path(r'D:\UE\exports\character_creator\fixed_head_hair_20261004_v1\bases')/sex
    base='CC_FIXED_HEAD_'+sex.upper()
    fbx=root/(base+'.fbx');_,top=read_nodes(fbx)
    objects={n['props'][0]:n for n in top['Objects']['children']}
    mesh=next(n for n in objects.values() if n['name']=='Geometry' and n['props'][2]=='Mesh' and n['props'][1].split('\x00')[0]=='CC_Base_Body')
    mid=next(e['props'][2] for e in top['Connections']['children'] if e['props'][1]==mesh['props'][0])
    mats=[objects[e['props'][1]]['props'][1].split('\x00')[0] for e in top['Connections']['children'] if e['props'][2]==mid and objects.get(e['props'][1],{}).get('name')=='Material']
    p=value(mesh,'PolygonVertexIndex');assert len(p)%3==0 and np.all(p[2::3]<0)
    cp=np.where(p<0,-p-1,p).reshape(-1,3);xyz=value(mesh,'Vertices').reshape(-1,3)
    uve=child(mesh,'LayerElementUV');uv=value(uve,'UV').reshape(-1,2)[value(uve,'UVIndex')].reshape(-1,3,2)
    ids=value(child(mesh,'LayerElementMaterial'),'Materials')
    headid=mats.index('Std_Skin_Head_Pbr');headtri=np.flatnonzero(ids==headid)
    ims={name:linear(np.asarray(Image.open(root/(base+'.fbm')/(name+'_Diffuse.png')).convert('RGB'))) for name in mats if name.startswith('Std_Skin_')}
    edges={};graph=[]
    for i,vertices in enumerate(cp):
        for j in range(3):
            k=(j+1)%3;edge=tuple(sorted((int(vertices[j]),int(vertices[k]))));edges.setdefault(edge,[]).append((i,j,k))
            if ids[i]==headid:graph.append(edge)
    seeds={};samples=[];boundary_checks=[]
    for edge,rows in edges.items():
        if len(rows)!=2:continue
        a,b=rows
        if ids[a[0]]!=headid and ids[b[0]]!=headid:continue
        if ids[a[0]]==ids[b[0]]:continue
        h,o=(a,b) if ids[a[0]]==headid else (b,a)
        other=mats[ids[o[0]]]
        if not other.startswith('Std_Skin_'):continue
        for cpi in edge:
            hu=uv[h[0],int(np.flatnonzero(cp[h[0]]==cpi)[0])];ou=uv[o[0],int(np.flatnonzero(cp[o[0]]==cpi)[0])]
            delta=sample(ims[other],ou)-sample(ims[mats[headid]],hu)
            seeds.setdefault(cpi,[]).append(delta);samples.append((xyz[cpi],delta))
        hmid=uv[h[0],[h[1],h[2]]].mean(0);omid=uv[o[0],[o[1],o[2]]].mean(0)
        hc=sample(ims[mats[headid]],hmid);oc=sample(ims[other],omid)
        samples.append((xyz[list(edge)].mean(0),oc-hc));boundary_checks.append((hmid,hc,oc))
    graph=np.unique(np.array(graph,dtype=int),axis=0);length=np.linalg.norm(xyz[graph[:,0]]-xyz[graph[:,1]],axis=1)
    adjacency=[[] for _ in xyz]
    for (a,b),lengthab in zip(graph,length):adjacency[a].append((b,float(lengthab)));adjacency[b].append((a,float(lengthab)))
    dist=np.full(len(xyz),np.inf);todo=[]
    for a in seeds:dist[a]=0;heapq.heappush(todo,(0,a))
    while todo:
        dd,a=heapq.heappop(todo)
        if dd!=dist[a]:continue
        for b,ll in adjacency[a]:
            nd=dd+ll
            if nd<dist[b]:dist[b]=nd;heapq.heappush(todo,(nd,b))
    points=np.array([x[0] for x in samples]);deltas=np.array([x[1] for x in samples])
    alldist=np.linalg.norm(xyz[:,None,:]-points[None,:,:],axis=2);ni=np.argsort(alldist,axis=1)[:,:min(8,len(points))];nn=np.take_along_axis(alldist,ni,axis=1)
    weights=1/np.maximum(nn,1e-5)**2;vertex_delta=(deltas[ni]*weights[:,:,None]).sum(1)/weights.sum(1)[:,None]
    # C1 smooth transition ending at 6 cm geodesic distance from seam.
    u=np.clip(dist/width,0,1);mask=1-u*u*(3-2*u);mask[~np.isfinite(mask)]=0
    premul=(vertex_delta*mask[:,None]).astype(np.float32)
    correction=np.zeros((size,size,3),dtype=np.float32);masktex=np.zeros((size,size),dtype=np.float32)
    tris=0
    for ti in headtri:
        corners=cp[ti]
        if not np.any(mask[corners]>0):continue
        texuv=uv[ti]*np.array([size-1,-(size-1)])+np.array([0,size-1])
        mn=np.maximum(np.floor(texuv.min(0)).astype(int)-1,0);mx=np.minimum(np.ceil(texuv.max(0)).astype(int)+1,size-1)
        xx,yy=np.meshgrid(np.arange(mn[0],mx[0]+1),np.arange(mn[1],mx[1]+1))
        a,b,c=texuv;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-9:continue
        w1=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;w2=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w3=1-w1-w2
        inside=(w1>=-1e-4)&(w2>=-1e-4)&(w3>=-1e-4);bary=np.stack((w1,w2,w3),-1)
        block=correction[mn[1]:mx[1]+1,mn[0]:mx[0]+1];block[inside]=(bary@premul[corners])[inside]
        blockm=masktex[mn[1]:mx[1]+1,mn[0]:mx[0]+1];blockm[inside]=(bary@mask[corners])[inside];tris+=1
    # Seam edge sampling can touch background pixels: extend nearest corrected
    # texel by 2 pixels while retaining exact neutral zero on face UV islands.
    for _ in range(2):
        valid=masktex>0
        for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
            shifted=np.roll(valid,(dy,dx),(0,1));pad=(~valid)&shifted
            if dy==1:pad[0]=False
            if dy==-1:pad[-1]=False
            if dx==1:pad[:,0]=False
            if dx==-1:pad[:,-1]=False
            correction[pad]=np.roll(correction,(dy,dx),(0,1))[pad];masktex[pad]=np.roll(masktex,(dy,dx),(0,1))[pad]
    output=np.zeros((size,size,4),dtype=np.uint8);output[:,:,:3]=np.clip(np.rint(correction/.5*127)+128,0,255).astype(np.uint8);output[:,:,3]=np.clip(np.rint(masktex*255),0,255).astype(np.uint8)
    path=out/(sex+'_neck_linear_delta_control.png');Image.fromarray(output,'RGBA').save(path)
    before=[];after=[]
    def srgb(x):
        x=np.clip(x,0,1);return 255*np.where(x<=.0031308,x*12.92,1.055*x**(1/2.4)-.055)
    for huv,hc,oc in boundary_checks:
        cd=(sample(output[:,:,:3].astype(np.float32),huv)/255-128/255)*(255*.5/127)
        before.append(np.abs(srgb(hc)-srgb(oc)));after.append(np.abs(srgb(hc+cd)-srgb(oc)))
    return {'sex':sex,'revision':'R06_wrapped_material_uv','source_fbx':str(fbx),'source_fbx_sha256':hashlib.sha256(fbx.read_bytes()).hexdigest(),'control_path':str(path),'control_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'data_semantics':'Linear RGB additive delta premultiplied by geodesic C1 mask; delta=(rgb-128/255)*(255*.5/127). A=debug mask only. Zero neutral RGB=128. Source samples use per-material UV wrapping, not UV clamping. Not an edited source photo.','range_linear':.5,'neutral':128/255,'decode_scale':255*.5/127,'geodesic_width_cm':width,'pixels_affected':int(np.count_nonzero(np.any(output[:,:,:3]!=128,axis=2))),'head_triangles_total':len(headtri),'head_triangles_corrected':tris,'face_outside_band_exact_neutral':True,'boundary_seed_count':len(seeds),'source_diffuses_unchanged':True,'source_color_boundary_check':{'before_mean_absolute_rgb_0_255':np.mean(before,axis=0).tolist(),'after_mean_absolute_rgb_0_255':np.mean(after,axis=0).tolist(),'before_p95_max_rgb_0_255':float(np.percentile(np.max(before,axis=1),95)),'after_p95_max_rgb_0_255':float(np.percentile(np.max(after,axis=1),95)),'scope':'Numeric bilinear wrapped source/control seam midpoint sampling, not UE render acceptance'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rows=[build(sex,a.output) for sex in ['female','male']]
    (a.output/'skin_seam_controls.json').write_text(json.dumps({'version':1,'controls':rows},indent=2),encoding='utf-8');print('SKIN_SEAM_CONTROLS='+json.dumps(rows))

if __name__=='__main__':main()
