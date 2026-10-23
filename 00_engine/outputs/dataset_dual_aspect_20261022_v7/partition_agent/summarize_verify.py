"""Verify only saved partition candidates against their immutable source chains."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import partition as p

rows=[]; summary={}; verification={}; distributions={}
for candidate in sorted(p.HERE.iterdir()):
    if not candidate.is_dir() or not any((candidate/s/'assignment.jsonl').exists() for s in ['train','test']): continue
    summary[candidate.name]={}
    for split in ['train','test']:
        assignment=candidate/split/'assignment.jsonl'
        if not assignment.exists(): continue
        d=p.load(split)
        records=[json.loads(x) for x in assignment.read_text(encoding='utf-8').splitlines()]
        assert len(records)==len(d['chains'])
        assert [r['id'] for r in records]==[c['id'] for c in d['chains']]
        assert all(r['aspect'] in p.ASPECTS for r in records)
        labels=np.array([p.ASPECTS.index(r['aspect']) for r in records],dtype=np.int8)
        assert all(r['aspect']=='landscape' for r in records if r['id'] in d['forbidden'])
        report,needs=p.stats(d,labels)
        old=json.loads((candidate/split/'stats.json').read_text(encoding='utf-8'))
        assert old==json.loads(json.dumps(report))
        assert report['all_start_cameras_covered_both']
        assert report['all_7_axes_covered_both']
        assert report['all_sexes_covered_both']
        req=json.loads((candidate/split/'node_requirements.json').read_text(encoding='utf-8'))
        assert all(req[a]==sorted(needs[i]) for i,a in enumerate(p.ASPECTS))
        summary[candidate.name][split]=report
        six_axes=['action','camera','hair','hair_color','site','wardrobe']
        for aspect in p.ASPECTS:
            st=report[aspect]; counts={k:st['axis_steps'][k] for k in six_axes}; total=sum(counts.values())
            single=st['edit_axis_mode_steps'].get('wardrobe|single_piece',0)
            whole=st['edit_axis_mode_steps'].get('wardrobe|whole_outfit',0)
            detail={'chains':st['chains'],'sex':st['chain_start_sex'],'six_axis_counts':counts,'six_axis_max_relative_deviation_pct':100*max(abs(v*6/total-1) for v in counts.values()),'six_axis_max_percentage_point_deviation':100*max(abs(v/total-1/6) for v in counts.values()),'wardrobe_single_piece':single,'wardrobe_whole_outfit':whole,'wardrobe_single_piece_fraction':single/(single+whole)}
            distributions.setdefault(candidate.name,{}).setdefault(split,{})[aspect]=detail
        rows.append(dict(candidate=candidate.name,split=split,original_nodes=report['original_nodes'],render_jobs=report['render_jobs'],shared_nodes=report['shared_nodes'],increase_pct=round(report['render_increase_fraction']*100,3),landscape_chains=report['landscape']['chains'],portrait_chains=report['portrait']['chains'],portrait_pct=round(report['portrait']['chain_fraction']*100,3),min_camera_portrait_pct=round(min(report['start_camera_portrait_fraction'].values())*100,3),max_camera_portrait_pct=round(max(report['start_camera_portrait_fraction'].values())*100,3)))
        verification[candidate.name+'/'+split]={'passed':True,'chains':len(records),'assignment_sha256':hashlib.sha256(assignment.read_bytes()).hexdigest(),'whole_chain_one_aspect':True,'source_chain_order_preserved':True,'node_requirements_exact':True,'all_start_cameras_and_axes_and_sexes_on_both':True,'portrait_forbidden_chain_count':len(d['forbidden'])}
with (p.HERE/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
p.dump(p.HERE/'summary.json',summary)
p.dump(p.HERE/'verification.json',verification)
p.dump(p.HERE/'distribution_detail.json',distributions)
p.dump(p.HERE/'economy_distribution_detail.json',distributions['economy'])
print(json.dumps(rows,indent=2))
