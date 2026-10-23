"""Join planner projection proxies; never promote them to pixel acceptance."""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
proxy_path=HERE.parent/'observability/camera_observability.json'
proxy_bytes=proxy_path.read_bytes()
proxy=json.loads(proxy_bytes)
index={(s['action'],s['camera'],s['aspect']):s for s in proxy['shots']}
keys=json.loads((HERE/'paired_probe_observability_keys.json').read_text(encoding='utf-8'))
joined=[]; counts=Counter();pair_risks={}
for r in keys:
    s=index.get((r['motion'],r['camera'],r['aspect']))
    out={**r,'proxy_found':s is not None}
    counts['rows']+=1
    if s:
        out.update({'planner_representative_sex':s['planner_representative_sex'],
                    'planner_sex_matches_node_sex':s['planner_representative_sex']==r['sex'],
                    'flags':s['flags'],'head_projected_height_px':s['head_projected_height_px'],
                    'head_fraction_with_half_box_in_frame':s['head_fraction_with_half_box_in_frame'],
                    'feet_fraction_intersecting_frame':s['feet_fraction_intersecting_frame'],
                    'identity_proxy_64px_front_fraction':s['identity_proxy_threshold_sweep']['64'],
                    'trajectory_sha256':s['trajectory_sha256'],
                    'approximately_static':s['approximately_static_1cm_0p1degree']})
        counts['proxy_rows_found']+=1
        counts['representative_sex_mismatch_rows']+=not out['planner_sex_matches_node_sex']
        if r['role'] in ('left_root','right_root'):
            d=pair_risks.setdefault(r['pair_index'],{'axis':r['history_difference_axis'],'roots':[]})
            d['roots'].append(out)
    joined.append(out)
summaries=[]
for pair,d in sorted(pair_risks.items()):
    a,b=d['roots']
    row={'pair_index':pair,'history_difference_axis':d['axis'],
         'both_roots_feet_absent_in_sparse_projection':all(x['flags']['feet_boxes_never_intersect_sparse_samples'] for x in (a,b)),
         'both_roots_lower_absent_in_sparse_projection':all(x['flags']['lower_proxy_never_intersects_sparse_samples'] for x in (a,b)),
         'any_root_identity_front64_proxy_zero':any(x['identity_proxy_64px_front_fraction']==0 for x in (a,b)),
         'any_root_representative_sex_mismatch':any(not x['planner_sex_matches_node_sex'] for x in (a,b)),
         'roots_trajectory_hash_equal':a['trajectory_sha256']==b['trajectory_sha256']}
    summaries.append(row)
    counts['pairs']+=1
    for k,v in row.items():
        if isinstance(v,bool): counts[k]+=v
    if d['axis'] in ('action','camera'):
        counts['motion_or_camera_difference_pairs']+=1
        counts['motion_camera_both_roots_lower_absent']+=row['both_roots_lower_absent_in_sparse_projection']
        counts['motion_camera_any_root_sex_mismatch']+=row['any_root_representative_sex_mismatch']
result={'status':'joined_planner_proxy_not_visual_acceptance','proxy_sha256':hashlib.sha256(proxy_bytes).hexdigest(),
        'limitations':proxy['limitations']+['Missing feet/lower body does not prove two motions are visually identical.',
            'Different trajectory hashes do not prove differences are perceptually discriminable.',
            'Same trajectory hash for identity-only changes says nothing about appearance distinguishability.'],
        'counts':dict(counts),'pair_summaries':summaries,'rows':joined}
(HERE/'paired_probe_observability.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result['counts'],indent=2))
