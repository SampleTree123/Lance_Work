import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('studio_v2', Path(__file__).parents[1] / 'ue_camera_studio_lighting_v2.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.mark.parametrize('path', [m.ASSET_ROOT + '/Maps/L_Test.L_Test',
    m.ASSET_ROOT + '/MapsV20/L_Test', '/Game/Unrelated/MapsV2/L_Test',
    m.MAP_ROOT + '../L_Test', m.MAP_ROOT + 'L_Test.L_Test:PersistentLevel'])
def test_rejects_old_maps_and_unowned_or_subobject_paths(path):
    with pytest.raises(ValueError):
        m.validate_world_path(path)


def test_accepts_only_clean_new_v2_map_package():
    assert m.validate_world_path(m.MAP_ROOT + 'L_Test.L_Test') == m.MAP_ROOT + 'L_Test'


@pytest.mark.parametrize('x,y', [(25,25), (-25,25), (-125,-225), (325,-425), (100,0), (-100,0)])
def test_world_checker_signed_coordinates_remain_two_colors_and_alternate(x, y):
    alpha = m.checker_alpha(x, y)
    assert alpha in (0., 1.)
    assert m.checker_alpha(x + 100., y) == 1. - alpha
    assert m.checker_alpha(x, y + 100.) == 1. - alpha
    assert m.checker_alpha(x + 200., y) == alpha


def test_only_key_casts_shadows_and_all_lights_are_white_directional_profile():
    assert [light['shadows'] for light in m.LIGHTS] == [True, False, False, False]
    assert [light['lux'] for light in m.LIGHTS] == [1.8, 1.2, .6, .6]
    assert len({light['label'] for light in m.LIGHTS}) == 4
    assert m.EXPOSURE_BIAS == .2
