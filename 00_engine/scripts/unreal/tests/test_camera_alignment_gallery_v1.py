import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('alignment_gallery',Path(__file__).parents[1]/'build_camera_alignment_gallery_v1.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture_data(tmp_path):
    data={'schema':'camera_motion_scene_alignment_review_v1','motions':[{'id':'dance','label':'舞蹈'}],
          'cameras':[{'id':'front','label':'正面全身'}],'scenes':[],
          'clips':[{'id':'dance_front','section':'cameras','motion_id':'dance','camera_id':'front','sex':'female',
                    'orientation':'landscape','verification_status':'encoded_verified','width':1280,'height':720,
                    'duration_seconds':1.,'fps':30.,'decoded_frames':30,'video':'clip.mp4'}]}
    video=tmp_path/'clip.mp4';video.write_bytes(b'fixture bytes are not a real decode result')
    c=data['clips'][0];c['video_sha256']=m.digest(video)
    receipt={'schema':'motion_scene_encoded_shot_v1','status':'encoded_verified','shot_id':c['id'],'video':c['video'],
             'video_sha256':c['video_sha256'],'width':1280,'height':720,'expected_frames':30,
             'decode':{'decoded_frames':30,'fps':30.,'measured_duration_seconds':1.,'dimensions':[1280,720],
                       'ffmpeg_full_decode_frames':30,'ffmpeg_full_decode_success':True}}
    rp=tmp_path/'receipt.json';rp.write_text(json.dumps(receipt),encoding='utf-8')
    c.update(verification_receipt='receipt.json',verification_receipt_sha256=m.digest(rp))
    return data

def test_pending_strips_media(tmp_path):
    data=fixture_data(tmp_path);data['clips'][0]['verification_status']='pending'
    data['clips'][0]['video']='../../must_not_be_read.mp4'
    result=m.validate(data,tmp_path)
    assert result['playable_count']==0 and 'video' not in result['clips'][0]

def test_verified_receipt_bound_to_media(tmp_path):
    data=fixture_data(tmp_path)
    assert m.validate(data,tmp_path)['playable_count']==1
    data=fixture_data(tmp_path);data['clips'][0]['duration_seconds']=.999
    with pytest.raises(ValueError,match='decode metadata'):m.validate(data,tmp_path)

def test_receipt_wrong_identity_rejected(tmp_path):
    data=fixture_data(tmp_path);rp=tmp_path/'receipt.json';r=json.loads(rp.read_text());r['shot_id']='other'
    rp.write_text(json.dumps(r));data['clips'][0]['verification_receipt_sha256']=m.digest(rp)
    with pytest.raises(ValueError,match='shot_id'):m.validate(data,tmp_path)

def test_path_escape_and_duplicate_rejected(tmp_path):
    with pytest.raises(ValueError):m.local_file(tmp_path,'../outside.mp4')
    data=fixture_data(tmp_path);data['clips'].append(copy.deepcopy(data['clips'][0]));data['clips'][1]['id']='different_id'
    with pytest.raises(ValueError,match='Duplicate combination'):m.validate(data,tmp_path)

def test_cross_sex_reference_must_be_same_motion_other_sex(tmp_path):
    data=fixture_data(tmp_path);c=copy.deepcopy(data['clips'][0]);c.update(id='cross',section='cross_sex',verification_status='pending',reference_clip_id='dance_front')
    data['clips'].append(c)
    with pytest.raises(ValueError,match='opposite sex'):m.validate(data,tmp_path)
    c['sex']='male';assert m.validate(data,tmp_path)['playable_count']==1

def test_html_data_cannot_escape_script(tmp_path):
    data=fixture_data(tmp_path);data['motions'][0]['label']='</script><script>alert(1)</script>'
    (tmp_path/'review_gallery_input_v1.json').write_text(json.dumps(data),encoding='utf-8')
    result=m.build(tmp_path);html=Path(result['index']).read_text(encoding='utf-8')
    assert '</script><script>alert(1)</script>' not in html
    assert '\\u003c/script\\u003e' in html

def test_presentation_camera_order_starts_front_full_without_changing_clips(tmp_path):
    data=fixture_data(tmp_path)
    data['cameras']=[{'id':x,'label':x} for x in ['front_upper','dolly_out_back','front_head','side_full','front_full','high_full','orbit_360','front']]
    old=copy.deepcopy(data['clips'])
    result=m.presentation(data)
    assert result['default_camera_id']=='front_full'
    assert [c['id'] for c in result['cameras']]==['front_full','side_full','front_upper','front_head','high_full','orbit_360','dolly_out_back','front']
    assert result['clips']==old

def test_legacy_labels_use_catalog_and_keep_distinct_sex_ids(tmp_path):
    data=fixture_data(tmp_path)
    data['motions']=[{'id':'ACT_F03_AUDIENCE_01','label':'ACT_F03_AUDIENCE_01','source_sex':'female'},
                     {'id':'ACT_M02_AUDIENCE_01','label':'ACT_M02_AUDIENCE_01','source_sex':'male'}]
    result=m.presentation(data)
    assert result['motions'][0]['label']=='做出观看表演时的回应动作（原女性动作）'
    assert result['motions'][1]['label']=='做出观看表演时的回应动作（原男性动作）'
    assert [row['id'] for row in result['motions']]==['ACT_F03_AUDIENCE_01','ACT_M02_AUDIENCE_01']
    assert result['display_label_source']['sha256']==m.digest(m.LEGACY_LABELS)

def risk(shot_id):
    return {'shot_id':shot_id,'level':'priority_review','visual_acceptance':'pending_not_passed',
            'title':'主体离框明显','message_zh':'所检查时刻面部不在画内。','duration_note_zh':'抽样不能推断持续时间。',
            'attention_seconds':[.3,.8]}

def test_visual_risk_does_not_change_verified_media_status(tmp_path):
    data=fixture_data(tmp_path);clip=data['clips'][0];clip['visual_risk']=risk(clip['id'])
    result=m.validate(data,tmp_path)
    assert result['playable_count']==1 and result['visual_risk_count']==1
    assert clip['verification_status']=='encoded_verified' and clip['visual_status']=='pending_not_passed'
    assert clip['human_acceptance']=='pending'

def test_visual_warning_wrong_shot_or_time_rejected(tmp_path):
    data=fixture_data(tmp_path);clip=data['clips'][0];clip['visual_risk']=risk('different_shot')
    with pytest.raises(ValueError,match='match this shot'):m.validate(data,tmp_path)
    clip['visual_risk']=risk(clip['id']);clip['visual_risk']['attention_seconds']=[20]
    with pytest.raises(ValueError,match='outside clip'):m.validate(data,tmp_path)

def test_assembler_visual_risk_source_binding(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    from assemble_camera_alignment_review_v1 import visual_risks
    assert visual_risks(tmp_path,{'clip'})==({},None)
    source=tmp_path/'smoke_visual_risks_for_review_v2.json'
    source.write_text(json.dumps({'schema':'camera_review_visual_risks_v1','automatic_visual_pass':False,'items':[risk('clip')]}),encoding='utf-8')
    result,pin=visual_risks(tmp_path,{'clip'})
    assert result['clip']['visual_acceptance']=='pending_not_passed' and pin['sha256']==m.digest(source)
    with pytest.raises(ValueError,match='Unknown or duplicate'):visual_risks(tmp_path,{'other'})


def explicit_scene_index_fixture(tmp_path):
    """Synthetic future-complete display fixture; never an actual relocation proof."""
    source=tmp_path/'original_scene_index.json';source.write_text('{}',encoding='utf-8')
    mappings=[]
    for i in range(24):
        receipt=tmp_path/f'formal_{i}.json';receipt.write_text('{"success":true}',encoding='utf-8')
        mappings.append({'old_prefix':f'/Game/Root{i}','new_prefix':f'/Game/Scenes/Root{i}',
            'status':'verified','verification_receipt':{'path':str(receipt),'sha256':m.digest(receipt)}})
    overlay=tmp_path/'overlay.json'
    overlay.write_text(json.dumps({'schema':'scene_folder_relocation_v1','status':'complete','mappings':mappings}),encoding='utf-8')
    proof=tmp_path/'global.json'
    proof.write_text(json.dumps({'schema':'final_registry_and_reference_check_v1','success':True,
        'scene_root_count':24,'map_count':74,'stale_scene_dependencies':[],
        'camera_render_started':False,'registry_sha256':m.digest(overlay)}),encoding='utf-8')
    scenes=[{'maps':[f'/Game/Scenes/Root{i}/Map0'],
             'all_maps':[f'/Game/Scenes/Root{i}/Map{j}' for j in range(4 if i<5 else 3)]} for i in range(24)]
    data={'schema':'gallery_scene_index_relocated_v2','camera_render_started':False,'scenes':scenes,
        'effective_map_counts':{'relocated_scene_roots':24,'relocated_scene_maps':74,'shared_starter_maps':3,
            'effective_gallery_maps':77,'display_cards':24,'retired_duplicate_worlds':1},
        'source_index':{'path':str(source),'sha256':m.digest(source)},
        'relocation_registry':{'path':str(overlay),'sha256':m.digest(overlay)},
        'global_relocation_proof':{'path':str(proof),'sha256':m.digest(proof)}}
    index=tmp_path/'relocated_v2.json';index.write_text(json.dumps(data),encoding='utf-8')
    return index,data,overlay,proof


def test_assembler_explicit_v2_reads_frozen_index_without_old_builder(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    from assemble_camera_alignment_review_v1 import scene_index
    import scene_path_relocation_v1 as relocation
    monkeypatch.setattr(relocation,'build_current_index',lambda *a,**k:pytest.fail('Old builder must not run'))
    path,data,_,_=explicit_scene_index_fixture(tmp_path)
    raw=path.read_bytes()
    scenes,pin=scene_index(tmp_path,path)
    assert scenes==data['scenes'] and pin=={'path':str(path.resolve()),'sha256':m.digest(path)}
    assert path.read_bytes()==raw


@pytest.mark.parametrize('bad',['source_bytes','global_failed','partial_overlay','formal_bytes','duplicate_map','v1'])
def test_assembler_explicit_v2_rejects_stale_or_partial_evidence(tmp_path,monkeypatch,bad):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    from assemble_camera_alignment_review_v1 import scene_index
    path,data,overlay,proof=explicit_scene_index_fixture(tmp_path)
    if bad=='source_bytes':Path(data['source_index']['path']).write_text('changed')
    elif bad=='global_failed':
        row=json.loads(proof.read_text());row['success']=False;proof.write_text(json.dumps(row))
        data['global_relocation_proof']['sha256']=m.digest(proof)
    elif bad=='partial_overlay':
        row=json.loads(overlay.read_text());row['mappings'].pop();overlay.write_text(json.dumps(row))
        data['relocation_registry']['sha256']=m.digest(overlay)
        row=json.loads(proof.read_text());row['registry_sha256']=m.digest(overlay);proof.write_text(json.dumps(row))
        data['global_relocation_proof']['sha256']=m.digest(proof)
    elif bad=='formal_bytes':(tmp_path/'formal_0.json').write_text('changed')
    elif bad=='duplicate_map':data['scenes'][1]['all_maps'][0]=data['scenes'][0]['all_maps'][0]
    elif bad=='v1':data['schema']='gallery_scene_index_v1'
    path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError):scene_index(tmp_path,path)


def test_assembler_explicit_parameter_is_used_and_bound_to_review(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    import assemble_camera_alignment_review_v1 as assembler
    import build_camera_alignment_gallery_v1 as builder
    path,data,_,_=explicit_scene_index_fixture(tmp_path)
    (tmp_path/'camera_trial_plan_v2.json').write_text('{"shots":[]}',encoding='utf-8')
    monkeypatch.setattr(builder,'build',lambda run:{'fixture_only':True})
    assert assembler.assemble(tmp_path,scene_index_path=path)=={'fixture_only':True}
    review=json.loads((tmp_path/'review_gallery_input_v1.json').read_text(encoding='utf-8'))
    assert review['scenes']==data['scenes']
    assert review['scene_index_source']['sha256']==m.digest(path)


def test_assembler_default_scene_index_keeps_existing_behavior(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    from assemble_camera_alignment_review_v1 import scene_index
    import scene_path_relocation_v1 as relocation
    assert scene_index(tmp_path)==([],None)
    (tmp_path/'scenes').mkdir();path=tmp_path/'scenes/gallery_scene_index_v1.json';path.write_text('{}')
    calls=[]
    def old_builder(p):calls.append(p);return {'scenes':[{'fixture_only':True}]}
    monkeypatch.setattr(relocation,'build_current_index',old_builder)
    assert scene_index(tmp_path)==([{'fixture_only':True}],None) and calls==[path]


def test_cross_visual_risk_binds_media_and_keeps_outfit_scope(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    from assemble_camera_alignment_review_v1 import cross_visual_risks
    media=tmp_path/'media.json';media.write_text('{}')
    source=tmp_path/'legacy_cross_sex_visual_audit_v1.json'
    source.write_text(json.dumps({'schema':'legacy_cross_sex_visual_audit_v1','media_validation':{'path':'media.json','sha256':m.digest(media),'success':True},'risks':[{'shot_id':'cross','type':'outfit_pose_compatibility','message_zh':'短裙待审','recommendation_zh':'保留动作','time_seconds':.73,'frame':22}]}),encoding='utf-8')
    result,pin=cross_visual_risks(tmp_path,{'cross'})
    assert result['cross']['type']=='outfit_pose_compatibility'
    assert result['cross']['visual_acceptance']=='pending_not_passed'
    assert '保留动作' in result['cross']['message_zh'] and pin['sha256']==m.digest(source)
    media.write_text('changed')
    with pytest.raises(ValueError,match='proof changed'):cross_visual_risks(tmp_path,{'cross'})


def test_additional_camera_risk_source_keeps_original_and_stays_pending(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    from assemble_camera_alignment_review_v1 import visual_risks
    names=['smoke_visual_risks_for_review_v2.json','first_batch_visual_risks_for_review_v1.json']
    for name,sid in zip(names,['old','new']):
        (tmp_path/name).write_text(json.dumps({'schema':'camera_review_visual_risks_v1','automatic_visual_pass':False,'items':[risk(sid)]}),encoding='utf-8')
    old,old_pin=visual_risks(tmp_path,{'old','new'})
    new,new_pin=visual_risks(tmp_path,{'old','new'},names[1])
    assert set(old|new)=={'old','new'} and old_pin!=new_pin
    assert all(item['visual_acceptance']=='pending_not_passed' for item in (old|new).values())
    report=json.loads((tmp_path/names[1]).read_text());report['automatic_visual_pass']=True
    (tmp_path/names[1]).write_text(json.dumps(report))
    with pytest.raises(ValueError,match='automatically accepted'):visual_risks(tmp_path,{'old','new'},names[1])


def test_prior_reference_clock_sha_and_no_main_count_inflation(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    from legacy_original_reference_v1 import load_references
    root=tmp_path/'references/legacy_original';root.mkdir(parents=True)
    data=fixture_data(root);clip=data['clips'][0]
    clock=dict(source_start_seconds=0,source_end_seconds=1,source_body_play_rate=1,duration_seconds=1,fps=30,frame_count=30)
    candidate={'records':[{'motion_id':'dance','original_sex':'female','accepted_playback_contract':clock,'variants':{'female':{'review_video':{'shot_id':clip['id'],'video':{'sha256':clip['video_sha256']},'receipt':{'sha256':clip['verification_receipt_sha256']}}}}}]}
    cp=tmp_path/'candidate.json';cp.write_text(json.dumps(candidate))
    index={'schema':'legacy_original_review_references_v1','candidate':{'path':'candidate.json','sha256':m.digest(cp)},'references':[{'motion_id':'dance','sex':'female','playback_contract':clock,'clip':clip,'copied_files':[]}]}
    (root/'index_v1.json').write_text(json.dumps(index))
    cross={'motion_id':'dance','sex':'male','playback_contract':clock}
    refs,pending=load_references(tmp_path,[cross]);assert len(refs)==1 and not pending
    assert refs[0]['not_current_render'] and refs[0]['video'].startswith('references/legacy_original/')
    # A mismatch keeps the fallback pending; it must never make the main clip playable.
    cross['playback_contract']=dict(clock,source_start_seconds=.1)
    refs,pending=load_references(tmp_path,[cross]);assert not refs and len(pending)==1
    cross['playback_contract']=clock;(root/'clip.mp4').write_bytes(b'changed')
    refs,pending=load_references(tmp_path,[cross]);assert not refs and len(pending)==1
