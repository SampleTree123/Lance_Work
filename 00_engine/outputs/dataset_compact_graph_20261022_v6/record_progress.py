"""Update only this independent offline branch's active-work pointer."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
state_path=REPO/'20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATE.json'
state=json.loads(state_path.read_text(encoding='utf-8-sig'))
branch=state['dataset_design_branch_20261021']
branch['active_optimization']={
    'run_root':'%OUTPUT_ROOT%/dataset_compact_graph_20261022_v6/',
    'status':'in_progress',
    'goal':'%OUTPUT_ROOT%/dataset_compact_graph_20261022_v6/GOAL.md',
    'started_at':'2026-10-22T00:45:58+08:00',
    'deadline':'2026-10-22T05:45:58+08:00',
    'focus':['fewer_nodes','initial_camera_distribution','single_garment_slot_distribution'],
    'previous_candidate_retained':'%OUTPUT_ROOT%/dataset_balanced_graph_20261022_v5/candidate_c_seed1/',
    'new_candidate_selected':False,
    'ue_changed':False,
}
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Updated dataset branch active optimization pointer; previous candidate retained.')
