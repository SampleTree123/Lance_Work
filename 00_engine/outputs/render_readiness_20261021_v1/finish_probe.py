import unreal as u,json,hashlib
from pathlib import Path
import pair_scene_review_20261019_v1 as panel
root=Path(__file__).resolve().parent
before=json.loads((root/'smoke_before.json').read_text(encoding='utf-8'))
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
c=getattr(u,panel.CACHE);d=c['worker'].synchronize()
sourcefile=Path('D:/UE/projects/datatry_02/Content')/(before['source_map'].removeprefix('/Game/')+'.umap')
def mats(world):
    out=[]
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if not a.get_actor_label().startswith('DM_SiteReview_'):continue
        for comp in a.get_components_by_class(u.SkeletalMeshComponent):
            mesh=comp.get_skinned_asset()
            if not mesh:continue
            out.append({'actor':a.get_actor_label(),'component':comp.get_name(),'mesh':mesh.get_path_name(),
                'materials':[m.get_path_name() if m else None for m in comp.get_materials()]})
    return out
copied=u.load_asset('/Game/DataMake/Validation/RenderReadiness20261021/SceneTrials/L_ReadinessSmoke')
volumes=[{'path':a.get_path_name(),'enabled':a.get_editor_property('enabled'),
          'unbound':a.get_editor_property('unbound'),'priority':a.get_editor_property('priority'),
          'settings':a.get_editor_property('settings').export_text()}
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.PostProcessVolume)]
result={'map':world.get_path_name(),'source_map_unchanged':hashlib.sha256(sourcefile.read_bytes()).hexdigest()==before['source_map_sha256'],
    'site_unchanged':d.get('site')==before['site'],'preview_unchanged':d.get('preview')==before['preview'],
    'appearance_unchanged':d.get('appearance_selection')==before['appearance_selection'],
    'post_process_volumes_unchanged':volumes==json.loads((root/'scene_postprocess_before.json').read_text(encoding='utf-8')),
    'pool_after':u.SystemLibrary.get_console_variable_int_value('r.Streaming.PoolSize'),
    'live_materials':mats(world),'copied_materials':mats(copied),
    'renderer_status':getattr(u,'_dm_readiness_renderer_20261021').status(u)}
(root/'finish_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('live_materials','copied_materials','renderer_status')},ensure_ascii=False))
