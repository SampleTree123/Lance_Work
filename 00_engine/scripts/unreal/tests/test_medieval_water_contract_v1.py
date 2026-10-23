"""Focused offline tests against frozen real source/target receipts; no UE."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, 'D:/UE/Lance_Work/00_engine/scripts/unreal')
sys.path.insert(0, str(Path(__file__).parent))
import ue_scene_folder_organization_v1 as m
import ue_medieval_water_contract_v1 as contract


class MedievalWaterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This performs the actual pinned receipt/source and 516 backup hashes.
        cls.evidence = contract.read_evidence(m)

    def setUp(self):
        self.before = copy.deepcopy(self.evidence['source']['signature'])
        self.after = copy.deepcopy(self.evidence['target']['signature'])
        self.relative = copy.deepcopy(self.evidence['target']['component_transforms'])
        self.water = copy.deepcopy(self.evidence['target']['water'])

    def compare(self):
        return contract.compare_live(m, self.evidence, self.before, self.after, self.relative, self.water)

    def test_real_frozen_geometry_and_all_fields_pass_only_exact_name_pair(self):
        raw = copy.deepcopy(self.after)
        compared = self.compare()
        self.assertTrue(contract.exact(m, compared, self.before))
        self.assertEqual(self.after, raw)
        self.assertEqual(contract.water_component(self.after)['mesh'], contract.TARGET_MESH)

    def test_missing_or_bad_receipt_pin_rejected(self):
        with patch.object(m, 'sha', return_value='0' * 64):
            with self.assertRaisesRegex(RuntimeError, 'receipt SHA'):
                contract.read_evidence(m)

    def test_ordinary_asset_with_same_leaf_rejected(self):
        self.water['mesh'] = '/Game/Scenes/Medieval_Environment/WaterInfoMesh_6.WaterInfoMesh_6'
        with self.assertRaisesRegex(RuntimeError, 'identity'):
            self.compare()

    def test_different_owner_rejected(self):
        self.water['mesh_outer'] = self.water['mesh_outer'].replace('WaterBodyOcean_1', 'WaterBodyOcean_2')
        with self.assertRaisesRegex(RuntimeError, 'identity'):
            self.compare()

    def test_different_component_rejected(self):
        self.water['component_name'] = 'DilatedWaterInfoMeshComponent'
        with self.assertRaisesRegex(RuntimeError, 'identity'):
            self.compare()

    def test_unknown_suffix_rejected(self):
        contract.water_component(self.after)['mesh'] = contract.TARGET_MESH.replace('_6', '_7')
        with self.assertRaisesRegex(RuntimeError, 'target signature'):
            self.compare()

    def test_vertex_change_rejected(self):
        geometry = self.water['geometry']['value']
        geometry['vertices'][0][1][0][0] += 1.0
        with self.assertRaisesRegex(RuntimeError, 'geometry/descriptor'):
            self.compare()

    def test_uv_change_rejected(self):
        self.water['geometry']['value']['triangles'][0]['uvs'][0] = ['changed UV']
        with self.assertRaisesRegex(RuntimeError, 'geometry/descriptor'):
            self.compare()

    def test_material_parameter_change_rejected(self):
        self.water['descriptor']['materials'][0]['scalar']['maxflowvelocity'] += 1.0
        with self.assertRaisesRegex(RuntimeError, 'geometry/descriptor'):
            self.compare()

    def test_other_actor_transform_change_rejected(self):
        actor = next(a for a in self.after['actors'] if a['name'] != 'WaterBodyOcean_1')
        actor['transform'][0] += 1.0
        with self.assertRaisesRegex(RuntimeError, 'target signature'):
            self.compare()

    def test_relative_transform_change_rejected(self):
        actor = next(a for a in self.relative if a['components'])
        actor['components'][0]['transform'][0] += 1.0
        with self.assertRaisesRegex(RuntimeError, 'relative transforms'):
            self.compare()

    def test_missing_complete_geometry_rejected(self):
        self.water['geometry'] = {'available': False, 'error': 'Unavailable'}
        with self.assertRaisesRegex(RuntimeError, 'complete geometry'):
            self.compare()


if __name__ == '__main__':
    unittest.main(verbosity=2)
