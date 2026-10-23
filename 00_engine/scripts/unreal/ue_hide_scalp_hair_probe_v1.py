

# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_hide_scalp_hair_probe_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

import unreal

level = unreal.EditorLevelLibrary.get_editor_world()
rows=[]
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if actor.get_actor_label() not in ('DM_ScalpHairReview_M02_Average','DM_ScalpHairReview_F02_Average'):
        continue
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        mesh = comp.get_editor_property('skeletal_mesh')
        if mesh and 'ScalpHairPilot' in mesh.get_path_name():
            before = comp.is_visible()
            comp.set_visibility(False, True)
            rows.append({'actor': actor.get_actor_label(), 'component': comp.get_name(), 'before_visible': before, 'after_visible': False, 'mesh': mesh.get_path_name()})
unreal.EditorLevelLibrary.save_current_level()
print('SAVED_HAIR_HIDDEN', level.get_path_name() if level else None)
for row in rows:
    print('ROW', row)

