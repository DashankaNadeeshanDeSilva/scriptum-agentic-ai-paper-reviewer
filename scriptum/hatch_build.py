"""Custom Hatch build hook.

Conditionally includes ``frontend/out/`` in the wheel when the directory
exists (built via ``NEXT_OUTPUT=export npm run build``).  When absent the
wheel still builds — the CLI prompts the user to build or run the dev server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        frontend_out = Path(self.root) / "frontend" / "out"
        if frontend_out.is_dir():
            build_data["force_include"][str(frontend_out)] = "scriptum_ai/frontend/out"
