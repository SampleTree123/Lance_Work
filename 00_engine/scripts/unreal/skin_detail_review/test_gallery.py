"""Input boundary tests; no UI or live UE claims."""
from pathlib import Path
import importlib.util
import json
import pytest

spec = importlib.util.spec_from_file_location("skin_gallery", Path(__file__).with_name("build_gallery.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def base():
    return {"schema":"skin_detail_review_v1", "characters":[{"id":"CFD40_AF_005", "sex":"female"}, {"id":"CFD40_LM_002", "sex":"male"}], "clips":[]}


def test_pending_never_publishes_unverified_video(tmp_path):
    d = base()
    d["clips"] = [{"character_id":"CFD40_AF_005", "framing":"head", "variant":"A", "status":"rendering", "video":"fake.mp4"}]
    r = m.build(tmp_path, write(tmp_path/"input.json", d))
    assert r["playable_count"] == 0 and len(r["clips"]) == 12
    assert "fake.mp4" not in (tmp_path/"gallery/index.html").read_text(encoding="utf-8")


def test_verified_receipt_contract_and_hash(tmp_path):
    video = tmp_path/"v.mp4"; video.write_bytes(b"fixture; receipt checks only")
    receipt = write(tmp_path/"r.json", {"status":"encoded_verified", "video_sha256":m.sha(video), "decode":m.CONTRACT})
    d = base();d["clips"]=[{"character_id":"CFD40_AF_005", "framing":"head", "variant":"A", "status":"encoded_verified", "video":"v.mp4", "video_sha256":m.sha(video), "receipt":"r.json", "receipt_sha256":m.sha(receipt)}]
    manifest = write(tmp_path/"input.json", d)
    assert m.build(tmp_path, manifest)["playable_count"] == 1
    video.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):m.build(tmp_path, manifest)


def test_reject_path_escape(tmp_path):
    with pytest.raises(ValueError):m.local_file(tmp_path.resolve(), "../outside.mp4")


def test_reject_duplicate_slot(tmp_path):
    d=base();r={"character_id":"CFD40_AF_005","framing":"upper","variant":"C","status":"pending"};d["clips"]=[r,r]
    with pytest.raises(ValueError,match="duplicate"):m.build(tmp_path,write(tmp_path/"input.json",d))


def test_script_injection_escaped(tmp_path):
    d=base();d["clips"]=[{"character_id":"CFD40_AF_005","framing":"head","variant":"C","status":"pending","reason":"</script><script>alert(1)</script>"}]
    m.build(tmp_path,write(tmp_path/"input.json",d))
    html=(tmp_path/"gallery/index.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)</script>" not in html
