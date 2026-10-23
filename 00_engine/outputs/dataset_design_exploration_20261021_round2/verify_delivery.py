"""Validate this research package's syntax, local links and pinned core evidence."""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote
import ast
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
GENERATED = {"DELIVERY_MANIFEST.json", "delivery_verification.json"}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    files = [p for p in HERE.rglob("*") if p.is_file()
             and "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name not in GENERATED]
    counts, failures = Counter(), []
    for p in files:
        try:
            if p.suffix == ".json":
                json.loads(p.read_text(encoding="utf-8-sig"))
                counts["json_syntax"] += 1
            elif p.suffix == ".jsonl":
                for line in p.read_text(encoding="utf-8-sig").splitlines():
                    if line.strip():
                        json.loads(line)
                        counts["jsonl_records_parsed"] += 1
                counts["jsonl_files"] += 1
            elif p.suffix == ".py":
                ast.parse(p.read_text(encoding="utf-8-sig"), filename=str(p))
                counts["python_syntax"] += 1
            elif p.suffix == ".md":
                for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", p.read_text(encoding="utf-8-sig")):
                    target = target.strip("<>").split("#", 1)[0]
                    if not target or target.startswith(("http:", "https:", "mailto:", "codex:")):
                        continue
                    if target.startswith("/D:/") or target.startswith("/C:/"):
                        target = target[1:]
                    target_path = Path(unquote(target))
                    if not target_path.is_absolute():
                        target_path = p.parent / target_path
                    if not target_path.exists():
                        failures.append({"file": str(p.relative_to(HERE)), "missing_local_link": target})
                    counts["local_links_checked"] += 1
        except Exception as ex:
            failures.append({"file": str(p.relative_to(HERE)), "error": str(ex)})
    core = json.loads((HERE/"core_verification.json").read_text(encoding="utf-8"))
    for split in ("train", "test"):
        for source in core["checks"][split]["sources"]:
            if digest(Path(source["path"])) != source["sha256"]:
                failures.append({"core_source_changed": source["path"]})
            counts["core_evidence_hashes"] += 1
    result = {
        "status": "passed" if not failures else "failed",
        "checks": dict(counts), "failures": failures,
        "independent_structure_evidence": "core_verification.json",
        "agent_scoped_evidence": [
            "graph/sampling_study_verification.json", "graph/bridge_verification.json",
            "language/plan_audit.json", "experimental_design/SELF_CHECK.json", "wardrobe_domains/SELF_CHECK.json"
        ],
        "review_resolutions": [
            "First-round five-axis probes are not claimed to be members of the second-round seven-axis graph.",
            "800 directed commutation pairs are explicitly distinguished from 200 unique four-state squares.",
            "Camera action-pair medians use conventional even-sample median.",
            "Registered identity value-pair coverage is distinguished from actual session usage.",
            "No generated media, UE acceptance, model result or final dataset freeze is claimed."
        ],
        "not_run": ["full repository audit", "UE/media validation", "model training/evaluation"],
        "scope": "Research package syntax/local navigation and pinned stable core; not proof every experimental conclusion or source web page is valid."
    }
    (HERE/"delivery_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    files.append(HERE/"delivery_verification.json")
    manifest = {
        "status": "offline_research_delivery",
        "reading_entry": "MORNING_BRIEF.md", "production_frozen": False,
        "files": [{"path": str(p.relative_to(HERE)).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": digest(p)}
                  for p in sorted(files)],
    }
    (HERE/"DELIVERY_MANIFEST.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "files": len(manifest["files"]), "checks": dict(counts), "failures": failures}, ensure_ascii=False))
    assert not failures


if __name__ == "__main__":
    main()
