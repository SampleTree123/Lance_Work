"""Compare saved .2 and actual .4 structural sessions and render projections."""
from collections import Counter,defaultdict
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
V6=ROOT.parent/'dataset_compact_graph_20261022_v6/selected_seed1'
V7=ROOT.parent/'dataset_dual_aspect_20261022_v7/selected_candidate'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sequence(p):
    rows=[json.loads(x) for x in (p/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
    groups=defaultdict(list)
    for c in rows:groups[f"{c['kind']}_{c['length']}"].append(c)
    def stats(cs):
        axes=[Counter(s['axis'] for s in c['steps']) for c in cs]
        total=sum(sum(a.values()) for a in axes);repeat=sum(sum(a.values())-len(a) for a in axes)
        return {'sessions':len(cs),'edit_steps':total,'mean_distinct_axes':sum(map(len,axes))/len(axes),'repeated_axis_step_count':repeat,'repeated_axis_step_fraction':repeat/total,'sessions_with_repeated_axis':sum(any(v>1 for v in a.values()) for a in axes),'sessions_with_repeated_axis_fraction':sum(any(v>1 for v in a.values()) for a in axes)/len(cs)}
    result=stats(rows);result['by_kind_length']={k:stats(v) for k,v in sorted(groups.items())};return result
def main():
    result={'scope':'one same-graph seed pair (.2 and .4); whole session axis repetition includes abandoned fork branches; not a three-seed stability claim','splits':{}}
    for split in ('train','test'):
        old=sequence(V6/split);new=sequence(ROOT/'structural_candidate'/split)
        os=read(V6/split/'sampling.json');ns=read(ROOT/'structural_candidate'/split/'sampling.json')
        result['splits'][split]={'decay02_sequence':old,'decay04_sequence':new,'delta_mean_distinct_axes':new['mean_distinct_axes']-old['mean_distinct_axes'],'delta_repeated_axis_step_fraction':new['repeated_axis_step_fraction']-old['repeated_axis_step_fraction'],'sampling':{name:{'history_axis_decay':s['history_axis_decay'],'axis_counts':s['axis_counts'],'nonidentity_relative_deviation':s['nonidentity_relative_deviation'],'edge_reuse_histogram':s['edge_reuse_histogram'],'four_use_edge_fraction':s['four_use_edge_fraction'],'quota_counts':s['quota_counts'],'core_coverage':s['edited_attribute_target_coverage']['wardrobe_core'],'unused_nodes':s['unused_nodes'],'start_camera_quota_met':s['start_camera_quota_met']} for name,s in [('decay02',os),('decay04',ns)]}}
        if (ROOT/'selected_candidate/SUMMARY.json').exists():
            oldcounts=read(V7/'SUMMARY.json')[split];newcounts=read(ROOT/'selected_candidate/SUMMARY.json')[split]
            result['splits'][split]['dual_aspect']={'decay02':oldcounts,'decay04':newcounts,'delta_render_nodes':newcounts['render_nodes']-oldcounts['render_nodes']}
    (ROOT/'decay_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({s:{'old_mean_distinct':r['decay02_sequence']['mean_distinct_axes'],'new_mean_distinct':r['decay04_sequence']['mean_distinct_axes'],'old_repeat_fraction':r['decay02_sequence']['repeated_axis_step_fraction'],'new_repeat_fraction':r['decay04_sequence']['repeated_axis_step_fraction'],'dual_aspect':r.get('dual_aspect')} for s,r in result['splits'].items()},ensure_ascii=False))
if __name__=='__main__':main()
