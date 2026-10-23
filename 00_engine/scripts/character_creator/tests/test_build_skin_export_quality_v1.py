"""Narrow offline evidence failures and the established ORM channel rule."""
import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[4]
SCRIPT = REPO / '00_engine/outputs/character_refresh_20261018_v1/build_skin_export_quality_v1.py'
spec = importlib.util.spec_from_file_location('skin_quality', SCRIPT)
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


@pytest.mark.parametrize('change', ['running', 'hook_other_person'])
def test_actual_prelash_identity_and_terminal_required(change):
    # Rejection occurs before any map/file or application access.
    proof = {'success': True, 'status': 'prelash_checkpoint_validated_not_final',
             'stage_validated': True, 'config': {'character_id': 'CFD40_AM_001'},
             'skin_normal_closure': {'character_id': 'CFD40_AM_001', 'complete': True}}
    if change == 'running':
        proof['status'] = 'running'
    else:
        proof['skin_normal_closure']['character_id'] = 'CFD40_AM_002'
    with pytest.raises(ValueError, match='terminal PRELASH'):
        quality.source_maps(proof, 'CFD40_AM_001', {})


def test_pending_assembly_rejected_before_export_access(tmp_path):
    paths = []
    for name, data in [('assembly', {'character_id': 'CFD40_AM_001', 'status': 'pending'}),
                       ('inventory', {}), ('audit', {})]:
        path = tmp_path / (name + '.json')
        path.write_text(json.dumps(data))
        paths.append(path)
    with pytest.raises(ValueError, match='pending refused'):
        quality.build('CFD40_AM_001', *paths)


def test_orm_uses_roughness_green_and_rejects_real_component_change(tmp_path):
    def image(name, rgb):
        path = tmp_path / (name + '.png')
        Image.new('RGB', (8, 8), rgb).save(path)
        return quality.pin(path)
    normal = image('normal', (128, 128, 255))
    ao = image('ao', (37, 55, 77))
    rough = image('rough', (2, 149, 220))  # Deliberately not gray.
    orm = image('orm', (37, 149, 0))
    snapshot = {'materials': [{'owner': 'avatar', 'mesh': 'CC_Base_Body', 'material': material,
                'textures': {'ambient_occlusion': ao, 'roughness': rough}}
                for material in quality.MATERIALS]}
    declaration = {'character': {'Object': {'character': {'Meshes': {'CC_Base_Body': {'Materials': {
        material + '_Pbr': {'Textures': {'Normal': {'Texture Path': 'normal.png'},
                                       'ORM': {'Texture Path': 'orm.png'}}}
        for material in quality.MATERIALS}}}}}}}
    path = tmp_path / 'character.json'
    path.write_text(json.dumps(declaration))
    inventory = {'files': [normal, orm]}
    maps = {material: normal for material in quality.MATERIALS}
    assert all(c['max_error'] == 0 for row in quality.compare_maps(maps, snapshot, inventory, path)
               for c in row['orm_source_components'])
    # Valid current pin, actual different source pixels: must not turn into tolerance.
    changed = copy.deepcopy(snapshot)
    changed['materials'][0]['textures']['roughness'] = image('different_rough', (2, 148, 220))
    with pytest.raises(ValueError, match='ORM component differs'):
        quality.compare_maps(maps, changed, inventory, path)
