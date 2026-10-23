"""Import new full native performances into the isolated five-second experiment."""
import importlib.util
import json
from pathlib import Path

RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/native_face_five_second_20261008_v1')
ASSET_ROOT='/Game/DataMake/Validation/NativeFaceFiveSecond20261008/Sources'

def run(task):
    path=Path(__file__).with_name('ue_import_native_face_clip_v1.py')
    spec=importlib.util.spec_from_file_location('_nf5s_import',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RUN=RUN
    module.ASSET_ROOT=ASSET_ROOT
    return module.run(task)

if __name__=='__main__':
    run(json.loads(Path(globals()['DM_NATIVE_FACE_IMPORT_TASK']).read_text(encoding='utf-8')))
