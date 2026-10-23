"""AF005 v3 entry with the actual recorded enable-flag list representation.

The v3 pre-Load failure is preserved. No operational or numerical gate changes.
"""
from pathlib import Path


def run(library, output_dir, log, api):
    path = Path(__file__).with_name('cc_repair_refresh_editing_checkpoint_v3.py')
    if api.sha256_file(str(path)) != 'eea834e4e1c7bc4e5546e4c6be056ebcc06ef4864ded58104a951340a76008e0':
        raise ValueError('Frozen bounded-entry implementation changed')
    source = path.read_text(encoding='utf-8-sig')
    old = "'row_enable_flags_uninterpreted': False"
    new = "'row_enable_flags_uninterpreted': [{'isChecked': False, 'object_name': 'qtEnableToolButton'}]"
    if source.count(old) != 1:
        raise ValueError('Actual enable-flag representation correction anchor changed')
    namespace = dict(__file__=__file__, __name__='_af005_bounded_entry_actual_flags_private')
    exec(compile(source.replace(old, new, 1), str(path), 'exec'), namespace)
    return namespace['run'](library, output_dir, log, api)
