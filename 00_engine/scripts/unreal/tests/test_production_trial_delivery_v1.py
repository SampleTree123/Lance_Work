"""Lightweight contract/HTML/command-boundary checks; no rendering or encoding."""
import copy
from pathlib import Path
import sys
import pytest
SCRIPTS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SCRIPTS))
import encode_production_trial_v1 as e
import build_production_trial_gallery_v1 as g
import open_production_trial_gallery_v1 as launcher


def plan():
    return {'schema':'production_four_trials_v1','site':{'name':'游乐园 / 1'},'appearance_selection':{'sex':'female','face_id':'smile'},
        'shots':[{'shot_id':'trial_'+str(i),'motion_id':'MOTION_CAND_036' if i<2 else 'MOTION_CAND_019',
            'motion_label':'模特步行' if i<2 else '思考','camera_id':('orbit_360','front_full','front_head','rear_three_quarter_upper')[i],
            'camera_label':'镜头','width':1440 if i<2 else 2560,'height':2560 if i<2 else 1440,'fps':30,'frame_count':300,'duration_seconds':10.} for i in range(4)]}


def probe():
    return {'streams':[{'codec_type':'video','codec_name':'h264','pix_fmt':'yuv420p','width':1440,'height':2560,
        'nb_read_frames':'300','avg_frame_rate':'30/1','r_frame_rate':'30/1','duration':'10.000000','start_time':'0.000000'}],
        'format':{'duration':'10.000000'},'frames':[{'best_effort_timestamp_time':f'{i/30:.6f}'} for i in range(300)]}


def test_four_trial_contract_and_resolution():
    assert len(e.validate_plan(plan()))==4
    p=plan();p['shots'][0]['width']=720
    with pytest.raises(ValueError):e.validate_plan(p)
    p=plan();p['shots'][0]['frame_count']=301
    with pytest.raises(ValueError):e.validate_plan(p)


def test_terminal_render_zero_start_and_plan_match():
    shots=e.validate_plan(plan());sid='trial_0'
    receipt={'attempt_id':'attempt','success':True,'status':'completed','jobs':[{'shot_id':sid}],
        'render_contract':{'fps':30,'format':'PNG','range_start_inclusive':0,'width':1440,'height':2560,'frame_counts_by_shot':{sid:300}}}
    assert e.validate_render(receipt,'attempt',shots)==receipt['jobs']
    receipt['render_contract']['range_start_inclusive']=1
    with pytest.raises(ValueError):e.validate_render(receipt,'attempt',shots)
    receipt['render_contract']['range_start_inclusive']=0;receipt['success']=False
    with pytest.raises(ValueError):e.validate_render(receipt,'attempt',shots)


def test_exact_zero_based_png_names_no_offset_gap_or_extra():
    names=[f'frame_{i:04d}.png' for i in range(300)];e.check_frame_names(names)
    for bad in (names[1:],names+[names[0]],[f'frame_{i:04d}.png' for i in range(1,301)]):
        with pytest.raises(ValueError):e.check_frame_names(bad)


def test_probe_requires_all300_correctly_timed_frames():
    data=probe();out=e.validate_probe(data,1440,2560)
    assert out['all_frame_timestamps_verified'] and out['decoded_frames']==300
    data['frames'][0]['best_effort_timestamp_time']='0.033333'
    with pytest.raises(ValueError):e.validate_probe(data,1440,2560)
    data=probe();data['streams'][0]['nb_read_frames']='299'
    with pytest.raises(ValueError):e.validate_probe(data,1440,2560)
    data=probe();data['streams'][0]['duration']='9.966667'
    with pytest.raises(ValueError):e.validate_probe(data,1440,2560)
    data=probe();data['streams'].append({'codec_type':'audio'})
    with pytest.raises(ValueError):e.validate_probe(data,1440,2560)


def test_paths_and_ids_cannot_escape_owned_run(tmp_path):
    with pytest.raises(ValueError):e.owned(tmp_path,tmp_path.parent/'escape')
    for bad in ('../oops','CON','bad/name','',None):
        with pytest.raises(ValueError):e.identifier(bad)
    with pytest.raises(ValueError):g.relative_file(tmp_path,'../escape')
    with pytest.raises(ValueError):g.relative_file(tmp_path,'C:/escape.mp4')


