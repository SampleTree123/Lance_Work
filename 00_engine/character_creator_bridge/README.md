# Character Creator Local Bridge

This directory contains the offline automation boundary between an external
agent and Character Creator 5.

## Components

| Path | Purpose |
|------|---------|
| `bridge_config.json` | Local paths, protocol version, polling, lease, and path allowlists |
| `protocol_v1.md` | Request, result, heartbeat, validation, and recovery contract |
| `plugin/main.py` | CC5 `OpenPlugin` entry point and single-consumer worker |
| `cc_bridge_client.py` | External CLI for health checks, submission, and waiting |
| `cc_undo_dialog_guard.ps1` | Opt-in exact-match handler for the known CC Undo Manager warning |
| `install_bridge.ps1` | Controlled installer for the CC5 `Bin64/OpenPlugin` directory |

## Intended flow

```text
agent/client -> atomic request JSON -> CC5 plugin -> RLPy command
agent/client <- terminal result JSON <- CC5 plugin
```

The bridge starts automatically with CC after installation. It also adds a
small Plugins menu for status, start, and stop operations. No bridge command
accepts arbitrary Python source.

## Initial validation sequence

1. Install the plugin.
2. Restart Character Creator 5.
3. Wait for a fresh heartbeat.
4. Submit `ping` and verify a successful terminal result.
5. Submit `scene_summary` and verify RLPy access.
6. Submit one `apply_face_recipe_preview` job and inspect its artifacts.
7. Submit `validate_bodyfit_library` to load each hash-locked canonical
   BodyFit project and compare its Body/Junction fingerprint with the library.

For unattended validation, `validate-bodies` accepts
`--auto-dismiss-undo-warning`. The external guard only invokes `OK` when the
CC process ID, dialog title, complete warning text, and button label all match
the known Undo Manager restart warning. Every dismissal is written to
`outputs/character_creator_bridge/dialog_guard/<job-id>.jsonl`. Other dialogs
are observed but never closed.

## BodyFit source projects

`cc_body_preset_library_v1.json` is the runtime source for the eight adult
BodyFit presets. Each hash-locked `.ccProject` is the canonical runtime body
entry point. The library stores body and junction Morph vectors for drift
detection and auditing, not for rebuilding the body from a neutral avatar.
After loading a BodyFit project, the selected primary head preset and face
identity recipe replace its initial face state.

The bridge remains `prototype-only` until all eight source projects pass the
body, face, eye, and interrupted-job recovery checks after a clean CC restart.
