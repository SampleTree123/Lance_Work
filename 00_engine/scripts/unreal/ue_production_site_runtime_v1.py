"""Private production clocks/appearance installer for the frozen point worker.

Importing is offline-safe. install(worker) changes only that private module;
Unreal work happens only when its caller dispatches an authorized operation.
"""
from __future__ import annotations

import bisect
import copy
from pathlib import Path

import scene_site_appearance_v1 as appearance
import production_motion_contract_v1 as motion_contract

REVISION = 2
ENGINE = Path(__file__).resolve().parents[2]
CAMERA_ROOT = ENGINE / 'outputs/production_workflow_20261017_v1/camera_library'
FORMAL_RUN = CAMERA_ROOT.parent
MOTION_BEFORE = FORMAL_RUN / 'production_motion_before_relocation_v1.json'
MOTION_ACTIVE = FORMAL_RUN / 'production_motion_formal_runtime_active_v1.json'
CONTENT = Path('D:/UE/projects/datatry_02/Content')
HAIR_TRIAL_SHADER = CONTENT / 'DataMake/Appearance/Materials/NeutralHairTrialsV1/M_Hair_NeutralBase_v1.uasset'
MODES = ('full', 'production10')
CAMERA_LABELS = dict(zip(
    ('front_full', 'front_three_quarter_full', 'side_full', 'rear_three_quarter_full', 'back_full',
     'front_upper', 'front_three_quarter_upper', 'side_upper', 'rear_three_quarter_upper', 'back_upper',
     'high_full', 'low_full', 'orbit_360', 'orbit_120', 'dolly_in_front', 'dolly_in_side', 'dolly_in_back',
     'dolly_out_front', 'dolly_out_side', 'dolly_out_back', 'front_head'),
    ('正面全身', '前侧全身', '侧面全身', '后侧全身', '背面全身', '正面上半身', '前侧上半身',
     '侧面上半身', '后侧上半身', '背面上半身', '俯拍全身', '仰拍全身', '360度环绕', '120度环绕',
     '正面推进', '侧面推进', '背面推进', '正面拉远', '侧面拉远', '背面拉远', '正面面部')))


