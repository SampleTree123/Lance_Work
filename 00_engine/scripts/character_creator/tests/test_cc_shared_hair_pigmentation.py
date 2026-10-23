"""Material scope preflight and the CC/UE shared pigmentation contract."""

import importlib.util
import os
from pathlib import Path
import sys
import types
from unittest import mock

import pytest


def load_subject():
    rlpy = types.ModuleType("RLPy")
    for index, channel in enumerate((
        "Diffuse", "Normal", "Roughness", "Specular", "Metallic",
        "AmbientOcclusion", "Opacity", "Bump", "Displacement", "Glow",
    )):
        setattr(rlpy, "EMaterialTextureChannel_" + channel, index)
    rlpy.EObjectModifiedType_Material = 1
    rlpy.RGlobal = types.SimpleNamespace(ObjectModified=lambda *args: None)
    pyside = types.ModuleType("PySide2")
    pyside.QtCore = types.SimpleNamespace()
    pyside.QtGui = types.SimpleNamespace()
    pyside.QtWidgets = types.SimpleNamespace(
        QApplication=types.SimpleNamespace(processEvents=lambda: None)
    )
    spec = importlib.util.spec_from_file_location(
        "cc_shared_hair_pigmentation_subject",
        Path(__file__).resolve().parents[1] / "cc_validate_body_reconstruction.py",
    )
    subject = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"RLPy": rlpy, "PySide2": pyside}), \
            mock.patch.dict(os.environ, {"CC_BODY_RECONSTRUCTOR_IMPORT_ONLY": "1"}):
        spec.loader.exec_module(subject)
    return subject


SUBJECT = load_subject()
COLOR = {
    "root_srgb": "#123456", "end_srgb": "#789ABC",
    "highlight_a_srgb": "#102030", "highlight_b_srgb": "#405060",
}


class Material:
    def __init__(self, shader=None, missing=(), reject_writes=False):
        self.shader = SUBJECT.SMART_HAIR_SHADER if shader is None else shader
        self.parameters = {
            **{name: (0.0, 0.0, 0.0)
               for name in SUBJECT.SMART_HAIR_COLOR_PARAMETERS.values()},
            **{name: (0.0,) for name in SUBJECT.SMART_HAIR_SCALAR_PARAMETERS},
        }
        for name in missing:
            self.parameters.pop(name, None)
        self.writes = []
        self.reject_writes = reject_writes

    def GetMaterialNames(self, mesh):
        return ["Hair"]

    def GetShader(self, mesh, material):
        return self.shader

    def GetShaderParameterNames(self, mesh, material):
        return list(self.parameters)

    def GetShaderParameter(self, mesh, material, parameter):
        return self.parameters[parameter]

    def SetShaderParameter(self, mesh, material, parameter, value):
        self.writes.append((parameter, value))
        if not self.reject_writes:
            self.parameters[parameter] = value


class Owner:
    def __init__(self, name, material):
        self.name = name
        self.material = material

    def GetMeshNames(self):
        return [self.name + "_mesh"]

    def GetID(self):
        return self.name

    def GetName(self):
        return self.name


@pytest.fixture
def rig(monkeypatch):
    owners = []
    monkeypatch.setattr(SUBJECT, "current_hair_material_owners", lambda avatar: owners)
    monkeypatch.setattr(SUBJECT, "avatar_part_type_for_slot", lambda slot: slot)
    monkeypatch.setattr(
        SUBJECT, "avatar_parts_of_type",
        lambda avatar, slot: [owner for owner, domain in owners if domain == slot],
    )
    monkeypatch.setattr(
        SUBJECT, "hair_material_component", lambda avatar, owner: (owner.material, "owner")
    )

    def add(domain, **kwargs):
        material = Material(**kwargs)
        owners.append((Owner(domain + str(len(owners)), material), domain))
        return material

    return add


def test_default_missing_scalp_stops_before_brow_writes(rig):
    brows = rig("eyebrows")
    with pytest.raises(SUBJECT.ReconstructionError, match="scalp_hair"):
        SUBJECT.apply_shared_hair_pigmentation(object(), COLOR, 0)
    assert brows.writes == []


def test_default_missing_brows_stops_before_scalp_writes(rig):
    scalp = rig("scalp_hair")
    with pytest.raises(SUBJECT.ReconstructionError, match="eyebrows"):
        SUBJECT.apply_shared_hair_pigmentation(object(), COLOR, 0)
    assert scalp.writes == []


def test_eyebrows_only_succeeds_with_no_scalp_and_exact_contract(rig):
    brows = rig("eyebrows")
    result = SUBJECT.apply_shared_hair_pigmentation(
        object(), COLOR, 0.25, target_domains=("eyebrows",)
    )
    assert result["required_domains"] == ["eyebrows"]
    assert result["domain_material_counts"] == {"eyebrows": 1}
    for field, parameter in SUBJECT.SMART_HAIR_COLOR_PARAMETERS.items():
        original = tuple(int(COLOR[field][i:i + 2], 16) / 255 for i in (1, 3, 5))
        gray = tuple(v / 255 for v in (196, 199, 201))
        expected = tuple(a + (b - a) * 0.25 for a, b in zip(original, gray))
        assert brows.parameters[parameter] == expected
        assert result["target_colors"][parameter] == list(expected)
    assert brows.parameters["_1st Dye Strength"] == (0.35,)
    assert brows.parameters["_2nd Dye Strength"] == (0.35,)


