"""Only test causal settings isolation; no fabricated real export success."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location('pbr_ab', Path(__file__).parents[1] / 'cc_probe_refresh_pbr_export_ab_v1.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_native_export_changes_only_requested_bit_and_passes_real_setting_object():
    class Settings:
        option = 11
        def GetOption(self): return self.option
        def SetOption(self, value): self.option = value; return True
        def GetOption2(self): return 21
        def GetOption3(self): return 31
        def GetTextureSize(self): return 0
        def GetTextureFormat(self): return 0
    flag = 16777216
    settings, observed, records = Settings(), [], []
    sdk = SimpleNamespace(**{probe.FLAG: flag}, EExportFbxOptions_InverseNormalY=134217728,
        RFileIO=SimpleNamespace(ExportFbxFile=lambda a, p, s: observed.append(s)))
    api = SimpleNamespace(checked=lambda label, status: status)
    probe.export_call(sdk, api, 'A', records)(object(), 'fixture_A.fbx', settings)
    assert settings.option == 11
    probe.export_call(sdk, api, 'B', records)(object(), 'fixture_B.fbx', settings)
    assert settings.option == 11 | flag and observed == [settings, settings]
    assert records[1]['actual'] == {**records[0]['before'], 'option': 11 | flag}
    assert records[1]['inverse_normal_y_unchanged'] is True
