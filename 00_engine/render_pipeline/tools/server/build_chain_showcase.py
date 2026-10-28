"""Build a small, static, traceable showcase from the delivered node graph.

Technical owner: SERVER_EXECUTION.md. Does not render or modify source media.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[4]
AXES = {'identity': '人物身份', 'hair': '发型', 'hair_color': '发色',
        'wardrobe': '服装', 'action': '动作', 'camera': '镜头', 'site': '场景'}
CAMERAS = dict(zip(
    ['back_full','back_upper','dolly_in_back','dolly_in_front','dolly_in_side',
     'dolly_out_back','dolly_out_front','dolly_out_side','front_full','front_head',
     'front_three_quarter_full','front_three_quarter_upper','front_upper','high_full',
     'low_full','orbit_120','orbit_360','rear_three_quarter_full','rear_three_quarter_upper',
     'side_full','side_upper'],
    ['背面全身','背面上半身','背面推近','正面推近','侧面推近','背面拉远','正面拉远',
     '侧面拉远','正面全身','正面头部特写','正面斜侧全身','正面斜侧上半身','正面上半身',
     '俯视全身','仰视全身','120°环绕','360°环绕','背面斜侧全身','背面斜侧上半身','侧面全身','侧面上半身']))
COLORS = {'black':'黑色','blue':'蓝色','gold':'金色','original':'原始发色',
          'pink':'粉色','red':'红色','silver_white':'银白色'}
SLOTS = {'shirts':'上衣','pants':'裤装','skirts':'裙装','coats':'外套','shoes':'鞋',
         'full_body':'连身服装','dresses':'连衣裙'}
EXCLUDED_ACTIONS = {'ACT_M04_LIVING_ROOM_SWING','ACT_M05_ELEVATOR_GREETING','MOTION_CAND_035'}


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def choose(sessions, nodes):
    candidates = [s for s in sessions
                  if len(s['steps']) in range(2,6)
                  and not any(t['is_branch'] for t in s['steps'])
                  and len(set(s['history_node_ids'])) == len(s['history_node_ids'])
                  and all(nodes[x]['state']['wardrobe']['family_id'] != 'female.bikini_ruana'
                          and nodes[x]['state']['action'] not in EXCLUDED_ACTIONS
                          for x in s['history_node_ids'])]
    selected, used, scenes, identities, axes = [], set(), set(), set(), Counter()
    # Choose long chains first; preserve two landscape and two portrait examples per group.
    for length in (5,4,3,2):
        for index, (aspect, sex) in enumerate([('landscape','female'),('landscape','male'),
                                              ('portrait','female'),('portrait','male')]):
            pool = [s for s in candidates if len(s['steps']) == length
                    and not used.intersection(s['history_node_ids'])
                    and nodes[s['root_node']]['state']['aspect'] == aspect
                    and nodes[s['root_node']]['state']['sex'] == sex]
            if not pool:
                raise ValueError(f'No disjoint candidate for {length}/{aspect}/{sex}')
            def score(s):
                states = [nodes[x]['state'] for x in s['history_node_ids']]
                edge_axes = {t['axis'] for t in s['steps']}
                return (20*len(edge_axes) + 10*sum(1/(1+axes[a]) for a in edge_axes)
                        + 7*len({x['site'] for x in states}-scenes)
                        + 3*len({x['identity'] for x in states}-identities)
                        + sum(4 if x['camera'].startswith(('front','dolly_out_front')) else
                              2 if x['camera'].startswith('orbit') else -2 for x in states)
                        - sum(5 if x['camera'] == 'front_head' else 0 for x in states))
            chosen = sorted(pool, key=lambda s: (-score(s), s['session_id']))[0]
            selected.append({'session_id':chosen['session_id'], 'edit_count':length,
                             'example_id':f'L{length}-{index+1:02d}'})
            used.update(chosen['history_node_ids'])
            scenes.update(nodes[x]['state']['site'] for x in chosen['history_node_ids'])
            identities.update(nodes[x]['state']['identity'] for x in chosen['history_node_ids'])
            axes.update(t['axis'] for t in chosen['steps'])
    return sorted(selected, key=lambda x:x['example_id'])


def labels(node, actions):
    s = node['state']; app = node['requested_appearance']
    hair_meshes = [m['name'].replace('_',' ') for m in app['hair']['fit']['meshes']
                   if 'base' not in m['name'].lower()]
    wardrobe = app['wardrobe_assets']
    wardrobe_rows = [dict(id=a['asset_id'], label=a['label'],
                         slot=SLOTS.get(a.get('slot'), '鞋' if a['asset_id']==s['wardrobe'].get('shared_shoe_id') else '部件'))
                     for a in wardrobe]
    return {'identity':s['identity'], 'sex':'女性' if s['sex']=='female' else '男性',
            'hair':s['hair']+' · '+' / '.join(hair_meshes),
            'hair_color':COLORS[s['hair_color']], 'wardrobe':wardrobe_rows,
            'action':actions.get(s['action'],s['action']), 'camera':CAMERAS.get(s['camera'],s['camera']),
            'site':node['scene']['name'], 'aspect':'横屏' if s['aspect']=='landscape' else '竖屏'}


def edge_description(edge, a, b):
    axis = edge['axis']; before, after = a['labels'], b['labels']
    delta = [k for k in a['state'] if a['state'][k] != b['state'][k]]
    if delta != [axis]:
        raise ValueError(f'Non-atomic edit: {edge["used_edge_key"]}: {delta}')
    if axis == 'wardrobe':
        old = {x['id']: x for x in before['wardrobe']}; new = {x['id']: x for x in after['wardrobe']}
        removed = [v for k,v in old.items() if k not in new]
        added = [v for k,v in new.items() if k not in old]
        def fmt(xs):
            return '；'.join(x['slot']+'：'+x['label'] for x in xs) or '无'
        # Labels alone can collide across outfit families; always retain exact asset IDs.
        return {'title':'更换'+SLOTS.get(edge.get('single_piece_target_slot'),'整套服装')
                if edge.get('mode')=='single_piece' else '更换整套服装',
                'before':fmt(removed),'after':fmt(added),
                'removed_assets':removed,'added_assets':added,
                'preserved_assets':[v for k,v in old.items() if k in new]}
    return {'title':'更换'+AXES[axis], 'before':before[axis], 'after':after[axis]}


def link_media(out, dataset, data, copy_media=False):
    media = out/'media'; media.mkdir(exist_ok=True)
    for key, row in data['nodes'].items():
        src = dataset/row['dataset_video']; target = media/(key+'.mp4')
        if not src.is_file():
            raise FileNotFoundError(src)
        if copy_media:
            if target.is_symlink():
                target.unlink()
            if not target.exists():
                temporary=target.with_suffix('.mp4.tmp')
                shutil.copyfile(src,temporary)
                temporary.replace(target)
            if hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(src.read_bytes()).digest():
                raise ValueError(f'Copied media checksum mismatch: {target}')
            continue
        if target.is_symlink():
            if target.resolve() != src.resolve():
                target.unlink()
            else:
                continue
        if target.exists():
            raise FileExistsError(f'Refusing to replace an existing media file: {target}')
        target.symlink_to(os.path.relpath(src, media))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=ROOT/'00_engine/outputs/data_v12_20261028')
    parser.add_argument('--output',type=Path,default=ROOT/'00_engine/render_pipeline/showcase/chain_examples_20261028')
    parser.add_argument('--link-only',action='store_true',help='Use frozen examples.json; no input catalog required')
    parser.add_argument('--copy-media',action='store_true',help='Materialize byte-identical copies; user-authorized showcase only')
    a = parser.parse_args(); out = a.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    if a.link_only:
        link_media(out,a.dataset.resolve(),read(out/'examples.json'),a.copy_media); return
    chains = read(a.dataset/'chains.json'); nodes = read(a.dataset/'nodes.json')['nodes']
    motions = read(ROOT/'00_engine/render_pipeline/workspace/00_engine/assets/character_creator/production_motion_library_20261017_v1.json')
    actions = {x['motion_id']:x['label_zh'] for x in motions['motions']}
    selection_path = out/'selection.json'
    if selection_path.exists():
        selected = read(selection_path)['examples']
    else:
        selected = choose(chains['sessions'],nodes)
        dump(selection_path,{'policy':'16 complete linear sessions, 4 per length 2..5; two sexes/two aspects per group; disjoint node IDs',
                             'excluded_outfit_families':['female.bikini_ruana'],
                             'excluded_actions':sorted(EXCLUDED_ACTIONS),'examples':selected})
    by_id = {s['session_id']:s for s in chains['sessions']}; cards, samples = {}, []
    for item in selected:
        s = by_id[item['session_id']]
        assert len(s['steps']) == item['edit_count']
        ids = s['history_node_ids']
        assert ids == [s['root_node']]+[e['target_node'] for e in s['steps']]
        for key in ids:
            n=nodes[key]
            assert n['state']['wardrobe']['family_id'] != 'female.bikini_ruana'
            assert n['state']['action'] not in EXCLUDED_ACTIONS
            cards[key]={'id':key,'dataset_video':n['video'],'state':n['state'],'output':n['output'],
                        'labels':labels(n,actions),'expression':'微笑（预制Smile动作）',
                        'animation_path':n['recorded_render']['animation_path']}
        edges=[]
        for i,e in enumerate(s['steps']):
            assert not e['is_branch'] and e['source_node']==ids[i] and e['target_node']==ids[i+1]
            assert e['source_history_occurrence']==i and e['output_history_occurrence']==i+1
            edges.append({**e,'axis_label':AXES[e['axis']],
                          'description':edge_description(e,cards[e['source_node']],cards[e['target_node']])})
        samples.append({**item,'split':s['split'],'root_node':s['root_node'],
                        'node_ids':ids,'steps':edges})
    assert Counter(s['edit_count'] for s in samples)=={2:4,3:4,4:4,5:4}
    assert len(cards)==sum(len(s['node_ids']) for s in samples)==72
    counts=Counter(e['axis'] for s in samples for e in s['steps'])
    data={'schema':'datamake_chain_showcase_v1','created_date':'2026-10-28',
          'title':'从一次编辑，到完整变化', 'description_source':'源/目标节点属性差异，不是尚待上传的正式训练prompt',
          'dataset':'data_v12_20261028','selection':read(selection_path),
          'source_sha256':{f:hashlib.sha256((a.dataset/f).read_bytes()).hexdigest() for f in ['chains.json','nodes.json']},
          'stats':{'chains':len(samples),'videos':len(cards),'edits':sum(counts.values()),'axes':dict(counts)},
          'chains':samples,'nodes':cards}
    dump(out/'examples.json',data)
    (out/'data.js').write_text('window.SHOWCASE_DATA = '+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';\n',encoding='utf-8')
    link_media(out,a.dataset.resolve(),data,a.copy_media)
    dump(out/'validation.json',{'status':'structural_checks_passed','stats':data['stats'],
                               'source_edges_verified':True,'atomic_state_diff_verified':True,
                               'complete_sessions_only':True,'all_media_exist':True,
                               'visual_acceptance':'pending_selected_sample_review'})
    print(json.dumps(data['stats'],ensure_ascii=False))


if __name__ == '__main__':
    main()
