"""Session-local fast interaction for the two-person review panel.

Assets are loaded on demand; source hashing and repeated acceptance audits are
disabled by explicit user request. Restart UE after changing source assets.
Intentional occlusion checks and their scene snapshot remain available.
"""
import copy
import json
import uuid
import importlib.util

VERSION = 1


def bind_catalog(contract):
    """Read the published lookup table, without rehashing all content on launch."""
    spec = importlib.util.spec_from_file_location('_pair_fast_catalog_' + uuid.uuid4().hex,
                                                 contract.FORMAL_HELPER)
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    pointer = loader.read(contract.FORMAL_POINTER)['catalog']
    document = loader.read(pointer['path'])
    loader.load = lambda: copy.deepcopy(document)
    domain = loader.appearance_contract()
    contract.formal_runtime = lambda: (loader, domain)
    return loader, domain


def configuration(revision):
    """Use the completed two-person import manifest, no source/package audit."""
    delivery = revision._read(revision.DELIVERY)
    members, pins = {}, [revision._pin(revision.DELIVERY)]
    for case in delivery['cases']:
        audit = revision._read(case['audit'])
        members[case['character_id']] = revision._validate_case(case, audit)
        pins.append(revision._pin(case['audit']))
    return {'schema': 'pair_revision_runtime_20261019_v1', 'ue_root': revision.UE_ROOT,
            'members': members, 'pins': pins, 'inputs': [], 'stamps': {},
            'asset_validation': False}


def disable_startup_asset_audits(graph):
    # Only this review's isolated graph; production publishers/renderers retain
    # their original policy. Missing files still fail at actual load/read.
    graph.load('production_motion_contract_v1').verify_pin = lambda record: None
    # The inherited point geometry is only a bootstrap for the current mode.
    # Its frozen provenance predates later sequence changes; do not relabel it
    # or re-run that historical audit on every review-only editor restart.
    graph.load('scene_site_review_geometry_v1').verify_sources = lambda records: None


def prepare_key(selection, motion_path, action, overlay):
    value = {k: v for k, v in selection.items() if k not in ('hair_color', 'eye_color', 'sources')}
    return json.dumps([value, motion_path, action, overlay or {}], sort_keys=True)


