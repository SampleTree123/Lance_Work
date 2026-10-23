

# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_disable_scalp_hair_shadows_v2.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

import unreal
names={'BundlePart01','BundlePart02','BundlePart03','BundlePart04'}
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if a.get_actor_label() not in ('DM_ScalpHairReview_M02_Average','DM_ScalpHairReview_F02_Average'):
        continue
    for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.get_name() in names and c.get_editor_property('skeletal_mesh'):
            c.set_editor_property('cast_shadow', False)
            print(a.get_actor_label(), c.get_name(), c.get_editor_property('cast_shadow'))
unreal.EditorLevelLibrary.save_current_level()

