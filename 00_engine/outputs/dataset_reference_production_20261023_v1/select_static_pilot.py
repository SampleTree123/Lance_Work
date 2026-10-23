"""Select a small real-ID reference sample; never modify adopted requirements."""
import json
from pathlib import Path
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
manifest=read(R/'static_reference_jobs.json');jobs=manifest['jobs']
carriers={j['job_id']:j for j in read(R/'carrier_jobs.json')['jobs']}
def slot(job):
    return next((a.get('slot','shared_shoes') for a in carriers[job['source_job_id']]['appearance']['wardrobe_assets'] if a['asset_id']==job.get('asset_id')),None)
selected=[next(j for j in jobs if j['reference_kind']=='scene' and j['source_job_id']=='train_node_000967')]
for target in ['shirts','shared_shoes','family_accessory']:
    selected.append(next(j for j in jobs if j['reference_kind']=='garment' and slot(j)==target and j['view']=='front'))
selected.append(next(j for j in jobs if j['reference_kind']=='identity'))
hair=next(j for j in jobs if j['reference_kind']=='hair' and j['view']=='front')
selected.append(hair)
state=carriers[hair['source_job_id']]['state']
selected.append(next(j for j in jobs if j['reference_kind']=='hair' and j['view']=='back' and carriers[j['source_job_id']]['state']['identity']==state['identity'] and j['hair_id']==hair['hair_id']))
manifest.update(jobs=selected,job_count=len(selected),selection_note='One background, shirt, shared shoes, accessory, identity, matching front/back hair carrier')
(R/'static_pilot_jobs.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print([(j['job_id'],j['reference_kind'],j.get('asset_id'),j.get('view')) for j in selected])
