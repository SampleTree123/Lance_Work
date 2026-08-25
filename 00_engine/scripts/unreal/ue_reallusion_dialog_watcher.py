#!/usr/bin/env python3
"""Confirm the two known Reallusion/FBX modal dialogs by keyboard.

This helper intentionally matches exact dialog title fragments and never uses
absolute screen coordinates. Run it only with the FullReference importer,
which presets the factory FBX UI before either dialog is confirmed.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import time


user32 = ctypes.WinDLL("user32", use_last_error=True)

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
user32.EnumChildWindows.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindowAsync.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL
user32.keybd_event.argtypes = [
    wintypes.BYTE,
    wintypes.BYTE,
    wintypes.DWORD,
    ctypes.c_size_t,
]
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

SW_SHOW = 5
VK_TAB = 0x09
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101


def window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def enumerate_windows() -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    seen: set[int] = set()

    def add(hwnd: int) -> None:
        value = int(hwnd)
        if value in seen:
            return
        seen.add(value)
        rows.append((value, window_pid(hwnd), window_text(hwnd)))

    @WNDENUMPROC
    def child_callback(hwnd: int, _lparam: int) -> bool:
        add(hwnd)
        return True

    @WNDENUMPROC
    def top_callback(hwnd: int, _lparam: int) -> bool:
        add(hwnd)
        user32.EnumChildWindows(hwnd, child_callback, 0)
        return True

    user32.EnumWindows(top_callback, 0)
    return rows


def find_project_pid(project_title: str) -> int | None:
    matches = {
        pid
        for _hwnd, pid, title in enumerate_windows()
        if project_title.lower() in title.lower()
        and "live coding" not in title.lower()
    }
    if len(matches) == 1:
        return next(iter(matches))
    return None


def send_key(hwnd: int, vk: int) -> None:
    if not user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0):
        raise RuntimeError(f"Unable to post key down {vk} to dialog {hwnd}")
    time.sleep(0.06)
    if not user32.PostMessageW(hwnd, WM_KEYUP, vk, 0):
        raise RuntimeError(f"Unable to post key up {vk} to dialog {hwnd}")
    time.sleep(0.12)


def focus_window(hwnd: int) -> None:
    user32.ShowWindowAsync(hwnd, SW_SHOW)
    foreground = user32.GetForegroundWindow()
    foreground_pid = wintypes.DWORD()
    foreground_thread = user32.GetWindowThreadProcessId(
        foreground, ctypes.byref(foreground_pid)
    )
    target_pid = wintypes.DWORD()
    target_thread = user32.GetWindowThreadProcessId(
        hwnd, ctypes.byref(target_pid)
    )
    current_thread = kernel32.GetCurrentThreadId()
    attached_threads: list[int] = []
    try:
        for thread_id in {foreground_thread, target_thread}:
            if thread_id and thread_id != current_thread:
                if user32.AttachThreadInput(current_thread, thread_id, True):
                    attached_threads.append(thread_id)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        for thread_id in reversed(attached_threads):
            user32.AttachThreadInput(current_thread, thread_id, False)
    if user32.GetForegroundWindow() != hwnd:
        raise RuntimeError(f"Unable to foreground dialog handle {hwnd}")
    time.sleep(0.35)


def confirm_auto_setup(hwnd: int) -> None:
    # Fresh Auto Setup dialogs have no keyboard focus. The stable order is:
    # Auto Setup checkbox, Control Rig checkbox, Online Manual, OK.
    for _ in range(4):
        send_key(hwnd, VK_TAB)
    send_key(hwnd, VK_RETURN)


def confirm_fbx_import(hwnd: int) -> None:
    # The FBX dialog opens with "Import All" as its focused default action.
    send_key(hwnd, VK_RETURN)


def is_auto_setup_title(title: str) -> bool:
    lowered = title.strip().lower()
    return "auto setup" in lowered and "import options" in lowered


def is_fbx_import_title(title: str) -> bool:
    # Localized Slate titles can be returned with replacement characters by
    # GetWindowTextW. The controlled import has only one FBX-prefixed modal.
    return title.strip().lower().startswith("fbx")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-title", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deadline = time.monotonic() + args.timeout_seconds
    pid = None
    events: list[dict] = []
    handled_auto_setup: set[int] = set()
    handled_fbx: set[int] = set()
    pending_auto_setup: dict[int, dict] = {}
    pending_fbx: dict[int, dict] = {}

    while time.monotonic() < deadline:
        if pid is None:
            dialog_pids = {
                owner_pid
                for _hwnd, owner_pid, title in enumerate_windows()
                if is_auto_setup_title(title) or is_fbx_import_title(title)
            }
            if len(dialog_pids) == 1:
                pid = next(iter(dialog_pids))
        if pid is None:
            pid = find_project_pid(args.project_title)
            if pid is None:
                time.sleep(0.25)
                continue

        now = time.monotonic()
        windows = enumerate_windows()
        current_handles = {hwnd for hwnd, _owner_pid, _title in windows}

        for pending, handled, dialog_name in (
            (pending_auto_setup, handled_auto_setup, "auto_setup"),
            (pending_fbx, handled_fbx, "fbx_import"),
        ):
            for hwnd, state in list(pending.items()):
                if hwnd in current_handles:
                    continue
                handled.add(hwnd)
                events.append(
                    {
                        "dialog": dialog_name,
                        "handle": hwnd,
                        "title": state["title"],
                        "attempts": state["attempts"],
                        "closed": True,
                    }
                )
                del pending[hwnd]

        for hwnd, owner_pid, title in windows:
            if owner_pid != pid or not title:
                continue
            if is_auto_setup_title(title) and hwnd not in handled_auto_setup:
                state = pending_auto_setup.setdefault(
                    hwnd,
                    {"title": title, "attempts": 0, "last_attempt": 0.0},
                )
                if now - state["last_attempt"] >= 1.0:
                    confirm_auto_setup(hwnd)
                    state["attempts"] += 1
                    state["last_attempt"] = now
            elif is_fbx_import_title(title) and hwnd not in handled_fbx:
                state = pending_fbx.setdefault(
                    hwnd,
                    {"title": title, "attempts": 0, "last_attempt": 0.0},
                )
                if now - state["last_attempt"] >= 1.0:
                    confirm_fbx_import(hwnd)
                    state["attempts"] += 1
                    state["last_attempt"] = now

        if handled_auto_setup and handled_fbx:
            print(json.dumps({"success": True, "pid": pid, "events": events}, ensure_ascii=False))
            return 0
        time.sleep(0.25)

    print(
        json.dumps(
            {
                "success": False,
                "pid": pid,
                "events": events,
                "error": "dialog watcher timed out",
            },
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
