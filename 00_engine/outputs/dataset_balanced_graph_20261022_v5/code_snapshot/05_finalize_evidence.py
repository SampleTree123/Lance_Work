"""Pin actual inputs/code and check the scoped offline delivery, without UE."""
import hashlib,json,shutil,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}

def main():
    codes=[HERE/n for n in ['build_balanced.py','sample_balanced.py','run_sampling.py','audit_candidate.py','summarize_results.py','finalize_evidence.py']]
    dependencies=[BASE/'dataset_trial_build_20261021_v1'/n for n in ('build_trial.py','normalize_catalog.py','catalog.json')]
    dependencies += [BASE/'dataset_local_support_20261021_v3'/'resample_local.py',BASE/'dataset_local_support_20261021_v3'/'blocks'/'build_blocks.py']
    snapshot=HERE/'code_snapshot';snapshot.mkdir(exist_ok=True)
    snapshots=[]
    for i,p in enumerate(codes+dependencies):
        target=snapshot/f'{i:02d}_{p.name}';shutil.copyfile(p,target)
        snapshots.append({'source':pin(p),'snapshot':pin(target)})
    current=read(HERE/'catalog_current.json');frozen=read(HERE/'catalog_snapshot.json')
    equality={k:current[k]==frozen[k] for k in ('sexes','actions','cameras','sites','exclusions','hair_colors','candidate_policy')}
    runtime=[]
    for item in current['source_pins']:
        p=Path(item['path'])
        row=pin(p);row['matches_catalog_capture']=row['sha256']==item['sha256'];runtime.append(row)
    methods={'date':'2026-10-22','scope':'offline graph and session manifests only; no rendered video',
             'current_catalog_semantics_match_consumed_frozen_catalog':equality,
             'runtime_source_pins':runtime,'code_and_input_snapshots':snapshots,
             'construction_seeds':{'train':2026102201,'test':2026102202},
             'sampling_seeds':[{'train':x,'test':x+1} for x in (2026102251,2026102271,2026102291)],
             'primary_candidate':'candidate_c_seed1','alternative_seed_runs_not_additional_dataset_samples':['candidate_c_seed2','candidate_c_seed3'],
             'external_dependencies':'Existing project Python registry and saved catalogue; code snapshots are forensic copies, original imports resolve project-relative paths.',
             'randomness_scope':'three sampling seeds on one fixed graph; no construction-seed robustness claim',
             'experimental_history':{'candidate_a_seed1':'initial six-axis imbalance and incomplete changed-target coverage; not selected',
                 'candidate_b_seed1':'balanced and full used-node values, but one changed garment target missing; not selected',
                 'candidate_c_seed1':'explicit coverage plus balanced low-reuse sampling; primary candidate'}}
    write(HERE/'INPUTS_AND_METHODS.json',methods)
    checks=[]
    def check(name,ok,detail=None):checks.append({'name':name,'passed':bool(ok),'detail':detail})
    check('current_catalog_matches_consumed_snapshot',all(equality.values()),equality)
    check('runtime_input_hashes_unchanged_since_capture',all(r['matches_catalog_capture'] for r in runtime))
    for name in ('candidate_c_seed1','candidate_c_seed2','candidate_c_seed3'):
        a=read(HERE/name/'audit.json')
        check(name+'_independent_hard_audit',a['passed_hard_checks'])
        check(name+'_train_garments_truly_introduced',a['train']['wardrobe']['introduced_core_target_coverage']['distinct']==239)
        for split in ('train','test'):
            r=a[split]
            check(name+'_'+split+'_four_use_soft_target',r['soft_targets']['four_use_fraction_at_most_0_005'])
            check(name+'_'+split+'_all_registered_nodes_used',r['counts']['unused_nodes']==0)
    artifact_paths=[HERE/n for n in ('README.md','GOAL.md','RULES.json','REPORT.md','CURRENT_CANDIDATE.json','comparison.json','sampling_stability.json','initial_camera_distribution.json','INPUTS_AND_METHODS.json','documentation_result_sync.json')]
    artifact_paths.extend(p for name in ('candidate_c_seed1','candidate_c_seed2','candidate_c_seed3') for p in (HERE/name).rglob('*') if p.is_file())
    check('required_artifacts_present',all(p.exists() for p in artifact_paths))
    write(HERE/'DELIVERY_MANIFEST.json',{'created_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'artifacts':[pin(p) for p in artifact_paths]})
    check('three_seed_stability_recorded',len(read(HERE/'sampling_stability.json'))==3)
    report={'status':'passed' if all(c['passed'] for c in checks) else 'failed','checks':checks,
            'limits':['No rendering or visual QA','Not a model-quality evaluation','Test is a value subset, not an unseen-scene split',
                      'Initial camera marginal distribution remains graph-dependent; see REPORT.md',
                      'Mean edge reuse near 2 is a soft reduction target; wardrobe reuse is lower than 2',
                      'Conditional wardrobe single/whole is near, not exactly, 50/50']}
    write(HERE/'delivery_verification.json',report)
    print(json.dumps({'status':report['status'],'checks':len(checks),'failures':[c for c in checks if not c['passed']]}))
    if report['status']!='passed':raise SystemExit(1)

if __name__=='__main__':main()
