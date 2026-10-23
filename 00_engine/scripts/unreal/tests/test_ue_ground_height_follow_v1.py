"""Fixed shooting support preserves authored jumps without collision dependence."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import ue_ground_height_follow_v1 as ground
import ue_production_trial_render_v1 as trials


def vector(x=0., y=0., z=0.):
    return NS(x=x, y=y, z=z)


def fixture(monkeypatch, site_id):
    config = ground.FIXED_SITE_SUPPORT[site_id]
    site = {'site_id': site_id, **copy.deepcopy(config), 'position': copy.deepcopy(config['saved_position_cm'])}
    position = vector(**site['position'])
    actor = NS(get_actor_location=lambda: position)
    body = NS(get_world_transform=lambda: position)
    monkeypatch.setattr(ground, 'body_component', lambda u, a: body)
    # Large horizontal travel and a 200cm authored jump must have no effect on
    # the analytic plane. Pelvis Z is never used as a ground correction.
    monkeypatch.setattr(ground, 'pelvis_position', lambda u, anim, t: vector(t*5000., t*-2500., 100.+200.*t))
    transform = lambda a, p: vector(a.x+p.x, a.y+p.y, a.z+p.z)
    u = NS(MathLibrary=NS(transform_location=transform))
    return u, actor, site


@pytest.mark.parametrize('site_id', list(ground.FIXED_SITE_SUPPORT))
def test_plane_covers_full_jump_and_travel_without_world_or_collision(monkeypatch, site_id):
    u, actor, site = fixture(monkeypatch, site_id)
    baseline = actor.get_actor_location().z
    values = [ground.sample(u, actor, object(), t, site=site) for t in (0., 10., 2.5, 10.)]
    assert all(row['actor_z_cm'] == baseline and row['offset_z_cm'] == 0. for row in values)
    assert values[1] == values[-1]  # Arbitrary seek order does not accumulate.
    assert values[1]['world_xy_cm'][0] - values[0]['world_xy_cm'][0] == 50000.
    assert values[1]['support_plane']['plane_z_cm'] == site['position']['z']
    assert values[1]['support_plane']['coverage'] == 'infinite_xy'
    trajectory = ground.sample_trajectory(u, actor, object(), frame_count=300, site=site)
    assert len(trajectory['frames']) == 301
    assert trajectory['frames'][-1]['t'] == 10.
    assert ground.require_trajectory_support(trajectory, site) is trajectory
    assert actor.get_actor_location().z == baseline  # Read-only bake.


def test_nonconfigured_site_keeps_missing_collision_failure(monkeypatch):
    u, actor, _ = fixture(monkeypatch, 'site_98aac485de')
    u.UnrealEditorSubsystem = object()
    u.get_editor_subsystem = lambda _: NS(get_editor_world=lambda: object())
    u.Vector = vector
    u.TraceTypeQuery = NS(ECC_VISIBILITY=object())
    u.DrawDebugTrace = NS(NONE=object())
    u.SystemLibrary = NS(line_trace_single=lambda *args: None)
    with pytest.raises(ValueError, match='没有可碰撞地面'):
        ground.sample(u, actor, object(), 0., site={'site_id': 'other'})


def test_support_is_scoped_by_saved_id_and_exact_map():
    assert ground.support_for_site({'name': '九龙巷道/1', 'map': '/Game/Scenes/Kowloon/Maps/Kowloon'}) is None
    with pytest.raises(ValueError, match='场景不一致'):
        ground.support_for_site({'site_id': 'site_98aac485de', 'map': '/Game/Elsewhere'})


def test_resaved_height_moves_plane_and_preserves_original_provenance(monkeypatch):
    _, _, site = fixture(monkeypatch, 'site_98aac485de')
    site['position']['z'] = 123.5
    plane = ground.support_for_site(site)
    assert plane['plane_z_cm'] == 123.5
    assert plane['saved_position_cm']['z'] == 0.
    site['position']['z'] = float('nan')
    with pytest.raises(ValueError, match='有效高度'):
        ground.support_for_site(site)


def test_preview_and_render_share_site_policy_and_preserve_source(monkeypatch):
    u, actor, site = fixture(monkeypatch, 'site_cbee266c51')
    original = copy.deepcopy(site)
    u.Vector = vector
    u.load_asset = lambda path: object()
    writes = []
    actor.set_actor_location = lambda location, sweep, teleport: writes.append(location.z)
    state = {'character': actor, 'site': site}
    w = NS(u=u, live=lambda: state, owned=lambda: [actor])
    preview = ground.apply_preview(w, {'animation_path': '/Fixture'}, 5.)
    monkeypatch.setattr(trials, 'module', lambda name: ground)
    rendered = trials.sample_ground_height(u, actor, object(), object(), {'frame_count': 2}, site=site)
    assert rendered['support_plane'] == preview['support_plane']
    assert all(row['actor_z_cm'] == preview['actor_z_cm'] for row in rendered['frames'])
    assert writes == [-14110.]
    assert site == original


def test_legacy_or_wrong_plane_trajectory_cannot_be_reused(monkeypatch):
    u, actor, site = fixture(monkeypatch, 'site_98aac485de')
    old = {'frames': [{'actor_z_cm': 0., 'offset_z_cm': 0.}]}
    with pytest.raises(ValueError, match='new trial ID'):
        ground.require_trajectory_support(old, site)
    trajectory = ground.sample_trajectory(u, actor, object(), frame_count=2, site=site)
    trajectory['frames'][1]['actor_z_cm'] = 1.
    with pytest.raises(ValueError, match='constant actor Z'):
        ground.require_trajectory_support(trajectory, site)
