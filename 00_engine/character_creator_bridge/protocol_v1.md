# Character Creator Bridge Protocol v1

The bridge is a local, offline, single-consumer file queue. It does not open a
TCP port and it never evaluates Python supplied by a client.

## Runtime layout

The configured `runtime_root` contains:

```text
inbox/                 atomically published requests waiting for CC
processing/            the request currently claimed by CC
completed_requests/    original requests retained after success
failed_requests/       original requests retained after failure
results/               one terminal result JSON per job ID
state/heartbeat.json   current plugin lease and liveness
logs/bridge.jsonl      append-only plugin events
artifacts/             command outputs created by CC
```

Writers create a temporary file in the destination directory, flush and fsync
it, and publish it with `os.replace`. CC claims a request using another atomic
rename. A partially written JSON file is therefore never visible as a job.

## Request

Filename: `<job_id>.json`

```json
{
  "protocol_version": 1,
  "job_id": "20260721T173000000000Z_a1b2c3d4",
  "created_at": "2026-07-21T17:30:00+08:00",
  "command": "ping",
  "payload": {},
  "client": {
    "name": "cc_bridge_client",
    "version": "0.1.0"
  }
}
```

`job_id` must match `[A-Za-z0-9][A-Za-z0-9_.-]{7,127}`. Duplicate IDs are
idempotent: if a terminal result already exists, the command is not executed
again.

## Result

Filename: `results/<job_id>.json`

```json
{
  "protocol_version": 1,
  "job_id": "20260721T173000000000Z_a1b2c3d4",
  "command": "ping",
  "status": "succeeded",
  "plugin_version": "0.1.0",
  "instance_id": "...",
  "started_at": "...",
  "finished_at": "...",
  "result": {},
  "error": null
}
```

Terminal statuses are `succeeded`, `failed`, and `rejected`. Failures include
an exception type, message, and local traceback. If a duplicate request arrives
after a terminal result exists, CC retains that original result, archives the
duplicate request with a suffix, and does not execute it again.

## Heartbeat and lease

`state/heartbeat.json` is replaced at the configured heartbeat interval. It
contains the plugin instance ID, PID, state, active job ID, startup time, and
last update. A second plugin instance does not start while a different fresh
lease exists. A stale heartbeat older than `active_lease_seconds` can be
replaced after CC or the plugin has stopped.

The client considers the bridge ready only when:

- the heartbeat parses successfully;
- `state` is `idle` or `busy`;
- `updated_at` is within the lease interval;
- `protocol_version` matches.

## Commands

### `ping`

Read-only liveness test. Payload must be empty.

### `scene_summary`

Read-only RLPy test. Returns current avatar count and names.

### `apply_face_recipe_preview`

Loads one generated face recipe on the matching neutral base and writes its
left/front/right previews plus morph validation reports.

Required payload:

```json
{
  "recipe_file": "D:\\UE\\...\\face_recipes.json",
  "recipe_id": "MFACE_000001",
  "output_dir": "D:\\UE\\...\\artifacts\\MFACE_000001",
  "confirm_scene_replace": true
}
```

Input and output paths must resolve inside the roots allowed by
`bridge_config.json`. The explicit scene-replacement flag is required.

### `validate_bodyfit_library`

Loads the trusted BodyFit parameter library, compares each selected source
project with its stored body/junction vector, rebuilds the BodyFit on the clean
sex-matched neutral base, and writes source/reconstructed previews and Morph
validation reports.

Required payload:

```json
{
  "library_file": "D:\\UE\\...\\cc_body_preset_library_v1.json",
  "output_dir": "D:\\UE\\...\\artifacts\\bodyfit_validation",
  "confirm_scene_replace": true
}
```

Optional `preset_ids` is a non-empty list of BodyFit IDs. If omitted, all
presets in the library are validated. A successful result requires exact
body/junction reconstruction within the configured numeric tolerance and no
change to the clean base's face or unowned Morph groups.

## Recovery rules

- On startup, orphaned files in `processing` receive a failed result describing
  interruption by a previous plugin instance, then move to `failed_requests`.
- A malformed, oversized, unsupported, or path-escaping request is rejected.
- Exactly one job is executed at a time on CC's UI thread.
- Requests and terminal results are retained; automatic destructive cleanup is
  intentionally omitted from v1.
