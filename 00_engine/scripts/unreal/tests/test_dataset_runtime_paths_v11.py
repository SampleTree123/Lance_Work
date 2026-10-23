"""Portable-path fake fixtures only; does not import Unreal or touch UE assets."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "dataset_runtime_paths_v11.py"
SPEC = importlib.util.spec_from_file_location("tested_dataset_runtime_paths_v11", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimePathsTests(unittest.TestCase):
    def setUp(self):
        temp_root = SOURCE.parents[1].parent / "temp/dataset_runtime_paths_v11_tests"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.workspace, self.project = root / "different_workspace", root / "unrelated_project/NewProject.uproject"
        self.scripts = self.workspace / "00_engine/scripts/unreal"
        self.formal = self.workspace / "00_engine/outputs/production_workflow_20261017_v1"
        self.scripts.mkdir(parents=True)
        self.formal.mkdir(parents=True)
        self.project.parent.mkdir()
        self.project.write_text("{}", encoding="utf-8")
        self.adapter = MODULE.RuntimePaths(self.workspace, self.project)

    def test_read_pin_and_dynamic_helper_use_relocated_roots(self):
        evidence = self.workspace / "00_engine/outputs/example/audit.json"
        evidence.parent.mkdir(parents=True)
        evidence.write_text('{"audit":"unchanged source bytes"}', encoding="utf-8")
        old = "D:\\UE\\Lance_Work\\00_engine\\outputs\\example\\audit.json"
        pin = {"path": old, "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}
        pointer = self.formal / "pointer.json"
        pointer.write_text(json.dumps({"source": pin, "ue": "/Game/Characters/A.A"}), encoding="utf-8")
        before = pointer.read_bytes()
        helper = self.formal / "helper.py"
        helper.write_text("from pathlib import Path\nimport json\nCONTENT=Path('D:/UE/projects/datatry_02/Content')\n"
                          "def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))\n", encoding="utf-8")
        (self.scripts / "probe.py").write_text(
            "from pathlib import Path\nimport json,hashlib,importlib.util\n"
            "PROJECT_CONTENT=Path(__file__).resolve().parents[1]/'incorrect_derived_project/Content'\n"
            "def check(p):\n"
            " d=json.loads(Path(p).read_text(encoding='utf-8'))\n"
            " f=Path(d['source']['path'])\n"
            " return d['source']=={'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()},d['ue']\n"
            "def helper(p):\n"
            " s=importlib.util.spec_from_file_location('_fake_helper',p)\n"
            " m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m\n", encoding="utf-8")
        probe = self.adapter.load("probe")
        self.assertEqual(probe.check("D:/UE/Lance_Work/00_engine/outputs/production_workflow_20261017_v1/pointer.json"),
                         (True, "/Game/Characters/A.A"))
        self.assertEqual(probe.PROJECT_CONTENT, self.project.parent / "Content")
        dynamic = probe.helper(str(helper))
        self.assertEqual(dynamic.CONTENT, self.project.parent / "Content")
        self.assertEqual(dynamic.read(pointer)["source"]["path"], str(evidence))
        self.assertEqual(pointer.read_bytes(), before)

    def test_unknown_root_traversal_and_idempotence(self):
        self.assertEqual(self.adapter.path(self.workspace / "00_engine/test.json"), self.workspace / "00_engine/test.json")
        self.assertEqual(self.adapter.path("D:/UE/projects/datatry_02/datatry_02.uproject"), self.project)
        with self.assertRaisesRegex(ValueError, "Unmapped"):
            self.adapter.path("D:/UE/exports/needed.fbx")
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.adapter.path("D:/UE/Lance_Work/../escape")
        historical = {"source": "D:/UE/exports/historical.fbx", "object": "/Game/Mesh.Mesh"}
        self.assertEqual(self.adapter.relocate_document(historical), historical)

    def test_shared_json_and_pathlib_are_unchanged(self):
        import pathlib
        original_path, original_loads = pathlib.Path, json.loads
        (self.scripts / "probe.py").write_text("from pathlib import Path\nimport json\n", encoding="utf-8")
        probe = self.adapter.load("probe")
        self.assertIs(pathlib.Path, original_path)
        self.assertIs(json.loads, original_loads)
        self.assertIsNot(probe.Path, pathlib.Path)
        self.assertIsNot(probe.json, json)

    def test_real_night_configuration_resolves_case_audit_in_new_workspace(self):
        for name in ("night_character_review_v1.py", "ue_pair_revision_runtime_20261019_v1.py"):
            shutil.copyfile(SOURCE.with_name(name), self.scripts / name)
        audit = self.workspace / "00_engine/outputs/fake_import/import_audit.json"
        audit.parent.mkdir(parents=True)
        meshes = [{"role": r, "path": f"/Game/Fake/{r}.{r}"} for r in
                  ("body", "eyes", "teeth", "tongue", "tearline", "eye_occlusion", "eyelashes")]
        audit.write_text(json.dumps({"meshes": meshes}), encoding="utf-8")
        delivery = self.workspace / "00_engine/outputs/character_refresh_20261018_v1/user_edited_night_import_20261020_v1/delivery.json"
        delivery.parent.mkdir(parents=True)
        cases = [{"character_id": f"FAKE_{i:03d}", "sex": "female" if i < 20 else "male",
                  "skeleton": "/Game/Fake/Skeleton.Skeleton", "meshes": meshes,
                  "audit": "D:/UE/Lance_Work/00_engine/outputs/fake_import/import_audit.json"} for i in range(40)]
        delivery.write_text(json.dumps({"status": "imports_completed", "completed_count": 40,
                            "ue_root": "/Game/Fake", "cases": cases}), encoding="utf-8")
        before = delivery.read_bytes()
        night = self.adapter.load("night_character_review_v1")
        revision = self.adapter.load("ue_pair_revision_runtime_20261019_v1")
        result = night.configuration(revision)
        self.assertEqual(len(result["members"]), 40)
        self.assertEqual(revision.PROJECT, self.project)
        self.assertEqual(result["pins"][0]["path"], str(delivery))
        self.assertEqual(delivery.read_bytes(), before)

    def test_reference_worker_dynamic_shared_renderer_keeps_isolated_roots(self):
        shutil.copyfile(SOURCE.with_name("ue_dataset_reference_v11.py"), self.scripts / "ue_dataset_reference_v11.py")
        (self.scripts / "ue_dataset_render_v11.py").write_text(
            "from pathlib import Path\nfrom types import SimpleNamespace\nVERSION=2\n"
            "PROJECT_CONTENT=Path('D:/UE/projects/datatry_02/Content')\n"
            "def renderer(u,run,job,pool_mb):\n"
            " return SimpleNamespace(signature=signature(job),content=PROJECT_CONTENT)\n", encoding="utf-8")
        worker = self.adapter.load_reference_renderer()
        self.assertEqual(worker.S, self.scripts)
        self.assertEqual(worker.WORKSPACE, self.workspace)
        job = {"job_id": "ref_motion_fake", "reference_kind": "motion"}
        expected = hashlib.sha256(json.dumps({"reference_version": worker.VERSION, "main_policy_version": 2,
                                             "job": job}, sort_keys=True).encode()).hexdigest()
        self.assertEqual(worker.signature(job), expected)
        result = worker.renderer(None, self.workspace / "run", job)
        self.assertEqual(result.signature, expected)
        self.assertEqual(result.content, self.project.parent / "Content")
        self.assertEqual(result.LIVE_ATTRIBUTE, "_dm_dataset_reference_v11")
        carrier = self.workspace / "00_engine/outputs/ref/carrier_jobs.json"
        carrier.parent.mkdir(parents=True)
        carrier.write_text(json.dumps({"jobs": [{"job_id": "train_node_000000", "map": "/Game/Fake.Fake"}]}), encoding="utf-8")
        original = carrier.read_bytes()
        resolved, path = worker.source(carrier.parent, {"source_job_id": "train_node_000000",
            "source_jobs_path": "D:/UE/Lance_Work/00_engine/outputs/ref/carrier_jobs.json"})
        self.assertEqual(path, carrier)
        self.assertEqual(resolved["map"], "/Game/Fake.Fake")
        self.assertEqual(carrier.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
