"""Fresh-instance import bootstrap for the frozen load-only AF005 recovery.

Experimental Assembly Technical. The v1 import failure ran no LoadFile call.
"""
import importlib.util
from pathlib import Path
import sys


def run(library, output_dir, log, api):
    directory = Path(__file__).resolve().parent
    path = directory / 'cc_load_refresh_editing_checkpoint_v1.py'
    if api.sha256_file(str(path)) != 'a87f33868838fd63d3c1c6322de8b100619a51228672b17401dc42f4a7146aee':
        raise ValueError('Frozen load-only implementation changed')
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    spec = importlib.util.spec_from_file_location('_fresh_instance_af005_loader', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(library, output_dir, log, api)
