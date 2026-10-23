#!/usr/bin/env python3
"""Validate all CFG shards and build a review page. Owner: ../training_integration.md."""
import argparse
import html
import json
from pathlib import Path
from build_datamake_visual_sanity_review import video_check
from datamake_coinve_review_media import sampled_preview
from build_datamake_teacher_forced_conversation import sha256_file
from run_datamake_cfg4 import GROUPS, ORIGINAL, SUITE

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); a=ap.parse_args(); root=a.root.resolve()
    cases=ORIGINAL(json.loads(SUITE.read_text())); found={}; checks={}
    for group,t,v in GROUPS:
        for path in (root/group).glob('rank*/manifest.json'):
            m=json.loads(path.read_text()); assert m['status']=='generated'
            assert m['completed_steps']==1650
            assert m['arguments']['model']['cfg_text_scale']==t and m['arguments']['model']['cfg_vit_scale']==v
            assert m['adapter_load_check']['tensor_count']==m['adapter_load_check']['matching_after_bf16_cast']
            for c in m['cases']:
                key=(group,c['name']); assert key not in found
                found[key]=(path.parent,c)
                for o in c['outputs']:
                    p=path.parent/o['output']; info=video_check(p); assert info['decoded_frames']>0
                    checks[str(p.relative_to(root))]=info
        assert {name for g,name in found if g==group}=={c['name'] for c in cases}
    assert len(checks)==140
    (root/'references').mkdir(exist_ok=True)
    def vid(p):
        p=Path(p).resolve()
        if not p.is_relative_to(root):
            link=root/'references'/(sha256_file(p)[:16]+'_'+p.name)
            if not link.exists(): link.symlink_to(p)
            p=link
        return '<video controls muted preload="none" src="'+html.escape(str(p.relative_to(root)))+'"></video>'
    parts=['<!doctype html><meta charset="utf-8"><title>GT1650 CFG 对比</title><style>body{background:#151b24;color:#eee;font:16px system-ui;margin:24px}video{width:300px}table{display:block;overflow:auto}td,th{padding:10px;vertical-align:top;border:1px solid #456}pre{white-space:pre-wrap}</style><h1>GT1650 · 合成与真实数据 CFG 消融</h1><p>30步，固定seed；每行比较同一轮；合成数据区分GT历史与自回填。视觉CFG移除ViT条件，保留源VAE条件。</p>']
    for c in cases:
        parts.append('<h2>'+html.escape(c['name'])+'</h2><table><tr><th>指令 / GT</th>'+''.join('<th>'+g+'</th>' for g,_,_ in GROUPS)+'</tr>')
        for i,o in enumerate(c['outputs']):
            target=Path(o['gt_target'])
            if c.get('paired_crop'):
                target,_=sampled_preview(target,c['paired_crop'],root,sha256_file(target))
            parts.append('<tr><td><pre>'+html.escape(o['prompt'])+'</pre>'+vid(target)+'</td>')
            for g,_,_ in GROUPS:
                base,actual=found[(g,c['name'])]; parts.append('<td>'+vid(base/actual['outputs'][i]['output'])+'</td>')
            parts.append('</tr>')
        parts.append('</table>')
    (root/'index.html').write_text('\n'.join(parts))
    (root/'media_audit.json').write_text(json.dumps(checks,indent=2))
    print(root/'index.html')
if __name__=='__main__': main()
