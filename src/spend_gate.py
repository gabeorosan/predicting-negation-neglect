"""Spend gate: refuses OpenRouter requests and new Tinker clients unless Gabriel's cockpit pane allows them.

The cockpit mod (Claude Code, ~/.claude/dev-mods/.../cockpit) writes ~/.claude/spend/allowance.json:

    {"openrouter": {"enabled": true, "cap": 1.0, "since": "2026-10-01T20:00:00Z", "baseline": 2.37},
     "tinker": {"enabled": false, "cap": 0.0, "since": null}}

A missing or unreadable file allows nothing. The pane turns a provider off by itself once its spend since `since`
reaches `cap` (OpenRouter from the key's usage counter, exact within a minute; Tinker from billing records, which
lag by hours). This module only reads the switch: an OpenRouter request checks it each time, a Tinker run checks it
when it creates its ServiceClient (a run already going is not stopped).

Loaded in every Python process of this repo's venv by .venv/lib/python3.12/site-packages/zz_spend_gate.pth, which
calls install(): a post-import hook patches openai's request methods and tinker.ServiceClient when those modules load.
"""

import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
import sys
from pathlib import Path

ALLOWANCE = Path.home() / ".claude" / "spend" / "allowance.json"


class SpendNotAllowed(RuntimeError):
    pass


def allowed(provider: str) -> tuple[bool, str]:
    try:
        a = json.loads(ALLOWANCE.read_text()).get(provider) or {}
    except (OSError, ValueError):
        return False, f"no allowance file at {ALLOWANCE}"
    if not a.get("enabled"):
        return False, f"{provider} spend is switched off in the cockpit pane"
    return True, ""


def check(provider: str) -> None:
    if os.environ.get("SPEND_GATE_DRY") == "1":
        return
    ok, why = allowed(provider)
    if not ok:
        raise SpendNotAllowed(f"Blocked by the spend gate: {why}. Gabriel turns it on in the cockpit pane.")


def _is_openrouter(client) -> bool:
    return "openrouter.ai" in str(getattr(client, "base_url", "") or "")


def _patch_openai(mod) -> None:
    base = sys.modules.get("openai._base_client")
    if base is None:
        return
    for cls_name in ("SyncAPIClient", "AsyncAPIClient"):
        cls = getattr(base, cls_name, None)
        if cls is None or getattr(cls, "_spend_gate", False):
            continue
        orig = cls.request
        if cls_name == "AsyncAPIClient":

            async def request(self, *a, __orig=orig, **k):
                if _is_openrouter(self):
                    check("openrouter")
                return await __orig(self, *a, **k)

        else:

            def request(self, *a, __orig=orig, **k):
                if _is_openrouter(self):
                    check("openrouter")
                return __orig(self, *a, **k)

        cls.request = request
        cls._spend_gate = True


def _patch_tinker(mod) -> None:
    cls = getattr(mod, "ServiceClient", None)
    if cls is None or getattr(cls, "_spend_gate", False):
        return
    orig = cls.__init__

    def __init__(self, *a, **k):
        check("tinker")
        orig(self, *a, **k)

    cls.__init__ = __init__
    cls._spend_gate = True


PATCHES = {"openai": _patch_openai, "tinker": _patch_tinker}


class _Finder(importlib.abc.MetaPathFinder):
    """Finds openai and tinker through the ordinary path finder and patches each module right after it executes."""

    def find_spec(self, name, path, target=None):
        if name not in PATCHES:
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or spec.loader is None:
            return None
        loader = spec.loader
        orig_exec = loader.exec_module

        def exec_module(module, __orig=orig_exec, __name=name):
            __orig(module)
            PATCHES[__name](module)

        loader.exec_module = exec_module
        return spec


def install() -> None:
    if getattr(sys, "_spend_gate_installed", False):
        return
    sys._spend_gate_installed = True
    for name, patch in PATCHES.items():
        if name in sys.modules:
            patch(sys.modules[name])
    sys.meta_path.insert(0, _Finder())
