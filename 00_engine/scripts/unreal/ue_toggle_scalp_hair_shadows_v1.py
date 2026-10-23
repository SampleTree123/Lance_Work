

# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_toggle_scalp_hair_shadows_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

import unreal

level = unreal.EditorLevelLibrary.get_editor_world()
rows=[]
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if actor.get_actor_label() not in ('DM_ScalpHairReview_M02_Average','DM_ScalpHairReview_F02_Average'):
        continue
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if not comp.get_name().startswith('BundlePart'):
            continue
        if comp.get_editor_property('skeletal_mesh'):
            before=comp.get_editor_property('cast_shadow')
            comp.set_editor_property('cast_shadow', False)
            try: comp.set_editor_property('cast_dynamic_shadow', False)
            except Exception: pass
            rows.append({'actor':actor.get_actor_label(),'component':comp.get_name(),'before':before,'after':False})
unreal.EditorLevelLibrary.save_current_level()
print('SAVED', level.get_path_name() if level else None)
for r in rows: print('ROW', r)

