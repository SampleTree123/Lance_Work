import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cfd_native_batch40_contract_v1 as contract
import run_cfd_native_batch40_transfer_v1 as transfer
import run_cfd_native_batch40_review_v1 as review


def review_worker_function(name, **context):
    source = Path(__file__).resolve().parents[1]/'ue_cfd_native_batch40_review_v1.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == name)
    namespace = dict(context)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
    return namespace[name]


def test_review_preflight_never_loads_assets_and_missing_path_preserves_old_page():
    rows = cases()
    roles = {'body':'Body', **{f'support{i}':f'Support{i}' for i in range(5)}}
    for row in rows:
        row.update(standard_candidate_ready=True,audit_source={'path':'audit'},
            meshes=[{'role':role,'path':f"/case/{row['character_id']}/{role}"} for role in roles])
    paths = []
    state = SimpleNamespace(exists=True)
    def exists(path):
        paths.append(path)
        return state.exists
    def unexpected_load(path):
        pytest.fail('Preflight loaded an asset')
    worker_contract = SimpleNamespace(REGISTRY='registry',read=lambda p:{'cases':rows},page_cases=contract.page_cases)
    preflight = review_worker_function('preflight',contract=worker_contract,
        reference_choices=lambda hair:({}, {'male':{},'female':{}}),
        formal=SimpleNamespace(current_registry_path=lambda:'formal',read_registry=lambda p:{}),
        fixed=SimpleNamespace(BASE_ROLES=roles,_selection=lambda *a:({},[
            {'component_name':'Hair','mesh_path':'/shared/hair','kind':'hair'},
            {'component_name':'Outfit','mesh_path':'/shared/outfit','kind':'clothing'}])),
        sources=SimpleNamespace(source=lambda path:{'path':path}),
        unreal=SimpleNamespace(load_asset=unexpected_load,EditorAssetLibrary=SimpleNamespace(does_asset_exist=exists)))
    request = contract.normalize_request({})
    page,planned,_ = preflight(request)
    assert len(page) == len(planned) == 8
    assert len(paths) == 8*8 and '/shared/hair' in paths and '/shared/outfit' in paths
    state.exists = False
    events = []
    load_page = review_worker_function('load_page',preflight=preflight,
        legacy=SimpleNamespace(ensure_level=lambda:events.append('open')))
    with pytest.raises(RuntimeError,match='Missing review mesh'):
        load_page(request)
    assert events == []  # No old-slot changes or loading when metadata/path preflight fails.


def test_review_live_slot_ids_exclude_shared_assets_other_actors_and_prefix_collisions():
    rows = contract.validate_spec({'cases':cases()})
    old,kept = [r['character_id'] for r in rows[:2]]
    class Actor:
        def __init__(self,label,path): self.label,self.path = label,path
        def get_actor_label(self): return self.label
        def get_skeletal_mesh_asset(self):
            return SimpleNamespace(get_path_name=lambda:self.path) if self.path else None
    actors = [Actor('DM_CFD40_Slot01_Body',contract.UE_ROOT+'/'+old+'/Meshes/Body.Body'),
        Actor('DM_CFD40_Slot02_Body',contract.UE_ROOT+'/'+kept+'/Meshes/Body.Body'),
        Actor('DM_CFD40_Slot01_Hair','/Game/Shared/Hair.Hair'),
        Actor('DM_CFD40_Slot01_Outfit','/Game/Shared/Outfit.Outfit'),
        Actor('DM_CFD40_Slot01_Extra',contract.UE_ROOT+'/'+old+'Extra/Meshes/Body.Body'),
        Actor('Unrelated',contract.UE_ROOT+'/'+rows[2]['character_id']+'/Meshes/Body.Body'),
        Actor('DM_CFD40_Slot03_Body',None)]
    identify = review_worker_function('displayed_case_ids',PREFIX='DM_CFD40_',
        contract=SimpleNamespace(SPEC='spec',UE_ROOT=contract.UE_ROOT,read=lambda p:{'cases':rows},
            validate_spec=contract.validate_spec),unreal=SimpleNamespace(SkeletalMeshActor=Actor),
        legacy=SimpleNamespace(actors=lambda:SimpleNamespace(get_all_level_actors=lambda:actors),component=lambda a:a))
    assert identify() == {old,kept}


