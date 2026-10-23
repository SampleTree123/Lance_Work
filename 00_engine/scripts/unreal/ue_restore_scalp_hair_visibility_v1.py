

# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_restore_scalp_hair_visibility_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

import unreal
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    if actor.get_actor_label() not in ('DM_ScalpHairReview_M02_Average','DM_ScalpHairReview_F02_Average'):
        continue
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        mesh=comp.get_editor_property('skeletal_mesh')
        if mesh and 'ScalpHairPilot' in mesh.get_path_name():
            comp.set_visibility(True, True)
            print(actor.get_actor_label(), comp.get_name(), comp.is_visible())
unreal.EditorLevelLibrary.save_current_level()
print('HAIR_VISIBLE_RESTORED')

