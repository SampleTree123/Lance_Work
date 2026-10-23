import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('camera_render', Path(__file__).parents[1] / 'ue_camera_pilot_render_v1.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def job(shot='s01'):
    return {'shot_id': shot, 'map': m.ASSET_ROOT + '/L_Pilot', 'sequence': m.ASSET_ROOT + '/LS_Test.LS_Test'}


def test_owned_paths_are_canonical_and_do_not_create_directories(tmp_path):
    selected, output, receipt = m.validate_request([job()], 'attempt01', 1280, 720, tmp_path)
    assert selected[0]['map'].endswith('/L_Pilot.L_Pilot')
    assert output == tmp_path / 'renders' / 'attempt01'
    assert receipt == tmp_path / 'render_receipts' / 'attempt01.json'
    assert not output.exists()


@pytest.mark.parametrize('attempt', ['../escape', 'a/b', 'a\\b', 'C:other', 'NUL', 'CON', '', 'a.'])
def test_attempt_path_injection_rejected(tmp_path, attempt):
    with pytest.raises(ValueError):
        m.validate_request([job()], attempt, 1280, 720, tmp_path)


@pytest.mark.parametrize('asset', ['/Game/Unrelated/X', m.ASSET_ROOT + '2/X', m.ASSET_ROOT + '/../X',
                                  m.ASSET_ROOT + '/X.Other', m.ASSET_ROOT + '/X.X:Body'])
def test_external_or_subobject_assets_rejected(tmp_path, asset):
    value = job()
    value['sequence'] = asset
    with pytest.raises(ValueError):
        m.validate_request([value], 'a01', 1280, 720, tmp_path)


def test_case_insensitive_shot_collisions_rejected(tmp_path):
    with pytest.raises(ValueError, match='Duplicate'):
        m.validate_request([job('Shot'), job('shot')], 'a01', 1280, 720, tmp_path)


@pytest.mark.parametrize('existing', ['renders/a01', 'render_receipts/a01.json'])
def test_attempt_or_receipt_cannot_be_overwritten(tmp_path, existing):
    path = tmp_path / existing
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('preserve')
    with pytest.raises(ValueError, match='already exists'):
        m.validate_request([job()], 'a01', 1280, 720, tmp_path)
    assert path.read_text() == 'preserve'


def test_unowned_output_override_rejected(tmp_path):
    value = dict(job(), output='C:/unowned')
    with pytest.raises(ValueError):
        m.validate_request([value], 'a01', 1280, 720, tmp_path)


@pytest.mark.parametrize('samples', [1, 4])
def test_supported_spatial_samples_are_accepted_without_output_writes(tmp_path, samples):
    _, output, receipt = m.validate_request(
        [job()], 'aa01', 1280, 720, tmp_path, spatial_samples=samples)
    assert not output.exists() and not receipt.exists()


@pytest.mark.parametrize('samples', [0, 2, 8, -1, True, 4.0, '4', None])
def test_unsupported_spatial_samples_rejected_before_accessing_ue(samples):
    with pytest.raises(ValueError, match='Spatial samples'):
        m.start_render(None, [job()], 'aa01', spatial_samples=samples)


@pytest.mark.parametrize('options', [
    {'disable_texture_streaming': 1}, {'disable_texture_streaming': 'false'},
    {'engine_warmup_count': -1}, {'engine_warmup_count': True},
    {'render_warmup_count': 257}, {'render_warmup_count': 32.0},
])
def test_optional_loading_controls_rejected_before_ue(options):
    with pytest.raises(ValueError):
        m.start_render(None, [job()], 'skin01', **options)


def test_existing_callers_keep_loading_defaults():
    import inspect
    parameters = inspect.signature(m.start_render).parameters
    assert parameters['disable_texture_streaming'].default is False
    assert parameters['engine_warmup_count'].default == 16
    assert parameters['render_warmup_count'].default == 8


def test_skin_wrapper_forwards_same_loading_profile_for_every_job():
    skin_spec = importlib.util.spec_from_file_location('skin_scene', Path(__file__).parents[1] / 'ue_skin_detail_scene_v1.py')
    skin = importlib.util.module_from_spec(skin_spec)
    skin_spec.loader.exec_module(skin)
    captured = {}

    class Spy:
        def start_render(self, u, jobs, attempt_id, **kwargs):
            captured.update(kwargs)
            return {'jobs': jobs, 'attempt_id': attempt_id}

    skin.renderer = lambda: Spy()
    jobs = [job('A'), job('B'), job('C')]
    result = skin.render(None, jobs, 'all_skin')
    assert result['jobs'] == jobs
    assert captured == {'width': 1920, 'height': 1080, 'spatial_samples': 4,
                        'disable_texture_streaming': True,
                        'engine_warmup_count': 64, 'render_warmup_count': 32}
