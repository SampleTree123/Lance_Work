"""Extract human-readable diagnostic cases; no media, no graph mutation."""
from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from verify_trial import Verification, UPPER_CAMERAS, IDENTITY_CAMERAS
import normalize_catalog as nc

HERE = Path(__file__).resolve().parent
CANDIDATE = 'full_squares_uniform_nodes'
V = Verification()
CAT = V.catalog
LABELS = {key: {row['id']: row.get('label', row['id']) for row in CAT[plural]}
          for key, plural in [('action', 'actions'), ('camera', 'cameras'), ('site', 'sites')]}
AXIS_ZH = {'identity': '人物身份', 'hair': '发型', 'hair_color': '发色',
           'wardrobe': '服装', 'action': '动作', 'camera': '镜头', 'site': '场景点'}
COLOR_ZH = {'original': '原色', 'black': '黑色', 'gold': '金色', 'silver_white': '银白色',
            'red': '红色', 'blue': '蓝色', 'pink': '粉色'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def value_text(state, axis):
    if axis == 'hair_color':
        return COLOR_ZH[state[axis]]
    if axis == 'wardrobe':
        family, group = V.groups[state['sex'], state['wardrobe']['family_id'], state['wardrobe']['group_id']]
        return f"{family.get('label', family['family_id'])} / {group.get('label', group['group_id'])}"
    return LABELS.get(axis, {}).get(state[axis], state[axis])


def edge_description(source, target, edge):
    axis = edge['axis']
    if axis == 'wardrobe':
        mode = '整套换装' if edge['mode'] == 'whole_outfit' else f"只换 {edge.get('slot')} 单件"
        shoes = V.wardrobe(target)['shoes']
        suffix = ('赤脚，指令须明确赤脚' if not shoes else '目标鞋：' + ', '.join(shoes))
        changed_piece = ''
        if edge['mode'] == 'single_piece':
            slot = edge['slot']
            before = source['wardrobe']['slot_choices'].get(slot)
            after = target['wardrobe']['slot_choices'].get(slot)
            changed_piece = f'；单件资产 {before} → {after}'
        return f"{mode}：{value_text(source, axis)} → {value_text(target, axis)}{changed_piece}；{suffix}。"
    return f"修改{AXIS_ZH[axis]}：{value_text(source, axis)} → {value_text(target, axis)}。"


def make_graph_case(case_id, title, purpose, split, data, session, selected_steps):
    states = data['states']
    rows = []
    for index in selected_steps:
        edge = session['steps'][index - 1]
        source, target = states[edge['source']], states[edge['target']]
        rows.append({'round': index, 'source_position': edge['source_position'],
                     'edge': edge, 'source_state': source, 'target_state': target,
                     'human_readable': f"第{index}轮从历史位置{edge['source_position']}继续。" + edge_description(source, target, edge)})
    return {'id': case_id, 'title_zh': title, 'purpose_zh': purpose,
            'origin': 'existing_sampled_session', 'candidate': CANDIDATE, 'split': split,
            'session_id': session['id'], 'session': session, 'focus_steps': rows,
            'media_status': 'not_rendered_not_visual_verified', 'counts_as_new_main_budget': False}


def main():
    datasets = {}
    for split in ('train', 'test'):
        root = HERE / CANDIDATE / split
        nodes = read(root / 'nodes.json')
        sessions = [json.loads(line) for line in (root / 'sessions.jsonl').read_text(encoding='utf-8').splitlines() if line]
        datasets[split] = {'states': {r['id']: r['state'] for r in nodes}, 'sessions': sessions}
    cases = []
    missing = []

    def choose(case_id, title, purpose, predicate):
        for split, data in datasets.items():
            for session in data['sessions']:
                indices = predicate(session, data['states'])
                if indices:
                    cases.append(make_graph_case(case_id, title, purpose, split, data, session, indices))
                    return
        missing.append({'id': case_id, 'title_zh': title, 'purpose_zh': purpose})

    def upper_whole_then_full(session, states):
        for i, edge in enumerate(session['steps'][:-1]):
            after = session['steps'][i + 1]
            if (edge['axis'] == 'wardrobe' and edge['mode'] == 'whole_outfit'
                    and states[edge['source']]['camera'] in UPPER_CAMERAS
                    and after['axis'] == 'camera' and after['source'] == edge['target']
                    and states[after['target']]['camera'] not in UPPER_CAMERAS | {'front_head'}):
                return [i + 1, i + 2]
        return None

    choose('upper_whole_then_full', '半身整套换装后改全身镜头',
           '检查半身换整套时，未入镜的下装和鞋也已更新；随后全身镜头必须继承完整目标服装。', upper_whole_then_full)
    choose('single_preserves_shoes', '单件换装保持鞋子',
           '检查只换一个核心槽，实际鞋资产完整保持；不能把换鞋藏入单件编辑。',
           lambda s, states: next(([i + 1] for i, e in enumerate(s['steps'])
                                  if e['axis'] == 'wardrobe' and e['mode'] == 'single_piece'
                                  and V.wardrobe(states[e['source']])['shoes']), None))

    def fork_of_type(kind):
        def match(session, states):
            if session['kind'] != 'fork':
                return None
            t = session['fork_round']
            parent = session['steps'][t - 1]['source_position']
            wanted = ((kind == 'intermediate' and parent > 0)
                      or (kind == 'root' and parent == 0)
                      or (kind == 'terminal' and t == session['length']))
            return [t] if wanted else None
        return match

    for kind, title, purpose in [
        ('intermediate', '从中间历史版本分叉', '检查完整继承选中的中间版本，不合并最新版本或弃支属性。'),
        ('terminal', '最后一轮分叉', '检查末轮直接选旧版本是合法结构，不要求分叉后再编辑。'),
        ('root', '回到初始视频分叉', '检查历史位置0是初始视频，不与第1轮结果混淆。')]:
        choose('fork_' + kind, title, purpose, fork_of_type(kind))

    def return_case(session, states):
        steps, history = session['steps'], session['history']
        for i in range(len(steps) - 1):
            if (steps[i]['axis'] == steps[i + 1]['axis']
                    and steps[i]['source_position'] == i
                    and steps[i + 1]['source_position'] == i + 1
                    and history[i] == history[i + 2]):
                return [i + 1, i + 2]
        return None

    choose('same_axis_return', '同一属性连续修改后恢复原状态',
           '检查合法恢复会复用先前canonical视频节点；这不是文本改写，也不需要强制换另一编辑轴。', return_case)
    choose('mono_axis_session', '整条会话只修改一个属性',
           '检查不强制至少两个编辑轴；不同实际属性值与历史父位置仍形成不同结构。',
           lambda s, states: list(range(1, s['length'] + 1))
           if len({e['axis'] for e in s['steps']}) == 1 else None)
    for camera in sorted(IDENTITY_CAMERAS):
        choose('identity_' + camera, '身份编辑：' + camera,
               '检查同sex换身份只在四个允许镜头内发生，服装、头发、动作、场景和镜头规则继承。',
               lambda s, states, camera=camera: next(([i + 1] for i, e in enumerate(s['steps'])
                                                      if e['axis'] == 'identity' and states[e['source']]['camera'] == camera), None))

    # Missing combinations are constructed only as explicit extra diagnostic
    # states, independent of the main graph/session counts.
    diagnostic = []
    rng = random.Random(20261021)
    for request in missing:
        case_id = request['id']
        if case_id != 'upper_whole_then_full':
            raise RuntimeError('Missing required existing case needs an explicit lawful constructor: ' + case_id)
        source = next(copy.deepcopy(s) for data in datasets.values() for s in data['states'].values()
                      if s['camera'] in UPPER_CAMERAS)
        target = copy.deepcopy(source)
        target['wardrobe'] = nc.sample_whole_change(source['sex'], source['wardrobe'], rng, require_upper_change=True)
        target['wardrobe']['hair_id'] = source['wardrobe'].get('hair_id')
        final = copy.deepcopy(target)
        final['camera'] = next(camera for camera in sorted(V.pools['camera'])
                               if camera not in UPPER_CAMERAS | {'front_head'}
                               and V.legal_scene(dict(final, camera=camera)))
        local_states = {0: source, 1: target, 2: final}
        local_edges = [{'source': 0, 'target': 1, 'axis': 'wardrobe', 'mode': 'whole_outfit'},
                       {'source': 1, 'target': 2, 'axis': 'camera', 'mode': 'attribute'}]
        before_errors = sum(V.errors.values())
        for i, state in local_states.items():
            V.check_node({'id': i, 'state': state}, 'diagnostic')
        for edge in local_edges:
            V.check_edge(edge, local_states, 'diagnostic')
        if sum(V.errors.values()) != before_errors:
            raise RuntimeError('Extra diagnostic failed independent validation: ' + str(V.errors))
        diagnostic.append({**request, 'origin': 'extra_legal_domain_construction',
                           'counts_against_main_budget': False, 'nodes': local_states, 'edges': local_edges,
                           'human_readable': [edge_description(local_states[e['source']], local_states[e['target']], e) for e in local_edges],
                           'independent_integrity_validated': True, 'visual_verified': False})

    payload = {'candidate': CANDIDATE, 'scope': '符号状态／历史源的对抗检查案例；说明文本仅用于审阅，不是冻结训练指令模板。',
               'main_graph_mutated': False, 'rendered': False, 'visual_verified': False,
               'existing_case_count': len(cases), 'extra_diagnostic_count': len(diagnostic),
               'cases': cases, 'extra_diagnostic_file': 'diagnostic_cases.json'}
    (HERE / 'ADVERSARIAL_CASES.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / 'diagnostic_cases.json').write_text(json.dumps({'candidate': CANDIDATE,
        'counts_against_main_budget': False, 'rendered': False, 'visual_verified': False, 'cases': diagnostic},
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 对抗案例审阅', '', f'候选：`{CANDIDATE}`。以下{len(cases)}例来自已经采样的真实结构会话；额外合法构造{len(diagnostic)}例单列在 `diagnostic_cases.json`，不计主视频预算。', '',
             '所有案例均只检查符号状态和继承，未渲染、未视觉验收。中文说明是审阅示意，不冻结训练文本。完整source/target state与父位置见 `ADVERSARIAL_CASES.json`。', '']
    for case in cases:
        lines += ['## ' + case['title_zh'], '', case['purpose_zh'], '',
                  f"来源：`{case['split']}/{case['session_id']}`，{case['session']['length']}轮，历史节点 `{case['session']['history']}`。", '']
        for step in case['focus_steps']:
            lines += ['- ' + step['human_readable']]
            if step['edge']['axis'] == 'wardrobe':
                source_w, target_w = V.wardrobe(step['source_state']), V.wardrobe(step['target_state'])
                lines += [f"- 源鞋 `{list(source_w['shoes'])}`；目标鞋 `{list(target_w['shoes'])}`。目标完整core：`{list(target_w['core'])}`。"]
            if case['id'].startswith('fork_'):
                t = step['round']
                hist = case['session']['history']
                states = datasets[case['split']]['states']
                abandoned, chosen = states[hist[t - 1]], step['source_state']
                differences = [AXIS_ZH[a] for a in AXIS_ZH
                               if (V.wardrobe(abandoned)['assets'] != V.wardrobe(chosen)['assets']
                                   if a == 'wardrobe' else abandoned[a] != chosen[a])]
                lines += [f"- 最新历史位置{t-1}与所选旧版的不同属性：{'、'.join(differences) or '无完整state差异（历史出现位置不同）'}。应从所选旧版继承。"]
        lines += ['']
    if diagnostic:
        lines += ['## 额外合法诊断', '', '以下组合未在采样会话内找到，按当前合法domain单独构造，不算主图节点或主集会话。', '']
        for case in diagnostic:
            lines += ['- ' + case['title_zh'] + '：' + ' '.join(case['human_readable'])]
    lines += ['', '## 检查边界', '',
              '这组案例用来检查完整服装继承、鞋子保留、历史出现位置、合法恢复及身份镜头条件。它不证明人物／参考图片的视觉质量，也不改变主候选的图条件抽样偏差。具体合法性与分布诊断见 `verification_full_squares_uniform_nodes.json`。', '']
    (HERE / 'ADVERSARIAL_CASES.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'existing_cases': len(cases), 'extra_diagnostics': len(diagnostic),
                      'missing_case_ids': [r['id'] for r in missing]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
