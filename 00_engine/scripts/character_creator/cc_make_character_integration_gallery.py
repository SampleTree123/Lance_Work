"""Build a static review gallery from a CC5 integration summary."""

import argparse
import html
import json
import os
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SUMMARY = (
    SCRIPT_DIR / "cc_character_integration_automation_summary_v1.json"
)
AGE_ORDER = {"young": 0, "middle": 1, "older": 2}
SEX_ORDER = {"male": 0, "female": 1}
IMAGE_GROUPS = (
    (
        "Assembly overview",
        (
            ("source_preview", "Source BodyFit"),
            ("reconstructed_preview", "Assembled character"),
        ),
    ),
    (
        "Identity angles",
        (
            ("face_front_preview", "Front"),
            ("face_three_quarter_preview", "Three-quarter"),
            ("face_profile_preview", "Profile"),
            (
                "face_post_pose_neutral_preview",
                "Neutral after pose validation",
            ),
        ),
    ),
    (
        "Hair coverage",
        (
            ("hair_rear_three_quarter_preview", "Rear three-quarter"),
            ("hair_rear_preview", "Rear"),
        ),
    ),
    (
        "Eye closure and gaze",
        (
            ("face_blink_bilateral_preview", "Blink both"),
            ("face_blink_left_preview", "Blink left"),
            ("face_blink_right_preview", "Blink right"),
            ("face_look_left_preview", "Look left"),
            ("face_look_right_preview", "Look right"),
            ("face_look_up_preview", "Look up"),
            ("face_look_down_preview", "Look down"),
            ("face_squint_preview", "Squint"),
            ("face_widen_preview", "Widen"),
        ),
    ),
    (
        "Brow poses",
        (
            ("face_brow_raise_preview", "Raise both"),
            ("face_brow_raise_left_preview", "Raise left"),
            ("face_brow_down_preview", "Brow down"),
        ),
    ),
    (
        "Mouth expressions",
        (
            ("face_smile_preview", "Smile"),
            ("face_jaw_open_preview", "Jaw open"),
            (
                "face_jaw_open_three_quarter_preview",
                "Jaw open three-quarter",
            ),
        ),
    ),
)


def read_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def image_source(image_path, output_path):
    relative = os.path.relpath(
        os.path.realpath(image_path),
        output_path.parent,
    )
    return Path(relative).as_posix()


def case_sort_key(case):
    return (
        SEX_ORDER.get(case.get("sex"), 99),
        case.get("bodyfit_id") or "",
        AGE_ORDER.get(case.get("age_label"), 99),
        case.get("preset_id") or "",
    )


def load_final_results(summary):
    results = {}
    for result_path in summary.get("selected_result_paths") or []:
        path = Path(result_path)
        if not path.is_file():
            raise RuntimeError(
                "Missing selected result: {}".format(path)
            )
        document = read_json(path)
        records = document.get("results")
        if not isinstance(records, list):
            records = [document]
        for record in records:
            preset_id = record.get("preset_id")
            if not isinstance(preset_id, str):
                raise RuntimeError(
                    "Selected result has no preset_id: {}".format(path)
                )
            if preset_id in results:
                raise RuntimeError(
                    "Duplicate selected result: {}".format(preset_id)
                )
            results[preset_id] = record
    return results


