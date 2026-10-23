"""Sample saved legal graphs; each seed has independent output artifacts."""
import argparse,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'dataset_local_support_20261021_v3'))
from resample_local import Domain,load_graph,read,write,save_graph
from sample_balanced import sample

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--graph',default='candidate_a');ap.add_argument('--output',default='candidate_a_seed1');ap.add_argument('--seed',type=int,default=2026102251);ap.add_argument('--attempts',type=int,default=240);args=ap.parse_args()
    d=Domain();forbidden=set();summary={};start=time.time()
    for j,(split,total) in enumerate([('train',12000),('test',2400)]):
        src=HERE/args.graph/split;g=load_graph(src,d,forbidden)
        meta=read(src/'metrics.json')['construction']
        ss,sm=sample(g,total,args.seed+j,max_attempts=args.attempts,progress_every=1000)
        meta['sampling']=sm;meta['sample_seed']=args.seed+j;meta['source_graph']=str(src)
        summary[split]=save_graph(HERE/args.output/split,g,ss,meta)
        forbidden.update(g.keys)
        print('SAMPLED',split,len(ss),'unused',sm['unused_nodes'],'axis',sm['axis_counts'],'reuse',sm['edge_reuse_histogram'],'deviation',sm['nonidentity_relative_deviation'],flush=True)
    summary['elapsed_seconds']=time.time()-start;write(HERE/args.output/'SUMMARY.json',summary)

if __name__=='__main__':main()
