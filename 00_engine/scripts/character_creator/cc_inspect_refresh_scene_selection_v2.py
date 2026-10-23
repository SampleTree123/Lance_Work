"""Read-only native row inventory; retain opaque RLHANDLE roles as unreadable.

Experimental Assembly Technical. The v1 failed receipt is preserved unchanged.
"""
from pathlib import Path


def run(library, output_dir, log, api):
    path = Path(__file__).with_name('cc_inspect_refresh_scene_selection_v1.py')
    if api.sha256_file(str(path)) != '51b8388b0facce87a95a0401421029f32a85c95e91e8dca5eae5b67662433591':
        raise ValueError('Frozen read-only scene inventory v1 changed')
    source = path.read_text(encoding='utf-8-sig')
    anchor = '                    value = item.data(column, role)\n'
    if source.count(anchor) != 1:
        raise ValueError('Frozen tree role anchor changed')
    source = source.replace(anchor, '''                    try:
                        value = item.data(column, role)
                    except Exception as error:
                        cell['user_roles'][str(role)] = dict(read_error=str(error), opaque_value_not_interpreted=True)
                        continue
''', 1)
    source = source.replace("('GetVisible', 'IsVisible', 'IsLocked', 'GetLock')", "('GetVisible', 'IsVisible', 'IsLocked', 'GetLock', 'GetAvatarType', 'GetType')", 1)
    source = source.replace('row[name] = simple(getter())', "row[name] = simple(getter(api.RLPy.RGlobal.GetTime()) if name == 'IsVisible' else getter())", 1)
    namespace = dict(__file__=str(path), __name__='_readonly_scene_selection_v2_private')
    exec(compile(source, str(path), 'exec'), namespace)
    return namespace['run'](library, output_dir, log, api)
