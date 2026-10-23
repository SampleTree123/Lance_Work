"""Bounded texture A/B on existing owned captures; no source or prepared asset writes."""
import importlib
import json
from pathlib import Path
import time
import uuid

LIVE='_dm_dataset_texture_probe_v1'

def dispatch(request):
    import unreal as u
    import ue_dataset_render_v11 as main
    importlib.reload(main)
    run=Path(request['run_root'])
    renderer=main.renderer(u,run)
    renderer.LIVE_ATTRIBUTE=LIVE
    if request['action']=='status': return renderer.status(u)
    if request['action']=='verify_materials':
        prepared=main.read(Path(request['source_run'])/'jobs'/request['job_id']/'prepared.json')
        levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
        other=main.read(Path(request['other_prepared']))['job']['map']
        for path in [other,prepared['job']['map']]:
            if not path.startswith(main.ASSETS+'/'):raise ValueError('Only owned capture maps')
            if not levels.load_level(path.split('.')[0]):raise RuntimeError('Cannot reload saved capture')
        actual={}
        for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
            if actor.get_actor_label()!='DM_SiteReview_Dataset_Character':continue
            for c in actor.get_components_by_class(u.SkeletalMeshComponent):
                for i in range(c.get_num_materials()):
                    m=c.get_material(i)
                    if m:actual[(c.get_name(),i)]=m.get_path_name()
        checks=[]
        for binding in prepared['persistent_materials']['bindings']:
            key=(binding['component'].rsplit('.',1)[-1],binding['material_index'])
            checks.append({'component':key[0],'slot':key[1],'expected':binding['material'],'actual':actual.get(key),'match':actual.get(key)==binding['material']})
        result={'success':bool(checks) and all(c['match'] for c in checks),'checks':checks,'source_maps_modified':False}
        main.write(run/'MATERIAL_RELOAD_CHECK.json',result)
        return result
    if request['action']=='evict':
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        u.SystemLibrary.execute_console_command(world,'StreamOut 4096')
        return {'success':True,'scope':'temporary streaming cache eviction only; no asset writes'}
    if request['action']=='prepare_reference':
        import ue_dataset_reference_pilot_v11 as ref
        importlib.reload(ref)
        fixture=Path(request['fixture_run'])
        job=next(j for j in main.read(fixture/'reference_pilot_jobs.json')['jobs'] if j['job_id']==request['job_id'])
        return ref.prepare(u,fixture,job)
    if request['action']!='render':raise ValueError('Only status/render')
    source=Path(request['source_run']); jid=request['job_id']
    prepared=main.read(source/'jobs'/jid/'prepared.json')
    manifest='reference_pilot_jobs.json' if jid.startswith('ref_') else 'main_jobs.json'
    job=next(j for j in main.read(source/manifest)['jobs'] if j['job_id']==jid)
    mode=request['texture_mode']
    if mode not in ('inherit','fully_load','disabled'):raise ValueError(mode)
    renderer=main.renderer(u,run,job,10240); renderer.LIVE_ATTRIBUTE=LIVE
    original=renderer.persist
    def persist(state):
        original(state)
        if state['receipt']['status']=='submitted' and not state.get('texture_probe_configured'):
            for qj in state['queue'].get_jobs():
                game=qj.get_configuration().find_or_add_setting_by_class(u.MoviePipelineGameOverrideSetting)
                method={'inherit':u.MoviePipelineTextureStreamingMethod.NONE,
                        'fully_load':u.MoviePipelineTextureStreamingMethod.FULLY_LOAD,
                        'disabled':u.MoviePipelineTextureStreamingMethod.DISABLED}[mode]
                game.set_editor_property('texture_streaming',method)
            state['receipt']['texture_probe']={'mode':mode,'method':str(method),'same_saved_map_and_sequence':prepared['job'],
                'scope':'texture loading only; no resolution, camera, lighting, AA or LOD changes'}
            state['texture_probe_configured']=True
            original(state)
    renderer.persist=persist
    # Sample the actual PIE world late in engine warmup rather than the editor viewport.
    tick_state={'count':0,'handle':None,'start':time.monotonic()}
    def inspect(delta):
        try:
            world=u.EditorLevelLibrary.get_game_world()
            if world:
                tick_state['count']+=1
                if tick_state['count']==100:
                    values={name:u.SystemLibrary.get_console_variable_int_value(name) for name in
                        ['r.TextureStreaming','r.Streaming.FullyLoadUsedTextures','r.Streaming.UseAllMips','r.Streaming.MipBias','r.Streaming.PoolSize','sg.TextureQuality']}
                    main.write(run/'texture_runtime.json',{'world':world.get_path_name(),'tick':100,'cvars':values,'mode':mode})
                    u.log('DM_TEXTURE_PROBE_BEGIN '+str(run))
                    u.SystemLibrary.execute_console_command(world,'ListTextures -csv -alphasort')
                    u.log('DM_TEXTURE_PROBE_END '+str(run))
                    u.unregister_slate_pre_tick_callback(tick_state['handle'])
                    return
            if time.monotonic()-tick_state['start']>120:
                u.unregister_slate_pre_tick_callback(tick_state['handle'])
        except Exception as exc:
            main.write(run/'texture_runtime_error.json',{'error':str(exc)})
            u.unregister_slate_pre_tick_callback(tick_state['handle'])
    tick_state['handle']=u.register_slate_pre_tick_callback(inspect)
    setattr(u,LIVE+'_probe',(inspect,tick_state))
    return renderer.start_render(u,[prepared['job']],jid+'_'+uuid.uuid4().hex[:8],width=job['width'],height=job['height'])
