# First-Batch Dataset Tools

This directory contains deterministic builders for the first multi-round edit
dataset. Runtime assets remain in their owning CC/UE registries; these tools
only freeze logical references and generate portable manifests.

## Config graph builder

```powershell
python build_first_batch_config_graph_v1.py `
  --source first_batch_graph_source_20260820_v1.json `
  --output-dir ..\..\outputs\first_batch_dataset\graph_20260820_v1
```

The source manifest must already be `frozen`. Every asset needs a stable ID,
portable `source_ref`, SHA-256 lock, version, compatibility, and validated or
frozen status. Missing identities, outfits, scene bindings, cameras, lighting,
anchors, or expressions are hard failures.

Outputs:

- `assets.json`
- `required_exports.json`
- `nodes.jsonl`
- `edges.jsonl`
- `chains.jsonl`
- `render_jobs.jsonl`
- `build_report.json`

The current first-batch contract is 16 sparse FullReference Looks, six actions
per sex, four camera/expression states per compatible Look/action pair, and 384
unique render nodes. The default chain plan emits 4,000 deterministic 3--5
step chains with progressive, rollback, and closed-cycle classes.