def test_explicit_brows_scope_ignores_unselected_invalid_hair(rig):
    scalp = rig("scalp_hair", shader="Wrong hair shader")
    beard = rig("facial_hair", missing=("RootColor",))
    brows = rig("eyebrows")
    result = SUBJECT.apply_shared_hair_pigmentation(
        object(), COLOR, 0, target_domains=["eyebrows"]
    )
    assert result["material_count"] == 1
    assert scalp.writes == beard.writes == []
    assert len(brows.writes) == 10


def test_legacy_default_still_colors_three_present_domains(rig):
    materials = [rig(domain) for domain in ("scalp_hair", "eyebrows", "facial_hair")]
    result = SUBJECT.apply_shared_hair_pigmentation(object(), COLOR, 1)
    assert result["required_domains"] == ["eyebrows", "facial_hair", "scalp_hair"]
    assert result["material_count"] == 3
    assert all(material.parameters["RootColor"] == pytest.approx((196 / 255, 199 / 255, 201 / 255))
               for material in materials)


def test_present_beard_without_approved_shader_fails_before_any_write(rig):
    scalp = rig("scalp_hair")
    brows = rig("eyebrows")
    beard = rig("facial_hair", shader="PBR",
                missing=tuple(SUBJECT.SMART_HAIR_COLOR_PARAMETERS.values()))
    with pytest.raises(SUBJECT.ReconstructionError, match="facial_hair"):
        SUBJECT.apply_shared_hair_pigmentation(object(), COLOR, 0)
    assert scalp.writes == brows.writes == beard.writes == []


@pytest.mark.parametrize("bad_kwargs, message", [
    ({"missing": ("TipColor",)}, "lacks color parameters"),
    ({"shader": "Wrong hair shader"}, "Unknown hair-color shader"),
])
def test_later_invalid_material_is_preflighted_before_earlier_writes(rig, bad_kwargs, message):
    scalp = rig("scalp_hair")
    brows = rig("eyebrows", **bad_kwargs)
    with pytest.raises(SUBJECT.ReconstructionError, match=message):
        SUBJECT.apply_shared_hair_pigmentation(object(), COLOR, 0)
    assert scalp.writes == brows.writes == []


@pytest.mark.parametrize("domains", [[], ["unknown"], "eyebrows", 1, [["eyebrows"]]])
def test_invalid_target_domains_are_rejected_before_writes(rig, domains):
    brows = rig("eyebrows")
    with pytest.raises(SUBJECT.ReconstructionError, match="Target hair domains"):
        SUBJECT.apply_shared_hair_pigmentation(
            object(), COLOR, 0, target_domains=domains
        )
    assert brows.writes == []


@pytest.mark.parametrize("fraction", [-0.001, 1.001, float("nan")])
def test_invalid_gray_fraction_does_not_write(rig, fraction):
    brows = rig("eyebrows")
    with pytest.raises(SUBJECT.ReconstructionError, match="gray fraction"):
        SUBJECT.apply_shared_hair_pigmentation(
            object(), COLOR, fraction, target_domains=("eyebrows",)
        )
    assert brows.writes == []


def test_roundtrip_failure_remains_an_error_not_false_success(rig):
    brows = rig("eyebrows", reject_writes=True)
    with pytest.raises(SUBJECT.ReconstructionError, match="did not round-trip"):
        SUBJECT.apply_shared_hair_pigmentation(
            object(), COLOR, 0, target_domains=("eyebrows",)
        )
    assert brows.writes  # SDK errors are explicitly not claimed to be transactional.


def test_explicit_scope_missing_domain_is_not_satisfied_by_scalp(rig):
    scalp = rig("scalp_hair")
    with pytest.raises(SUBJECT.ReconstructionError, match="eyebrows"):
        SUBJECT.apply_shared_hair_pigmentation(
            object(), COLOR, 0, target_domains=("eyebrows",)
        )
    assert scalp.writes == []


@pytest.mark.parametrize("invalid_color", ["123456", "#12345", "#XX3456"])
def test_invalid_color_contract_is_rejected_before_writes(rig, invalid_color):
    brows = rig("eyebrows")
    payload = dict(COLOR, highlight_b_srgb=invalid_color)
    with pytest.raises(SUBJECT.ReconstructionError, match="#RRGGBB"):
        SUBJECT.apply_shared_hair_pigmentation(
            object(), payload, 0, target_domains=("eyebrows",)
        )
    assert brows.writes == []


def test_missing_optional_scalars_preserves_legacy_compatibility(rig):
    brows = rig("eyebrows", missing=tuple(SUBJECT.SMART_HAIR_SCALAR_PARAMETERS))
    result = SUBJECT.apply_shared_hair_pigmentation(
        object(), COLOR, 0, target_domains=("eyebrows",)
    )
    assert len(brows.writes) == 4
    assert result["materials"][0]["scalar_after"] == {}
