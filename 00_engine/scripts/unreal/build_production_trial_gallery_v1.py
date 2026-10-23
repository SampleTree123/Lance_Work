"""Four-card Chinese trial review from validated media; no server or UE calls."""
from __future__ import annotations
import argparse
import html
import json
import math
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import encode_production_trial_v1 as media

RUN=media.RUN
FACES={'none':'无表情','smile':'微笑','idle':'自然','displeased':'不悦','surprised':'惊讶'}
CAMERAS={'orbit_360':'360° 环绕','front_full':'正面全身','front_head':'面部特写','rear_three_quarter_upper':'后侧上半身'}


def seconds(value):
    return '—' if value is None else f'{value:.1f} 秒'


def processing_total(timing):
    values=[timing.get(k) for k in ('preparation_seconds','render_seconds','png_validation_seconds','encoding_seconds','media_validation_seconds')]
    if any(v is None for v in values):return None
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):raise ValueError('Invalid recorded processing time')
    return sum(values)


def wall_clock(events,shot_id,attempt):
    ends=[i for i,e in enumerate(events) if e.get('stage')=='trial_verified' and e.get('shot_id')==shot_id and e.get('attempt')==attempt]
    if len(ends)!=1:return None
    end=ends[0]
    renders=[i for i,e in enumerate(events[:end]) if e.get('stage')=='render_start' and e.get('shot_id')==shot_id and e.get('attempt')==attempt]
    if len(renders)!=1:return None
    render=renders[0]
    starts=[i for i,e in enumerate(events[:render]) if e.get('stage')=='prepare_start' and e.get('shot_id')==shot_id]
    if not starts:return None
    start=starts[-1]
    # Never combine preparation from a different retry or render attempt.
    if any(e.get('stage')=='render_start' and e.get('shot_id')==shot_id for e in events[start:render]):return None
    elapsed=(datetime.fromisoformat(events[end]['at'])-datetime.fromisoformat(events[start]['at'])).total_seconds()
    return elapsed if math.isfinite(elapsed) and elapsed>=0 else None


def relative_file(run,value):
    if not isinstance(value,str) or not value or Path(value).is_absolute() or ':' in value:
        raise ValueError('Require relative owned media URL')
    path=media.owned(run,Path(run)/value)
    if not path.is_file():raise FileNotFoundError(path)
    return path


def validated_media(run,shot,plan_pin):
    path=Path(run)/'media_receipts'/(shot['shot_id']+'.json')
    if not path.exists():return None
    record=media.read(path)
    if record.get('schema')!='production_trial_media_v1' or record.get('status')!='encoded_verified' or record.get('success') is not True:
        raise ValueError('Trial media receipt is not verified')
    if record.get('shot_id')!=shot['shot_id'] or record.get('pins',{}).get('plan')!=plan_pin or record.get('shot_plan_sha256')!=media.object_sha(shot):raise ValueError('Media/plan binding differs')
    if (record.get('width'),record.get('height'),record.get('fps'),record.get('frames'),record.get('duration_seconds'))!=(shot['width'],shot['height'],30,300,10.):raise ValueError('Media resolution/timing differs')
    decode=record['decode']
    if decode.get('ffprobe_full_decode_success') is not True or decode.get('ffmpeg_full_decode_success') is not True or decode.get('all_frame_timestamps_verified') is not True or decode.get('decoded_frames')!=300 or decode.get('ffmpeg_full_decode_frames')!=300 or decode.get('first_frame_timestamp_seconds')!=0:
        raise ValueError('Trial full-decode/first-frame proof incomplete')
    if (decode.get('width'),decode.get('height'),decode.get('fps'),decode.get('duration_seconds'))!=(shot['width'],shot['height'],30.,10.):
        raise ValueError('Decoded trial dimensions/rate/duration differ')
    first=decode.get('first_frame',{})
    if first.get('png_name')!='frame_0000.png' or not 0<=first.get('decoded_rgb_mean_absolute_error',float('inf'))<=12. or first.get('mean_absolute_error_limit_8bit')!=12.:
        raise ValueError('First source-frame comparison is incomplete')
    for key in ('video','poster'):
        asset=relative_file(run,record[key]['path'])
        if media.sha(asset)!=record[key]['sha256']:raise ValueError('Trial '+key+' hash changed')
    if relative_file(run,record['video']['path']).stat().st_size!=record['video']['bytes']:raise ValueError('Trial video size changed')
    return dict(record,receipt=media.pin(path))


