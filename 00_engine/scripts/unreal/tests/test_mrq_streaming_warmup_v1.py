"""Boundary checks for first-view warmup; no Unreal process or render required."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mrq_streaming_warmup_v1 as warmup


@pytest.fixture(autouse=True)
def isolated_local_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(warmup, 'LOCAL_PROFILE', tmp_path/'profile.json')


def owned_job(name, values):
    settings = SimpleNamespace(get_editor_property=values.__getitem__, set_editor_property=values.__setitem__)
    config = SimpleNamespace(find_or_add_setting_by_class=lambda cls: settings)
    return SimpleNamespace(job_name=name, get_configuration=lambda: config)


def test_every_job_is_read_back_without_changing_sampling_or_output():
    settings = [{'use_camera_cut_for_warm_up': False, 'engine_warm_up_count': 16,
                 'render_warm_up_count': 8, 'render_warm_up_frames': False,
                 'spatial_sample_count': spatial, 'temporal_sample_count': 1}
                for spatial in (1, 4)]
    jobs = [owned_job(str(i), values) for i, values in enumerate(settings)]
    result = warmup.apply(SimpleNamespace(MoviePipelineAntiAliasingSetting=object()),
                          SimpleNamespace(get_jobs=lambda: jobs))
    assert [row['job_name'] for row in result['readback_by_job']] == ['0', '1']
    for i, values in enumerate(settings):
        assert result['readback_by_job'][i]['settings'] == warmup.SETTINGS
        assert values == {**warmup.SETTINGS, 'spatial_sample_count': (1, 4)[i], 'temporal_sample_count': 1}
    assert 'not measured' in result['streaming_completion']


def test_explicit_camera_cut_preroll_is_rejected_instead_of_silently_replaced():
    values = {'use_camera_cut_for_warm_up': True, 'engine_warm_up_count': 16}
    before = dict(values)
    with pytest.raises(ValueError, match='explicit camera-cut preroll'):
        warmup.apply(SimpleNamespace(MoviePipelineAntiAliasingSetting=object()),
                     SimpleNamespace(get_jobs=lambda: [owned_job('preroll', values)]))
    assert values == before


def test_empty_queue_cannot_claim_verified_warmup():
    with pytest.raises(ValueError, match='populated owned queue'):
        warmup.apply(SimpleNamespace(), SimpleNamespace(get_jobs=lambda: []))


def test_local_profile_is_machine_scoped_and_missing_profile_inherits(monkeypatch):
    monkeypatch.setattr(warmup.platform, 'node', lambda: 'LOCAL-PC')
    assert warmup.pool_profile()['pool_size_mb'] is None
    warmup.LOCAL_PROFILE.write_text(json.dumps({'schema': 'local_texture_streaming_profile_v1',
        'machine_name': 'local-pc', 'pool_size_mb': 7000}), encoding='utf-8')
    actual = warmup.pool_profile()
    assert actual['pool_size_mb'] == 7000 and actual['source'] == 'local_machine_profile'
    assert len(actual['sha256']) == 64
    monkeypatch.setattr(warmup.platform, 'node', lambda: 'DIFFERENT-PC')
    with pytest.raises(ValueError, match='belong to this machine'):
        warmup.pool_profile()
    assert warmup.pool_profile(6000) == {'source': 'explicit_parameter', 'pool_size_mb': 6000}


@pytest.mark.parametrize('value', [True, 0, -1, '7000', 7000.5])
def test_invalid_pool_budget_cannot_disable_or_unlimit_streaming(value):
    with pytest.raises(ValueError, match='integer'):
        warmup.pool_profile(value)


def test_mrq_budget_is_separate_and_legacy_profile_still_works(monkeypatch):
    monkeypatch.setattr(warmup.platform, 'node', lambda: 'LOCAL-PC')
    profile = {'schema': 'local_texture_streaming_profile_v1',
               'machine_name': 'local-pc', 'pool_size_mb': 7000, 'mrq_pool_size_mb': 10240}
    warmup.LOCAL_PROFILE.write_text(json.dumps(profile), encoding='utf-8')
    assert warmup.pool_profile()['pool_size_mb'] == 7000
    assert warmup.pool_profile(for_render=True)['pool_size_mb'] == 10240
    profile.pop('mrq_pool_size_mb')
    warmup.LOCAL_PROFILE.write_text(json.dumps(profile), encoding='utf-8')
    assert warmup.pool_profile(for_render=True)['pool_size_mb'] == 7000


@pytest.mark.parametrize('bad_readback', [False, True])
def test_pool_uses_reversible_mrq_cvar_and_retains_existing_overrides(bad_readback):
    aa_values = {'use_camera_cut_for_warm_up': False}
    aa = SimpleNamespace(get_editor_property=aa_values.__getitem__, set_editor_property=aa_values.__setitem__)
    entries = [SimpleNamespace(name='r.MotionBlurQuality', value=0., is_enabled=True),
               SimpleNamespace(name='r.Streaming.PoolSize', value=1000., is_enabled=False)]
    calls = []
    def update(name, value):
        calls.append((name, value))
        if not bad_readback: entries[-1].value = value
        return True
    def enable(name, enabled):
        assert name == warmup.POOL_CVAR
        entries[-1].is_enabled = enabled
        return True
    cvars = SimpleNamespace(add_or_update_console_variable=update,
        update_console_variable_enable_state=enable, get_console_variables=lambda: entries)
    aa_class, cvar_class = object(), object()
    def setting(cls):
        assert cls in (aa_class, cvar_class)
        return aa if cls is aa_class else cvars
    job = SimpleNamespace(job_name='owned', get_configuration=lambda: SimpleNamespace(find_or_add_setting_by_class=setting))
    u = SimpleNamespace(MoviePipelineAntiAliasingSetting=aa_class, MoviePipelineConsoleVariableSetting=cvar_class)
    if bad_readback:
        with pytest.raises(ValueError, match='failed readback'):
            warmup.apply(u, SimpleNamespace(get_jobs=lambda: [job]), pool_size_mb=7000)
    else:
        result = warmup.apply(u, SimpleNamespace(get_jobs=lambda: [job]), pool_size_mb=7000)
        assert result['readback_by_job'][0]['texture_pool_cvar'] == {
            'name': warmup.POOL_CVAR, 'value': 7000., 'is_enabled': True}
        assert result['texture_pool']['pool_size_mb'] == 7000
    assert calls == [(warmup.POOL_CVAR, 7000.)]
    assert entries[0].name == 'r.MotionBlurQuality' and entries[0].value == 0. and entries[0].is_enabled
