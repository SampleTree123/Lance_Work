"""Regression for review PNGs that contain a scene but render fully transparent."""

from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_hair_sex_fit_gallery_v1 as gallery
import run_hair_sex_fit_review_v1 as controller


def test_zero_alpha_is_rejected_then_repaired_without_changing_rgb(tmp_path, monkeypatch):
    monkeypatch.setattr(controller, "REVIEW_ROOT", tmp_path)
    captures = tmp_path / "captures"
    captures.mkdir()
    path = captures / "sample.png"
    source = Image.new("RGBA", (900, 900), (95, 124, 200, 0))
    source.putpixel((450, 450), (201, 92, 12, 0))
    source.save(path)
    raw_bytes = path.read_bytes()

    assert not gallery.inspect_png(path)["displayable"]
    report = controller.normalize_captures()
    assert report["converted"] == 1
    assert gallery.inspect_png(path)["displayable"]
    assert (tmp_path / "captures_raw_zero_alpha/sample.png").read_bytes() == raw_bytes
    with Image.open(path) as repaired:
        assert repaired.mode == "RGB"
        assert repaired.tobytes() == source.convert("RGB").tobytes()
    repaired_bytes = path.read_bytes()
    assert controller.normalize_captures()["converted"] == 0
    assert path.read_bytes() == repaired_bytes


def test_unreadable_or_black_png_does_not_pass(tmp_path):
    black = tmp_path / "black.png"
    Image.new("RGB", (900, 900)).save(black)
    assert not gallery.inspect_png(black)["displayable"]
    broken = tmp_path / "broken.png"
    broken.write_bytes(black.read_bytes()[:40])
    assert not gallery.inspect_png(broken).get("displayable", False)


def test_untouched_render_target_clear_color_is_rejected(tmp_path):
    captures = tmp_path / "captures"
    captures.mkdir()
    plan = {"cases": [{"review_index": 1, "sex": "female", "hair_id": "HAIR_TEST"}]}
    for view in controller.VIEWS:
        path = captures / gallery.image_name(plan["cases"][0], view)
        Image.new("RGB", (900, 900), (46, 46, 46)).save(path)
        info = gallery.inspect_png(path)
        assert info["uniform_rgb"] and not info["displayable"]
    import pytest
    with pytest.raises(RuntimeError, match="Invalid rendered images"):
        controller.validate_captures(plan, 1, 1, captures)


def test_hidden_scalp_gallery_keeps_baseline_and_links_each_original_view(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(gallery, "ROOT", tmp_path)
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setattr(gallery, "SOURCE_REVIEW", source)
    candidate = tmp_path / "candidate"
    (candidate / "captures").mkdir(parents=True)
    (tmp_path / "captures").mkdir()
    cases = [{"review_index": index, "sex": sex, "hair_id": "HAIR_HB1_09", "display_name": "Test"}
             for index, sex in ((1, "female"), (31, "male"))]
    (candidate / "review_plan.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
    originals = {}
    for case in cases:
        for view in gallery.VIEWS:
            filename = gallery.image_name(case, view)
            pixels = Image.new("RGB", (900, 900), (60, 80, 90))
            pixels.putpixel((450, 450), (190, 20, 80))
            pixels.save(candidate / "captures" / filename)
            baseline = tmp_path / "captures" / filename
            baseline.write_bytes(b"baseline evidence retained")
            originals[baseline] = baseline.read_bytes()
    (tmp_path / "gallery.html").write_text("baseline gallery", encoding="utf-8")

    gallery.build_gallery(candidate, scalp_hidden=True)

    report = json.loads((candidate / "gallery_validation.json").read_text(encoding="utf-8"))
    assert report["complete"] and report["valid_images"] == 12
    assert report["scalp_hidden_candidate"] and report["visual_acceptance"] == "pending_human_review"
    markup = (candidate / "gallery.html").read_text(encoding="utf-8")
    assert markup.count("原版对照</a>") == 12
    assert "../captures/001_female_HAIR_HB1_09_front.png" in markup
    assert (tmp_path / "gallery.html").read_text(encoding="utf-8") == "baseline gallery"
    assert all(path.read_bytes() == data for path, data in originals.items())
