from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "run_first_batch_local_sample_render.py"
SPEC = importlib.util.spec_from_file_location(
    "run_first_batch_local_sample_render", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
with mock.patch.dict(sys.modules, {"imageio_ffmpeg": mock.Mock()}):
    SPEC.loader.exec_module(MODULE)


class RenderOffscreenTests(unittest.TestCase):
    def test_headless_linux_defaults_to_offscreen(self) -> None:
        self.assertTrue(
            MODULE.resolve_render_offscreen(
                None, platform_name="linux", display=""
            )
        )

    def test_linux_display_and_windows_default_to_visible(self) -> None:
        self.assertFalse(
            MODULE.resolve_render_offscreen(
                None, platform_name="linux", display=":97"
            )
        )
        self.assertFalse(
            MODULE.resolve_render_offscreen(
                None, platform_name="win32", display=""
            )
        )

    def test_explicit_override_wins(self) -> None:
        self.assertFalse(
            MODULE.resolve_render_offscreen(
                False, platform_name="linux", display=""
            )
        )
        self.assertTrue(
            MODULE.resolve_render_offscreen(
                True, platform_name="win32", display=""
            )
        )


class FfmpegResolutionTests(unittest.TestCase):
    def test_explicit_executable_wins(self) -> None:
        with (
            mock.patch.dict(os.environ, {"DM_FFMPEG_EXE": sys.executable}),
            mock.patch.object(MODULE.shutil, "which") as which,
        ):
            self.assertEqual(MODULE.resolve_ffmpeg_exe(), str(Path(sys.executable).resolve()))
        which.assert_not_called()

    def test_invalid_explicit_executable_fails(self) -> None:
        with mock.patch.dict(
            os.environ, {"DM_FFMPEG_EXE": "/missing/dm-ffmpeg"}
        ):
            with self.assertRaisesRegex(RuntimeError, "not executable"):
                MODULE.resolve_ffmpeg_exe()

    def test_system_ffmpeg_precedes_imageio(self) -> None:
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/ffmpeg"),
        ):
            self.assertEqual(MODULE.resolve_ffmpeg_exe(), "/usr/bin/ffmpeg")
        MODULE.imageio_ffmpeg.get_ffmpeg_exe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
