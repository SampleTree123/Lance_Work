"""Three-frame static MRQ smoke in an owned scene copy, not a data batch."""
import unreal as u, importlib, json, hashlib
from pathlib import Path
import pair_scene_review_20261019_v1 as panel
import mrq_streaming_warmup_v1 as warmup
import ue_primary_scene_samples_v1 as samples
import ue_production_trial_render_v1 as trials
root=Path(__file__).resolve().parent
panel=importlib.reload(panel);warmup=importlib.reload(warmup);samples=importlib.reload(samples)
profile=panel.ensure_local_texture_budget(u)
c=getattr(u,panel.CACHE);w=c['worker'];d=w.synchronize()
if (d.get('playback') or {}).get('playing'):
    raise RuntimeError('Pause live review playback before smoke render')
sub=u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
if sub.is_rendering():raise RuntimeError('Another render is active')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
source=world.get_path_name().split('.')[0]
camera=d.get('camera')
if not camera:raise RuntimeError('Current review camera required')
sourcefile=Path('D:/UE/projects/datatry_02/Content')/(source.removeprefix('/Game/')+'.umap')
before={'source_map':source,'source_map_sha256':hashlib.sha256(sourcefile.read_bytes()).hexdigest(),
    'site':d.get('site'),'preview':d.get('preview'),'appearance_selection':d.get('appearance_selection'),
    'pool_before':u.SystemLibrary.get_console_variable_int_value('r.Streaming.PoolSize'),
    'local_profile':profile}
(root/'smoke_before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
base='/Game/DataMake/Validation/RenderReadiness20261021'
dest=base+'/SceneTrials/L_ReadinessSmoke'
seqpath=base+'/SceneTrials/LS_ReadinessSmoke'
if u.EditorAssetLibrary.does_asset_exist(dest) or u.EditorAssetLibrary.does_asset_exist(seqpath):
    raise RuntimeError('Owned smoke assets already exist; inspect previous outcome')
copied=u.EditorAssetLibrary.duplicate_asset(source,dest)
if not isinstance(copied,u.World):raise RuntimeError('Scene copy failed')
if not u.EditorAssetLibrary.save_loaded_asset(copied,False):raise RuntimeError('Scene copy save failed')
seq=u.AssetToolsHelpers.get_asset_tools().create_asset(
    seqpath.rsplit('/',1)[-1],seqpath.rsplit('/',1)[0],u.LevelSequence,u.LevelSequenceFactoryNew())
seq.set_display_rate(u.FrameRate(30,1));seq.set_tick_resolution_directly(u.FrameRate(24000,1))
seq.set_playback_start(0);seq.set_playback_end(3)
binding=seq.add_spawnable_from_instance(camera)
cut=seq.add_track(u.MovieSceneCameraCutTrack).add_section()
cut.set_range(0,3);cut.set_camera_binding_id(seq.get_binding_id(binding))
if not u.EditorAssetLibrary.save_loaded_asset(seq,False):raise RuntimeError('Smoke sequence save failed')
renderer=trials.module('ue_motion_scene_render_v1')
renderer.RUN=root;renderer.ASSET_ROOT=base;renderer.LIVE_ATTRIBUTE='_dm_render_readiness_smoke_20261021'
samples.sample_renderer(renderer)
setattr(u,'_dm_readiness_renderer_20261021',renderer)
result=renderer.start_render(u,[{'shot_id':'readiness_3frames','map':dest,'sequence':seqpath}],
    'readiness_smoke_v1',width=512,height=288)
print(json.dumps({'submitted':True,'receipt_path':result['receipt_path'],
    'scene_source_unchanged':hashlib.sha256(sourcefile.read_bytes()).hexdigest()==before['source_map_sha256'],
    'frames':3,'width':512,'height':288}))