def test_gallery_pending_exact_four_cards_and_no_unverified_video(tmp_path):
    e.write(tmp_path/'four_trials_plan.json',plan());data=g.gather(tmp_path)
    assert data['playable_count']==0 and len(data['cards'])==4
    text=g.render_html(data)
    assert text.count('<article>')==4 and '<video' not in text
    assert '1440 × 2560' in text and '2560 × 1440' in text
    assert '实际处理耗时与文件大小' in text and '微笑' in text
    assert g.build(tmp_path)['playable']==0


def test_gallery_escapes_user_site_names_and_configuration(tmp_path):
    p=plan();p['site']['name']='<script>alert(1)</script>';p['appearance_selection']['character_id']='</pre><img src=x onerror=alert(1)>'
    e.write(tmp_path/'four_trials_plan.json',p);text=g.render_html(g.gather(tmp_path))
    assert '<script>alert(1)</script>' not in text
    assert '&lt;script&gt;' in text
    assert '<img src=x' not in text


def test_actual_elapsed_not_inferred_from_frame_count():
    r={'submitted_at':'2026-10-17T10:00:00+00:00','finished_at':'2026-10-17T10:03:00+00:00'}
    assert e.elapsed(r,'submitted_at','finished_at')==180.
    assert e.elapsed({},'submitted_at','finished_at') is None


def test_gallery_requires_verified_hash_bound_media_and_first_png(tmp_path):
    p=plan();shot=p['shots'][0];e.write(tmp_path/'four_trials_plan.json',p);plan_pin=e.pin(tmp_path/'four_trials_plan.json')
    (tmp_path/'videos').mkdir();video=tmp_path/'videos/test.mp4';poster=tmp_path/'videos/test.jpg'
    # Only receipt/hash plumbing is exercised; these bytes are never decoded.
    video.write_bytes(b'fixture');poster.write_bytes(b'poster')
    record={'schema':'production_trial_media_v1','success':True,'status':'encoded_verified','shot_id':shot['shot_id'],
        'pins':{'plan':plan_pin},'shot_plan_sha256':e.object_sha(shot),'width':1440,'height':2560,'fps':30,'frames':300,'duration_seconds':10.,
        'decode':dict(e.validate_probe(probe(),1440,2560),ffprobe_full_decode_success=True,ffmpeg_full_decode_success=True,
            ffmpeg_full_decode_frames=300,first_frame={'png_name':'frame_0000.png','decoded_rgb_mean_absolute_error':1.,'mean_absolute_error_limit_8bit':12.}),
        'video':{'path':'videos/test.mp4','sha256':e.sha(video),'bytes':video.stat().st_size},
        'poster':{'path':'videos/test.jpg','sha256':e.sha(poster)}}
    path=tmp_path/'media_receipts'/(shot['shot_id']+'.json');e.write(path,record)
    assert g.validated_media(tmp_path,shot,plan_pin)['status']=='encoded_verified'
    record['decode']['first_frame']['png_name']='frame_0001.png';e.write(path,record)
    with pytest.raises(ValueError):g.validated_media(tmp_path,shot,plan_pin)
    record['decode']['first_frame']['png_name']='frame_0000.png';e.write(path,record);video.write_bytes(b'changed')
    with pytest.raises(ValueError):g.validated_media(tmp_path,shot,plan_pin)


def test_launcher_uses_loopback_current_run_and_protected_port_skips(tmp_path):
    ports=launcher.candidate_ports(8886,12)
    assert ports[0]==8886 and 8893 not in ports
    assert not set(ports)&launcher.PROTECTED_PORTS
    assert launcher.gallery_url(8886)=='http://127.0.0.1:8886/trial_gallery/index.html'
    with pytest.raises(ValueError):launcher.gallery_url(8880)
    with pytest.raises(ValueError):launcher.candidate_ports(True)
    with pytest.raises(ValueError):launcher.paths(tmp_path)
