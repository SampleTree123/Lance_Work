#!/usr/bin/env python3
"""Four independent inference workers. Owner: ../training_integration.md."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

LANCE = Path(__file__).resolve().parents[1]
SUITE = LANCE / 'configs/datamake_mixed_complete_chain_review_20260911.json'
GROUPS = [('baseline',1,1),('text3',3,1),('text5',5,1),('vit3',1,3),('vit5',1,5)]
import prepare_datamake_chain_review as prep
ORIGINAL = prep.make_cases

def plan():
    cases = ORIGINAL(json.loads(SUITE.read_text()))
    jobs = [(g,t,v,c) for g,t,v in GROUPS for c in cases]
    bins, costs = [[] for _ in range(4)], [0]*4
    for g,t,v,c in sorted(jobs, key=lambda j: -cost(j)):
        rank = min(range(4), key=lambda i: costs[i])
        bins[rank].append((g,t,v,c['name']))
        costs[rank] += cost((g,t,v,c))
    assert len({(j[0],j[3]) for b in bins for j in b}) == 95
    return bins

def cost(job):
    _,t,v,c = job
    return sum(o['round'] + 2 for o in c['outputs']) * (1 + (t>1 or v>1) + (v>1))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--checkpoint',type=Path,required=True)
    ap.add_argument('--group',choices=[g[0] for g in GROUPS])
    ap.add_argument('--rank',type=int,default=int(os.environ.get('SLURM_PROCID',0)))
    ap.add_argument('--plan-only',action='store_true')
    a=ap.parse_args(); root=a.root.resolve(); bins=plan()
    if a.plan_only:
        print(json.dumps(bins,indent=2)); return
    if not a.group:
        for g,_,_ in GROUPS:
            if any(j[0]==g for j in bins[a.rank]):
                subprocess.run([sys.executable,__file__,'--root',str(root),'--checkpoint',str(a.checkpoint),'--rank',str(a.rank),'--group',g],check=True)
        return
    names={j[3] for j in bins[a.rank] if j[0]==a.group}
    prep.make_cases=lambda suite:[c for c in ORIGINAL(suite) if c['name'] in names]
    _,t,v=next(j for j in GROUPS if j[0]==a.group)
    import run_datamake_lora_visual_sanity as runner
    sys.argv=[str(Path(runner.__file__)), '--checkpoint',str(a.checkpoint),'--suite',str(SUITE),'--output-dir',str(root/a.group/f'rank{a.rank}'),'--cfg-text-scale',str(t),'--cfg-vit-scale',str(v)]
    runner.main()

if __name__=='__main__': main()
