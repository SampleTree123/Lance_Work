"""Run the bounded complete-character UE pilot using the existing editor.

No CC operation or export. --launch starts an editor only if none is available.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path

from run_fixed_head_hair_v1 import launch, remote

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[2]
RUN = REPO / '00_engine/outputs/unreal_character_import/complete_character_skeleton_pilot_20261005_v1'
MANIFEST = RUN / 'complete_character_import_manifest_v1.json'
LEVEL = '/Game/DataMake/Validation/CompleteCharacterSkeleton20261005/L_DM_CompleteCharacterSkeleton_Pilot_v001'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=['import', 'audit', 'stage', 'open', 'status'], required=True)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--nullrhi', action='store_true', help='Import only, without GPU rendering')
    args = parser.parse_args()
    if args.action == 'status':
        path = RUN / 'standard_candidate_registry.json'
        print(path.read_text(encoding='utf-8') if path.exists() else 'Not imported')
        return
    if args.nullrhi and args.action == 'open':
        parser.error('Visual review requires a rendering editor')
    runner = RUN / 'runner' / (args.action + '_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    runner.mkdir(parents=True, exist_ok=True)
    if args.launch:
        launch(runner, null_rhi=args.nullrhi)
    if args.action in ('import', 'audit'):
        script = SCRIPTS / 'ue_import_complete_character_skeleton_pilot_v1.py'
        variables = {'DM_COMPLETE_CHARACTER_MANIFEST': str(MANIFEST)}
        if args.action == 'audit':
            variables['DM_COMPLETE_CHARACTER_AUDIT_ONLY'] = True
        command = 'import runpy; runpy.run_path(' + repr(str(script)) + ',init_globals=' + repr(variables) + '); print("Complete-character import returned")'
    elif args.action == 'stage':
        script = SCRIPTS / 'ue_stage_complete_character_skeleton_pilot_v1.py'
        variables = {'DM_COMPLETE_CHARACTER_STAGE': True}
        command = 'import runpy; runpy.run_path(' + repr(str(script)) + ',init_globals=' + repr(variables) + ')'
    else:
        command = 'import unreal; levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Save current level changes first"; assert levels.load_level(' + repr(LEVEL) + '); unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(480,0,130),unreal.Rotator(yaw=180)); print("Complete-character review level opened")'
    result = remote(command, runner, args.action, timeout=1200)
    print(json.dumps({'success': result['command_result']['success'], 'action': args.action, 'runner': str(runner)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
