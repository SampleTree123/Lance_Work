"""Offline, within-group CFD morphometric selection aid; no CC/UE mutations.

Uses the supplied CFD objective measurements, not a face-recognition embedding.
Dataset labels are read from filenames and verified against self-report metadata.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import random
import re
import sys
import warnings

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'CFD Version 3.0'
DEFAULT_RUN = ROOT / '00_engine/outputs/character_creator_analysis/cfd_face_diversity_20261007_v1'
GROUPS = ('AF', 'AM', 'BF', 'BM', 'LF', 'LM', 'WF', 'WM')
FEATURES = (
    ('eye_aspect', '眼裂高宽比', 'EyeHeightAvg', 'EyeWidthAvg', .125),
    ('eye_width', '眼宽／颧部脸宽', 'EyeWidthAvg', 'FaceWidthCheeks', .125),
    ('nose_width', '鼻宽／颧部脸宽', 'NoseWidth', 'FaceWidthCheeks', .125),
    ('nose_length', '鼻长／颧部脸宽', 'NoseLength', 'FaceWidthCheeks', .125),
    ('lip_thickness', '唇厚／颧部脸宽', 'LipThickness', 'FaceWidthCheeks', .20),
    ('midface_length', '瞳孔至上唇／颧部脸宽', 'PupilLipAvg', 'FaceWidthCheeks', .15),
    ('chin_length', '下唇至下巴／颧部脸宽', 'BottomLipChin', 'FaceWidthCheeks', .05),
    ('lower_face_width', '嘴部高度脸宽／颧部脸宽', 'FaceWidthMouth', 'FaceWidthCheeks', .05),
    ('cheek_to_chin', '脸颊至下巴／颧部脸宽', 'CheeksAvg', 'FaceWidthCheeks', .05),
)
WEIGHTS = np.array([f[4] for f in FEATURES], dtype=float)
REQUIRED = sorted({v for f in FEATURES for v in f[2:4]})
LIMITATIONS = [
    '这是官方二维测量比例的组内形态距离，不是完整容貌相似度、身份识别或相似百分比。',
    '不使用肤色、头发、额头/发际线、主观评分或族群典型性；族群和性别只沿用数据标签。',
    '缺少眼间距、嘴宽、眼角倾斜、鼻尖/唇形、侧脸深度等信息，不能以9个比例覆盖所有面部差异。',
    '每组独立标准化，距离只适合组内比较，不能据此比较男性和女性哪个更多样。',
    '权重与±3裁剪为项目启发式设置，未验证为人类感知或Headshot保留差异的最优度量。',
    '照片差异不保证Headshot及固定头皮修正后同等保留；不据此修改既有40角色。',
    '贪心选样偏向特征分散，可能选到形态极端者；它不是人口代表性抽样或全局最优解。',
]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def ratios(measurements):
    values = []
    for _, _, numerator, denominator, _ in FEATURES:
        a, b = float(measurements[numerator]), float(measurements[denominator])
        if not np.isfinite(a) or not np.isfinite(b) or a <= 0 or b <= 0:
            raise ValueError('Non-positive/non-finite measurement: ' + numerator + '/' + denominator)
        values.append(a / b)
    return np.array(values)


def robust_standardize(matrix):
    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2 or not np.isfinite(x).all() or len(x) < 2:
        raise ValueError('A finite matrix with at least two rows is required')
    center = np.median(x, axis=0)
    scale = 1.4826 * np.median(np.abs(x - center), axis=0)
    std = np.std(x, axis=0)
    fallback = scale <= 1e-12
    scale = np.where(fallback, std, scale)
    constant = scale <= 1e-12
    scale = np.where(constant, 1., scale)
    z = (x - center) / scale
    z[:, constant] = 0.
    return np.clip(z, -3., 3.), {
        'center': center.tolist(), 'scale': scale.tolist(), 'std_fallback': fallback.tolist(),
        'constant': constant.tolist(), 'clipped_cells_per_row': (np.abs(z) > 3.).sum(axis=1).tolist(),
        'method': 'median / (1.4826 * MAD), std fallback, constant=0; clip [-3,3]',
    }


def distance_matrix(z):
    x = np.asarray(z, dtype=float)
    if x.ndim != 2 or x.shape[1] != len(FEATURES) or not np.isfinite(x).all():
        raise ValueError('Expected finite nine-column matrix')
    delta = x[:, None, :] - x[None, :, :]
    return np.sqrt(np.sum(delta * delta * WEIGHTS, axis=2))


def neighbors(ids, distances, index, count=5, farthest=False):
    candidates = [i for i in range(len(ids)) if i != index]
    candidates.sort(key=lambda i: ((-1 if farthest else 1) * float(distances[index, i]), ids[i]))
    return [{'subject_id': ids[i], 'distance': float(distances[index, i])} for i in candidates[:count]]


def select_diverse(ids, distances, k, seed, excluded=()):
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate subject IDs')
    excluded = set(excluded)
    pool = sorted((i for i, identifier in enumerate(ids) if identifier not in excluded), key=lambda i: ids[i])
    if not 1 <= k <= len(pool):
        raise ValueError(f'k={k} exceeds eligible pool {len(pool)} or is below 1')
    chosen = [random.Random(seed).choice(pool)]
    while len(chosen) < k:
        candidates = [i for i in pool if i not in chosen]
        chosen.append(min(candidates, key=lambda i: (-min(float(distances[i, j]) for j in chosen), ids[i])))
    return [ids[i] for i in chosen]


def selection_stats(ids, distances, selected):
    indices = [ids.index(identifier) for identifier in selected]
    values = [float(distances[a, b]) for n, a in enumerate(indices) for b in indices[n + 1:]]
    return {'min_pair_distance': min(values) if values else None,
            'mean_pair_distance': float(np.mean(values)) if values else None}


def workbook_records(path):
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = workbook['CFD U.S. Norming Data']
        rows = list(sheet.values)
        headers = list(rows[7])
        indices = {name: headers.index(name) for name in ['Model', 'EthnicitySelf', 'GenderSelf'] + REQUIRED}
        result = {}
        for row in rows[9:]:
            identifier = row[indices['Model']]
            if not identifier:
                continue
            if identifier in result:
                raise ValueError('Duplicate workbook Model ' + identifier)
            result[identifier] = {name: row[index] for name, index in indices.items()}
        workbook.close()
    return result


def inventory(data_root, metadata):
    records = []
    seen, hashes = set(), set()
    for sex, suffix in [('female', 'F'), ('male', 'M')]:
        source = data_root / 'Images/CFD-Combined' / sex / 'cfd'
        paths = sorted(p for p in source.rglob('*') if p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
        if not paths:
            raise ValueError('Empty source directory ' + str(source))
        for path in paths:
            match = re.fullmatch(r'CFD-([ABLW][FM])-(\d+)-(\d+)-N\.(jpg|jpeg|png)', path.name, re.I)
            if not match or match[1][-1] != suffix:
                raise ValueError('Unexpected filename / sex folder: ' + str(path))
            group = match[1].upper()
            identifier = group + '-' + match[2]
            m = metadata[identifier]
            if m['EthnicitySelf'] != group[0] or m['GenderSelf'] != group[1]:
                raise ValueError('Filename versus metadata label mismatch ' + identifier)
            digest = sha(path)
            if identifier in seen or digest in hashes:
                raise ValueError('Duplicate subject or photo bytes ' + identifier)
            seen.add(identifier)
            hashes.add(digest)
            with Image.open(path) as image:
                size = image.size
                image.verify()
            raw = {name: float(m[name]) for name in REQUIRED}
            feature = ratios(raw)
            records.append({'subject_id': identifier, 'group': group, 'sex': sex, 'photo_path': str(path.resolve()),
                            'photo_sha256': digest, 'image_size': list(size), 'measurements': raw,
                            'ratios': dict(zip([f[0] for f in FEATURES], feature.tolist()))})
    if seen != set(metadata):
        raise ValueError('Main-image inventory and workbook do not match: ' + str(sorted(set(metadata) ^ seen)))
    return sorted(records, key=lambda r: r['subject_id'])


def thumbnail(record, run, detector):
    import cv2
    with Image.open(record['photo_path']) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        small = image.copy()
        small.thumbnail((720, 500))
        boxes = detector.detectMultiScale(cv2.cvtColor(np.asarray(small), cv2.COLOR_RGB2GRAY),
                                         scaleFactor=1.1, minNeighbors=5, minSize=(70, 70))
        if len(boxes):
            x, y, w, h = max(boxes, key=lambda b: int(b[2]) * int(b[3]))
            scale = image.width / small.width
            cx, cy = (x + w / 2) * scale, (y + h / 2) * scale
            half = max(w, h) * scale * .66
            box = (max(0, int(cx - half)), max(0, int(cy - half)),
                   min(image.width, int(cx + half)), min(image.height, int(cy + half)))
            crop_method = 'opencv_haar_largest_face_square_margin_for_preview_only'
        else:
            side = min(image.size)
            box = ((image.width - side) // 2, 0, (image.width + side) // 2, side)
            crop_method = 'central_square_fallback_preview_requires_review'
        preview = image.crop(box)
        preview.thumbnail((240, 240))
        target = run / 'thumbnails' / (record['subject_id'] + '.jpg')
        target.parent.mkdir(parents=True, exist_ok=True)
        preview.save(target, quality=88)
    return {'path': target.relative_to(run).as_posix(), 'crop_box': list(box), 'method': crop_method,
            'affects_distance': False, 'source_face_detections': len(boxes)}


def selection_document(analysis, groups, k, seed, excluded):
    result = {'schema_version': 1, 'status': 'candidate_only_not_character_creation_request',
              'analysis_input_fingerprint': analysis['input_fingerprint'], 'k_per_group': k, 'seed': seed,
              'algorithm': 'sorted IDs; seeded random first; greedy maximize minimum distance; ties by ID',
              'excluded_subjects': sorted(excluded), 'groups': {}, 'limitations': LIMITATIONS}
    for group in groups:
        info = analysis['groups'][group]
        ids = info['subject_ids']
        matrix = np.array(info['distances'])
        # Independent group seeds remain stable if caller changes group order.
        group_seed = int(hashlib.sha256(f'{seed}:{group}'.encode()).hexdigest()[:16], 16)
        chosen = select_diverse(ids, matrix, k, group_seed, excluded)
        result['groups'][group] = {'subject_ids': chosen, 'derived_seed': group_seed,
                                   **selection_stats(ids, matrix, chosen)}
    by_id = {r['subject_id']: r for r in analysis['records']}
    result['photos'] = [{'subject_id': identifier, 'group': group,
                        'path': by_id[identifier]['photo_path'], 'sha256': by_id[identifier]['photo_sha256']}
                       for group, value in result['groups'].items() for identifier in value['subject_ids']]
    return result


def gallery(analysis, selection, target):
    payload = json.dumps({'records': analysis['records'], 'features': analysis['features'],
                          'groups': {g: {k: v for k, v in r.items() if k != 'distances'}
                                     for g, r in analysis['groups'].items()}, 'selection': selection}, ensure_ascii=False)
    payload = payload.replace('</', '<\\/')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>CFD 组内面部差异选样</title>
<style>body{font:16px system-ui;margin:24px;background:#f4f6f8;color:#202a35}h1{font-size:26px}button,select{padding:9px;margin:4px} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}.card{background:white;padding:10px;border-radius:8px;border:1px solid #ddd}.card img{width:100%;max-width:240px;aspect-ratio:1;object-fit:contain} .tag{color:#42688a;font-size:13px}.warn{background:#fff1cc;padding:12px}#detail{background:white;padding:16px;margin:14px 0}.pairs{display:flex;gap:12px;overflow:auto}.pairs .card{min-width:160px;max-width:190px}table{border-collapse:collapse}td,th{padding:5px 12px;border-bottom:1px solid #ddd}</style>
<h1>CFD 组内面部差异选样</h1><p>597 张主库中性照片 · 官方测量数据 · 全部在本地显示</p>
<div class="warn">距离越小，9项面部比例越接近。仅在同组内比较，不是身份识别或相似百分比，也不能保证生成后仍有同等差异。缩略图只用于观察，不参与距离计算。建议名单不会自动创建人物。</div>
<p><label>分组 <select id="group"></select></label><button id="suggested">看每组5人建议</button><button id="all">看本组全部</button><span id="status"></span></p>
<div id="detail">点击人物查看最接近／最不同的候选及具体比例。</div><div id="grid" class="grid"></div>
<script>const DATA=__DATA__;const byId=Object.fromEntries(DATA.records.map(r=>[r.subject_id,r]));let mode='suggested';
const group=document.getElementById('group'), grid=document.getElementById('grid');Object.keys(DATA.groups).forEach(g=>group.add(new Option(g+' · '+DATA.groups[g].subject_ids.length+' 人',g)));
function card(id,distance){const r=byId[id];const el=document.createElement('div');el.className='card';const im=document.createElement('img');im.src=r.preview.path;im.loading='lazy';im.alt=id;el.append(im);const b=document.createElement('button');b.textContent=id;b.onclick=()=>detail(id);el.append(b);const label=document.createElement('div');label.className='tag';label.textContent=(distance===undefined?'':('比例距离 '+distance.toFixed(3)+' · '))+(r.previously_used?'已用于现有40人':'')+(r.clipped_feature_count?' · 裁剪维度 '+r.clipped_feature_count:'');el.append(label);return el;}
function render(){const g=group.value;const ids=mode==='all'?DATA.groups[g].subject_ids:DATA.selection.groups[g].subject_ids;grid.replaceChildren(...ids.map(id=>card(id)));document.getElementById('status').textContent=ids.length+' 人 · 种子 '+DATA.selection.seed;}
function detail(id){const r=byId[id],panel=document.getElementById('detail');panel.replaceChildren();const h=document.createElement('h2');h.textContent=id+' · 组内比较';panel.append(h);for(const [name,rows] of [['最接近的5人',r.nearest],['差异最大的5人',r.farthest]]){const t=document.createElement('h3');t.textContent=name;panel.append(t);const box=document.createElement('div');box.className='pairs';box.append(...rows.map(n=>card(n.subject_id,n.distance)));panel.append(box);} const table=document.createElement('table');const title=document.createElement('caption');title.textContent='该照片的原始比例（非标准化分）';table.append(title);DATA.features.forEach(f=>{const tr=document.createElement('tr');[f.label,r.ratios[f.id].toFixed(4)].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td);});table.append(tr);});panel.append(table);const a=document.createElement('a');a.href='file:///'+r.photo_path.replaceAll('\\\\','/');a.textContent='查看原照片';panel.append(a);}
group.onchange=render;document.getElementById('suggested').onclick=()=>{mode='suggested';render()};document.getElementById('all').onclick=()=>{mode='all';render()};render();</script></html>'''
    target.write_text(page.replace('__DATA__', payload), encoding='utf-8')


def analyze(data_root, run, seed):
    import cv2
    workbook = data_root / 'CFD 3.0 Norming Data and Codebook.xlsx'
    records = inventory(data_root, workbook_records(workbook))
    run.mkdir(parents=True, exist_ok=True)
    prior_path = ROOT / '00_engine/outputs/unreal_character_import/cfd_native_batch40_20261006_v1/sampling_manifest.json'
    prior = read_json(prior_path) if prior_path.exists() else {'characters': []}
    prior_ids = {r['subject_id'].removeprefix('CFD-') for r in prior['characters']}
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    fingerprint = hashlib.sha256(json.dumps({'workbook': sha(workbook),
        'photos': [(r['subject_id'], r['photo_sha256']) for r in records]}, sort_keys=True).encode()).hexdigest()
    result = {'schema_version': 1, 'created_at': datetime.now().astimezone().isoformat(),
              'method_version': 'cfd_official_9ratio_robust_weighted_v1',
              'status': 'offline_morphometric_selection_aid_not_perceptual_validation',
              'script_sha256': sha(__file__), 'input_fingerprint': fingerprint,
              'workbook': {'path': str(workbook), 'sha256': sha(workbook), 'sheet': 'CFD U.S. Norming Data',
                           'headers_row': 8, 'first_data_row': 10},
              'sources': ['https://www.chicagofaces.org/', 'https://doi.org/10.3758/s13428-014-0532-5'],
              'features': [{'id': f[0], 'label': f[1], 'numerator': f[2], 'denominator': f[3], 'weight': f[4]}
                           for f in FEATURES], 'groups': {}, 'records': records, 'limitations': LIMITATIONS}
    for group in GROUPS:
        members = [r for r in records if r['group'] == group]
        ids = [r['subject_id'] for r in members]
        x = np.array([[r['ratios'][f[0]] for f in FEATURES] for r in members])
        z, normalization = robust_standardize(x)
        distances = distance_matrix(z)
        values = distances[np.triu_indices(len(ids), 1)]
        info = {'subject_ids': ids, 'normalization': normalization, 'distances': distances.tolist(),
                'pair_count': len(values), 'pair_distance_quantiles': dict(zip(['p10', 'median', 'p90'],
                    np.quantile(values, [.1, .5, .9]).tolist()))}
        result['groups'][group] = info
        for i, record in enumerate(members):
            record.update({'standardized_clipped': z[i].tolist(),
                           'clipped_feature_count': normalization['clipped_cells_per_row'][i],
                           'nearest': neighbors(ids, distances, i), 'farthest': neighbors(ids, distances, i, farthest=True),
                           'previously_used': record['subject_id'] in prior_ids})
        folder = run / 'groups'
        folder.mkdir(exist_ok=True)
        with (folder / (group + '_distances.csv')).open('w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.writer(stream)
            writer.writerow(['subject_id'] + ids)
            writer.writerows([[identifier] + row.tolist() for identifier, row in zip(ids, distances)])
        print(json.dumps({'group': group, 'subjects': len(ids), 'pairs': len(values)}), flush=True)
    for i, record in enumerate(records, 1):
        record['preview'] = thumbnail(record, run, detector)
        if i % 100 == 0:
            print(json.dumps({'thumbnails_done': i, 'total': len(records)}), flush=True)
    example = selection_document(result, GROUPS, 5, seed, set())
    write_json(run / 'analysis.json', result)
    write_json(run / 'selection_example_k5.json', example)
    with (run / 'photo_features.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        names = ['subject_id', 'group', 'sex', 'photo_path', 'photo_sha256', 'previously_used', 'clipped_feature_count']
        writer = csv.DictWriter(stream, fieldnames=names + [f[0] for f in FEATURES])
        writer.writeheader()
        writer.writerows([{**{k: r[k] for k in names}, **r['ratios']} for r in records])
    gallery(result, example, run / 'index.html')
    check = {'success': True, 'photos': len(records), 'groups': {g: len(v['subject_ids']) for g, v in result['groups'].items()},
             'all_measurements_finite_positive': True, 'all_photos_readable_unique_subject_and_sha': True,
             'all_workbook_labels_match_filenames_and_sex_folders': True,
             'all_pair_matrices_symmetric_zero_diagonal_finite': all(np.allclose(v['distances'], np.array(v['distances']).T)
                and np.allclose(np.diag(v['distances']), 0) and np.isfinite(v['distances']).all() for v in result['groups'].values()),
             'thumbnail_fallback_ids': [r['subject_id'] for r in records if 'fallback' in r['preview']['method']],
             'multiple_detected_faces_ids': [r['subject_id'] for r in records if r['preview']['source_face_detections'] > 1],
             'prior_batch40_matched': sum(r['previously_used'] for r in records),
             'total_pairs': sum(v['pair_count'] for v in result['groups'].values()),
             'human_perceptual_and_Headshot_validation': 'not_performed_not_required_for_offline_candidate_aid'}
    if not check['all_pair_matrices_symmetric_zero_diagonal_finite']:
        raise RuntimeError('Invalid distance matrix')
    write_json(run / 'analysis_check.json', check)
    print(json.dumps(check, ensure_ascii=False), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    build = commands.add_parser('analyze')
    build.add_argument('--data-root', type=Path, default=DATA)
    build.add_argument('--run', type=Path, default=DEFAULT_RUN)
    build.add_argument('--seed', type=int, default=20261007)
    select = commands.add_parser('select')
    select.add_argument('--analysis', type=Path, default=DEFAULT_RUN / 'analysis.json')
    select.add_argument('--groups', nargs='+', choices=GROUPS, default=list(GROUPS))
    select.add_argument('--k', type=int, required=True)
    select.add_argument('--seed', type=int, required=True)
    select.add_argument('--exclude-used', action='store_true')
    select.add_argument('--exclude', nargs='*', default=[])
    select.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'analyze':
        analyze(args.data_root.resolve(), args.run.resolve(), args.seed)
    else:
        data = read_json(args.analysis)
        excluded = {s.removeprefix('CFD-') for s in args.exclude}
        if args.exclude_used:
            excluded.update(r['subject_id'] for r in data['records'] if r['previously_used'])
        result = selection_document(data, args.groups, args.k, args.seed, excluded)
        result['analysis_source'] = {'path': str(args.analysis.resolve()), 'sha256': sha(args.analysis)}
        write_json(args.output, result)
        print(json.dumps({g: r['subject_ids'] for g, r in result['groups'].items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
