"""Copy one newly prepared Japanese v4/v5 sequence, add camera-only -16..0 hold.

No UE connection on import. Caller owns UE. Never modifies input map/sequence.
Use returned job with camera_cut_warmup_shot_ids=[job['shot_id']] in renderer.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT='/Game/DataMake/Validation/MotionPortraitScenePilot20261011/SceneTrials/'
RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1')
CONTENT=Path('D:/UE/projects/datatry_02/Content')

def _file(asset,extension='.uasset'):
    return CONTENT/(asset.split('.')[0].removeprefix('/Game/')+extension)

def _pin(p):
    return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def _keys(u,channel):
    out=[]
    for k in channel.get_keys():
        t=k.get_time(time_unit=u.MovieSceneTimeUnit.DISPLAY_RATE)
        out.append({'frame':int(t.frame_number.value),'sub_frame':float(t.sub_frame),'value':float(k.get_value()),'interpolation':str(k.get_interpolation_mode())})
    return sorted(out,key=lambda x:(x['frame'],x['sub_frame']))

def _inventory(u,sequence):
    cameras=[];animations=[]
    for b in sequence.get_bindings():
        for track in b.get_tracks():
            for section in track.get_sections():
                if isinstance(track,u.MovieSceneSkeletalAnimationTrack):
                    p=section.get_editor_property('params');a=p.get_editor_property('animation')
                    row={'component':str(b.get_display_name()),'start':section.get_start_frame(),'end':section.get_end_frame(),'animation':a.get_path_name(),'rate_scale':float(a.get_editor_property('rate_scale')),'play_rate':float(u.MovieSceneTimeWarpExtensions.to_fixed_play_rate(p.get_editor_property('play_rate')))}
                    for name in ['reverse','force_custom_mode']:
                        row[name]=bool(p.get_editor_property(name))
                    for name in ['start_frame_offset','end_frame_offset','first_loop_start_frame_offset']:
                        row[name]=int(p.get_editor_property(name).value)
                    animations.append(row)
                elif isinstance(track,(u.MovieScene3DTransformTrack,u.MovieSceneFloatTrack)):
                    cameras.append((str(b.get_display_name()),track,section))
                else:
                    raise ValueError('Unexpected bound track: '+track.get_class().get_name())
    return cameras,sorted(animations,key=lambda x:x['component'])

def create(u,job):
    if set(job)!={'shot_id','map','sequence'}:raise ValueError('Expected exact prepared job')
    source=job['sequence'].split('.')[0];map_path=job['map'].split('.')[0]
    # Keep historical v4 explicitly allowed, plus the authorized v5 replacement.
    # Require the same shot identity in map/sequence; never mix revisions or owners.
    if not re.fullmatch(r'scene_japanese_village_v(?:4|5)_[A-Za-z0-9_]+',job['shot_id']):
        raise ValueError('Only new Japanese v4/v5 trial inputs are allowed')
    if source!=ROOT+'LS_'+job['shot_id'] or map_path!=ROOT+'L_'+job['shot_id']:
        raise ValueError('Map and sequence must exactly match the Japanese trial shot')
    if job['sequence'] not in (source,source+'.'+source.rsplit('/',1)[1]) or job['map'] not in (map_path,map_path+'.'+map_path.rsplit('/',1)[1]):
        raise ValueError('Unexpected object path suffix')
    if not re.fullmatch(r'/[A-Za-z0-9_/]+',source):raise ValueError('Bad package path')
    target=source+'_preroll16_v1'
    report=RUN/'scene_sequences'/(job['shot_id']+'_preroll16_v1.json')
    if u.EditorAssetLibrary.does_asset_exist(target) or report.exists():raise ValueError('Refusing overwrite')
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    if dirty:raise ValueError('Save or resolve dirty packages before isolated preroll copy')
    pins=[_pin(_file(source)),_pin(_file(map_path,'.umap'))]
    original=u.load_asset(source);assert isinstance(original,u.LevelSequence)
    assert original.get_playback_start()==0 and original.get_playback_end()==300
    rate=original.get_display_rate();assert (rate.numerator,rate.denominator)==(30,1)
    original_cam,original_anim=_inventory(u,original);assert len(original_anim)==6 and len(original_cam)==2
    originals=[]
    for binding,track,section in original_cam:
        assert section.get_start_frame()==0 and section.get_end_frame()==301
        originals.append([_keys(u,c) for c in section.get_all_channels()])
    assert sorted(len(x) for x in originals)==[1,9]
    for channels in originals:
        for keys in channels:assert [k['frame'] for k in keys]==list(range(301)) and all(k['sub_frame']==0 for k in keys)
    seq=u.EditorAssetLibrary.duplicate_asset(source,target);assert isinstance(seq,u.LevelSequence)
    cams,animations=_inventory(u,seq);assert animations==original_anim
    for (_,track,section),before in zip(cams,originals):
        channels=list(section.get_all_channels());assert [_keys(u,c) for c in channels]==before
        section.set_start_frame(-16)
        for c,keys in zip(channels,before):
            c.add_key(u.FrameNumber(-16),keys[0]['value'],sub_frame=0.,time_unit=u.MovieSceneTimeUnit.DISPLAY_RATE,interpolation=u.MovieSceneKeyInterpolation.CONSTANT)
    cuts=[s for t in seq.get_tracks() if isinstance(t,u.MovieSceneCameraCutTrack) for s in t.get_sections()]
    assert len(cuts)==1 and cuts[0].get_start_frame()==0 and cuts[0].get_end_frame()==300
    cuts[0].set_start_frame(-16)
    assert u.EditorAssetLibrary.save_loaded_asset(seq,only_if_is_dirty=False)
    cams,animations=_inventory(u,seq);assert animations==original_anim
    for (_,track,section),before in zip(cams,originals):
        assert section.get_start_frame()==-16 and section.get_end_frame()==301
        for c,keys in zip(section.get_all_channels(),before):
            after=_keys(u,c);assert len(after)==302 and after[1:]==keys
            assert after[0]['frame']==-16 and after[0]['sub_frame']==0 and after[0]['value']==keys[0]['value'] and 'CONSTANT' in after[0]['interpolation']
    assert seq.get_playback_start()==0 and seq.get_playback_end()==300
    for p in pins:assert _pin(Path(p['path']))==p
    result={'shot_id':job['shot_id'],'map':job['map'],'sequence':seq.get_path_name()}
    payload={'success':True,'job':result,'source_job':job,'source_pins':pins,'target_pin':_pin(_file(target)),'preroll_start_frame':-16,'playback_range':[0,300],'camera_original_key_rows_unchanged':True,'camera_added_constant_keys':10,'body_face_sections_unchanged':animations,'source_packages_unchanged':True,'render_requires_camera_cut_warmup_shot_ids':[job['shot_id']],'runtime_visual_acceptance':'pending','helper_pin':_pin(Path(__file__))}
    report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
