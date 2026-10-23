from pathlib import Path
import copy,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from distributed_builder import Domain,read,write
def main():
    source=read(ROOT/'plan6/look_selection.json');looks=copy.deepcopy(source['looks']);audit=read(ROOT/'trial8/node_frequency_train.json')
    counts=audit['distributions']['core_asset']['counts'];assets=sorted(counts);c=np.array([counts[a] for a in assets],dtype=float)
    rows=[r for r in read(ROOT/'audit_work/wardrobe_binding_witness.json')['rows'] if r['visibility']=='full'];d=Domain()
    def vector(row):
        core=set(row['visible_core']);upper=set(d.nc.upper_asset_ids(row['sex'],row['choice']))&core
        return np.array([13.0 if a in upper else (11.5 if a in core else 0) for a in assets])
    A=np.array([vector(r) for r in rows]);changes=[]
    def objective(v):
        ratio=v/np.mean(v,axis=-1,keepdims=True)
        return .02*np.sum((ratio-1)**2,axis=-1)+100*np.sum(np.maximum(.60-ratio,0)**2+np.maximum(ratio-1.40,0)**2,axis=-1)
    for iteration in range(12):
        over={a for a,v in zip(assets,c/c.mean()) if v>1.40};best=None;score=objective(c)
        for i,row in enumerate(looks):
            if not over.intersection(row['visible_core']):continue
            candidates=c[None,:]-vector(row)[None,:]+A;scores=objective(candidates);j=int(np.argmin(scores))
            if scores[j]<score-1e-8:score=float(scores[j]);best=(i,j,candidates[j])
        if best is None:break
        i,j,c=best;changes.append({'index':i,'old_family':looks[i]['family'],'new_family':rows[j]['family'],'old_core':looks[i]['visible_core'],'new_core':rows[j]['visible_core']});looks[i]=copy.deepcopy(rows[j])
    out=ROOT/'plan7';out.mkdir(exist_ok=False)
    summary={'look_slots':len(looks),'method':'replace overexposed ordinary look slots before building; no additional nodes or singleton coverage patches','source':'plan6/look_selection.json','actual_source_frequency':'trial8/node_frequency_train.json','changes':changes,'predicted_min_ratio':float(c.min()/c.mean()),'predicted_max_ratio':float(c.max()/c.mean())}
    write(out/'look_selection.json',{'summary':summary,'looks':looks});print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