def _write_immutable(path, value):
    path = Path(path)
    if path.exists():
        if motion_contract.read(path) != value:
            raise ValueError('正式动作来源记录已存在，不会覆盖：' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as stream:
            import json
            json.dump(value, stream, ensure_ascii=False, indent=2)


def capture_motion_before_relocation():
    """Root calls after all52 bakes, BEFORE any reference/skeleton moves."""
    if MOTION_BEFORE.exists():
        return motion_contract.pin(MOTION_BEFORE)
    data = motion_contract.load_contract(verify_sources=True)
    rows = []
    for entry in data['motions']:
        for sex in ('female', 'male'):
            variant = motion_contract.receipt_variant(entry, sex, check_assets=True)
            if variant is None:
                raise ValueError('搬移前必须先完成52个男女动作资产验收。')
            rows.append({'motion_id': entry['motion_id'], 'sex': sex, 'variant': variant})
    document = {'schema': 'production_motion_before_relocation_v1',
                'contract': motion_contract.pin(motion_contract.CONTRACT), 'variants': rows,
                'validated_variant_count': 52,
                'scope': 'all_original_bake_proofs_and_source_and104_formal_files_hashed_before_relocation'}
    _write_immutable(MOTION_BEFORE, document)
    return motion_contract.pin(MOTION_BEFORE)


def publish_formal_motion_runtime():
    """Bind old all-frame proof to explicit saved-reference and current hashes.

    Does not reuse an old byte-preservation claim for reserialized assets. Each
    changed file must be explained by the relocation receipt that saved it.
    """
    formal = appearance.formal_runtime()
    if not formal:
        raise ValueError('请先发布正式资产目录。')
    loader, domain = formal
    relocation = loader.load()
    before = motion_contract.read(MOTION_BEFORE)
    if before.get('schema') != 'production_motion_before_relocation_v1' or before.get('validated_variant_count') != 52:
        raise ValueError('缺少搬移前52动作版本的完整验收快照。')
    motion_contract.verify_pin(before['contract'])
    data = motion_contract.load_contract()
    by_id = {row['motion_id']: row for row in data['motions']}
    expected = {(mid, sex) for mid in by_id for sex in ('female', 'male')}
    actual = [(row['motion_id'], row['sex']) for row in before['variants']]
    if len(actual) != 52 or set(actual) != expected:
        raise ValueError('搬移动作快照必须恰好包含26动作的男女52版本。')
    overlay = {**relocation.get('relocated_packages', {}), **relocation['path_overlay']}
    saved = {}
    moved = set()
    for record in relocation['move_receipts']:
        motion_contract.verify_pin(record)
        receipt = motion_contract.read(record['path'])
        if receipt.get('success') is not True:
            raise ValueError('正式动作目录不能引用失败的搬移回执。')
        for row in receipt.get('saved_referencers', []):
            saved.setdefault(row['package'], set()).add(row['sha256'])
        moved.update(row['new_package'] for row in receipt.get('completed', []) if row.get('verified') and row.get('new_package'))
    variants = []
    for row in before['variants']:
        entry, sex = by_id[row['motion_id']], row['sex']
        old = row['variant']
        motion_contract.verify_pin(old['receipt'])
        # Validate all numerical and semantic proof fields again, while the
        # BEFORE snapshot proves byte checks already passed before relocation.
        proof = motion_contract.receipt_variant(entry, sex, check_assets=False)
        if proof != old:
            raise ValueError('原动作验收回执与搬移前快照不一致。')
        current = {}
        for kind in ('source', 'production10'):
            original = old[kind]
            asset = overlay.get(original['asset'], original['asset'])
            package = asset.split('.')[0]
            file = CONTENT / (package.removeprefix('/Game/') + '.uasset')
            record = {**motion_contract.pin(file), 'asset': asset}
            changed = record['sha256'] != original['sha256'] or Path(record['path']).resolve() != Path(original['path']).resolve()
            if changed and record['sha256'] not in saved.get(package, set()) and package not in moved:
                raise ValueError('动作文件已改变但没有明确搬移/引用重存回执：' + package)
            current[kind] = {**record, 'relocation_reserialized': changed}
        variants.append({'motion_id': row['motion_id'], 'sex': sex, **current, 'original_bake_receipt': old['receipt'],
                         'shared_skeleton': overlay.get(old['shared_skeleton'], old['shared_skeleton'])})
    document = {'schema': 'production_motion_formal_runtime_v1', 'complete': True, 'variant_count': 52,
                'contract': before['contract'], 'before': motion_contract.pin(MOTION_BEFORE),
                'formal_catalog': domain.formal_runtime_source, 'move_receipts': relocation['move_receipts'],
                'variants': variants,
                'validation_scope': 'pre_relocation_all_frame_body_proof_plus_explicit_reference_resave_receipts_and_current104_hashes',
                'post_relocation_all_frame_revalidation': False, 'visual_acceptance': 'not_inferred'}
    key = appearance.io.digest(document)[:20]
    path = FORMAL_RUN / ('production_motion_formal_runtime_' + key + '.json')
    _write_immutable(path, document)
    appearance.io.write(MOTION_ACTIVE, {'catalog': motion_contract.pin(path)})
    return {'catalog': motion_contract.pin(path), 'variants': 52}


def load_formal_motion_runtime():
    if not MOTION_ACTIVE.is_file():
        return None
    pin = motion_contract.read(MOTION_ACTIVE)['catalog']
    motion_contract.verify_pin(pin)
    document = motion_contract.read(pin['path'])
    if document.get('schema') != 'production_motion_formal_runtime_v1' or document.get('variant_count') != 52 or document.get('complete') is not True:
        raise ValueError('正式动作目录不完整。')
    for key in ('before', 'contract', 'formal_catalog'):
        motion_contract.verify_pin(document[key])
    for record in document['move_receipts']:
        motion_contract.verify_pin(record)
    lookup = {}
    for row in document['variants']:
        if (row['motion_id'], row['sex']) in lookup:
            raise ValueError('正式动作版本编号重复。')
        for key in ('source', 'production10', 'original_bake_receipt'):
            motion_contract.verify_pin(row[key])
        lookup[(row['motion_id'], row['sex'])] = row
    policy = motion_contract.read(document['contract']['path'])
    expected = {(row['motion_id'], sex) for row in policy['motions'] for sex in ('female', 'male')}
    if len(lookup) != 52 or set(lookup) != expected:
        raise ValueError('正式动作目录中的男女版本与26动作合同不一致。')
    return {'document': document, 'source': pin, 'variants': lookup}


def load_mode(mode, *, root=CAMERA_ROOT):
    if mode not in MODES:
        raise ValueError('请选择完整动作预览或正式10秒预览。')
    folder = Path(root) / mode
    geometry = motion_contract.read(folder / 'geometry.json')
    catalog = motion_contract.read(folder / 'catalog.json')
    for record in geometry['sources']:
        motion_contract.verify_pin(record)
    plan = motion_contract.read(folder / 'camera_plan.json')
    if (plan.get('schema') != 'production_camera_library_v1' or plan.get('view') != mode
            or len(geometry.get('shots', [])) != 1092 or len(geometry.get('actions', [])) != 26
            or len(catalog.get('cameras', [])) != 21 or len(plan.get('shots', [])) != 1092):
        raise ValueError('生产镜头目录须包含26动作、21镜头和横竖1092组合。')
    pins = [motion_contract.pin(folder / name) for name in ('geometry.json', 'catalog.json', 'camera_plan.json')]
    shots = {s['shot_id']: s for s in plan['shots']}
    if set(shots) != {s['shot_id'] for s in geometry['shots']}:
        raise ValueError('镜头计划与空间检查目录不一致。')
    frame_index = {}
    for sid, shot in shots.items():
        frames = shot['frames'] + [shot['endpoint_validation_frame']]
        frames.sort(key=lambda r: r['t'])
        frame_index[sid] = ([r['t'] for r in frames], frames)
    return {'mode': mode, 'geometry': geometry, 'catalog': catalog, 'shots': shots,
            'frames': frame_index, 'pins': pins, 'source_pins': geometry['sources']}


def sample_frame(mode_data, shot_id, t):
    times, frames = mode_data['frames'][shot_id]
    j = min(len(times) - 1, bisect.bisect_left(times, t))
    if j and abs(times[j - 1] - t) < abs(times[j] - t):
        j -= 1
    return frames[j]


def install(w):
    watched = [Path(__file__), Path(__file__).with_name('scene_site_appearance_v1.py'),
               Path(__file__).with_name('ue_ground_height_follow_v1.py'),
               Path(__file__).with_name('ue_scene_site_appearance_v1.py'), appearance.FORMAL_POINTER,
               appearance.FORMAL_HELPER, appearance.FORMAL_CORRECTIONS,
               appearance.FORMAL_COLOR_TRIAL_CATALOG, appearance.FORMAL_COLOR_TRIAL_RUNTIME, MOTION_ACTIVE]
    if HAIR_TRIAL_SHADER.is_file():
        watched.append(HAIR_TRIAL_SHADER)
    context = [(str(path), (path.stat().st_size, path.stat().st_mtime_ns) if path.is_file() else None) for path in watched]
    if (getattr(w, '_production_site_installed', None) == REVISION
            and getattr(w, '_production_site_context', None) == context):
        return w
    if getattr(w, '_production_site_installed', None) is not None:
        # Reinstall a revised private adapter without wrapping its old closures.
        import ue_scene_site_appearance_v1 as assembler
        assembler.invalidate_cache(w.u)
        for name, original in getattr(w, '_production_site_originals', {}).items():
            setattr(w, name, original)
    originals = {name: getattr(w, name) for name in
                 ('live', 'state', 'catalog', 'stamp', 'dispatch', 'save_site', 'load_site', 'restore', 'play')}
    originals.update({name: getattr(w, name) for name in ('snap', 'check_action_sample') if hasattr(w, name)})
    motion_data = motion_contract.load_contract()
    by_motion = {r['motion_id']: r for r in motion_data['motions']}
    appearance_data = appearance.catalog()
    formal = appearance.formal_runtime()
    formal_motions = load_formal_motion_runtime() if formal else None
    formal_overlay = getattr(formal[1], 'formal_path_overlay', {}) if formal else {}
    appearance_root = w.RUN / 'appearances'
    base_pins = [motion_contract.pin(__file__), motion_contract.pin(motion_contract.CONTRACT)]
    base_pins += [motion_contract.pin(Path(__file__).with_name(name)) for name in
                  ('scene_site_appearance_v1.py', 'ue_scene_site_appearance_v1.py', 'ue_ground_height_follow_v1.py')]
    base_pins += list(appearance_data['sources'].values())
    if formal:
        base_pins += [motion_contract.pin(appearance.FORMAL_HELPER), motion_contract.pin(appearance.FORMAL_POINTER)]
        base_pins += copy.deepcopy(getattr(formal[1], 'formal_correction_pins', []))
        base_pins += copy.deepcopy(getattr(formal[1], 'formal_palette_compatibility_pins', []))
        if appearance.FORMAL_COLOR_TRIAL_RUNTIME.is_file():
            base_pins.append(motion_contract.pin(appearance.FORMAL_COLOR_TRIAL_RUNTIME))
        if HAIR_TRIAL_SHADER.is_file():
            base_pins.append(motion_contract.pin(HAIR_TRIAL_SHADER))
    if formal_motions:
        base_pins += [formal_motions['source'], motion_contract.pin(MOTION_ACTIVE)]
    active = {'data': None}

    def running(d):
        return (d.get('job') or {}).get('status') == 'running'

    def configure(d, mode):
        if mode not in MODES:
            raise ValueError('未知预览时长模式。')
        if active['data'] is not None and active['data']['mode'] == mode and d.get('_production_revision') == REVISION:
            return
        if running(d):
            raise ValueError('检查进行中，请先停止检查再切换预览时长。')
        # Preflight the replacement before touching the live mode. Retain only
        # the new expanded plan after the transactional switch completes.
        prepared = load_mode(mode)
        if d.get('playback_handle') or (d.get('playback') or {}).get('playing'):
            w.pause_playback()
        active['data'] = prepared
        d.update(local=prepared['geometry'], source_mode=mode,
                 shot_index={r['shot_id']: r for r in prepared['geometry']['shots']},
                 frozen_shots=prepared['shots'], loaded_plan_roots=set(), motions={},
                 runtime_inputs=base_pins + prepared['pins'] + prepared['source_pins'],
                 input_stats={}, input_result=None, report=None, job=None,
                 _production_revision=REVISION)
        d.pop('appearance_readback', None)
        if d.get('preview'):
            d['preview']['source_mode'] = mode
        if 'appearance_selection' not in d:
            d['appearance_selection'] = appearance.default_selection(appearance_data)
            d['appearance_config_id'] = None
        elif formal:
            d['appearance_selection'] = appearance.validate_selection(d['appearance_selection'], appearance_data)
        d['asset_path_overlay'] = copy.deepcopy(formal_overlay)

    def live():
        d = originals['live']()
        configure(d, d.get('source_mode', 'production10'))
        return d

    def stamp():
        d = live()
        result = w.geo.canonical_sha({'base': originals['stamp'](), 'production_revision': REVISION,
            'source_mode': d['source_mode'], 'appearance': appearance.io.digest(d['appearance_selection'])})
        intent = d.get('migrated_exclusion_intent')
        site = d.get('site')
        if (intent and site and intent['restrictions']
                and all(site.get(k) == intent['site_binding'].get(k) for k in ('site_id', 'map', 'position', 'yaw'))):
            excluded = [row for row in site.get('allowed_combinations', []) if row.get('decision') == 'excluded']
            still_restricted = all(row in excluded for row in intent['restrictions'])
            # This signature preserves conservative user intent through clocks,
            # identities and source pins. It never signs a pass or old issues.
            if still_restricted and (site.get('decisions_stamp_kind') == 'exclusion_intent_only'
                                     or site.get('decisions_stamp') != result):
                site['allowed_combinations'] = copy.deepcopy(intent['restrictions'])
                site['issue_reviews'] = {}
                site['decisions_stamp_kind'] = 'exclusion_intent_only'
                site['decisions_stamp'] = result
        return result

    def apply_selection(p):
        d = live()
        mode = p.get('source_mode', d['source_mode'])
        selected = p.get('appearance_selection', d['appearance_selection'])
        changed = mode != d['source_mode'] or selected != d['appearance_selection']
        if changed and running(d):
            raise ValueError('检查进行中，请先停止检查再更换人物或预览时长。')
        if changed:
            selected = appearance.validate_selection(selected, appearance_data)
            w.pause_playback()
        configure(d, mode)
        if selected != d['appearance_selection']:
            d['appearance_selection'] = selected
            d['appearance_config_id'] = None
            d['report'] = None
            d.pop('appearance_readback', None)
        return d

    def state():
        result = originals['state']()
        d = live()
        result.update(appearance_selection=copy.deepcopy(d['appearance_selection']),
                      appearance_config_id=d.get('appearance_config_id'), source_mode=d['source_mode'],
                      appearance_configs=appearance.list_configurations(root=appearance_root))
        if d.get('appearance_readback'):
            result['appearance_readback'] = copy.deepcopy(d['appearance_readback'])
        if d.get('historical_site_review'):
            result['historical_site_review'] = copy.deepcopy(d['historical_site_review'])
            result['pending_exclusion_suggestions'] = copy.deepcopy(d.get('pending_exclusion_suggestions', []))
            result['pending_previous_allowed_combinations'] = copy.deepcopy(d.get('pending_previous_allowed_combinations', []))
        if d.get('migrated_exclusion_intent'):
            result['exclusion_intent_migration'] = copy.deepcopy(d['migrated_exclusion_intent'])
        return result

    def catalog():
        result = originals['catalog']()
        d = live()
        current = active['data']['catalog']
        result['motions'] = [{'id': r['motion_id'], 'label': by_motion[r['motion_id']]['label_zh'],
                              'duration_seconds': r['clock']['duration_seconds']} for r in current['actions']]
        result['cameras'] = [{'id': r.get('camera_id', r.get('id')),
                              'label': CAMERA_LABELS.get(r.get('camera_id', r.get('id')),
                                  r.get('camera_label', r.get('label', r.get('camera_id', r.get('id')))))}
                             for r in current['cameras']]
        result.update(appearance_catalog=appearance_data, source_mode=d['source_mode'],
                      matrix={'motions': 26, 'cameras': 21, 'aspects': 2, 'combinations': 1092})
        return result

    def frozen_shot(shot_id):
        live()
        if not w.input_status()['valid']:
            raise ValueError('人物、动作或镜头输入已改变，请重新加载当前目录。')
        try:
            return active['data']['shots'][shot_id]
        except KeyError as exc:
            raise ValueError('当前预览时长目录中不存在所选镜头。') from exc

    def resolve_motion(d, motion_id, sex):
        key = (motion_id, sex, d['source_mode'])
        if key not in d['motions']:
            entry = by_motion[motion_id]
            if formal:
                if formal_motions is None:
                    raise ValueError('资产已搬移，请先发布带搬移证据的正式动作目录，不能继续使用旧文件哈希。')
                variant = formal_motions['variants'].get((motion_id, sex))
            else:
                variant = motion_contract.receipt_variant(entry, sex)
            if variant is None:
                raise ValueError('该性别动作尚未完成正式10秒资产验收，请等待准备完成。')
            record = variant['production10' if d['source_mode'] == 'production10' else 'source']
            asset = w.u.load_asset(record['asset'])
            if not isinstance(asset, w.u.AnimSequence):
                raise ValueError('已验收动作资产加载失败：' + record['asset'])
            d['motions'][key] = asset
            # Hash once at first selection; ordinary input polling uses stats.
            d['runtime_inputs'] += [record, variant.get('receipt', variant.get('original_bake_receipt'))]
            d['input_stats'], d['input_result'] = {}, None
        return d['motions'][key]

    def preview(p):
        if p.get('_playback_tick'):
            d = w.require_site()
            shot = d['playback_shot']
        else:
            d = apply_selection(p)
            w.require_site()
            shot, _ = w.select(p)
            w.enable_live_view()
        original = frozen_shot(shot['shot_id'])
        t = max(0., min(float(p.get('time_seconds', 0.)), shot['clock']['duration_seconds']))
        row = sample_frame(active['data'], shot['shot_id'], t)
        t = row['t']
        selected = d['appearance_selection']
        sex = selected['sex']
        u = w.u
        import ue_motion_portrait_scene_pilot_v1 as stage
        import ue_scene_site_appearance_v1 as assembler
        ch = d.get('character')
        if not ch or not u.SystemLibrary.is_valid(ch) or d.get('sex') != sex:
            if ch and u.SystemLibrary.is_valid(ch):
                assembler.invalidate_cache(u, ch)
                w.actors().destroy_actor(ch)
            template_path = d.get('asset_path_overlay', {}).get(stage.SOURCES[sex], stage.SOURCES[sex])
            template = u.load_asset(template_path)
            candidates = [a for a in u.GameplayStatics.get_all_actors_of_class(template, u.Actor)
                          if a.get_actor_label() == 'DM_CCWH_' + sex + '_Character']
            if len(candidates) != 1:
                raise ValueError('未找到既有模块化人物模板：' + sex)
            ch = w.actors().duplicate_actor(candidates[0], w.world(), u.Vector(0, 0, 0))
            ch.set_actor_label(w.PREFIX + 'Character')
            d['character'], d['sex'] = ch, sex
        position = [d['site']['position'][k] for k in ('x', 'y', 'z')]
        yaw = d['site']['yaw']
        ch.set_actor_location(w.vec(position), False, False)
        ch.set_actor_rotation(u.Rotator(pitch=0, yaw=yaw, roll=0), False)
        motion = resolve_motion(d, shot['motion_id'], sex)
        body_t = t
        ground_start_t = 0.
        if d['source_mode'] == 'full':
            mapping = motion_contract.map_output_time(by_motion[shot['motion_id']], t, 'full', sex)
            if len(mapping) != 1:
                raise ValueError('完整动作模式需要单一原始动作时刻。')
            body_t = mapping[0]['source_seconds']
            ground_start_t = motion_contract.map_output_time(by_motion[shot['motion_id']], 0., 'full', sex)[0]['source_seconds']
        actual = assembler.apply_actor(u, ch, selected, body_t, motion,
            body_action_id=shot['motion_id'], data=appearance_data, path_overlay=d.get('asset_path_overlay'))
        d['appearance_readback'] = actual
        import ue_ground_height_follow_v1 as ground_follow
        ground_follow.apply_preview(w, actual, body_t, ground_start_t)
        camera = d.get('camera')
        if not camera or not u.SystemLibrary.is_valid(camera):
            camera = w.actors().spawn_actor_from_class(u.CameraActor, u.Vector(), u.Rotator(), transient=True)
            camera.set_actor_label(w.PREFIX + 'Camera')
            d['camera'] = camera
        loc = w.geo.transform_point(row['position'], position, yaw)
        rotation = list(row['rotation_pitch_yaw_roll']); rotation[1] += yaw
        camera.set_actor_location(w.vec(loc), False, False)
        camera.set_actor_rotation(u.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]), False)
        component = camera.get_component_by_class(u.CameraComponent)
        component.set_field_of_view(row['horizontal_fov_degrees'])
        component.set_editor_property('aspect_ratio', original['aspect_ratio'])
        component.set_editor_property('constrain_aspect_ratio', True)
        from ue_primary_saved_site_review_v1 import apply_camera_exposure
        apply_camera_exposure(component, d['site'].get('exposure_compensation', 0.))
        if not p.get('_playback_tick'):
            u.EditorLevelLibrary.pilot_level_actor(camera)
        d['preview'] = {'action_id': shot['motion_id'], 'camera_id': shot['camera_id'],
                        'aspect': shot['orientation'], 'time_seconds': t, 'source_mode': d['source_mode']}
        if d['ranges'] and not p.get('_playback_tick'):
            w.show_ranges(True)
        return d['preview']

    def play(p):
        apply_selection(p)
        originals['play'](p)
        d = live()
        d['playback_selection'].update(source_mode=d['source_mode'])

    def save_site(p):
        d = w.require_site()
        config_id = p.get('appearance_config_id')
        if config_id is not None:
            config = appearance.load_configuration(config_id, appearance_data, root=appearance_root)
            if config['selection'] != d['appearance_selection']:
                raise ValueError('当前外观与保存配置不一致，请先另存完整外观。')
            d['appearance_config_id'] = config_id
        # Link only; no appearance values are mixed into legacy point position.
        if d.get('appearance_config_id'):
            d['site']['appearance_config_id'] = d['appearance_config_id']
        d['site']['source_mode'] = d['source_mode']
        d['site']['review_runtime'] = 'production_site_runtime_v2'
        old_kind = d['site'].get('decisions_stamp_kind')
        if 'allowed_combinations' in p:
            d['site']['decisions_stamp_kind'] = 'explicit_current_user_choice'
        try:
            result = originals['save_site'](p)
        except Exception:
            intent = d.get('migrated_exclusion_intent')
            if intent and d['site'].get('allowed_combinations') == intent['restrictions']:
                d['site']['decisions_stamp_kind'] = old_kind
            raise
        restrictions = [copy.deepcopy(row) for row in d['site'].get('allowed_combinations', []) if row.get('decision') == 'excluded']
        if restrictions:
            d['migrated_exclusion_intent'] = {'status': 'explicit_saved_restrictions_not_validation_pass',
                'site_binding': {k: copy.deepcopy(d['site'].get(k)) for k in ('site_id', 'map', 'position', 'yaw')},
                'restrictions': restrictions, 'source_file': motion_contract.pin(result),
                'old_allowed_promoted': False, 'old_issues_promoted': False, 'old_report_promoted': False}
        else:
            d.pop('migrated_exclusion_intent', None)
        return result

    def load_site(p):
        # Validate linked appearance before the existing loader mutates live state.
        sid = p['site_id']
        path = (w.RUN / 'sites' / (sid + '.json')).resolve()
        if path.parent != (w.RUN / 'sites').resolve():
            raise ValueError('无效拍摄点编号。')
        record = w.read(path)
        site = record['site']
        linked = appearance.load_configuration(site['appearance_config_id'], appearance_data, root=appearance_root) if site.get('appearance_config_id') else None
        mode = site.get('source_mode', live()['source_mode'])
        if site['map'] != w.current_map():
            raise ValueError('请先打开拍摄点所属场景。')
        configure(live(), mode)
        # Bypass only the former imported-policy wrapper: it re-stamped old
        # 30-action exclusions as current and rejects the four retired motions.
        # The frozen loader itself still creates/restores the temporary point.
        loader = originals['load_site']
        for name, cell in zip(getattr(getattr(loader, '__code__', None), 'co_freevars', ()),
                              getattr(loader, '__closure__', None) or ()):
            if name == 'original_load':
                loader = cell.cell_contents
                break
        loader(p)
        d = live()
        if linked:
            d['appearance_selection'] = linked['selection']
            d['appearance_config_id'] = linked['id']
        else:
            d['appearance_config_id'] = None
        standard = d['site'].get('imported_camera_standard')
        if standard and (standard.get('configuration') != w.geo.pin(w.geo.CAMERA_STANDARD)
                or standard.get('standard_id') != 'nonface_landscape_distance050_fov_compensated_v3'
                or standard.get('distance_factor') != .5 or standard.get('scope') != 'nonface_landscape'
                or standard.get('portrait_and_face_unchanged') is not True):
            raise ValueError('保存点不属于当前已接受的相机标准。')
        combinations = {(s.get('motion_id'), s.get('camera_id'), s.get('orientation')) for s in d['local']['shots']}
        old_rows = copy.deepcopy(site.get('imported_excluded_combinations', []))
        saved_rows = copy.deepcopy(site.get('allowed_combinations', []))
        saved_keys = {tuple(row.get(k) for k in ('action_id', 'camera_id', 'aspect')) for row in saved_rows}
        candidates = [(row, 'imported_excluded_combinations') for row in old_rows
                      if tuple(row.get(k) for k in ('action_id', 'camera_id', 'aspect')) not in saved_keys]
        candidates += [(row, 'saved_allowed_combinations') for row in saved_rows if row.get('decision') == 'excluded']
        carried, origins, seen = [], [], set()
        retired = []
        for row in old_rows:
            if row.get('decision') != 'excluded':
                raise ValueError('旧导入记录只能包含明确排除，不能包含通过决定。')
        for row, origin in candidates:
            key = tuple(row.get(k) for k in ('action_id', 'camera_id', 'aspect'))
            if key in combinations:
                if key not in seen:
                    carried.append(row)
                    origins.append({'combination': {k: row[k] for k in ('action_id', 'camera_id', 'aspect')}, 'origin': origin})
                    seen.add(key)
            elif row.get('action_id') in motion_contract.REMOVED:
                retired.append(row)
            else:
                raise ValueError('旧排除记录包含无法对应的镜头或动作。')
        d['historical_site_review'] = {'site_id': sid, 'source': motion_contract.pin(path),
            'imported_excluded_combinations': old_rows, 'retired_motion_exclusions': retired,
            'allowed_combinations': copy.deepcopy(site.get('allowed_combinations', [])),
            'issue_reviews': copy.deepcopy(site.get('issue_reviews', {})),
            'decisions_stamp': site.get('decisions_stamp'), 'status': 'historical_clock_not_current_acceptance'}
        archive = w.RUN / 'historical_site_reviews' / (sid + '_' + appearance.io.digest(record)[:20] + '.json')
        _write_immutable(archive, {'schema': 'scene_site_historical_review_v1',
                                 'source': motion_contract.pin(path), 'record': record})
        d['historical_site_review']['archive'] = motion_contract.pin(archive)
        d['pending_exclusion_suggestions'] = []
        d['pending_previous_allowed_combinations'] = [row for row in saved_rows if row.get('decision') == 'allowed']
        current_clock = (site.get('review_runtime') == 'production_site_runtime_v2'
                         and record.get('input_fingerprint') == d['local']['input_fingerprint'])
        # Old-clock decisions need explicit review. A save from this runtime
        # may retain its existing stamp, which ordinary freshness checks still
        # validate; no loader manufactures a new pass/decision stamp.
        if not current_clock:
            d['site']['allowed_combinations'] = copy.deepcopy(carried)
            d['site']['issue_reviews'] = {}
            d['site'].pop('decisions_stamp', None)
            if carried:
                d['site']['decisions_stamp_kind'] = 'exclusion_intent_only'
                d['migrated_exclusion_intent'] = {'status': 'active_conservative_restrictions_not_validation_pass',
                    'site_binding': {k: copy.deepcopy(d['site'].get(k)) for k in ('site_id', 'map', 'position', 'yaw')},
                    'restrictions': copy.deepcopy(carried), 'origins': origins,
                    'source_archive': motion_contract.pin(archive), 'retired_count': len(retired),
                    'old_allowed_promoted': False, 'old_issues_promoted': False, 'old_report_promoted': False}
                w.stamp()  # Intent-only decision binding, no geometry report.
            else:
                d.pop('migrated_exclusion_intent', None)
        else:
            if carried:
                d['migrated_exclusion_intent'] = {'status': 'saved_current_restrictions_protected_on_input_change',
                    'site_binding': {k: copy.deepcopy(d['site'].get(k)) for k in ('site_id', 'map', 'position', 'yaw')},
                    'restrictions': copy.deepcopy(carried), 'origins': origins,
                    'source_archive': motion_contract.pin(archive), 'retired_count': len(retired),
                    'old_allowed_promoted': False, 'old_issues_promoted': False, 'old_report_promoted': False}
            else:
                d.pop('migrated_exclusion_intent', None)
        # Old saved reports use another clock and input fingerprint. Preserve the
        # saved file, but expose no old report as current production evidence.
        if not current_clock:
            d['report'] = None

    def restore():
        import ue_scene_site_appearance_v1 as assembler
        assembler.invalidate_cache(w.u)
        originals['restore']()
        d = live()
        d.pop('appearance_readback', None)
        d.pop('migrated_exclusion_intent', None)
        d.pop('historical_site_review', None)
        d.pop('pending_previous_allowed_combinations', None)

    def snap():
        import ue_ground_height_follow_v1 as ground_follow
        site = w.require_site()['site']
        support = ground_follow.support_for_site(site)
        if support is None:
            return originals['snap']()
        # The shooting plane is already at the current point Z: snapping is a
        # successful no-op, with no collision trace or marker/terrain mutation.
        return {'point': [float(site['position'][k]) for k in ('x', 'y')] + [support['plane_z_cm']],
                'normal': [0., 0., 1.], 'distance': 0., 'actor': None,
                'support_policy': ground_follow.FIXED_SUPPORT_VERSION, 'support_plane': support}

    def check_action_sample(job, action, sample):
        import ue_ground_height_follow_v1 as ground_follow
        support = ground_follow.support_for_site(job.get('site'))
        if support is not None:
            # Only floor probes use the analytic plane. Delegate the original
            # bones/body collision logic unchanged; ray/sphere and all camera
            # visibility checks remain the original scene queries.
            job.setdefault('scope', {})['ground_support'] = {
                'support_policy': ground_follow.FIXED_SUPPORT_VERSION, 'support_plane': support,
                'ground_probe_policy': 'analytically_covered_infinite_xy',
                'body_collision_policy': 'unchanged', 'camera_occlusion_policy': 'unchanged'}
            sample = {**sample, 'ground_probes': []}
        return originals['check_action_sample'](job, action, sample)

    def dispatch(p):
        p = {**p, **p.get('payload', {})}
        act = p['action']
        d = live()
        if running(d) and act not in {'status', 'catalog', 'poll_check', 'cancel_check', 'restore', 'playback_status'}:
            raise ValueError('检查进行中，请等待完成或停止检查。')
        if act in {'set_appearance', 'save_appearance', 'load_appearance'}:
            w.pause_playback()
            if act == 'load_appearance':
                saved = appearance.load_configuration(p['config_id'], appearance_data, root=appearance_root)
                apply_selection({'appearance_selection': saved['selection']})
                d['appearance_config_id'] = saved['id']
            else:
                apply_selection(p)
                if act == 'save_appearance':
                    saved = appearance.save_configuration(p['name'], d['appearance_selection'], appearance_data, root=appearance_root)
                    d['appearance_config_id'] = saved['id']
            if d.get('site') and d['site']['map'] == w.current_map() and d.get('preview'):
                preview({**d['preview'], 'appearance_selection': d['appearance_selection']})
            return {'success': True, 'action': act, 'request_id': p.get('request_id'), 'state': state(),
                    'catalog': catalog(), 'message': '人物外观已保存。' if act == 'save_appearance' else '人物外观已更新。'}
        if act in {'preview', 'play', 'overview', 'check_start', 'check_all'}:
            apply_selection(p)
        result = originals['dispatch'](p)
        if act in {'status', 'preview', 'play', 'overview', 'check_start', 'check_all'}:
            result['catalog'] = catalog()
        return result

    w.live, w.state, w.stamp, w.catalog = live, state, stamp, catalog
    w.frozen_shot, w.preview, w.play = frozen_shot, preview, play
    w.save_site, w.load_site, w.restore, w.dispatch = save_site, load_site, restore, dispatch
    if 'snap' in originals:
        w.snap = snap
    if 'check_action_sample' in originals:
        w.check_action_sample = check_action_sample
    w._production_site_installed = REVISION
    w._production_site_context = context
    w._production_site_originals = originals
    return w