def gather(run=RUN,resource_report=None):
    run=Path(run).resolve();plan_path=run/'four_trials_plan.json';plan=media.read(plan_path);media.validate_plan(plan);plan_pin=media.pin(plan_path)
    cards=[];events=[];events_path=run/'serial_trials/events.jsonl'
    if events_path.is_file():
        for line in events_path.read_text(encoding='utf-8').splitlines():
            try:events.append(json.loads(line))
            except json.JSONDecodeError:continue
    for index,shot in enumerate(plan['shots'],1):
        record=validated_media(run,shot,plan_pin)
        card={'number':index,'shot_id':shot['shot_id'],'motion_label':shot['motion_label'],
            'camera_label':CAMERAS.get(shot['camera_id'],shot.get('camera_label',shot['camera_id'])),
            'width':shot['width'],'height':shot['height'],'fps':30,'duration_seconds':10.,'playable':record is not None,
            'orientation_label':'竖屏' if shot['height']>shot['width'] else '横屏','human_acceptance':'pending'}
        if record:
            card.update(video=record['video'],poster=record['poster'],timing=record['timing'],media_receipt=record['receipt'],
                first_frame=record['decode']['first_frame'],verification_status='encoded_verified',attempt=record['attempt'])
        else:
            prepared=run/'prepared'/(shot['shot_id']+'.json')
            card.update(timing={'preparation_seconds':media.read(prepared).get('preparation_seconds') if prepared.exists() else None},verification_status='pending')
        card['processing_total_seconds']=processing_total(card['timing'])
        card['wall_clock_seconds']=wall_clock(events,shot['shot_id'],record['attempt']) if record else None
        cards.append(card)
    resources=None
    if resource_report:
        path=media.owned(run,resource_report)
        resources={'file':path.relative_to(run).as_posix(),'pin':media.pin(path),'data':media.read(path)}
    return {'schema':'production_four_trial_gallery_v1','plan':plan_pin,'site':plan['site'],
            'appearance_selection':plan['appearance_selection'],'cards':cards,'playable_count':sum(c['playable'] for c in cards),
            'resources':resources,'human_acceptance':'pending'}


