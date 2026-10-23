"""Small matched-seed diagnostic: same sampler, graphs only differ."""
import argparse,json,sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
V3=ROOT.parent/'dataset_local_support_20261021_v3'
sys.path.insert(0,str(V3))
from resample_local import Domain,load_graph,sample_local,write,ID_CAMERAS

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);a=p.parse_args()
    d=Domain();out={'seeds':[20261122,20261142,20261162],'sampler':str(V3/'resample_local.py'),
                    'scope':'Sampling-seed sensitivity on fixed graphs; not construction-seed robustness. No new no-repeat restriction.', 'runs':{}}
    for name,path in [('baseline_v3',V3/'linked_complete'),(a.candidate.name,a.candidate)]:
        out['runs'][name]={}
        for split,count in [('train',12000),('test',2400)]:
            g=load_graph(path/split,d);rows=[]
            for seed in out['seeds']:
                ss,meta=sample_local(g,count,seed+(split=='test'))
                bylength={}
                for length in range(2,6):
                    part=[s for s in ss if s['length']==length]
                    bylength[str(length)]={'chains':len(part),'mean_axes':sum(len({r['axis'] for r in s['steps']}) for s in part)/max(1,len(part))}
                rows.append({'seed':seed+(split=='test'),'chains':len(ss),'used_nodes':len({u for s in ss for u in s['history']}),
                             'by_length':bylength,'revisit_share':sum(len(set(s['history']))<len(s['history']) for s in ss)/len(ss),
                             'identity_camera_start_share':sum(g.nodes[s['history'][0]]['camera'] in ID_CAMERAS for s in ss)/len(ss),
                             'sampling_errors':meta['errors_and_retries']})
            out['runs'][name][split]=rows
            print(name,split,json.dumps(rows,ensure_ascii=False),flush=True)
    write(ROOT/'audit/sampling_stability.json',out)

if __name__=='__main__':main()
