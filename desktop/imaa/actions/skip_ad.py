"""Native "Skip ad" fallback: find a visible *Skip* button in the foreground window and press it.

Used when the browser helper is not connected. Windows uses UI Automation; other platforms rely on the
browser helper.
"""

from __future__ import annotations

import logging
import re
import sys

log = logging.getLogger(__name__)

SKIP_RE = re.compile(
    r"^\s*(skip(\s+ads?)?|skip\s+ad\s*now|تخط[يّ]+(\s+الإعلان(ات)?)?|تجاوز(\s+الإعلان)?|passer(\s+l['’]annonce)?|"
    r"omitir(\s+anuncios?)?|(werbung\s+)?überspringen|pular(\s+anúncios?)?|salta(\s+annunci)?|reklam[ıi]\s+geç|atla)"
    r"\s*[›>»▶]*\s*$",
    re.IGNORECASE,
)


def matches(text: str) -> bool:
    return bool(text) and bool(SKIP_RE.match(text.strip()))


def skip_native() -> bool:
    if sys.platform == "win32":
        try:
            return _skip_windows()
        except Exception:
            log.exception("UI Automation skip failed")
    return False


def _skip_windows() -> bool:
    import ctypes

    import comtypes
    import comtypes.client

    comtypes.CoInitialize()
    try:
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen.UIAutomationClient import (  # type: ignore[import-not-found]
            CUIAutomation,
            IUIAutomation,
            IUIAutomationInvokePattern,
        )

        uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False
        root = uia.ElementFromHandle(hwnd)
        UIA_ControlTypePropertyId, UIA_ButtonControlTypeId = 30003, 50000
        TreeScope_Descendants, UIA_InvokePatternId = 4, 10000
        cond = uia.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_ButtonControlTypeId)
        found = root.FindAll(TreeScope_Descendants, cond)
        for i in range(found.Length):
            el = found.GetElement(i)
            if not matches(el.CurrentName or "") or el.CurrentIsOffscreen:
                continue
            try:
                pattern = el.GetCurrentPattern(UIA_InvokePatternId)
                pattern.QueryInterface(IUIAutomationInvokePattern).Invoke()
                return True
            except comtypes.COMError:
                rect = el.CurrentBoundingRectangle
                from imaa.actions import keys

                old = keys.mouse_position()
                keys.move_to((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
                keys.click("left")
                keys.move_to(*old)
                return True
        return False
    finally:
        comtypes.CoUninitialize()