def write_text_atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def card_markup(case, output_path, detail_path):
    artifacts = case.get("artifact_paths") or {}
    body_path = artifacts.get("reconstructed_preview")
    face_path = artifacts.get("face_front_preview")
    if not body_path or not os.path.isfile(body_path):
        raise RuntimeError(
            "Missing reconstructed preview for {}".format(
                case.get("preset_id")
            )
        )
    if not face_path or not os.path.isfile(face_path):
        raise RuntimeError(
            "Missing face preview for {}".format(case.get("preset_id"))
        )

    values = {
        "age": case.get("age_label") or "unknown",
        "body": image_source(body_path, output_path),
        "bodyfit": case.get("bodyfit_id") or "unknown",
        "face": image_source(face_path, output_path),
        "face_recipe": case.get("face_recipe_id") or "unknown",
        "hair": case.get("scalp_hair_display_name") or "None",
        "detail": image_source(detail_path, output_path),
        "preset": case.get("preset_id") or "unknown",
        "sex": case.get("sex") or "unknown",
        "skin": case.get("skin_asset_id") or "unknown",
    }
    values = {
        key: html.escape(str(value), quote=True)
        for key, value in values.items()
    }
    return """\
      <article class="role-card" data-sex="{sex}" data-age="{age}">
        <header class="card-header">
          <div>
            <h2>{preset}</h2>
            <p>{bodyfit}</p>
          </div>
          <span class="age-label age-{age}">{age}</span>
        </header>
        <div class="image-pair">
          <figure>
            <a href="{body}" target="_blank" rel="noreferrer">
              <img src="{body}" alt="{preset} full body" loading="lazy">
            </a>
            <figcaption>Full body</figcaption>
          </figure>
          <figure>
            <a href="{face}" target="_blank" rel="noreferrer">
              <img src="{face}" alt="{preset} face front" loading="lazy">
            </a>
            <figcaption>Face front</figcaption>
          </figure>
        </div>
        <dl>
          <div><dt>Sex</dt><dd>{sex}</dd></div>
          <div><dt>Face recipe</dt><dd>{face_recipe}</dd></div>
          <div><dt>Skin</dt><dd>{skin}</dd></div>
          <div><dt>Hair</dt><dd>{hair}</dd></div>
        </dl>
        <a class="detail-link" href="{detail}">Open all 23 images</a>
      </article>""".format(**values)


def evidence_group_markup(title, items, artifacts, output_path):
    figures = []
    for artifact_id, label in items:
        image_path = artifacts.get(artifact_id)
        if not image_path or not os.path.isfile(image_path):
            raise RuntimeError(
                "Missing {} for {}".format(
                    artifact_id,
                    output_path.stem,
                )
            )
        values = {
            "file": html.escape(
                os.path.basename(image_path),
                quote=True,
            ),
            "label": html.escape(label, quote=True),
            "source": html.escape(
                image_source(image_path, output_path),
                quote=True,
            ),
        }
        figures.append(
            """\
          <figure class="evidence-item">
            <a href="{source}" target="_blank" rel="noreferrer">
              <img src="{source}" alt="{label}" loading="lazy">
            </a>
            <figcaption>
              <strong>{label}</strong>
              <span>{file}</span>
            </figcaption>
          </figure>""".format(**values)
        )
    return """\
      <section class="evidence-group">
        <header>
          <h2>{title}</h2>
          <span>{count} images</span>
        </header>
        <div class="evidence-grid">
{figures}
        </div>
      </section>""".format(
        title=html.escape(title),
        count=len(figures),
        figures="\n".join(figures),
    )