@pytest.mark.parametrize('unload_fails', [False,True])
def test_review_clears_then_releases_only_departing_cases_before_next_page_load(unload_fails):
    events = []
    plan = ([{'character_id':'retained'},{'character_id':'incoming'}],[],{})
    def preflight(request):
        events.append('preflight')
        return plan
    def release(identifier):
        events.append('release:'+identifier)
        if unload_fails:
            raise RuntimeError('Current character package unload failed')
        return {'receipt':'old_receipt','success':True}
    def prepare(request,value):
        assert value is plan
        events.append('load_new')
        return plan[0],[],plan[2]
    shared = SimpleNamespace(verify_baseline=lambda:events.append('verify'))
    load_page = review_worker_function('load_page',preflight=preflight,
        displayed_case_ids=lambda:{'departing','retained'},clear_slot_actors=lambda:events.append('clear'),
        legacy=SimpleNamespace(ensure_level=lambda:events.append('level') or 'level',
            cache=lambda:{'compatibility':{}}),
        transfer=SimpleNamespace(shared_runtime=lambda:shared,release_saved_case_packages=release),prepare=prepare)
    if unload_fails:
        with pytest.raises(RuntimeError,match='unload failed'):
            load_page({})
        assert events == ['preflight','level','verify','clear','release:departing','verify']
    else:
        result = load_page({})
        assert events == ['preflight','level','verify','clear','release:departing','verify','load_new']
        assert result[-1] == [{'receipt':'old_receipt','success':True}]


def test_split_recovery_is_opt_in_and_bound_to_bm001_source(tmp_path, monkeypatch):
    monkeypatch.setattr(contract, 'RUN', tmp_path)
    expected = {'character_id':'CFD40_BM_001','sex':'male','fbx':{'sha256':'locked'}}
    assert transfer.split_subdir('CFD40_BM_001', expected) == 'Meshes'
    config = {'schema_version':1,'character_id':'CFD40_BM_001',
              'split_subdir':'MeshesRecovery20261007',
              'input_fingerprint':hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest()}
    path = transfer.case_root('CFD40_BM_001')/'split_recovery_config.json'
    contract.write(path, config)
    assert transfer.split_subdir('CFD40_BM_001', expected) == 'MeshesRecovery20261007'
    assert transfer.split_subdir('CFD40_AF_001', {}) == 'Meshes'
    with pytest.raises(ValueError,match='bind'):
        transfer.split_subdir('CFD40_BM_001', {**expected,'changed':True})
    contract.write(transfer.case_root('CFD40_AF_001')/path.name, config)
    with pytest.raises(ValueError,match='bind'):
        transfer.split_subdir('CFD40_AF_001', expected)
    for bad in ('Meshes','../MeshesRecovery','MeshesRecovery/Sub','MeshesRecovery\\Sub'):
        contract.write(path, {**config,'split_subdir':bad})
        with pytest.raises(ValueError,match='safe new single'):
            transfer.split_subdir('CFD40_BM_001', expected)


def cases():
    return [{'character_id':f'{sex}_{group}_{n}','sex':sex,'group':group,'group_index':n}
            for n in range(1,6) for group in reversed(contract.GROUPS) for sex in reversed(contract.SEXES)]


