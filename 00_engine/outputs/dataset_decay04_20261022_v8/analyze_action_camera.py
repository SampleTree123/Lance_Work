"""Experimental action/camera coverage; owner: DATASET_DESIGN_EXPLORATION_20261021.md."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT.parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def summarize(candidate):
    catalog = read(OUTPUTS / 'dataset_trial_build_20261021_v1/catalog.json')
    actions = {a['id']: a['label'] for a in catalog['actions']}
    cameras = {a['id']: a['label'] for a in catalog['cameras']}
    references = read(candidate / 'reference_manifest.json')['requirements']
    refs = [r for r in references if r['kind'] == 'motion']
    nodes_by_split = {s: read(candidate/s/'nodes.json') for s in ['train','test']}
    rows = []
    for action, label in actions.items():
        row = {'action': action, 'label': label, 'splits': {}}
        selected_refs = [r for r in refs if r['key']['action'] == action]
        row['reference_clips'] = len(selected_refs)
        row['reference_cameras'] = sorted({r['key']['camera'] for r in selected_refs})
        combined = []
        for split, nodes in nodes_by_split.items():
            selected = [n for n in nodes if n['state']['action'] == action]
            combined.extend(selected)
            counts = collections.Counter(n['state']['camera'] for n in selected)
            row['splits'][split] = {'videos': len(selected), 'content_states':len({n['content_id'] for n in selected}),
                'camera_counts':dict(counts), 'camera_count':len(counts),
                'top_camera_share':max(counts.values(),default=0)/max(1,len(selected))}
        counts = collections.Counter(n['state']['camera'] for n in combined)
        row.update(videos=len(combined), camera_counts=dict(counts),camera_count=len(counts),
                   top_camera_share=max(counts.values(),default=0)/max(1,len(combined)))
        rows.append(row)
    files=[candidate/'reference_manifest.json']+[candidate/s/'nodes.json' for s in nodes_by_split]
    return {'candidate':str(candidate),'scope':'unique rendered node demands, not session-weighted appearances; camera counts merge sexes/aspects',
            'inputs':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
            'main_video_count':sum(len(n) for n in nodes_by_split.values()),'motion_reference_count':len(refs),
            'camera_labels':cameras, 'actions':rows,
            'summary':{'main_camera_count_distribution':dict(collections.Counter(r['camera_count'] for r in rows)),
                       'reference_camera_count_distribution':dict(collections.Counter(len(r['reference_cameras']) for r in rows)),
                       'main_action_camera_pairs':sum(r['camera_count'] for r in rows),
                       'reference_action_camera_pairs':sum(len(r['reference_cameras']) for r in rows)}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,default=OUTPUTS/'dataset_dual_aspect_20261022_v7/selected_candidate');p.add_argument('--name',default='baseline_action_camera');args=p.parse_args()
    data=summarize(args.candidate)
    (ROOT/(args.name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 动作与镜头覆盖统计','',f"数据来源：`{args.candidate}`。主视频按唯一渲染节点统计；镜头种类合并男女和横竖屏，不以副本重复计数。",'',
        '| 动作 | 训练主视频 | 训练镜头种类 | 测试主视频 | 测试镜头种类 | 全部主视频镜头种类 | 动作参考镜头种类 | 参考视频数 | 主视频最大单镜头占比 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in data['actions']:
        t,e=r['splits']['train'],r['splits']['test']
        lines.append(f"| {r['label']} | {t['videos']} | {t['camera_count']} | {e['videos']} | {e['camera_count']} | {r['camera_count']} | {len(r['reference_cameras'])} | {r['reference_clips']} | {r['top_camera_share']:.1%} |")
    lines+=['','## 明细','']
    for r in data['actions']:
        lines += [f"### {r['label']}（{r['action']}）",'', '主视频镜头：'+ '、'.join(f"{data['camera_labels'].get(k,k)} {v}" for k,v in sorted(r['camera_counts'].items())), '', '动作参考镜头：'+'、'.join(data['camera_labels'].get(k,k) for k in r['reference_cameras']),'']
    (ROOT/(args.name+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(data['summary']))

if __name__=='__main__': main()
