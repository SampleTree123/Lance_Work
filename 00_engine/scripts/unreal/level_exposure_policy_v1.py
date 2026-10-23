"""Let saved level post-process volumes own exposure in preview and rendering."""

POLICY = 'inherit_saved_level_exposure_v1'
OVERRIDES = (
    'override_auto_exposure_method',
    'override_auto_exposure_bias',
    'override_auto_exposure_bias_curve',
    'override_auto_exposure_meter_mask',
    'override_auto_exposure_apply_physical_camera_exposure',
    'override_auto_exposure_low_percent',
    'override_auto_exposure_high_percent',
    'override_auto_exposure_min_brightness',
    'override_auto_exposure_max_brightness',
    'override_auto_exposure_speed_up',
    'override_auto_exposure_speed_down',
    'override_histogram_log_min',
    'override_histogram_log_max',
    'override_camera_iso',
    'override_camera_shutter_speed',
)


def apply(component):
    settings = component.get_editor_property('post_process_settings')
    for key in OVERRIDES:
        settings.set_editor_property(key, False)
    component.set_editor_property('post_process_settings', settings)
    return {'policy':POLICY, 'camera_override':False,
            'scene_settings_unchanged':True, 'legacy_point_compensation_ignored':True}
