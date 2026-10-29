"""macOS 前台激活辅助。

Tk 的 focus_force() 只影响 Tk 内部焦点，不会让应用成为 macOS 前台应用。
应用处于非激活状态时，第一次点击只会激活窗口而不会触发控件，表现为
"按钮点一两下没反应"。这里通过 Objective-C 运行时显式激活自身。
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from typing import Any

_ACTIVATE = b"activate"
_ACTIVATE_IGNORING_OTHERS = b"activateIgnoringOtherApps:"
_RESPONDS_TO_SELECTOR = b"respondsToSelector:"


def _load_objc_runtime() -> ctypes.CDLL | None:
    for candidate in (ctypes.util.find_library("objc"), "/usr/lib/libobjc.A.dylib"):
        if not candidate:
            continue
        try:
            return ctypes.CDLL(candidate)
        except OSError:
            continue
    return None


def _query_shared_application() -> tuple[ctypes.CDLL, Any, int] | None:
    """返回 (libobjc, objc_msgSend, NSApplication 实例)，失败时返回 None。"""
    libobjc = _load_objc_runtime()
    if libobjc is None:
        return None
    try:
        libobjc.objc_getClass.restype = ctypes.c_void_p
        libobjc.objc_getClass.argtypes = [ctypes.c_char_p]
        libobjc.sel_registerName.restype = ctypes.c_void_p
        libobjc.sel_registerName.argtypes = [ctypes.c_char_p]

        app_class = libobjc.objc_getClass(b"NSApplication")
        if not app_class:
            return None

        send = libobjc.objc_msgSend
        send.restype = ctypes.c_void_p
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        shared_app = send(app_class, libobjc.sel_registerName(b"sharedApplication"))
        if not shared_app:
            return None
        return libobjc, send, shared_app
    except (AttributeError, ValueError):
        return None


def is_application_active() -> bool:
    """当前进程是否已是 macOS 前台应用。"""
    if sys.platform != "darwin":
        return False
    runtime = _query_shared_application()
    if runtime is None:
        return False
    libobjc, send, shared_app = runtime
    try:
        send.restype = ctypes.c_bool
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        return bool(send(shared_app, libobjc.sel_registerName(b"isActive")))
    except (AttributeError, ValueError):
        return False


def activate_application() -> None:
    """把当前进程激活为前台应用；非 macOS 或调用失败时静默返回。"""
    if sys.platform != "darwin":
        return
    runtime = _query_shared_application()
    if runtime is None:
        return
    libobjc, send, shared_app = runtime

    def responds(selector: bytes) -> bool:
        send.restype = ctypes.c_bool
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        result = send(
            shared_app,
            libobjc.sel_registerName(_RESPONDS_TO_SELECTOR),
            libobjc.sel_registerName(selector),
        )
        return bool(result)

    try:
        if responds(_ACTIVATE):
            send.restype = None
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            send(shared_app, libobjc.sel_registerName(_ACTIVATE))

        if responds(_ACTIVATE_IGNORING_OTHERS):
            send.restype = None
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool]
            send(shared_app, libobjc.sel_registerName(_ACTIVATE_IGNORING_OTHERS), True)
    except (AttributeError, ValueError):
        return