def detail_document(
    case,
    result,
    output_path,
    index_path,
    previous_path,
    next_path,
):
    artifacts = result.get("artifacts") or {}
    png_artifacts = {
        key: value
        for key, value in artifacts.items()
        if isinstance(value, str) and value.lower().endswith(".png")
    }
    classified = {
        artifact_id
        for unused_title, items in IMAGE_GROUPS
        for artifact_id, unused_label in items
    }
    groups = list(IMAGE_GROUPS)
    unclassified = sorted(set(png_artifacts) - classified)
    if unclassified:
        groups.append(
            (
                "Other evidence",
                tuple(
                    (artifact_id, artifact_id.replace("_", " ").title())
                    for artifact_id in unclassified
                ),
            )
        )
    group_markup = "\n".join(
        evidence_group_markup(
            title,
            items,
            png_artifacts,
            output_path,
        )
        for title, items in groups
    )
    image_count = sum(len(items) for unused_title, items in groups)
    if image_count != len(png_artifacts):
        raise RuntimeError(
            "Image grouping mismatch for {}".format(case["preset_id"])
        )

    def navigation_link(path, label, disabled_label):
        if path is None:
            return '<span class="nav-disabled">{}</span>'.format(
                html.escape(disabled_label)
            )
        return '<a href="{}">{}</a>'.format(
            html.escape(image_source(path, output_path), quote=True),
            html.escape(label),
        )

    values = {
        "age": html.escape(str(case.get("age_label") or "unknown")),
        "back": html.escape(
            image_source(index_path, output_path),
            quote=True,
        ),
        "bodyfit": html.escape(
            str(case.get("bodyfit_id") or "unknown")
        ),
        "face_recipe": html.escape(
            str(case.get("face_recipe_id") or "unknown")
        ),
        "groups": group_markup,
        "hair": html.escape(
            str(case.get("scalp_hair_display_name") or "None")
        ),
        "image_count": image_count,
        "next": navigation_link(
            next_path,
            "Next role",
            "Next role",
        ),
        "preset": html.escape(str(case.get("preset_id") or "unknown")),
        "previous": navigation_link(
            previous_path,
            "Previous role",
            "Previous role",
        ),
        "sex": html.escape(str(case.get("sex") or "unknown")),
        "skin": html.escape(
            str(case.get("skin_asset_id") or "unknown")
        ),
    }
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{preset} - CC5 Review</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #eef1f4;
      --surface: #ffffff;
      --ink: #17202a;
      --muted: #68737d;
      --line: #cbd2d9;
      --accent: #176b55;
      --accent-hover: #0f5543;
      --image-bg: #1d232b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      letter-spacing: 0;
    }}
    a {{ color: var(--accent); }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.97);
      backdrop-filter: blur(10px);
    }}
    .topbar-inner {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 14px 24px;
    }}
    .back-link {{
      display: inline-block;
      margin-bottom: 9px;
      font-size: 13px;
      font-weight: 650;
      text-decoration: none;
    }}
    .title-row {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 18px;
    }}
    h1 {{
      margin: 0;
      font-size: 23px;
      line-height: 1.2;
    }}
    .role-subtitle {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .role-nav {{
      display: flex;
      gap: 8px;
    }}
    .role-nav a, .nav-disabled {{
      min-width: 96px;
      padding: 7px 10px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: var(--surface);
      font-size: 12px;
      text-align: center;
      text-decoration: none;
    }}
    .role-nav a:hover {{
      border-color: var(--accent);
      color: var(--accent-hover);
    }}
    .nav-disabled {{ color: #a5adb5; }}
    main {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 22px 24px 40px;
    }}
    .role-meta {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 1px;
      overflow: hidden;
      margin-bottom: 22px;
      border: 1px solid var(--line);
      border-radius: 5px;
      background: var(--line);
    }}
    .role-meta div {{
      min-width: 0;
      padding: 11px 12px;
      background: var(--surface);
    }}
    .role-meta dt {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 650;
      text-transform: uppercase;
    }}
    .role-meta dd {{
      overflow-wrap: anywhere;
      margin: 4px 0 0;
      font-size: 12px;
      line-height: 1.35;
    }}
    .evidence-group {{
      margin-bottom: 22px;
      border-top: 3px solid var(--accent);
      background: var(--surface);
    }}
    .evidence-group > header {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-top: 0;
    }}
    .evidence-group h2 {{
      margin: 0;
      font-size: 16px;
    }}
    .evidence-group header span {{
      color: var(--muted);
      font-size: 12px;
    }}
    .evidence-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      padding: 12px;
      border: 1px solid var(--line);
      border-top: 0;
      background: #f7f8fa;
    }}
    .evidence-item {{
      min-width: 0;
      overflow: hidden;
      margin: 0;
      border: 1px solid #bfc7ce;
      border-radius: 5px;
      background: var(--surface);
    }}
    .evidence-item a {{
      display: block;
      aspect-ratio: 1 / 1;
      overflow: hidden;
      background: var(--image-bg);
    }}
    .evidence-item img {{
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
    }}
    .evidence-item figcaption {{
      min-height: 55px;
      padding: 8px 10px;
    }}
    .evidence-item strong {{
      display: block;
      font-size: 12px;
    }}
    .evidence-item span {{
      display: block;
      overflow-wrap: anywhere;
      margin-top: 3px;
      color: var(--muted);
      font-size: 10px;
      line-height: 1.3;
    }}
    @media (max-width: 780px) {{
      .topbar-inner, main {{
        padding-left: 12px;
        padding-right: 12px;
      }}
      .title-row {{
        align-items: flex-start;
        flex-direction: column;
      }}
      .role-nav {{ width: 100%; }}
      .role-nav a, .nav-disabled {{ flex: 1 1 0; }}
      .role-meta {{ grid-template-columns: 1fr 1fr; }}
      .evidence-grid {{
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 8px;
        padding: 8px;
      }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="back-link" href="{back}">All 24 roles</a>
      <div class="title-row">
        <div>
          <h1>{preset}</h1>
          <p class="role-subtitle">{bodyfit} / {age} / {image_count} images</p>
        </div>
        <nav class="role-nav" aria-label="Role navigation">
          {previous}
          {next}
        </nav>
      </div>
    </div>
  </header>
  <main>
    <dl class="role-meta">
      <div><dt>Sex</dt><dd>{sex}</dd></div>
      <div><dt>Age</dt><dd>{age}</dd></div>
      <div><dt>Face recipe</dt><dd>{face_recipe}</dd></div>
      <div><dt>Skin</dt><dd>{skin}</dd></div>
      <div><dt>Hair</dt><dd>{hair}</dd></div>
    </dl>
{groups}
  </main>
</body>
</html>
""".format(**values)


def build_gallery(summary_path, output_path):
    summary = read_json(summary_path)
    cases = sorted(
        summary.get("cases") or [],
        key=case_sort_key,
    )
    if len(cases) != 24:
        raise RuntimeError(
            "Expected 24 integration cases, found {}".format(len(cases))
        )
    if not all(case.get("structural_pass") is True for case in cases):
        raise RuntimeError(
            "Gallery input contains a case without structural_pass=true"
        )

    final_results = load_final_results(summary)
    preset_ids = {case.get("preset_id") for case in cases}
    if set(final_results) != preset_ids:
        raise RuntimeError(
            "Summary cases and selected result files do not match"
        )

    detail_directory = output_path.with_suffix("")
    detail_paths = {
        case["preset_id"]: (
            detail_directory / (case["preset_id"] + ".html")
        )
        for case in cases
    }
    cards = "\n".join(
        card_markup(
            case,
            output_path,
            detail_paths[case["preset_id"]],
        )
        for case in cases
    )
    total_images = 0
    for index, case in enumerate(cases):
        preset_id = case["preset_id"]
        result = final_results[preset_id]
        total_images += sum(
            1
            for value in (result.get("artifacts") or {}).values()
            if isinstance(value, str) and value.lower().endswith(".png")
        )
        page = detail_document(
            case=case,
            result=result,
            output_path=detail_paths[preset_id],
            index_path=output_path,
            previous_path=(
                detail_paths[cases[index - 1]["preset_id"]]
                if index > 0
                else None
            ),
            next_path=(
                detail_paths[cases[index + 1]["preset_id"]]
                if index + 1 < len(cases)
                else None
            ),
        )
        write_text_atomic(detail_paths[preset_id], page)

    document = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CC5 Character Integration Review</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #eef1f4;
      --surface: #ffffff;
      --ink: #17202a;
      --muted: #68737d;
      --line: #cbd2d9;
      --accent: #176b55;
      --accent-ink: #ffffff;
      --young: #2b6cb0;
      --middle: #8a5a00;
      --older: #7b3f5c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      letter-spacing: 0;
    }}
    .page-header {{
      position: sticky;
      top: 0;
      z-index: 10;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(10px);
    }}
    .header-inner {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 18px 24px 14px;
    }}
    .title-row {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 18px;
    }}
    h1 {{
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
      font-weight: 680;
    }}
    .result-count {{
      color: var(--muted);
      font-size: 14px;
      white-space: nowrap;
    }}
    .filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 20px;
      margin-top: 14px;
    }}
    .filter-group {{
      display: flex;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 5px;
      background: var(--surface);
    }}
    .filter-group button {{
      min-height: 34px;
      padding: 6px 13px;
      border: 0;
      border-right: 1px solid var(--line);
      background: transparent;
      color: var(--ink);
      font: inherit;
      font-size: 13px;
      cursor: pointer;
    }}
    .filter-group button:last-child {{ border-right: 0; }}
    .filter-group button[aria-pressed="true"] {{
      background: var(--accent);
      color: var(--accent-ink);
    }}
    main {{
      max-width: 1500px;
      margin: 0 auto;
      padding: 24px;
    }}
    .gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 430px), 1fr));
      gap: 18px;
    }}
    .role-card {{
      min-width: 0;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      box-shadow: 0 2px 8px rgba(23, 32, 42, 0.08);
    }}
    .role-card[hidden] {{ display: none; }}
    .card-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 64px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
    }}
    .card-header h2 {{
      margin: 0;
      font-size: 16px;
      line-height: 1.25;
    }}
    .card-header p {{
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .age-label {{
      flex: 0 0 auto;
      padding: 4px 7px;
      border-left: 3px solid currentColor;
      background: #f4f6f8;
      font-size: 12px;
      font-weight: 650;
      text-transform: uppercase;
    }}
    .age-young {{ color: var(--young); }}
    .age-middle {{ color: var(--middle); }}
    .age-older {{ color: var(--older); }}
    .image-pair {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1px;
      background: var(--line);
    }}
    figure {{
      min-width: 0;
      margin: 0;
      background: #1d232b;
    }}
    figure a {{
      display: block;
      aspect-ratio: 1 / 1;
      overflow: hidden;
    }}
    figure img {{
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
    }}
    figcaption {{
      min-height: 30px;
      padding: 7px 10px;
      background: #242b34;
      color: #f0f3f5;
      font-size: 12px;
    }}
    dl {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      margin: 0;
      padding: 12px 14px 14px;
      gap: 9px 14px;
    }}
    dl div {{ min-width: 0; }}
    dt {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 650;
      text-transform: uppercase;
    }}
    dd {{
      overflow-wrap: anywhere;
      margin: 3px 0 0;
      font-size: 12px;
      line-height: 1.35;
    }}
    .detail-link {{
      display: block;
      margin: 0 14px 14px;
      padding: 9px 12px;
      border-radius: 4px;
      background: var(--accent);
      color: var(--accent-ink);
      font-size: 13px;
      font-weight: 650;
      text-align: center;
      text-decoration: none;
    }}
    .detail-link:hover {{ background: #0f5543; }}
    .empty {{
      padding: 64px 16px;
      color: var(--muted);
      text-align: center;
    }}
    @media (max-width: 620px) {{
      .header-inner, main {{ padding-left: 12px; padding-right: 12px; }}
      .title-row {{ align-items: flex-start; flex-direction: column; gap: 5px; }}
      .filters {{ gap: 9px; }}
      .filter-group {{ width: 100%; }}
      .filter-group button {{ flex: 1 1 auto; padding-inline: 8px; }}
      .image-pair {{ grid-template-columns: 1fr; }}
      dl {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header class="page-header">
    <div class="header-inner">
      <div class="title-row">
        <h1>CC5 Character Integration Review</h1>
        <span class="result-count" id="result-count">24 roles / 552 images</span>
      </div>
      <div class="filters">
        <div class="filter-group" aria-label="Sex filter">
          <button type="button" data-filter="sex" data-value="all" aria-pressed="true">All</button>
          <button type="button" data-filter="sex" data-value="male" aria-pressed="false">Male</button>
          <button type="button" data-filter="sex" data-value="female" aria-pressed="false">Female</button>
        </div>
        <div class="filter-group" aria-label="Age filter">
          <button type="button" data-filter="age" data-value="all" aria-pressed="true">All ages</button>
          <button type="button" data-filter="age" data-value="young" aria-pressed="false">Young</button>
          <button type="button" data-filter="age" data-value="middle" aria-pressed="false">Middle</button>
          <button type="button" data-filter="age" data-value="older" aria-pressed="false">Older</button>
        </div>
      </div>
    </div>
  </header>
  <main>
    <section class="gallery" id="gallery">
{cards}
    </section>
    <p class="empty" id="empty" hidden>No roles match the selected filters.</p>
  </main>
  <script>
    const active = {{ sex: "all", age: "all" }};
    const cards = [...document.querySelectorAll(".role-card")];
    const count = document.getElementById("result-count");
    const empty = document.getElementById("empty");
    const imagesPerRole = 23;

    function applyFilters() {{
      let visible = 0;
      for (const card of cards) {{
        const show =
          (active.sex === "all" || card.dataset.sex === active.sex) &&
          (active.age === "all" || card.dataset.age === active.age);
        card.hidden = !show;
        if (show) visible += 1;
      }}
      count.textContent =
        `${{visible}} of ${{cards.length}} roles / ` +
        `${{visible * imagesPerRole}} images`;
      empty.hidden = visible !== 0;
    }}

    for (const button of document.querySelectorAll("[data-filter]")) {{
      button.addEventListener("click", () => {{
        const filter = button.dataset.filter;
        active[filter] = button.dataset.value;
        for (const peer of document.querySelectorAll(
          `[data-filter="${{filter}}"]`
        )) {{
          peer.setAttribute(
            "aria-pressed",
            String(peer === button)
          );
        }}
        applyFilters();
      }});
    }}
  </script>
</body>
</html>
""".format(cards=cards)

    write_text_atomic(output_path, document)
    return len(cases), total_images


def main():
    parser = argparse.ArgumentParser(
        description="Build a static CC5 character review gallery."
    )
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    summary_path = Path(args.summary).resolve()
    output_path = Path(args.output).resolve()
    count, image_count = build_gallery(summary_path, output_path)
    print(
        "Wrote {} roles and {} images to {}".format(
            count,
            image_count,
            output_path,
        )
    )


if __name__ == "__main__":
    main()
