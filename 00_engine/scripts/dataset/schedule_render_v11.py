"""Order immutable render jobs by scene/person; balance whole scenes over workers."""
import argparse
import hashlib
import json
from pathlib import Path

def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def key(job):
    s=job['state']
    return (job['site']['map'],s['site'],s['sex'],s['identity'],canonical(s['wardrobe']),s['hair'],s['hair_color'],s['action'],s['camera'],s['aspect'],job['job_id'])
def transitions(jobs):
    names=('scene','identity','wardrobe','hair','hair_color','action','camera','aspect')
    count={k:0 for k in names}
    for a,b in zip(jobs,jobs[1:]):
        for k in names:
            before=a['site']['map'] if k=='scene' else a['state'][k]
            after=b['site']['map'] if k=='scene' else b['state'][k]
            count[k]+=before!=after
    return count
def build(source,workers):
    jobs=source['jobs'];ordered=sorted(jobs,key=key); groups={}
    for j in ordered: groups.setdefault(j['site']['map'],[]).append(j)
    bins=[[] for _ in range(workers)]
    for scene,items in sorted(groups.items(),key=lambda kv:(-len(kv[1]),kv[0])):
        selected=min(range(workers),key=lambda i:(len(bins[i]),i));bins[selected].extend(items)
    flat=[j['job_id'] for b in bins for j in b]
    if len(flat)!=len(set(flat)) or set(flat)!={j['job_id'] for j in jobs}:raise ValueError('Duplicate/missing jobs')
    report={'schema':'dataset_render_schedule_v11_v1','jobs':len(jobs),'workers':workers,'scenes':len(groups),
            'before':transitions(jobs),'after':transitions(ordered),'jobs_by_worker':[len(b) for b in bins],
            'policy':'scene > site > sex > identity > wardrobe > hair > color > action > camera > aspect',
            'worker_policy':'largest scene first, assign each whole scene to lightest worker by video count',
            'balance_limit':'count proxy only; scene throughput and GPU speed may differ; no source states or graph edges change',
            'encoding':'serial baseline; one encoder worker can be overlapped after server CPU/RAM measurement',
            'ordering_sha256':hashlib.sha256(canonical([j['job_id'] for j in ordered]).encode()).hexdigest()}
    return ordered,bins,report
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jobs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=1);args=p.parse_args()
    if args.workers<1:raise ValueError('workers must be positive')
    source=json.loads(args.jobs.read_text(encoding='utf-8-sig'));ordered,bins,report=build(source,args.workers)
    args.out.mkdir(parents=True,exist_ok=True)
    base={k:v for k,v in source.items() if k not in ('jobs','job_count')}
    for name,items in [('ordered_jobs.json',ordered)]+[(f'worker_{i:02d}.json',b) for i,b in enumerate(bins)]:
        (args.out/name).write_text(json.dumps({**base,'job_count':len(items),'jobs':items},ensure_ascii=False,indent=2),encoding='utf-8')
    (args.out/'schedule_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))
if __name__=='__main__':main()
