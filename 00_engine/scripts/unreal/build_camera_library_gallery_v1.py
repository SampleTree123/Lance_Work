"""Build the camera-library follow-up review without modifying old media.

Technical owner: SCENE_CAMERA_SEQUENCE.md section 8. Experimental, offline only.
Reuses the tested two-panel UI and copies only small review MP4/JPEG derivatives.
"""
from pathlib import Path
import hashlib
import json
import shutil
import build_camera_pilot_gallery_v1 as gallery

S = Path(__file__).resolve().parent
OLD = S.parents[1] / 'outputs/unreal_character_import/camera_motion_pilot_20261009_v1'
RUN = OLD.with_name('camera_library_expansion_20261010_v1')
EXCLUDED = {4, 11, 16, 24, 27}
REVISE = {5, 9, 30, 31}


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    plan = read(RUN / 'expansion_plan_v1.json')
    old = read(OLD / 'camera_pilot_delivery_manifest_v1.json')
    feedback = RUN / 'human_camera_feedback_v1.json'
    if not feedback.is_file():
        raise ValueError('User feedback record is required')
    clips = []
    preserved = []
    for source in old['clips']:
        number = int(source['shot_id'].split('_')[1])
        if number in EXCLUDED:
            continue
        c = dict(source)
        for field in ('video', 'poster'):
            src = OLD / c[field]
            dst = RUN / 'videos' / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and digest(dst) != digest(src):
                raise ValueError('Previous review copy changed: ' + str(dst))
            if not dst.exists():
                shutil.copyfile(src, dst)
            preserved.append({'source': str(src), 'copy': str(dst), 'sha256': digest(src)})
            c[field] = dst.relative_to(RUN).as_posix()
        c['review_status'] = 'pending' if number in REVISE else 'accepted'
        c['review_evidence'] = str(feedback)
        c['review_label'] = '上一版 · 需要调整' if number in REVISE else '你已认可'
        clips.append(c)
    for shot in plan['shots']:
        sid = shot['shot_id']
        framing_names = {'full': '全身', 'upper': '上半身', 'head': '面部近景', 'wide': '环境远景'}
        framing = shot['camera_spec']['framing']
        description = '取景：' + framing_names[framing['start']]
        if framing['end'] != framing['start']:
            description += '逐渐变为' + framing_names[framing['end']]
        description += '。与推荐的旧样片使用同一角色、穿搭和动作。'
        receipt = RUN / 'media_receipts' / (sid + '.json')
        verified = read(receipt) if receipt.exists() else None
        if verified and (verified.get('status') != 'encoded_verified' or
                         verified['video_sha256'] != digest(RUN / verified['video'])):
            raise ValueError('New media receipt does not match: ' + sid)
        clips.append({
            'shot_id': sid, 'shot_type': shot['shot_type'],
            'family': 'static' if shot['camera_spec']['movement']['kind'] == 'fixed' else 'dynamic',
            'camera_label': shot['camera_label'], 'camera_spec': shot['camera_spec'],
            'motion_label': shot['motion_label'], 'sex': shot['sex'],
            'duration_seconds': 10, 'measured_duration_seconds': 10 if verified else None,
            'trajectory_sha256': shot['trajectory_sha256'],
            'video': 'videos/' + sid + '.mp4', 'poster': 'videos/' + sid + '.jpg',
            'render_status': 'rendered' if verified else 'pending',
            'review_status': 'pending', 'review_label': '新增补测 · 等你审查' if verified else '新增补测 · 尚未渲染',
            'note': description,
            'source_shot_id': shot['source_shot_id'],
        })
    rows = gallery.normalize_manifest({'schema': 'camera_pilot_delivery_manifest_v1',
                                       'unified_duration_seconds': 10, 'clips': clips}, RUN)
    for row, clip in zip(rows, clips):
        row['review_label'] = clip['review_label']
    names = ['向前行走', '舒展舞步', '调整站姿', '弯腰伸展', '甩头转身', '边走边思考', '好奇探看']
    configs = []
    for name in names:
        additions = [c for c in clips if c.get('source_shot_id') and c['motion_label'].split('（')[0].strip() == name]
        if not additions:
            continue
        selected = next((c for c in additions if c['camera_spec']['movement']['kind'] in ('dolly_in', 'dolly_out')), additions[0])
        if selected['source_shot_id'] not in {c['shot_id'] for c in clips}:
            raise ValueError('Recommended reference is excluded or absent')
        configs.append({'name': name, 'pair': [selected['source_shot_id'], selected['shot_id']],
                        'hint': '左边是上一轮样片，右边是本轮补测。比较取景、移动幅度，以及人物有没有离开画面。',
                        'label': '同一角色与动作 · 旧样片 ↔ 新补测'})
    template = (S / 'camera_pilot_gallery_v2.html').read_text(encoding='utf-8')
    begin, end = template.index('const configs=['), template.index('const help=')
    template = template[:begin] + 'const configs=' + json.dumps(configs, ensure_ascii=False) + ';\n' + template[end:]
    template = template.replace('相机样片审查', '相机样片审查 · 共用镜头库')
    template = template.replace('看看同一个动作换个镜头后是什么效果，选出你觉得舒服、清楚的拍摄方式。',
                                '保留你认可的镜头，比较新组合与改进后的推近、拉远。')
    template = template.replace("r.duration_label}`:''", "r.duration_label} · ${r.review_label}`:''")
    template = template.replace("+' · '+r.duration_label;", "+' · '+r.duration_label+' · '+r.review_label;")
    template = template.replace("(help[r.shot_type]||r.note||", "(r.note||help[r.shot_type]||")
    template = template.replace('这组最容易看出固定镜头与跟拍的区别。', '先比较推荐组合，再向下选择其他新增镜头。')
    template = template.replace('左边相机停在远处，人物走过整个画面；右边相机跟着人物移动，人物大小比较稳定。',
                                '左边是你认可的前方跟拍；右边是新增的俯视跟拍。还可以在下方选择上半身跟拍。')
    template = template.replace('比较正面全身与环绕。留意举手、转身时是否完整入画，以及绕过去时是否舒服。',
                                '在已认可的正面镜头基础上，比较新增的仰视、背侧和60°环绕。留意举手、转身时是否完整入画。')
    template = template.replace('这一组专门检查短动作放慢到十秒后的节奏。原动作开始、结束时含站姿，表情仍按正常速度播放。',
                                '这组慢放节奏已获得你的认可。本次比较相同动作的全身和新增上半身取景。')
    data = json.dumps(rows, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    output = template.replace('__TITLE__', '共用镜头库 · 补测审查').replace('__DATA__', data).replace('__COUNT__', str(len(rows))).replace('__READY__', str(sum(r['playable'] for r in rows)))
    dest = RUN / 'gallery/index.html'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(output, encoding='utf-8')
    launcher = dest.parent / '打开相机审查.cmd'
    launcher.write_text('@echo off\n"C:\\ProgramData\\anaconda3\\python.exe" "' + str(S/'open_camera_library_gallery_v1.py') + '" %*\nif errorlevel 1 pause\n', encoding='utf-8')
    manifest = {'schema': 'camera_library_review_delivery_v1', 'clips': clips, 'configs': configs,
                'old_media_copies': preserved, 'user_feedback': str(feedback),
                'new_human_acceptance': 'pending', 'excluded_prior_shot_numbers': sorted(EXCLUDED)}
    (RUN / 'review_delivery_manifest_v1.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'index': str(dest), 'clips': len(rows), 'playable': sum(r['playable'] for r in rows)}


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False))