def render_html(data):
    esc=lambda x:html.escape(str(x),quote=True)
    href=lambda path:'../'+quote(path,safe='/')
    cards=[];table=[]
    for card in data['cards']:
        label=esc(card['motion_label']);camera=esc(card['camera_label']);timing=card['timing']
        if card['playable']:
            player=f'<video controls playsinline preload="metadata" loop poster="{href(card["poster"]["path"])}"><source src="{href(card["video"]["path"])}" type="video/mp4"></video>'
            size=f'{card["video"]["bytes"]/1024/1024:.1f} MB'
            action=f'<a href="{href(card["video"]["path"])}" download>下载原视频</a>'
            status='<span class="verified">完整解码已通过 · 300 帧</span>'
        else:
            player='<div class="pending">正在准备样片</div>';size='—';action='';status='<span>待生成与校验</span>'
        cards.append(f'<article><header><small>样片 {card["number"]} · {card["orientation_label"]}</small><h2>{label} · {camera}</h2></header><div class="player {"portrait" if card["height"]>card["width"] else "landscape"}">{player}</div><footer><p>{card["width"]} × {card["height"]} · 30 帧/秒 · 10 秒 · {size}</p><div class="status">{status}{action}</div></footer></article>')
        table.append('<tr>'+''.join(f'<td>{value}</td>' for value in [f'{card["number"]} · {label}',camera,seconds(timing.get('preparation_seconds')),seconds(timing.get('render_seconds')),seconds(timing.get('png_validation_seconds')),seconds(timing.get('encoding_seconds')),seconds(timing.get('media_validation_seconds')),seconds(card.get('processing_total_seconds')),seconds(card.get('wall_clock_seconds')),size])+'</tr>')
    selection=data['appearance_selection'];face=FACES.get(selection.get('face_id'),selection.get('face_id','未记录'))
    character='女性' if selection.get('sex')=='female' else '男性'
    config=esc(json.dumps(selection,ensure_ascii=False,indent=2))
    resource=''
    if data['resources']:
        metrics=data['resources']['data']
        trial_scope=metrics.get('scope')=='four_successful_revised_trials_preparation_render_encoding_validation_intervals_only'
        scope_label='本次四条样片制作期间（含准备、渲染、编码和验证；采样值）' if trial_scope else '整个监控时段（不局限于渲染）'
        if (type(metrics.get('samples')) is int and metrics['samples']>0
                and all(type(metrics.get(k)) in (int,float) and math.isfinite(metrics[k]) and metrics[k]>=0
                        for k in ('minimum_available_ram_gib','maximum_gpu_used_mib','minimum_disk_free_gib'))):
            unreal=metrics.get('maximum_unreal_rss_gib')
            unreal_text=f'，最高 UE 内存占用 {unreal:.1f} GiB' if type(unreal) in (int,float) and math.isfinite(unreal) and unreal>=0 else ''
            resource=f'<p class="resource">{scope_label}共 {metrics["samples"]} 次采样：最低可用内存 {metrics["minimum_available_ram_gib"]:.1f} GiB，最高显存占用 {metrics["maximum_gpu_used_mib"]/1024:.1f} GiB{unreal_text}，最低磁盘余量 {metrics["minimum_disk_free_gib"]:.1f} GiB。采样值不代表连续监测的绝对峰值。</p>'
        resource+=f'<p class="resource"><a href="{href(data["resources"]["file"])}">查看{"四条样片制作期间" if trial_scope else "整个监控时段"}的资源记录</a></p>'
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>正式流程 · 四条样片</title><style>
*{box-sizing:border-box}body{margin:0;background:#10171d;color:#edf2f3;font:16px/1.65 "Microsoft YaHei",system-ui,sans-serif}main{max-width:1380px;margin:auto;padding:44px 28px}h1{font-size:34px;line-height:1.3;margin:10px 0}h2{font-size:20px;margin:4px 0}p{margin:8px 0}small,.muted{color:#a9b7c1}.eyebrow{color:#7ad8bb;font-size:13px;letter-spacing:.16em}.intro{margin-bottom:28px;max-width:900px}.config{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}.config span{background:#1c2a32;border:1px solid #30444e;padding:7px 13px;border-radius:25px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{background:#19232b;border:1px solid #30414b;border-radius:16px;overflow:hidden}header,footer{padding:18px 22px}.player{background:#06090c;display:flex;justify-content:center;align-items:center;min-height:300px}.portrait{height:620px}.landscape{aspect-ratio:16/9}.player video{max-width:100%;width:100%;height:100%;max-height:620px;object-fit:contain}.pending{padding:100px 0;color:#7f919c}.status{display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:13px}.verified{color:#80d8ba}a{color:#91d6ff;text-decoration:none}a:hover{text-decoration:underline}.table-wrap{overflow:auto;border:1px solid #30414b;border-radius:12px;margin-top:36px}table{width:100%;border-collapse:collapse;font-size:14px;white-space:nowrap}caption{text-align:left;font-size:20px;font-weight:bold;padding:18px;background:#19232b}th,td{text-align:left;padding:13px 16px;border-top:1px solid #30414b}th{color:#aabac3}details{margin-top:24px}pre{white-space:pre-wrap;word-break:break-word;font-size:12px;color:#aabac3;background:#162129;padding:20px;border-radius:12px}.resource{margin-top:20px}@media(max-width:820px){main{padding:24px 16px}.cards{grid-template-columns:1fr}.portrait{height:600px}h1{font-size:28px}.status{flex-wrap:wrap}}
</style><main><section class="intro"><div class="eyebrow">DATAMAKE · 正式流程试拍</div><h1>同一场景，四条十秒样片</h1><p class="muted">检查动作、表情、衣着和镜头的实际画面。点击播放一条视频时，其他视频会暂停。</p>'''+f'<div class="config"><span>场景：{esc(data["site"].get("name","未记录"))}</span><span>{character}角色 · {esc(face)}</span><span>{data["playable_count"]} / 4 条已校验</span></div></section><section class="cards">'+''.join(cards)+'</section><div class="table-wrap"><table><caption>实际处理耗时与文件大小</caption><thead><tr><th>动作</th><th>镜头</th><th>准备</th><th>渲染</th><th>PNG 校验</th><th>编码</th><th>视频验证</th><th>处理合计</th><th>实际用时</th><th>文件</th></tr></thead><tbody>'+''.join(table)+'</tbody></table></div><p class="muted">处理合计为准备、渲染、PNG 校验、编码和视频验证之和，不包含轮询与额外载入等待。实际用时为同一条样片从开始准备到文件验证完成的时钟间隔，包含这些等待；缺少对应记录时显示“—”。曝光保持原设置，日照下皮肤可能较亮，画面效果仍待你审看。</p>'+resource+f'<details><summary>查看完整人物外观配置</summary><pre>{config}</pre></details>'+'''<script>document.querySelectorAll('video').forEach(v=>v.addEventListener('play',()=>document.querySelectorAll('video').forEach(other=>{if(other!==v)other.pause()})));</script></main></html>'''


def build(run=RUN,resource_report=None):
    run=Path(run).resolve();data=gather(run,resource_report);folder=run/'trial_gallery';folder.mkdir(parents=True,exist_ok=True)
    media.write(folder/'gallery_data.json',data)
    temp=folder/'index.html.partial';temp.write_text(render_html(data),encoding='utf-8');temp.replace(folder/'index.html')
    return {'index':str(folder/'index.html'),'playable':data['playable_count'],'total':4,'human_acceptance':'pending'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-root',type=Path,default=RUN);parser.add_argument('--resource-report',type=Path)
    args=parser.parse_args();print(json.dumps(build(args.run_root,args.resource_report),ensure_ascii=False))
