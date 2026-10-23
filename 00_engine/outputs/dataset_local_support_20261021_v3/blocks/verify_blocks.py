"""Bounded independent semantic check of a saved local-block candidate."""
from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'dataset_trial_build_20261021_v1'))
from verify_trial import Verification

def main():
    ap=argparse.ArgumentParser();ap.add_argument('candidate',nargs='?',default='diverse');args=ap.parse_args()
    root=HERE/args.candidate;v=Verification();report={'scope':'offline semantic nodes/edges/session checks, no UE or pixels','splits':{}};keys={}
    for split in ('train','test'):
        report['splits'][split],keys[split]=v.verify_split(root,split,True)
    overlap=keys['train']&keys['test']
    v.check(not overlap,'complete_canonical_cross_split_disjoint',len(overlap))
    report.update(errors=dict(v.errors),examples=dict(v.examples),cross_split_overlap=len(overlap),success=not v.errors)
    (root/'independent_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('success','errors','cross_split_overlap')},ensure_ascii=False))
    raise SystemExit(0 if report['success'] else 1)
if __name__=='__main__':main()
