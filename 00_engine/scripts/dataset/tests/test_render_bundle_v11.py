import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('bundle_launcher', Path(__file__).parents[1]/'run_render_bundle_v11.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture_bundle(tmp_path):
    bundle = tmp_path/'bundle with spaces'
    bundle.mkdir()
    (bundle/'jobs.json').write_text(json.dumps({'jobs':[{'job_id':'ref_a'}]}))
    (bundle/'carrier_jobs.json').write_text('{"jobs":[]}')
    queue = {'jobs':'jobs.json','worker_module':'ue_dataset_reference_v11','output_subdir':'references',
             'seed_files':{'carrier_jobs.json':'carrier_jobs.json'}}
    (bundle/'RENDER_CONFIG.json').write_text(json.dumps({'queues':{'hair':queue},
        'runtime':{'portable_runtime':True,'command_timeout':600,'render_timeout':3600,'discovery_timeout':120}}))
    machine={k:str(tmp_path/k) for k in ('workspace_root','project_root','engine_root','output_root')}
    machine['texture_pool_mb']=4096
    return bundle,machine,queue


def test_preview_and_forwarding(tmp_path):
    b,machine,q=fixture_bundle(tmp_path)
    cmd,run,_=m.build_command(b,machine,'hair',1,['ref_a'])
    assert cmd[cmd.index('--jobs')+1]==str(b/'jobs.json')
    assert cmd[cmd.index('--pool-mb')+1]=='4096'
    assert '--portable-runtime' in cmd and cmd[-4:]==['--limit','1','--job-id','ref_a']
    assert run==Path(machine['output_root'])/'references'
    assert not Path(machine['output_root']).exists()


def test_seed_and_resume_mismatch(tmp_path):
    b,machine,q=fixture_bundle(tmp_path); run=tmp_path/'output'
    m.seed_output(b,run,q)
    assert (run/'carrier_jobs.json').read_bytes()==(b/'carrier_jobs.json').read_bytes()
    (run/'carrier_jobs.json').write_text('different')
    with pytest.raises(ValueError,match='different carrier'):
        m.seed_output(b,run,q)
    assert (run/'carrier_jobs.json').read_text()=='different'


@pytest.mark.parametrize('case',['queue','limit','id','pool','path'])
def test_bad_input_fails_before_execution(tmp_path,case):
    b,machine,q=fixture_bundle(tmp_path)
    if case=='pool': machine['texture_pool_mb']=None
    if case=='path': machine['engine_root']=None
    with pytest.raises(ValueError):
        m.build_command(b,machine,'wrong' if case=='queue' else 'hair',
                        0 if case=='limit' else None,['unknown'] if case=='id' else [])
    assert not Path(machine['output_root']).exists()

