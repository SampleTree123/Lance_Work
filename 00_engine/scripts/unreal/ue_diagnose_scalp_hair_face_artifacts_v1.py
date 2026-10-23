import unreal

actors = unreal.EditorLevelLibrary.get_all_level_actors()
for actor in actors:
    if actor.get_actor_label() not in ('DM_ScalpHairReview_F02_Average', 'DM_ScalpHairReview_M02_Average'):
        continue
    print('ACTOR', actor.get_actor_label())
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        mesh = comp.get_editor_property('skeletal_mesh')
        mesh_path = mesh.get_path_name() if mesh else None
        mats = []
        for i in range(comp.get_num_materials()):
            mat = comp.get_material(i)
            if mat:
                parent = None
                try:
                    parent = mat.get_editor_property('parent')
                except Exception:
                    pass
                mats.append({'slot': i, 'path': mat.get_path_name(), 'parent': parent.get_path_name() if parent else None})
        leader = None
        try:
            leader = comp.get_editor_property('leader_pose_component')
        except Exception:
            pass
        rec = {
            'name': comp.get_name(),
            'visible': comp.is_visible(),
            'mesh': mesh_path,
            'materials': mats,
            'leader': leader.get_name() if leader else None,
        }
        for prop in ('cast_shadow', 'cast_dynamic_shadow', 'cast_hidden_shadow', 'visible_in_ray_tracing', 'render_in_main_pass', 'receives_decals', 'render_custom_depth'):
            try:
                rec[prop] = comp.get_editor_property(prop)
            except Exception:
                pass
        print('COMP', rec)