def install(current):
    if current.get('fast_version') == VERSION:
        install_session_updates(current)
        return current
    w, a, graph = current['worker'], current['assembly'], current['graph']
    u = w.u
    formal = a.contract.formal_runtime()
    if formal:
        loader, domain = formal
        loaded = loader.load()
        loader.load = lambda *args, **kwargs: loaded
        a.contract.formal_runtime = lambda: formal
        # Catalog identity and registry are fixed for this inspection session.
        for obj, name in ((domain.identities, 'identity_catalog'), (domain.slots, '_registry'),
                          (loader, 'accepted_faces')):
            original = getattr(obj, name)
            cache = {}
            def once(*args, _original=original, _cache=cache, **kwargs):
                if 'value' not in _cache:
                    _cache['value'] = _original(*args, **kwargs)
                return _cache['value']
            setattr(obj, name, once)

    names, compatibility = {}, {}
    def bone_names(mesh):
        key = mesh.get_path_name()
        if key not in names:
            reader = u.SkeletonModifier()
            if not reader.set_skeletal_mesh(mesh):
                raise RuntimeError('无法读取部件骨骼：' + key)
            names[key] = {str(n) for n in reader.get_all_bone_names()}
        return names[key]

    def follow_mode(body, follower):
        key = (body.get_path_name(), follower.get_path_name())
        if key not in compatibility:
            # This selects the existing leader/copy-pose binding, not a fit audit.
            extra = sorted(bone_names(follower) - bone_names(body))
            compatibility[key] = {'follow_mode': 'copy_pose' if extra else 'leader_pose',
                                  'extra_reference_bones': extra,
                                  'scope': 'review_binding_only_no_compatibility_validation'}
        return compatibility[key]
    a.review.compatibility = follow_mode

    import pair_review_face_fast_v1 as face_fast
    face_fast.install(a)
    import pair_review_material_fast_v1 as material_fast
    material_fast.install(graph, u)

    original_prepare, prepared = a.prepare, {}
    def prepare(api, selection, motion, *, body_action_id=None, data=None, path_overlay=None):
        key = prepare_key(selection, a.fixed.object_path(motion), body_action_id, path_overlay)
        if key not in prepared:
            body_selection = dict(selection, face_id='none')
            result = original_prepare(api, body_selection, motion, body_action_id=body_action_id,
                                      data=data, path_overlay=path_overlay)
            result['motion'], result['face'] = face_fast.resolve(
                api, a, selection, motion, body_action_id, data=data, path_overlay=path_overlay)
            prepared[key] = result
        return dict(prepared[key], selection=copy.deepcopy(selection))
    a.prepare = prepare

    session = uuid.uuid4().hex
    scene_cache, catalog_cache = {}, {}
    original_scene, original_catalog = w.scene_signature, w.catalog
    def scene_signature():
        map_path = w.current_map()
        if map_path not in scene_cache:
            scene_cache[map_path] = original_scene()
        return scene_cache[map_path]
    w.scene_signature = scene_signature
    w.input_status = lambda force=False: {
        'valid': True, 'changed_files': [], 'signature': 'review_unchecked_' + session,
        'validation_performed': False, 'policy': 'user_requested_no_repeated_input_validation'}

    def catalog():
        mode = w.live().get('source_mode')
        if mode not in catalog_cache:
            catalog_cache[mode] = original_catalog()
        return catalog_cache[mode]
    w.catalog = catalog
    original_dispatch = w.dispatch
    def dispatch(request):
        action = request.get('action')
        # Explicit spatial checks keep their functionality; ordinary browsing
        # does not scan the entire map or filesystem after every click.
        if action in {'check_start', 'check_all', 'save_site', 'open_scene', 'load_site', 'restore'}:
            scene_cache.clear()
        if action in {'save_site', 'load_site', 'create_site', 'open_scene', 'restore', 'catalog'}:
            catalog_cache.clear()
        result = original_dispatch(request)
        if 'state' in result:
            result['state']['asset_validation_mode'] = 'disabled_for_fast_review'
        result['fast_review'] = {'version': VERSION, 'asset_validation': False}
        return result
    w.dispatch = dispatch
    d = w.live()
    # Old reports were tied to the previous strict input signature.
    d['report'] = None
    current.update(fast_version=VERSION, fast_caches={'prepared': prepared, 'bones': names,
                   'compatibility': compatibility, 'catalog': catalog_cache, 'scene': scene_cache})
    install_session_updates(current)
    return current


def install_session_updates(current):
    """Also applied to an already-open worker without destroying its scene."""
    if current.get('fast_session_updates'):
        return
    w, a = current['worker'], current['assembly']
    # Cold face generation needs the same pair catalog and mesh relocation as
    # ordinary preparation. Bind them for callers retained by an open session.
    old_prepare = a._pair_fast_faces['prepare']
    def cold_prepare(api, selection, motion, **kwargs):
        if kwargs.get('data') is None:
            kwargs['data'] = current['data']
        if kwargs.get('path_overlay') is None:
            kwargs['path_overlay'] = {
                **w.live().get('asset_path_overlay', {}),
                **a._pair_revision_runtime['overlays'][selection['character_id']]}
        return old_prepare(api, selection, motion, **kwargs)
    a._pair_fast_faces['prepare'] = cold_prepare
    directory = current['graph'].load('scene_site_catalog_v1')
    old_directory = directory.build_catalog
    directory_cache = {}
    def directory_catalog(*args, **kwargs):
        key = repr((args, sorted(kwargs.items())))
        if key not in directory_cache:
            directory_cache[key] = old_directory(*args, **kwargs)
        return copy.deepcopy(directory_cache[key])
    directory.build_catalog = directory_catalog
    original_dispatch = w.dispatch
    def dispatch(request):
        action = request.get('action')
        if action in {'save_site', 'create_site', 'load_site', 'open_scene', 'restore', 'catalog'}:
            directory_cache.clear()
        d = w.live()
        selection = request.get('appearance_selection') or request.get('payload', {}).get('appearance_selection')
        if selection and selection.get('sex') != d.get('sex') and d.get('character'):
            # Release attached lashes while their leader still has a live bone
            # buffer, before the existing preview code destroys the old actor.
            current['revision'].clear(a, d['character'])
        return original_dispatch(request)
    w.dispatch = dispatch
    current['fast_session_updates'] = True
