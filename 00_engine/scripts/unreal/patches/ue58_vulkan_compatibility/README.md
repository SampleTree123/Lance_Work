# UE 5.8 Vulkan compatibility patch archive

This directory preserves the eight source patches used during the H200 Vulkan
investigation. They were moved out of the disposable `UE58VulkanCubeSmoke`
project before storage cleanup on 2026-08-30.

The accepted first-batch render did not use an unmodified stock binary. Its
exact executable and launch profile are recorded in:

```text
00_engine/outputs/delivery/first_batch_candidate_20260830_v002/
  release_evidence/render_run/profile.json
```

The accepted profile is `h200_vulkan_sm6_580_tokyo_v1`, on NVIDIA H200 with
driver `580.126.20`. The recorded editor executable SHA-256 is:

```text
6047eecdd356c375af7e7d890fa5d6cf338dc6fa3f6e308c4012c7d3a9af904c
```

Do not blindly apply every patch to another UE tree. Several patches are
diagnostic, and the exact production behavior also depends on the frozen
command-line profile. Use `SERVER_EXECUTION.md` and the retained profile to
reconstruct or audit the engine before a new render batch.

## Public repository scope (2026-10-23)

The eight `.patch` bodies are retained on the server and excluded from the
public GitHub repository by the root `.gitignore`, with user approval.
This README and lightweight provenance remain versioned. A Git clone alone
does not include the engine source patches or reconstruct the historical
engine binary; retrieve those separately through an appropriately licensed
and access-controlled channel before reproducing that engine build.
