---
name: character-factory-doc-maintenance
description: Maintain the DataMake Character Factory documentation after workflow, implementation, validation, status, plan, registry, or output changes. Use when recording project progress, closing a stage, changing current work, reconciling docs with code, or preparing a documentation audit.
---

# Character Factory Documentation Maintenance

Maintain the documentation as an operating system for the project, not as a conversation log. Work from verified repository and runtime evidence; do not promote an experiment, file existence, or a successful command to an accepted capability without the required Gate evidence.

The versioned source under `%LANCE_ROOT%/.codex/skills/character-factory-doc-maintenance/` is authoritative. A workspace-level copy may be installed for discovery; when the two differ, update the versioned source first and then resync the installed copy.

## Locate The Authority

Find `%LANCE_ROOT%` and use:

```text
20_planning/data_design/character_creator/full_process/README.md
20_planning/data_design/character_creator/full_process/GOVERNANCE.md
20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATE.json
```

Read the Master, Governance, current project status, current plan, affected `WF-*`, its Technical implementation, and its Workflow/Batch status before editing. Follow links from the active tree; do not use rebuild snapshots or legacy trees as current authority.

Also use the independent [Registry index](../../../20_planning/data_design/character_creator/full_process/registry/README.md) when a machine authority or owner changes. Reference explains terms and paths; Registry only supports reverse lookup.

## Decide What Must Change

Update only owners of changed facts:

- Long-term sequence, inputs, outputs, or Gate: Workflow; create an ADR when this changes architecture or semantics.
- Stable validation ID, trigger, evidence, pass/fail, invalidation, or result owner: Validation subsystem; implementation command remains in the owning Technical document.
- Stable output ID, storage class, Run Root, Manifest, promotion, or retention semantics: Output subsystem; production command and domain fields remain in the owning Technical document.
- Scripts, commands, field-level configuration, domain output structure, validation implementation, or recovery: owning Technical document.
- Current machine authority or reverse lookup mapping: Registry index plus the owning Technical document.
- Current capability, current phase, active batch, blocker, or unique next action: Status and `PROJECT_STATE.json`.
- Future requirement or acceptance condition: current Plan requirement.
- Completed accepted fact: Workflow/Batch Status plus Milestone; move a fully complete plan to completed history.
- New output: producing Technical document and an ownership rule for any new output category; add a precise retention rule only when it must be kept, then rebuild Output Inventory.

Do not duplicate dynamic counts in Master, root READMEs, Workflow, and code READMEs. Keep exact batch values in Batch Status and machine configurations.

## Independent Closure First

Treat Workflow, Validation, Output, Technical, Status, Plan, History, Decisions, Reference, Registry, Governance, Templates, and Master as independently auditable subsystems. For every affected subsystem:

1. verify its own role, index, required fields, lifecycle/status semantics, and internal consistency;
2. fix that subsystem without relying on another document to fill its missing definition;
3. record a concrete independent check result.

Only after all affected subsystems pass independently, verify explicit cross-layer contracts such as `WF-* -> VAL-* -> Technical -> OUT-* -> Status`, `Plan Requirement -> Workflow Status/Evidence`, `ADR -> affected definitions`, and `Master -> subsystem entry`. Do not combine unrelated repairs merely to make a global link audit pass.

## Update Order

1. Inspect Git changes, relevant code/configuration, and machine evidence.
2. Identify every affected subsystem and update each owning document independently.
3. Update the owning Technical implementation, then its Script Catalog entry when code ownership changed.
4. Update affected Workflow/Batch Status and exact current output/evidence pointers.
5. Update the current Plan requirement state and evidence links when implementation progress changed.
6. Update `PROJECT_STATUS.md` and `PROJECT_STATE.json` when the active phase, current plan, blockers, validations, outputs, or next action changed.
7. Add a Milestone or ADR only when its criteria are met; move fully completed plans to History.
8. Check only the explicit cross-layer contracts affected by the change.
9. Rebuild machine catalogs and run the full audit.

If evidence is incomplete, write `pending`, `partial`, or the concrete blocker. Do not write `accepted` or `completed` optimistically.

## Script And Output Ownership

Every active script needs a lifecycle and Technical owner. Every output scope needs a producing Technical owner, while retention remains a separate reviewed decision. Rebuild from `%LANCE_ROOT%`:

The Character Factory Script Catalog covers `00_engine/` and `20_planning/implementation/`; `10_research/model_experiments/` is a separate downstream research scope. Every `production` script must be named by its owner Technical document, and catalog hashes must match the working tree.

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
```

Treat `unclassified` outputs as protected. Never delete them merely because they are old. Only reviewed `superseded` or `disposable` paths may become cleanup candidates, and only after replacement evidence and manifests are checked.

## Validation

Run:

```powershell
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
python -m pytest `
  00_engine/scripts/documentation/tests `
  00_engine/scripts/dataset/tests `
  00_engine/scripts/unreal/tests -q
```

Require every independent subsystem check to pass before accepting the cross-layer result. Fix broken navigation, stale catalog entries, plan/status disagreement, missing owners, invalid `VAL-*`/`OUT-*` mappings, and invalid retention references before reporting completion. If a test depends on CC, UE, PySide2, local binary assets, or a server that is unavailable, record the exact skipped boundary instead of claiming a full pass.

## Safety Boundaries

- Never edit `rebuild_reference_*`, legacy snapshots, or their manifests.
- Never revert unrelated worktree changes.
- Never delete outputs, UE assets, CC projects, or legacy documentation as part of routine maintenance without an explicit reviewed cleanup decision.
- Keep the Master human-readable. Do not commit generated line-by-line link traces into the active tree.
- During authorized execution, preserve one and only one `current` primary plan. Only after the completed plan is moved to History and no next task is authorized, record `PROJECT_STATE.project_phase=idle_after_completed_plan` with an explicit `current_plan_id=null`; this state requires zero current plans. Multiple current plans are always invalid. Do not promote queued work merely to fill the index or pass an audit.

Finish with a concise report naming changed authorities, current plan/workflow, audit results, skipped checks, and any unresolved discrepancy.
