# UE 5.8 Vulkan Cube Smoke

This isolated content-only project tests the lowest practical Linux pixel path:

- one engine-provided cube and floor;
- one camera and basic lights;
- Vulkan SM5 with Lumen, Nanite, VSM and ray tracing disabled;
- a packaged `HighResShot`, independent of MRQ and production plugins.

The tracked Python script regenerates the ignored `.umap`. The runner separates
environment capture, map generation, packaging and rendering so each stage has
its own logs and exit status.

Run from an allocated GPU node and keep one evidence root for all stages:

```bash
export RUN_ROOT="$PWD/00_engine/outputs/server_preflight/ue58_vulkan_cube_smoke/job${SLURM_JOB_ID}_manual"
bash 00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh environment
bash 00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh prepare
bash 00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh package
bash 00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh render
```

Generated packages, DDC, logs and images stay under `RUN_ROOT` and are ignored by
Git. A successful render must contain a non-empty `renders/cube_smoke_01.png`
and pass a visual non-black check.
Compatibility probes may set `PACKAGE_ROOT` to reuse an immutable package and
write each attempt to a new evidence root. `RENDER_CAPTURE=0`,
`RENDER_VALIDATION`, the Vulkan compatibility controls,
`RENDER_TRANSLUCENCY_LIGHTING_VOLUME`, `RENDER_PSO_PRECACHING`,
`RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED` and the tonemap diagnostic controls
are recorded in a per-attempt config file.
The runner invokes packaged `UnrealGame` directly so an outer timeout cannot
leave the launcher child running.

## Verified results: 2026-08-28

The first controlled run used Slurm job `117538` on node `GDS9B74`:

- NVIDIA H200, driver `565.57.01`, forced NVIDIA Vulkan ICD;
- UE `5.8.0-55116800`, Vulkan SM5, bindless and advanced UE5 rendering
  features disabled;
- map generation, cook and legacy Pak packaging passed;
- nine render probes all ended with RenderThread timeout and exit code `139`;
- validation repeatedly reported `VUID-vkCmdDraw-None-09600` for
  `FBlackTextureWithSRV` (`GENERAL` expected, `SHADER_READ_ONLY_OPTIMAL`
  observed);
- no probe produced a PNG, including probes without HighResShot and without
  the validation layer.

The complete evidence is under:

```text
00_engine/outputs/server_preflight/ue58_vulkan_cube_smoke/
  job117538_20260828_live01/
```

See its `REPORT.md` before re-running. This result proves that the original
UE 5.8/H200/565 environment is not a usable pixel-rendering baseline.

A follow-up runtime ablation is under
`job117538_20260828_compat_ab01/`. Disabling the translucency lighting volume
removed `RWAmbient1` but exposed a post-process LUT `RWOutputTexture` format
mismatch; disabling Dynamic Rendering did not change the failure chain.

The server-retained `Patches/` set was subsequently compiled with a source-complete UE
5.8 tree. The compatibility package includes typed buffer/texture clear, LUT,
light-grid/manual-fetch, breadcrumb, translucency and tonemap diagnostics. On
the 565.57.01 node it produced one valid but fully black PNG and later stalled
in `BasePass -> BasicShapeMaterial Cube`, so that path remains failed.

The same patched package was then run on Slurm job `117593`, node `8GS9B74`:

- NVIDIA H200, GPU UUID `GPU-aa8fcb15-176d-82d6-4453-4c11a49bfb7f`, driver
  `580.126.20`;
- the no-light control advanced 20 frames and exited cleanly;
- a point-lit map produced a visible `640x360` PNG;
- three additional independent processes each initialized in 2.47-3.40
  seconds, saved a PNG, advanced 20 frames and exited with code 0;
- all three 8166-byte PNGs have SHA-256
  `2dec100ddf33431f546a5a4f63cd8a4c352e610bce670eb87a83a6eb2f45633b`;
- the stability logs contain no GPU hang or RenderThread timeout; Validation
  was disabled for these three deterministic runs.

The retained three-run evidence is:

```text
00_engine/outputs/server_preflight/ue58_vulkan_cube_smoke/
  job117593_driver580_v28_point_three_capture/
```

This proves the H200 server can render UE 5.8 Vulkan pixels and establishes a
strong driver boundary between 565.57.01 and 580.126.20. It is not a complete
server production gate: the image is diagnostic quality, and the real project,
plugins, two-start stability and 10-node benchmark remain unverified.

`r.PSOPrecaching=1` can trigger a UE 5.8 counter ensure and about 100 seconds of
cold startup on both drivers. It was nonfatal on 580.126.20. The deterministic
three-run check used `r.PSOPrecaching=0`, which avoided the ensure and reduced
startup to a few seconds.

A separate `-vulkanvalidation=2` run under
`job117593_driver580_v29_point_validation/` also saved the same PNG and exited
0, but reported an `OutComputeTexture` storage format mismatch, a HighResShot
`FDummyViewport` image-layout mismatch and an undestroyed `SceneDepthZ` image at
device shutdown. The 580 path is render-capable, not yet validation-clean.

As approved on 2026-10-23, the engine source `.patch` bodies in `Patches/`
remain server-local and are excluded from public GitHub synchronization.
The archived patch [README](../../scripts/unreal/patches/ue58_vulkan_compatibility/README.md)
describes their provenance and the separate engine reproduction requirement.
