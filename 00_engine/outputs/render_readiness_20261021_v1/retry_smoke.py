import unreal as u,json,time,importlib
import mrq_streaming_warmup_v1
importlib.reload(mrq_streaming_warmup_v1)
from pathlib import Path
root=Path(__file__).resolve().parent
samples=[]
started=time.monotonic()
def tick(delta):
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    now=time.monotonic()
    if now-started>180 or (samples and not world):
        u.unregister_slate_post_tick_callback(getattr(u,'_dm_readiness_probe_tick'))
        return
    if not world or (samples and now-samples[-1]['time']<.4):return
    row={'time':now,'world':world.get_path_name(),'cvars':{}}
    for key in ['r.Streaming.PoolSize','r.Streaming.MipBias','r.Streaming.UsePerTextureBias','r.Streaming.Boost',
                'r.Streaming.LimitPoolSizeToVRAM','r.Streaming.FramesForFullUpdate','r.SkeletalMeshLODBias','sg.TextureQuality']:
        row['cvars'][key]=u.SystemLibrary.get_console_variable_float_value(key)
    row['components']=[]
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if not a.get_actor_label().startswith('DM_SiteReview_'):continue
        for comp in a.get_components_by_class(u.SkeletalMeshComponent):
            if comp.get_name() not in ['FullBody','Body']:continue
            row['components'].append({'name':comp.get_name(),'forced_lod':comp.get_editor_property('forced_lod_model'),
                'materials':[m.get_path_name() if m else None for m in comp.get_materials()]})
    samples.append(row)
    (root/'streaming_tick_budget10240.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
    if len(samples) in (1,5):
        u.SystemLibrary.execute_console_command(world,'DumpTextureStreamingStats')
        u.SystemLibrary.execute_console_command(world,'InvestigateTexture defaultMat')
setattr(u,'_dm_readiness_probe_callback',tick)
setattr(u,'_dm_readiness_probe_tick',u.register_slate_post_tick_callback(tick))
r=getattr(u,'_dm_readiness_renderer_20261021')
base='/Game/DataMake/Validation/RenderReadiness20261021/SceneTrials/'
print(r.start_render(u,[{'shot_id':'readiness_3frames','map':base+'L_ReadinessSmoke','sequence':base+'LS_ReadinessSmoke'}],
    'readiness_budget10240_v1',width=1024,height=576))
