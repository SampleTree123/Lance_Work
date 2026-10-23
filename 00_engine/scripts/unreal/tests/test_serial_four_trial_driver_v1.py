"""Bounded resume/resource contracts only; no UE, renders, network or encoding."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest

PATH=Path(__file__).resolve().parents[3]/'outputs/production_workflow_20261017_v1/run_serial_four_trials_v1.py'
spec=importlib.util.spec_from_file_location('_test_serial_four_trials',PATH)
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)


def fixture_data(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,'RUN',tmp_path);monkeypatch.setattr(driver,'STATE',tmp_path/'serial_trials')
    shot={'shot_id':'trial','width':1440,'height':2560}
    prepared={'job':{'shot_id':'trial','map':'map','sequence':'sequence'},
        'prepared_assets':[{'path':str(tmp_path/'map.umap'),'sha256':'mapsha'},{'path':str(tmp_path/'sequence.uasset'),'sha256':'seqsha'}]}
    receipt={'attempt_id':'attempt','status':'completed','success':True,'jobs':[prepared['job']],
        'inputs':prepared['prepared_assets'],'render_contract':{'width':1440,'height':2560,'fps':30,'range_start_inclusive':0,'frame_counts_by_shot':{'trial':300}}}
    return shot,prepared,receipt


def test_resource_guard_enforces_requested_ram_and_disk_before_start(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,'RUN',tmp_path)
    monkeypatch.setattr(driver.psutil,'virtual_memory',lambda:SimpleNamespace(available=6*2**30))
    monkeypatch.setattr(driver.psutil,'disk_usage',lambda _:(_ for _ in ()).throw(SystemError('bad format char')))
    monkeypatch.setattr(driver.shutil,'disk_usage',lambda _:SimpleNamespace(free=11*2**30))
    assert driver.resource_guard()['available_ram_gib']==6.
    monkeypatch.setattr(driver.psutil,'virtual_memory',lambda:SimpleNamespace(available=4.99*2**30))
    with pytest.raises(RuntimeError):driver.resource_guard()
    monkeypatch.setattr(driver.psutil,'virtual_memory',lambda:SimpleNamespace(available=6*2**30))
    monkeypatch.setattr(driver.shutil,'disk_usage',lambda _:SimpleNamespace(free=9.99*2**30))
    with pytest.raises(RuntimeError):driver.resource_guard()


def test_exact_prepared_files_job_and_frame_grid_required(tmp_path,monkeypatch):
    shot,prepared,receipt=fixture_data(tmp_path,monkeypatch)
    assert driver.render_matches(receipt,prepared,shot)
    receipt['inputs'][0]=dict(receipt['inputs'][0],sha256='changed')
    # Avoid sharing the mutated fixture list with prepared.
    prepared['prepared_assets']=[{'path':str(tmp_path/'map.umap'),'sha256':'mapsha'},{'path':str(tmp_path/'sequence.uasset'),'sha256':'seqsha'}]
    assert not driver.render_matches(receipt,prepared,shot)


def test_verified_receipt_can_resume_over_preserved_failed_history(tmp_path,monkeypatch):
    shot,prepared,receipt=fixture_data(tmp_path,monkeypatch)
    driver.write(tmp_path/'render_receipts/good.json',receipt)
    driver.write(tmp_path/'render_receipts/failed.json',dict(receipt,status='failed',success=False))
    assert driver.find_render(prepared,shot)[0].name=='good.json'


def test_uncertain_failed_or_duplicate_attempts_never_auto_retry(tmp_path,monkeypatch):
    shot,prepared,receipt=fixture_data(tmp_path,monkeypatch)
    path=tmp_path/'render_receipts/uncertain.json'
    driver.write(path,dict(receipt,status='submission_outcome_unknown',success=False))
    with pytest.raises(ValueError):driver.find_render(prepared,shot)
    driver.write(path,receipt);driver.write(path.with_name('second_good.json'),dict(receipt,attempt_id='second'))
    with pytest.raises(ValueError):driver.find_render(prepared,shot)


def test_active_receipt_is_observed_exactly_and_terminal_failure_stops(tmp_path,monkeypatch):
    shot,prepared,receipt=fixture_data(tmp_path,monkeypatch)
    path=tmp_path/'render_receipts/active.json';driver.write(path,dict(receipt,status='submitted',success=False))
    assert driver.find_render(prepared,shot)[0]==path
    driver.write(path,dict(receipt,status='failed',success=False))
    with pytest.raises(RuntimeError):driver.await_render(path,prepared,shot,1)


def test_import_has_no_unreal_module_or_dispatch():
    assert 'unreal' not in driver.__dict__
    source=PATH.read_text('utf-8')
    assert "time.sleep(10)" in source
    assert '.kill(' not in source and '.terminate(' not in source
    assert 'resource_guard()' in source