@pytest.fixture
def package_release_case(tmp_path, monkeypatch):
    monkeypatch.setattr(contract, 'RUN', tmp_path)
    monkeypatch.setattr(contract, 'SPEC', tmp_path/'spec.json')
    rows = cases()
    contract.write(contract.SPEC, {'cases':rows})
    identifier = rows[0]['character_id']
    root = transfer.case_root(identifier)
    contract.write(root/identifier/'import_state.json', {'status':'audited'})
    contract.write(root/identifier/'import_audit.json', {'success':True,'standard_candidate_ready':True})
    class Package:
        def __init__(self, name): self.name = name
        def get_path_name(self): return self.name
    prefix = contract.UE_ROOT+'/'+identifier+'/'
    current = [Package(prefix+'MaterialWitnessInteractive/Material'), Package(prefix+'Meshes/Body')]
    other = [Package(contract.UE_ROOT+'/'+identifier+'Extra/Meshes/Body'),
             Package(contract.UE_ROOT+'/Other/Meshes/Body'),
             Package(contract.UE_ROOT+'/SharedSkeletons/SKEL_CFDShared_Female_v1')]
    events = []
    state = SimpleNamespace(dirty=[],result=(True,''))
    def unload(packages):
        events.append(('unload',[p.get_path_name() for p in packages]))
        return state.result
    ue = SimpleNamespace(Package=Package,ObjectIterator=lambda cls:iter(current+other),
        EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_content_packages=lambda:state.dirty,
            unload_packages=unload),SystemLibrary=SimpleNamespace(collect_garbage=lambda:events.append(('gc',))))
    monkeypatch.setitem(sys.modules, 'unreal', ue)
    return SimpleNamespace(identifier=identifier,root=root,current=current,other=other,events=events,state=state)


def test_package_release_isolates_current_prefix_and_preserves_remaining_package_evidence(package_release_case):
    case = package_release_case
    case.state.dirty = case.other  # Dirty unrelated/shared packages must not affect this release.
    result = transfer.release_saved_case_packages(case.identifier)
    names = [p.get_path_name() for p in case.current]
    assert case.events == [('unload',names),('gc',)]
    record = contract.read(result['receipt'])
    assert record['success'] and record['remaining_loaded_packages'] == sorted(names)
    assert result['selected_count'] == 2 and result['any_packages_unloaded']
    with pytest.raises(ValueError,match='Unknown batch character'):
        transfer.release_saved_case_packages('../Other')
    assert case.events == [('unload',names),('gc',)]


def test_package_release_rejects_dirty_current_packages_before_unload(package_release_case):
    case = package_release_case
    case.state.dirty = case.current[:1]
    with pytest.raises(RuntimeError,match='unsaved current character'):
        transfer.release_saved_case_packages(case.identifier)
    assert not case.events
    record = contract.read(next(case.root.glob('package_release_*.json')))
    assert not record['success'] and record['dirty_packages'] == [case.current[0].get_path_name()]


@pytest.mark.parametrize('result', ((False,''),(True,'package failed')))
def test_package_release_stops_and_records_failed_unload(package_release_case, result):
    case = package_release_case
    case.state.result = result
    with pytest.raises(RuntimeError,match='package unload failed'):
        transfer.release_saved_case_packages(case.identifier)
    assert [event[0] for event in case.events] == ['unload']
    record = contract.read(next(case.root.glob('package_release_*.json')))
    assert not record['success'] and record['error'] == result[1]


def test_package_release_skips_empty_current_prefix(package_release_case):
    case = package_release_case
    case.current.clear()
    result = transfer.release_saved_case_packages(case.identifier)
    assert result['skipped_empty'] and result['selected_count'] == 0
    assert case.events == [('gc',)]


def test_completed_skip_releases_packages_then_rechecks_shared_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(contract, 'RUN', tmp_path)
    events = []
    shared = SimpleNamespace(verify_baseline=lambda:events.append('verify'))
    monkeypatch.setattr(transfer, 'shared_runtime', lambda:shared)
    monkeypatch.setattr(transfer, '_import_character', lambda *args:{'skipped_completed':True})
    def release(identifier):
        events.append('release')
        return {'success':True}
    monkeypatch.setattr(transfer, 'release_saved_case_packages', release)
    result = transfer.editor_import('known')
    assert result['skipped_completed'] and result['package_release']['success']
    assert events == ['verify','verify','release','verify']
    events.clear()
    transfer.editor_import('known',audit_only=True)
    assert events == ['verify','verify']


