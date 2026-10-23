"""Reuse unchanged reference semantics on the actual v3 candidate; no media calls."""
import json
from pathlib import Path
from resample_local import V1, ROOT
from plan_references import Planner, pin


def main():
    planner = Planner(ROOT / 'linked_complete', 20261021)
    contract = ROOT.parents[2] / '20_planning/data_design/character_creator/full_process/technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md'
    planner.inputs += [pin(contract), pin(__file__)]
    summary = planner.run()
    print(json.dumps({k:v for k,v in summary.items() if k not in ['unfrozen','split_counts']}, ensure_ascii=False))


if __name__ == '__main__':main()
