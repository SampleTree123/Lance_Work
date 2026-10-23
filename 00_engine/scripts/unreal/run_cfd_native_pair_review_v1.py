"""Existing Chinese fixed-slot panel, redirected to the isolated native CFD pair."""
from pathlib import Path
import run_cfd_native_pair_transfer_v1 as transfer
import run_complete_character_slot_review_v1 as panel
from cfd_native_pair_ue_target_v1 import select_panel_node

panel.ROOT = transfer.RUN / 'runtime'
panel.WORKER = Path(__file__).resolve().with_name('ue_cfd_native_pair_review_v1.py')
panel.LEVEL = transfer.LEVEL
panel.previous.ROOT = transfer.RUN / 'runtime/controller'
panel.previous.LEVEL = transfer.LEVEL
panel.select_node = select_panel_node


if __name__ == '__main__':
    panel.entrypoint()