def test_five_comparison_pages_cover_every_identity_once_and_require_eight_imports():
    values = contract.validate_spec({'cases':cases()})
    pages = [contract.page_cases(values,n) for n in range(1,6)]
    assert len({c['character_id'] for p in pages for c in p}) == 40
    for n,page in enumerate(pages,1):
        assert [(c['sex'],c['group'],c['group_index']) for c in page] == [
            (sex,group,n) for sex in ('male','female') for group in ('A','B','L','W')]
    with pytest.raises(ValueError,match='eight completed'):
        contract.page_cases(values[1:],1)
    with pytest.raises(ValueError,match='Duplicate'):
        contract.validate_spec({'cases':values[:-1]+[values[0]]})


def accepted():
    return {'success':True,'sexes':['female','male'],'morph_passed':True,
            'skeletal_animation_passed':True,'visual_accepted':True,'evidence':['representative report']}


def test_static_shared_import_success_cannot_bypass_dynamic_and_visual_gate(tmp_path,monkeypatch):
    for key in ('success','morph_passed','skeletal_animation_passed','visual_accepted'):
        receipt = accepted()
        receipt[key] = False
        with pytest.raises(RuntimeError,match='Morph, skeletal animation and visual'):
            transfer.validate_acceptance(receipt)
    transfer.validate_acceptance(accepted())
    receipt = tmp_path/'acceptance.json'
    contract.write(receipt,accepted())
    gates = []
    for sex in ('female','male'):
        p = tmp_path/(sex+'.json')
        contract.write(p,{'success':True,'identity_mesh_reference_preserved':True})
        gates.append(transfer.pair.source(p))
    monkeypatch.setattr(contract,'RUN',tmp_path)
    contract.write(tmp_path/'shared_skeleton_config.json',{
        'representative_acceptance':transfer.pair.source(receipt),'representative_gate':gates})
    assert transfer.common_shared_config()['representative_gate'] == gates
    contract.write(receipt,{**accepted(),'visual_accepted':False})
    with pytest.raises(RuntimeError,match='missing or changed'):
        transfer.common_shared_config()


def test_registry_rejects_individual_skeleton_even_when_import_audit_succeeded(tmp_path,monkeypatch):
    monkeypatch.setattr(contract,'RUN',tmp_path)
    monkeypatch.setattr(contract,'SPEC',tmp_path/'spec.json')
    monkeypatch.setattr(contract,'REGISTRY',tmp_path/'registry.json')
    rows = cases()
    contract.write(contract.SPEC,{'cases':rows})
    shared = {'cases':[{'sex':sex,'shared_skeleton':'/Game/Batch/Shared/'+sex} for sex in contract.SEXES]}
    contract.write(tmp_path/'shared_skeleton_config.json',shared)
    monkeypatch.setattr(transfer,'common_shared_config',lambda:shared)
    row = rows[0]
    folder = transfer.case_root(row['character_id'])
    manifest = folder/'import_manifest.json'
    audit = folder/'audit.json'
    contract.write(manifest,{'cases':[row]})
    contract.write(audit,{'success':True,'all_source_morph_names_preserved':True})
    contract.write(folder/'standard_candidate_registry.json',{
        'manifest_sha256':transfer.pair.source(manifest)['sha256'],'cases':[{
            **row,'standard_candidate_ready':True,'skeleton':'/Game/Individual/Skeleton', 'audit':str(audit)}]})
    with pytest.raises(ValueError,match='shared Skeleton contract'):
        transfer.refresh_registry()
    assert not contract.REGISTRY.exists()


def test_review_callback_uses_scoped_remote_and_verifies_result(tmp_path,monkeypatch):
    monkeypatch.setattr(contract,'RUN',tmp_path)
    calls = []
    def remote(command,run,tag,**kwargs):
        calls.append((command,tag,kwargs))
        contract.write(run/'display.json',{'success':True,'request':contract.normalize_request({}),
            'level':contract.LEVEL,'displayed':[{}]*8})
    monkeypatch.setattr(contract,'target_remote',lambda:remote)
    assert review.show({},node_id='visible-id')['success']
    assert calls[0][2]['node_id'] == 'visible-id'
    with pytest.raises(RuntimeError,match='requested page/view'):
        review.show({'focus':'1'},node_id='visible-id')
